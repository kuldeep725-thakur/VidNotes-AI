from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BACKEND_DIR / "data"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    gemini_api_key: str = ""
    supadata_api_key: str = ""
    gemini_model: str = "gemini-3.5-flash"
    # Comma-separated models tried in order when the main model is overloaded,
    # out of quota or unavailable. Each model has its own free-tier quota.
    gemini_fallback_models: str = "gemini-3.8-flash,gemini-3.7-flash,gemini-3.5-flash-lite,gemini-3.1-flash-lite"
    # minimal, low, medium or high. Leave empty for the model's default.
    gemini_thinking_level: str = "low"
    # Optional backup provider, used only when Gemini is out of quota, busy or
    # timing out. Leave the key empty to use Gemini alone.
    groq_api_key: str = ""
    groq_model: str = "openai/gpt-oss-120b"
    # low, medium or high (supported by the gpt-oss models). Empty for the default.
    groq_reasoning_effort: str = "low"
    groq_base_url: str = "https://api.groq.com/openai/v1"
    groq_timeout_seconds: float = 180.0

    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # Accounts and cloud sync (optional). Without SUPABASE_URL the app runs in
    # local single-user mode with no login, exactly like earlier versions.
    supabase_url: str = ""
    # The publishable key is designed to be public: it is sent to the browser,
    # which uses it only for sign-in. Never put a secret key here.
    supabase_publishable_key: str = ""
    supabase_timeout_seconds: float = 15.0
    # Postgres connection string (Supabase "Session pooler" URL) for cloud
    # storage. Empty means the local SQLite file below.
    database_url: str = ""

    database_path: Path = DATA_DIR / "vidnotes.db"

    supadata_base_url: str = "https://api.supadata.ai/v1"
    supadata_timeout_seconds: float = 60.0
    # native: existing captions only; auto: fall back to AI transcription
    # (costs more Supadata credits); generate: always use AI transcription.
    supadata_transcript_mode: str = "auto"
    # Supadata may process long transcripts asynchronously; this caps the wait.
    supadata_job_max_wait_seconds: float = 300.0

    gemini_timeout_seconds: float = 300.0
    gemini_max_retries: int = 3

    # About 4 characters per token: 60k chars keeps each chunk well inside
    # the model's context while leaving room for instructions and output.
    chunk_max_chars: int = 60_000
    # Roughly 10 hours of speech. Longer transcripts are rejected with a clear
    # message instead of being silently truncated.
    max_transcript_chars: int = 600_000

    max_request_bytes: int = 16_384

    @property
    def auth_enabled(self) -> bool:
        return bool(self.supabase_url and self.supabase_publishable_key)

    @property
    def supabase_auth_url(self) -> str:
        return f"{self.supabase_url.rstrip('/')}/auth/v1"

    @property
    def sqlalchemy_url(self) -> str:
        if not self.database_url:
            return f"sqlite:///{self.database_path}"
        # Supabase shows "postgresql://..."; SQLAlchemy needs the driver name.
        for prefix in ("postgresql://", "postgres://"):
            if self.database_url.startswith(prefix):
                return "postgresql+psycopg://" + self.database_url[len(prefix):]
        return self.database_url

    @property
    def uses_postgres(self) -> bool:
        return self.sqlalchemy_url.startswith("postgresql")

    @property
    def cors_origin_list(self) -> list[str]:
        return _split_list(self.cors_origins)

    @property
    def gemini_models(self) -> list[str]:
        models = [self.gemini_model, *_split_list(self.gemini_fallback_models)]
        return list(dict.fromkeys(model for model in models if model))


def _split_list(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
