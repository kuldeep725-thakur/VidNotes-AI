import logging
import time
from typing import TypeVar

import httpx
from google import genai
from google.genai import errors, types
from pydantic import BaseModel

from app.core.config import get_settings
from app.core.errors import AppError, ExternalServiceError

logger = logging.getLogger(__name__)

SchemaT = TypeVar("SchemaT", bound=BaseModel)

# The SDK retries these statuses with exponential backoff before giving up.
_RETRYABLE_STATUS_CODES = [408, 429, 500, 502, 503, 504]
# After retries, these statuses make us try the fallback model instead.
_FALLBACK_STATUS_CODES = {404, 429, 500, 502, 503, 504}
# Models whose daily quota ran out are skipped for a while instead of being
# retried on every request. Maps model name -> time.monotonic() to retry at.
_QUOTA_PAUSE_SECONDS = 3600
_exhausted_models: dict[str, float] = {}


class GeminiClient:
    def __init__(self):
        settings = get_settings()
        if not settings.gemini_api_key:
            raise AppError("Gemini API key is missing. Add GEMINI_API_KEY to backend/.env.", 500)
        self._models = settings.gemini_models
        self._thinking = (
            types.ThinkingConfig(thinking_level=settings.gemini_thinking_level.upper())
            if settings.gemini_thinking_level
            else None
        )
        self._client = genai.Client(
            api_key=settings.gemini_api_key,
            http_options=types.HttpOptions(
                timeout=int(settings.gemini_timeout_seconds * 1000),
                retry_options=types.HttpRetryOptions(
                    attempts=settings.gemini_max_retries,
                    initial_delay=2.0,
                    max_delay=30.0,
                    http_status_codes=_RETRYABLE_STATUS_CODES,
                ),
            ),
        )

    def generate_text(self, prompt: str, system_instruction: str) -> str:
        response = self._generate(prompt, self._config(system_instruction))
        if not response.text:
            raise ExternalServiceError("Gemini returned an empty response. Please try again.")
        return response.text

    def generate_structured(self, prompt: str, system_instruction: str, schema: type[SchemaT]) -> SchemaT:
        config = self._config(system_instruction, response_mime_type="application/json", response_schema=schema)
        response = self._generate(prompt, config)
        if isinstance(response.parsed, schema):
            return response.parsed

        finish_reason = response.candidates[0].finish_reason if response.candidates else None
        logger.warning("Gemini returned unparseable output (finish reason: %s)", finish_reason)
        if finish_reason == types.FinishReason.MAX_TOKENS:
            raise ExternalServiceError("The AI response was too long and got cut off. Try fewer quiz questions.")
        raise ExternalServiceError("Gemini returned an incomplete response. Please try again.")

    def _config(self, system_instruction: str, **extra) -> types.GenerateContentConfig:
        return types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=0.3,
            thinking_config=self._thinking,
            **extra,
        )

    def _generate(self, prompt: str, config: types.GenerateContentConfig) -> types.GenerateContentResponse:
        available = [m for m in self._models if _exhausted_models.get(m, 0) <= time.monotonic()]
        if not available:
            raise ExternalServiceError(
                "The daily Gemini quota is used up for every configured model. Try again tomorrow, add more "
                "models to GEMINI_FALLBACK_MODELS, or use a paid API key.",
                429,
            )

        last_error: errors.APIError | None = None
        for model in available:
            try:
                return self._client.models.generate_content(model=model, contents=prompt, config=config)
            except errors.APIError as exc:
                logger.warning("Gemini model %s failed with %s: %s", model, exc.code, (exc.message or "")[:200])
                if exc.code not in _FALLBACK_STATUS_CODES:
                    raise self._error_for(exc) from exc
                if exc.code == 429 and "per day" in (exc.message or "").lower():
                    _exhausted_models[model] = time.monotonic() + _QUOTA_PAUSE_SECONDS
                last_error = exc
            except httpx.TimeoutException as exc:
                raise ExternalServiceError("Gemini did not respond in time. Please try again.", 504) from exc
            except httpx.HTTPError as exc:
                raise ExternalServiceError("Could not reach Gemini. Check your internet connection.") from exc
        raise self._error_for(last_error) from last_error

    def _error_for(self, exc: errors.APIError) -> AppError:
        message = (exc.message or "").lower()
        if exc.code in (401, 403) or "api key" in message:
            return ExternalServiceError("Gemini rejected the API key. Check GEMINI_API_KEY in backend/.env.")
        if exc.code == 404:
            return ExternalServiceError(
                "The configured Gemini model is not available. Set GEMINI_MODEL in backend/.env to a current model."
            )
        if exc.code == 429 and "per day" in message:
            return ExternalServiceError(
                "The daily Gemini quota for your API key is used up. Try again tomorrow, add more models to "
                "GEMINI_FALLBACK_MODELS, or use a paid API key.",
                429,
            )
        if exc.code == 429:
            return ExternalServiceError("Gemini rate limit reached. Please wait a minute and try again.", 429)
        if exc.code == 504:
            return ExternalServiceError("Gemini took too long to respond. Please try again.", 504)
        if exc.code >= 500:
            return ExternalServiceError("Gemini is busy or temporarily unavailable. Please try again shortly.", 503)
        return ExternalServiceError(f"Gemini request failed ({exc.code}).")
