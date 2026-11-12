from app.services.supadata_client import TranscriptSegment
from app.utils.time_format import format_timestamp

# Segments are merged into lines of about this length so every line keeps a
# nearby [m:ss] marker the AI can cite as a timestamp.
_LINE_SECONDS = 30


def build_timed_lines(segments: list[TranscriptSegment]) -> list[str]:
    """Merge short caption segments into "[m:ss] text" lines."""
    lines: list[str] = []
    line_start: float | None = None
    words: list[str] = []

    for segment in segments:
        if line_start is None:
            line_start = segment.start_seconds
        words.append(segment.text)
        if segment.start_seconds - line_start >= _LINE_SECONDS:
            lines.append(f"[{format_timestamp(line_start)}] {' '.join(words)}")
            line_start, words = None, []

    if words and line_start is not None:
        lines.append(f"[{format_timestamp(line_start)}] {' '.join(words)}")
    return lines


def split_into_chunks(lines: list[str], max_chars: int) -> list[str]:
    """Group lines into chunks under max_chars, never splitting a line."""
    chunks: list[str] = []
    current: list[str] = []
    current_size = 0

    for line in lines:
        if current and current_size + len(line) > max_chars:
            chunks.append("\n".join(current))
            current, current_size = [], 0
        current.append(line)
        current_size += len(line) + 1

    if current:
        chunks.append("\n".join(current))
    return chunks
