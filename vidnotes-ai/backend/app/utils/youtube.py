import re
from urllib.parse import parse_qs, urlparse

from app.core.errors import AppError

_VIDEO_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{11}$")
_YOUTUBE_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com"}
_PATH_PREFIXES = ("/shorts/", "/embed/", "/live/", "/v/")


def extract_video_id(url: str) -> str:
    """Return the 11-character video ID from a YouTube URL.

    Only YouTube hosts are accepted, and the ID is the only part of the URL
    the backend ever uses, so user input can never redirect our requests
    to another server.
    """
    raw = url.strip()
    if "://" not in raw:
        raw = f"https://{raw}"

    parsed = urlparse(raw)
    host = (parsed.hostname or "").lower()
    candidate = ""

    if parsed.scheme in ("http", "https"):
        if host == "youtu.be":
            candidate = parsed.path.lstrip("/").split("/")[0]
        elif host in _YOUTUBE_HOSTS:
            if parsed.path == "/watch":
                candidate = parse_qs(parsed.query).get("v", [""])[0]
            else:
                for prefix in _PATH_PREFIXES:
                    if parsed.path.startswith(prefix):
                        candidate = parsed.path[len(prefix):].split("/")[0]
                        break

    if not _VIDEO_ID_PATTERN.match(candidate):
        raise AppError("Please enter a valid YouTube video link.", 422)
    return candidate


def canonical_url(video_id: str) -> str:
    return f"https://www.youtube.com/watch?v={video_id}"
