import pytest

from app.core.errors import AppError
from app.services.supadata_client import TranscriptSegment
from app.services.transcript_chunker import build_timed_lines, split_into_chunks
from app.utils.time_format import format_timestamp
from app.utils.youtube import extract_video_id


@pytest.mark.parametrize(
    "url",
    [
        "https://www.youtube.com/watch?v=aircAruvnKk",
        "https://youtube.com/watch?v=aircAruvnKk&t=30s",
        "youtu.be/aircAruvnKk",
        "https://m.youtube.com/watch?v=aircAruvnKk",
        "https://www.youtube.com/shorts/aircAruvnKk",
        "https://www.youtube.com/embed/aircAruvnKk",
        "https://www.youtube.com/live/aircAruvnKk?si=x",
    ],
)
def test_extract_video_id_accepts_youtube_links(url):
    assert extract_video_id(url) == "aircAruvnKk"


@pytest.mark.parametrize(
    "url",
    [
        "https://vimeo.com/12345",
        "https://evil.example.com/watch?v=aircAruvnKk",
        "https://youtube.com.evil.com/watch?v=aircAruvnKk",
        "file:///etc/passwd",
        "https://www.youtube.com/watch?v=short",
        "not a url",
    ],
)
def test_extract_video_id_rejects_other_links(url):
    with pytest.raises(AppError):
        extract_video_id(url)


def test_format_timestamp():
    assert format_timestamp(5) == "0:05"
    assert format_timestamp(725) == "12:05"
    assert format_timestamp(3725) == "1:02:05"


def test_chunking_keeps_every_line_and_respects_limit():
    segments = [TranscriptSegment(start_seconds=i * 5, text=f"sentence number {i}") for i in range(200)]
    lines = build_timed_lines(segments)
    assert lines[0].startswith("[0:00]")

    chunks = split_into_chunks(lines, max_chars=300)
    assert len(chunks) > 1
    assert all(len(chunk) <= 300 for chunk in chunks)
    assert "\n".join(chunks).split("\n") == lines
