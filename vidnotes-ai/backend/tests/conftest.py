"""Test setup: a throwaway SQLite database and dummy API keys.

The environment is configured before the app is imported, so the tests never
touch backend/data/vidnotes.db, a real Supabase project, or the real Supadata,
Gemini and Groq APIs.
"""

import os
import tempfile
from pathlib import Path

os.environ.update(
    {
        "DATABASE_PATH": str(Path(tempfile.mkdtemp()) / "test.db"),
        "GEMINI_API_KEY": "test-gemini-key",
        "SUPADATA_API_KEY": "test-supadata-key",
        "GROQ_API_KEY": "test-groq-key",
        # Never touch a real Supabase project or cloud database from tests,
        # even if backend/.env configures one. Tests switch accounts on themselves.
        "SUPABASE_URL": "",
        "SUPABASE_PUBLISHABLE_KEY": "",
        "DATABASE_URL": "",
    }
)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.database import Base, SessionLocal, engine, init_db  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(autouse=True)
def clean_database():
    init_db()
    yield
    with engine.begin() as connection:
        for table in reversed(Base.metadata.sorted_tables):
            connection.execute(table.delete())


@pytest.fixture
def client(monkeypatch):
    # Analysis jobs would call the real APIs, so the background task is disabled.
    monkeypatch.setattr("app.api.videos.process_video", lambda video_id: None)
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def db():
    session = SessionLocal()
    yield session
    session.close()
