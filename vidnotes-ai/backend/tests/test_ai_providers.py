"""Groq client and Gemini-to-Groq backup tests (no network)."""

import json

import httpx
import pytest

from app.core.errors import ExternalServiceError
from app.schemas.content import StudyPack, SummaryTopic
from app.services import groq_client
from app.services.ai_client import AIClient
from app.services.groq_client import GroqClient, strict_json_schema


def groq_response(content: str, finish_reason: str = "stop") -> httpx.Response:
    return httpx.Response(
        200, json={"choices": [{"message": {"role": "assistant", "content": content}, "finish_reason": finish_reason}]}
    )


def make_groq(handler) -> GroqClient:
    return GroqClient(transport=httpx.MockTransport(handler))


def test_strict_schema_meets_groq_rules():
    def check(node):
        if isinstance(node, dict):
            if node.get("type") == "object" and "properties" in node:
                assert node["additionalProperties"] is False
                assert sorted(node["required"]) == sorted(node["properties"])
            for value in node.values():
                check(value)
        elif isinstance(node, list):
            for item in node:
                check(item)

    schema = strict_json_schema(StudyPack)
    assert "$defs" in schema
    check(schema)


def test_groq_structured_request_and_parsing():
    def handler(request: httpx.Request):
        assert request.url.path == "/openai/v1/chat/completions"
        assert request.headers["authorization"] == "Bearer test-groq-key"
        payload = json.loads(request.content)
        assert payload["model"] == "openai/gpt-oss-120b"
        assert payload["reasoning_effort"] == "low"
        assert payload["messages"][0] == {"role": "system", "content": "rules"}
        assert payload["response_format"]["type"] == "json_schema"
        assert payload["response_format"]["json_schema"]["strict"] is True
        return groq_response(json.dumps({"title": "Neurons", "explanation": "Hold numbers."}))

    topic = make_groq(handler).generate_structured("prompt", "rules", SummaryTopic)
    assert topic == SummaryTopic(title="Neurons", explanation="Hold numbers.")


def test_groq_invalid_json_is_reported():
    with pytest.raises(ExternalServiceError, match="incomplete"):
        make_groq(lambda _r: groq_response('{"title": "x"}')).generate_structured("p", "s", SummaryTopic)


def test_groq_truncated_output_is_reported():
    with pytest.raises(ExternalServiceError, match="cut off"):
        make_groq(lambda _r: groq_response("{", finish_reason="length")).generate_text("p", "s")


@pytest.mark.parametrize(
    ("status", "message", "expected"),
    [
        (401, "Invalid API Key", "rejected the API key"),
        (404, "model not found", "is not available"),
        (413, "Request too large for model", "token-per-minute limit"),
        (429, "Rate limit reached", "rate limit"),
        (503, "Service Unavailable", "busy"),
    ],
)
def test_groq_errors(status, message, expected):
    body = {"error": {"message": message, "type": "invalid_request_error"}}
    with pytest.raises(ExternalServiceError, match=expected):
        make_groq(lambda _r: httpx.Response(status, json=body)).generate_text("p", "s")


class FakeClock:
    """Replaces time.monotonic/time.sleep so waits are recorded, not slept."""

    def __init__(self, monkeypatch):
        self.now = 0.0
        self.waits = []
        monkeypatch.setattr(groq_client.time, "monotonic", lambda: self.now)
        monkeypatch.setattr(groq_client.time, "sleep", self.sleep)

    def sleep(self, seconds):
        self.waits.append(seconds)
        self.now += seconds


def test_groq_waits_for_token_budget_after_rate_limit(monkeypatch):
    clock = FakeClock(monkeypatch)
    limited = httpx.Response(
        429,
        headers={"retry-after": "7", "x-ratelimit-reset-tokens": "36.5s"},
        json={"error": {"message": "tokens per minute"}},
    )
    responses = iter([limited, groq_response("hello")])
    assert make_groq(lambda _r: next(responses)).generate_text("p", "s") == "hello"
    assert clock.waits == [37.5]


