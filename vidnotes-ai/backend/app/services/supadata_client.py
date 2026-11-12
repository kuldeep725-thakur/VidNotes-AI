import time
from dataclasses import dataclass

import httpx

from app.core.config import get_settings
from app.core.errors import AppError, ExternalServiceError
from app.utils.youtube import canonical_url

# Supadata recommends polling transcript jobs every second.
_JOB_POLL_INTERVAL_SECONDS = 1
# Supadata's free plan allows about one request per second, so rate-limited
# requests are retried a few times with a growing delay.
_RATE_LIMIT_RETRIES = 3


@dataclass
class VideoMetadata:
    title: str
    channel_name: str | None
    thumbnail_url: str | None
    duration_seconds: int | None


@dataclass
class TranscriptSegment:
    start_seconds: float
    text: str


@dataclass
class Transcript:
    language: str | None
    segments: list[TranscriptSegment]


class SupadataClient:
    """Client for Supadata's GET /v1/metadata and GET /v1/transcript endpoints."""

    def __init__(self, transport: httpx.BaseTransport | None = None):
        settings = get_settings()
        if not settings.supadata_api_key:
            raise AppError("Supadata API key is missing. Add SUPADATA_API_KEY to backend/.env.", 500)
        # `transport` lets tests replace the network with canned responses.
        self._client = httpx.Client(
            base_url=settings.supadata_base_url,
            headers={"x-api-key": settings.supadata_api_key},
            timeout=settings.supadata_timeout_seconds,
            transport=transport,
        )
        self._max_job_wait = settings.supadata_job_max_wait_seconds
        self._transcript_mode = settings.supadata_transcript_mode

    def close(self) -> None:
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    def get_metadata(self, video_id: str) -> VideoMetadata:
        data = self._get("/metadata", {"url": canonical_url(video_id)})
        # Unified schema: author.displayName, media.duration (seconds) and
        # media.thumbnailUrl. author.name is accepted too in case it appears.
        author = data.get("author") or {}
        media = data.get("media") or {}
        duration = media.get("duration")
        return VideoMetadata(
            title=(data.get("title") or "Untitled video")[:300],
            channel_name=author.get("displayName") or author.get("name") or author.get("username"),
            thumbnail_url=media.get("thumbnailUrl") or f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg",
            duration_seconds=int(duration) if duration else None,
        )

    def get_transcript(self, video_id: str) -> Transcript:
        data = self._get("/transcript", {"url": canonical_url(video_id), "mode": self._transcript_mode})

        # Long or caption-less videos are processed asynchronously by Supadata.
        if "jobId" in data:
            data = self._wait_for_job(data["jobId"])

        segments = [
            TranscriptSegment(start_seconds=item.get("offset", 0) / 1000, text=item["text"].strip())
            for item in data.get("content") or []
            if isinstance(item, dict) and item.get("text", "").strip()
        ]
        if not segments:
            # A successful response with empty content means no speech was found.
            raise AppError("No speech was detected in this video, so notes cannot be generated.", 422)
        return Transcript(language=data.get("lang"), segments=segments)

    def _wait_for_job(self, job_id: str) -> dict:
        deadline = time.monotonic() + self._max_job_wait
        while time.monotonic() < deadline:
            data = self._get(f"/transcript/{job_id}", {})
            status = data.get("status")
            if status == "completed":
                return data
            if status == "failed":
                error = data.get("error")
                detail = (error.get("details") or error.get("message")) if isinstance(error, dict) else error
                raise AppError(f"Supadata could not create a transcript for this video. {detail or ''}".strip(), 422)
            time.sleep(_JOB_POLL_INTERVAL_SECONDS)
        raise ExternalServiceError("Transcript generation took too long. Please try again later.", 504)

    def _get(self, path: str, params: dict) -> dict:
        for attempt in range(_RATE_LIMIT_RETRIES + 1):
            try:
                response = self._client.get(path, params=params)
            except httpx.TimeoutException as exc:
                raise ExternalServiceError("Supadata did not respond in time. Please try again.", 504) from exc
            except httpx.HTTPError as exc:
                raise ExternalServiceError("Could not reach Supadata. Check your internet connection.") from exc

            if response.status_code != 429 or attempt == _RATE_LIMIT_RETRIES:
                break
            time.sleep(2 ** (attempt + 1))

        if response.status_code in (200, 202):
            return response.json()
        raise self._error_for(response)

    @staticmethod
    def _error_for(response: httpx.Response) -> AppError:
        try:
            body = response.json()
        except ValueError:
            body = {}
        detail = body.get("details") or body.get("message") or ""
        code = response.status_code

        if code in (401, 403):
            return ExternalServiceError("Supadata rejected the API key. Check SUPADATA_API_KEY in backend/.env.")
        if code == 402:
            return ExternalServiceError("This Supadata feature is not available on your current plan.")
        if code == 404:
            return AppError(f"Video or transcript not found{': ' + detail.rstrip('.') if detail else ''}.", 404)
        if code == 206 or body.get("error") == "transcript-unavailable":
            return AppError("This video has no transcript available, so notes cannot be generated.", 422)
        if code == 429:
            return ExternalServiceError(
                "Supadata rate or credit limit reached. Wait a minute, or check your plan's remaining credits.", 429
            )
        return ExternalServiceError(f"Supadata request failed ({code}). {detail}".strip())
