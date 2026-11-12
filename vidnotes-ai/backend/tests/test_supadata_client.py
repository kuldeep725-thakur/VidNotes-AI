"""Supadata client tests using canned responses shaped like the current API docs."""

import httpx
import pytest

from app.core.errors import AppError, ExternalServiceError
from app.services import supadata_client
from app.services.supadata_client import SupadataClient

VIDEO_ID = "dQw4w9WgXcQ"
CANONICAL_URL = f"https://www.youtube.com/watch?v={VIDEO_ID}"

METADATA_RESPONSE = {
    "platform": "youtube",
    "type": "video",
    "id": VIDEO_ID,
    "url": CANONICAL_URL,
    "title": "Rick Astley - Never Gonna Give You Up",
    "author": {"displayName": "Rick Astley", "avatarUrl": "https://yt3.ggpht.com/a"},
    "stats": {"views": 1, "likes": 1, "comments": None, "shares": None},
    "media": {"type": "video", "duration": 213, "thumbnailUrl": "https://i.ytimg.com/vi/x/maxresdefault.jpg"},
    "tags": [],
    "createdAt": "2009-10-25T00:00:00Z",
    "additionalData": {"channelId": "UC1"},
}

TRANSCRIPT_CONTENT = [
    {"text": "Never gonna give you up", "offset": 18000, "duration": 2000, "lang": "en"},
    {"text": "  ", "offset": 20000, "duration": 500, "lang": "en"},
    {"text": "never gonna let you down", "offset": 20500, "duration": 2000, "lang": "en"},
]


def make_client(handler) -> SupadataClient:
    return SupadataClient(transport=httpx.MockTransport(handler))


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    monkeypatch.setattr(supadata_client.time, "sleep", lambda _seconds: None)


def test_metadata_uses_unified_endpoint_and_parses_fields():
    def handler(request: httpx.Request):
        assert request.url.path == "/v1/metadata"
        assert request.url.params["url"] == CANONICAL_URL
        assert request.headers["x-api-key"] == "test-supadata-key"
        return httpx.Response(200, json=METADATA_RESPONSE)

    metadata = make_client(handler).get_metadata(VIDEO_ID)
    assert metadata.title == "Rick Astley - Never Gonna Give You Up"
    assert metadata.channel_name == "Rick Astley"
    assert metadata.duration_seconds == 213
    assert metadata.thumbnail_url == "https://i.ytimg.com/vi/x/maxresdefault.jpg"


def test_metadata_accepts_author_name_and_missing_media():
    body = {"title": None, "author": {"name": "Channel"}}
    metadata = make_client(lambda _r: httpx.Response(200, json=body)).get_metadata(VIDEO_ID)
    assert metadata.title == "Untitled video"
    assert metadata.channel_name == "Channel"
    assert metadata.duration_seconds is None
    assert metadata.thumbnail_url == f"https://i.ytimg.com/vi/{VIDEO_ID}/hqdefault.jpg"


def test_transcript_immediate_response():
    def handler(request: httpx.Request):
        assert request.url.path == "/v1/transcript"
        assert request.url.params["url"] == CANONICAL_URL
        assert request.url.params["mode"] == "auto"
        return httpx.Response(200, json={"content": TRANSCRIPT_CONTENT, "lang": "en", "availableLangs": ["en"]})

    transcript = make_client(handler).get_transcript(VIDEO_ID)
    assert transcript.language == "en"
    assert [s.text for s in transcript.segments] == ["Never gonna give you up", "never gonna let you down"]
    assert transcript.segments[0].start_seconds == 18.0


def test_transcript_async_job_is_polled_until_completed():
    job_states = iter(["queued", "active", "completed"])
    calls = []

    def handler(request: httpx.Request):
        calls.append(request.url.path)
        if request.url.path == "/v1/transcript":
            return httpx.Response(202, json={"jobId": "job-123"})
        assert request.url.path == "/v1/transcript/job-123"
        state = next(job_states)
        if state != "completed":
            return httpx.Response(200, json={"status": state})
        return httpx.Response(200, json={"status": "completed", "content": TRANSCRIPT_CONTENT, "lang": "hi"})

    transcript = make_client(handler).get_transcript(VIDEO_ID)
    assert transcript.language == "hi"
    assert len(transcript.segments) == 2
    assert calls == ["/v1/transcript"] + ["/v1/transcript/job-123"] * 3


def test_transcript_failed_job_reports_error_details():
    def handler(request: httpx.Request):
        if request.url.path == "/v1/transcript":
            return httpx.Response(202, json={"jobId": "job-1"})
        error = {"error": "transcript-unavailable", "message": "Transcript Unavailable", "details": "No audio track"}
        return httpx.Response(200, json={"status": "failed", "error": error})

    with pytest.raises(AppError, match="No audio track"):
        make_client(handler).get_transcript(VIDEO_ID)


def test_transcript_unavailable_206():
    body = {"error": "transcript-unavailable", "message": "Transcript Unavailable", "details": "No transcript"}
    with pytest.raises(AppError, match="no transcript available") as info:
        make_client(lambda _r: httpx.Response(206, json=body)).get_transcript(VIDEO_ID)
    assert info.value.status_code == 422


def test_transcript_with_no_speech():
    client = make_client(lambda _r: httpx.Response(200, json={"content": [], "lang": "en"}))
    with pytest.raises(AppError, match="No speech"):
        client.get_transcript(VIDEO_ID)


@pytest.mark.parametrize(
    ("status", "error_code", "message"),
    [
        (401, "unauthorized", "rejected the API key"),
        (402, "upgrade-required", "not available on your current plan"),
        (404, "not-found", "not found"),
        (500, "internal-error", "Supadata request failed"),
    ],
)
def test_error_responses(status, error_code, message):
    body = {"error": error_code, "message": "msg", "details": "details"}
    with pytest.raises(AppError, match=message):
        make_client(lambda _r: httpx.Response(status, json=body)).get_metadata(VIDEO_ID)


def test_rate_limit_is_retried_then_reported():
    calls = []

    def handler(request: httpx.Request):
        calls.append(request)
        return httpx.Response(429, json={"error": "limit-exceeded", "message": "Limit", "details": "Too many"})

    with pytest.raises(ExternalServiceError) as info:
        make_client(handler).get_metadata(VIDEO_ID)
    assert info.value.status_code == 429
    assert len(calls) == supadata_client._RATE_LIMIT_RETRIES + 1


def test_rate_limit_recovers():
    responses = iter([httpx.Response(429, json={}), httpx.Response(200, json=METADATA_RESPONSE)])
    assert make_client(lambda _r: next(responses)).get_metadata(VIDEO_ID).channel_name == "Rick Astley"
