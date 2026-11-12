def format_timestamp(total_seconds: int) -> str:
    """Format seconds as m:ss or h:mm:ss."""
    hours, remainder = divmod(max(int(total_seconds), 0), 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    return f"{minutes}:{seconds:02d}"