def test_groq_paces_requests_when_budget_is_low(monkeypatch):
    clock = FakeClock(monkeypatch)
    low_budget = {"x-ratelimit-remaining-tokens": "1000", "x-ratelimit-limit-tokens": "8000",
                  "x-ratelimit-reset-tokens": "52.5s"}
    full_budget = {"x-ratelimit-remaining-tokens": "7000", "x-ratelimit-limit-tokens": "8000",
                   "x-ratelimit-reset-tokens": "1s"}
    responses = iter([groq_response("one"), groq_response("two"), groq_response("three")])
    headers = iter([low_budget, full_budget, full_budget])

    def handler(_request):
        response = next(responses)
        response.headers.update(next(headers))
        return response

    client = make_groq(handler)
    assert [client.generate_text("p", "s") for _ in range(3)] == ["one", "two", "three"]
    assert clock.waits == [53.5]


def test_groq_does_not_wait_for_long_limits(monkeypatch):
    monkeypatch.setattr(groq_client.time, "sleep", lambda _s: pytest.fail("should not wait"))
    body = {"error": {"message": "Rate limit reached on tokens per day (TPD)"}}
    response = httpx.Response(429, headers={"retry-after": "3600"}, json=body)
    with pytest.raises(ExternalServiceError, match="daily Groq limit"):
        make_groq(lambda _r: response).generate_text("p", "s")


def test_groq_gives_up_after_retries(monkeypatch):
    monkeypatch.setattr(groq_client.time, "sleep", lambda _s: None)
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(429, headers={"retry-after": "1"}, json={"error": {"message": "tokens per minute"}})

    with pytest.raises(ExternalServiceError, match="rate limit"):
        make_groq(handler).generate_text("p", "s")
    assert len(calls) == groq_client._RATE_LIMIT_RETRIES + 1


def test_groq_truncated_strict_json_is_explained():
    body = {"error": {"message": "max completion tokens reached before generating a valid document"}}
    with pytest.raises(ExternalServiceError, match="cut off"):
        make_groq(lambda _r: httpx.Response(400, json=body)).generate_structured("p", "s", SummaryTopic)


def test_parse_duration():
    assert groq_client._parse_duration("7.66s") == pytest.approx(7.66)
    assert groq_client._parse_duration("2m59.56s") == pytest.approx(179.56)
    assert groq_client._parse_duration("120ms") == pytest.approx(0.12)
    assert groq_client._parse_duration("") is None


class FakeProvider:
    def __init__(self, error: ExternalServiceError | None = None):
        self.error = error
        self.calls = 0

    def generate_text(self, prompt, system_instruction):
        self.calls += 1
        if self.error:
            raise self.error
        return "from fake"


def make_ai_client(gemini, groq) -> AIClient:
    client = AIClient.__new__(AIClient)
    client._gemini, client._groq = gemini, groq
    return client


@pytest.mark.parametrize("status", [429, 503, 504])
def test_groq_takes_over_when_gemini_is_unavailable(status):
    gemini, groq = FakeProvider(ExternalServiceError("Gemini quota used up", status)), FakeProvider()
    assert make_ai_client(gemini, groq).generate_text("p", "s") == "from fake"
    assert (gemini.calls, groq.calls) == (1, 1)


def test_gemini_is_used_when_it_works():
    gemini, groq = FakeProvider(), FakeProvider()
    make_ai_client(gemini, groq).generate_text("p", "s")
    assert (gemini.calls, groq.calls) == (1, 0)


def test_configuration_errors_are_not_hidden_by_backup():
    gemini, groq = FakeProvider(ExternalServiceError("Gemini rejected the API key", 502)), FakeProvider()
    with pytest.raises(ExternalServiceError, match="rejected the API key"):
        make_ai_client(gemini, groq).generate_text("p", "s")
    assert groq.calls == 0


def test_without_groq_key_gemini_error_is_reported():
    gemini = FakeProvider(ExternalServiceError("Gemini quota used up", 429))
    with pytest.raises(ExternalServiceError, match="quota"):
        make_ai_client(gemini, None).generate_text("p", "s")
