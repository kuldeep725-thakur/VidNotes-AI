"""Optional Groq backup provider (OpenAI-compatible chat completions API)."""

import logging
import re
import time
from typing import TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from app.core.config import get_settings
from app.core.errors import AppError, ExternalServiceError

logger = logging.getLogger(__name__)

SchemaT = TypeVar("SchemaT", bound=BaseModel)

# Free-tier Groq limits tokens per minute (TPM), and Groq shortens answers to
# fit whatever budget is left. So requests are paced: when less than half the
# minute's budget remains, the next request waits for it to refill.
_RATE_LIMIT_RETRIES = 3
_MAX_RETRY_WAIT_SECONDS = 60
_DURATION_PART = re.compile(r"(\d+(?:\.\d+)?)(ms|h|m|s)")
_SECONDS_PER_UNIT = {"ms": 0.001, "s": 1, "m": 60, "h": 3600}


def strict_json_schema(schema: type[BaseModel]) -> dict:
    """Pydantic JSON schema adapted to Groq's strict structured-output rules.

    Strict mode requires every property to be required and every object to
    set additionalProperties to false.
    """

    def tighten(node):
        if isinstance(node, dict):
            if node.get("type") == "object" and "properties" in node:
                node["additionalProperties"] = False
                node["required"] = list(node["properties"])
            for value in node.values():
                tighten(value)
        elif isinstance(node, list):
            for item in node:
                tighten(item)
        return node

    return tighten(schema.model_json_schema())


class GroqClient:
    def __init__(self, transport: httpx.BaseTransport | None = None):
        settings = get_settings()
        if not settings.groq_api_key:
            raise AppError("Groq API key is missing. Add GROQ_API_KEY to backend/.env.", 500)
        self._model = settings.groq_model
        self._reasoning_effort = settings.groq_reasoning_effort
        # `transport` lets tests replace the network with canned responses.
        self._client = httpx.Client(
            base_url=settings.groq_base_url,
            headers={"Authorization": f"Bearer {settings.groq_api_key}"},
            timeout=settings.groq_timeout_seconds,
            transport=transport,
        )
        self._paused_until = 0.0

    def generate_text(self, prompt: str, system_instruction: str) -> str:
        return self._complete(prompt, system_instruction)

    def generate_structured(self, prompt: str, system_instruction: str, schema: type[SchemaT]) -> SchemaT:
        response_format = {
            "type": "json_schema",
            "json_schema": {"name": schema.__name__, "strict": True, "schema": strict_json_schema(schema)},
        }
        content = self._complete(prompt, system_instruction, response_format=response_format)
        try:
            return schema.model_validate_json(content)
        except ValidationError as exc:
            logger.warning("Groq returned JSON that does not match %s: %s", schema.__name__, exc)
            raise ExternalServiceError("Groq returned an incomplete response. Please try again.") from exc

    def _complete(self, prompt: str, system_instruction: str, **extra) -> str:
        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.3,
            **extra,
        }
        if self._reasoning_effort:
            payload["reasoning_effort"] = self._reasoning_effort

        response = self._post_with_retry(payload)
        if response.status_code != 200:
            raise self._error_for(response)

        choice = response.json()["choices"][0]
        if choice.get("finish_reason") == "length":
            # On the free tier, input plus output must fit the per-minute token limit.
            raise ExternalServiceError(
                "Groq's answer was cut off by your Groq plan's token limit. On the free plan Groq can only "
                "take over from Gemini for shorter videos (about 10 minutes)."
            )
        content = choice["message"].get("content")
        if not content:
            raise ExternalServiceError("Groq returned an empty response. Please try again.")
        return content

    def _post_with_retry(self, payload: dict) -> httpx.Response:
        for attempt in range(_RATE_LIMIT_RETRIES + 1):
            delay = self._paused_until - time.monotonic()
            if delay > 0:
                logger.info("Waiting %.0f seconds for the Groq token budget to refill", delay)
                time.sleep(delay)
            try:
                response = self._client.post("/chat/completions", json=payload)
            except httpx.TimeoutException as exc:
                raise ExternalServiceError("Groq did not respond in time. Please try again.", 504) from exc
            except httpx.HTTPError as exc:
                raise ExternalServiceError("Could not reach Groq. Check your internet connection.") from exc

            refill = _token_refill_seconds(response)
            if refill is not None:
                self._paused_until = time.monotonic() + refill
            if response.status_code != 429 or refill is None or attempt == _RATE_LIMIT_RETRIES:
                return response
        return response

    def _error_for(self, response: httpx.Response) -> AppError:
        try:
            message = response.json()["error"]["message"]
        except (ValueError, KeyError, TypeError):
            message = response.text[:200]
        logger.warning("Groq API error %s: %s", response.status_code, message)
        code = response.status_code
        lowered = message.lower()

        if code in (401, 403):
            return ExternalServiceError("Groq rejected the API key. Check GROQ_API_KEY in backend/.env.")
        if code == 404:
            return ExternalServiceError(
                f"The Groq model '{self._model}' is not available. Set GROQ_MODEL in backend/.env to a current model."
            )
        # Free-tier Groq models allow only a few thousand tokens per minute, so a
        # long transcript can be larger than a single request is allowed to be.
        if "max completion tokens" in lowered:
            # Strict JSON mode reports an answer cut short by the token budget as a 400.
            return ExternalServiceError(
                "Groq's answer was cut off by your Groq plan's token limit. On the free plan Groq can only "
                "take over from Gemini for shorter videos (about 10 minutes)."
            )
        if code == 413 or "request too large" in lowered:
            return ExternalServiceError(
                "This request is larger than your Groq plan's token-per-minute limit. "
                "Groq can only take over for shorter videos on the free plan.",
                413,
            )
        if code == 429 and "per day" in lowered:
            return ExternalServiceError("The daily Groq limit for your API key is used up. Try again tomorrow.", 429)
        if code == 429:
            return ExternalServiceError("Groq rate limit reached. Please wait a minute and try again.", 429)
        if code >= 500 or code == 498:
            return ExternalServiceError("Groq is busy or temporarily unavailable. Please try again shortly.", 503)
        return ExternalServiceError(f"Groq request failed ({code}).")


def _token_refill_seconds(response: httpx.Response) -> float | None:
    """Seconds to wait before the next request, or None if no wait is needed.

    Returns a wait after a 429, or when less than half of the per-minute token
    budget is left. Waits longer than a minute (e.g. a daily limit) return None.
    """
    headers = response.headers
    remaining, limit = headers.get("x-ratelimit-remaining-tokens"), headers.get("x-ratelimit-limit-tokens")
    budget_low = remaining is not None and limit is not None and float(remaining) < float(limit) / 2
    if response.status_code != 429 and not budget_low:
        return None

    waits = [_parse_duration(headers.get("x-ratelimit-reset-tokens", ""))]
    try:
        waits.append(float(headers.get("retry-after", "")))
    except ValueError:
        pass
    wait = max((w for w in waits if w is not None), default=None)
    if wait is None or wait > _MAX_RETRY_WAIT_SECONDS:
        return None
    return wait + 1


def _parse_duration(value: str) -> float | None:
    """Parse Groq durations such as "7.66s", "2m59.56s" or "120ms"."""
    parts = _DURATION_PART.findall(value)
    return sum(float(number) * _SECONDS_PER_UNIT[unit] for number, unit in parts) if parts else None
