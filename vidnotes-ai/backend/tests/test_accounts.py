"""Account mode: token verification, profiles, preferences, quiz results and
isolation between users (enforced by the services; Postgres adds RLS on top,
see test_postgres_rls.py)."""

import time
import uuid

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec

from app.core import auth
from app.core.config import get_settings
from app.models import QuizQuestion, Video, VideoStatus

SUPABASE_URL = "https://example-project.supabase.co"
ISSUER = f"{SUPABASE_URL}/auth/v1"
PRIVATE_KEY = ec.generate_private_key(ec.SECP256R1())


class FakeJWKSClient:
    """Stands in for Supabase's JWKS endpoint with our test public key."""

    def get_signing_key_from_jwt(self, token):
        return jwt.PyJWK.from_dict(
            {**jwt.algorithms.ECAlgorithm.to_jwk(PRIVATE_KEY.public_key(), as_dict=True), "alg": "ES256"}
        )


def make_token(user_id: str, *, name="Asha Verma", expires_in=3600, audience="authenticated", issuer=ISSUER, key=None):
    now = int(time.time())
    claims = {
        "sub": user_id,
        "aud": audience,
        "iss": issuer,
        "iat": now,
        "exp": now + expires_in,
        "email": f"{user_id[:8]}@example.com",
        "role": "authenticated",
        "app_metadata": {"provider": "google"},
        "user_metadata": {"full_name": name, "avatar_url": "https://lh3.googleusercontent.com/a/photo"},
    }
    return jwt.encode(claims, key or PRIVATE_KEY, algorithm="ES256", headers={"kid": "test-key"})


def headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def accounts(monkeypatch, client):
    settings = get_settings()
    monkeypatch.setattr(settings, "supabase_url", SUPABASE_URL)
    monkeypatch.setattr(settings, "supabase_publishable_key", "sb_publishable_test")
    monkeypatch.setattr(auth, "_jwks_client", lambda: FakeJWKSClient())
    auth._legacy_cache.clear()
    return client


@pytest.fixture
def alice(accounts):
    return headers(make_token(str(uuid.uuid4()), name="Alice"))


@pytest.fixture
def bob(accounts):
    return headers(make_token(str(uuid.uuid4()), name="Bob"))


def test_public_config_has_no_secrets(accounts):
    config = accounts.get("/api/config").json()
    assert config == {
        "auth_enabled": True,
        "cloud_sync": False,
        "supabase_url": SUPABASE_URL,
        "supabase_publishable_key": "sb_publishable_test",
    }


def test_local_mode_config(client):
    assert client.get("/api/config").json()["auth_enabled"] is False
    assert client.get("/api/me").json()["full_name"] == "Local user"


@pytest.mark.parametrize("path", ["/api/videos", "/api/todos", "/api/me", "/api/me/preferences"])
def test_protected_endpoints_need_a_token(accounts, path):
    response = accounts.get(path)
    assert response.status_code == 401
    assert response.json()["detail"] == "Please sign in to continue."


@pytest.mark.parametrize(
    "token",
    [
        "not-a-jwt",
        make_token(str(uuid.uuid4()), expires_in=-10),
        make_token(str(uuid.uuid4()), audience="anon"),
        make_token(str(uuid.uuid4()), issuer="https://evil.example.com/auth/v1"),
        make_token(str(uuid.uuid4()), key=ec.generate_private_key(ec.SECP256R1())),
    ],
    ids=["garbage", "expired", "wrong-audience", "wrong-issuer", "wrong-signature"],
)
def test_invalid_tokens_are_rejected(accounts, token):
    response = accounts.get("/api/todos", headers=headers(token))
    assert response.status_code == 401
    assert "sign in again" in response.json()["detail"]


def test_legacy_hs256_tokens_are_checked_with_the_auth_server(accounts, monkeypatch):
    user_id = str(uuid.uuid4())
    token = jwt.encode({"sub": user_id, "aud": "authenticated"}, "legacy-secret-at-least-32-characters!!", "HS256")
    calls = []

    def fake_get(url, headers, timeout):
        calls.append((url, headers))
        if headers["Authorization"] == f"Bearer {token}":
            return httpx.Response(200, json={"id": user_id, "email": "legacy@example.com", "user_metadata": {}})
        return httpx.Response(401, json={"msg": "invalid"})

    monkeypatch.setattr(auth.httpx, "get", fake_get)
    assert accounts.get("/api/me", headers=headers(token)).json()["email"] == "legacy@example.com"
    accounts.get("/api/todos", headers=headers(token))  # served from the short cache
    assert len(calls) == 1
    assert calls[0] == (f"{ISSUER}/user", {"apikey": "sb_publishable_test", "Authorization": f"Bearer {token}"})

    bad = jwt.encode({"sub": user_id}, "another-secret-at-least-32-characters!!", "HS256")
    assert accounts.get("/api/me", headers=headers(bad)).status_code == 401


def test_profile_comes_from_the_sign_in_and_keeps_edited_name(accounts):
    user_id = str(uuid.uuid4())
    profile = accounts.get("/api/me", headers=headers(make_token(user_id, name="Asha Verma"))).json()
    assert profile["id"] == user_id
    assert profile["full_name"] == "Asha Verma"
    assert profile["avatar_url"] == "https://lh3.googleusercontent.com/a/photo"
    assert profile["provider"] == "google"
    assert profile["stats"] == {"videos": 0, "quizzes_taken": 0, "open_tasks": 0, "done_tasks": 0}

    renamed = accounts.patch("/api/me", headers=headers(make_token(user_id)), json={"full_name": "  Asha V  "})
    assert renamed.json()["full_name"] == "Asha V"
    again = accounts.get("/api/me", headers=headers(make_token(user_id, name="Asha Verma"))).json()
    assert again["full_name"] == "Asha V"
    assert accounts.patch("/api/me", headers=headers(make_token(user_id)), json={"full_name": " "}).status_code == 422


def test_preferences_defaults_and_updates(accounts, alice, bob):
    assert accounts.get("/api/me/preferences", headers=alice).json() == {
        "theme": "dark",
        "default_language": "en",
        "default_quiz_count": 10,
    }
    updated = accounts.patch("/api/me/preferences", headers=alice, json={"theme": "light", "default_quiz_count": 15})
    assert updated.json() == {"theme": "light", "default_language": "en", "default_quiz_count": 15}
    assert accounts.get("/api/me/preferences", headers=alice).json()["theme"] == "light"
    assert accounts.get("/api/me/preferences", headers=bob).json()["theme"] == "dark"

    for bad in ({"theme": "blue"}, {"default_quiz_count": 50}, {"default_language": "fr"}, {"theme": None}):
        assert accounts.patch("/api/me/preferences", headers=alice, json=bad).status_code == 422


def test_users_cannot_see_or_change_each_others_data(accounts, alice, bob):
    video = accounts.post("/api/videos", headers=alice, json={"url": "https://youtu.be/aircAruvnKk"}).json()
    todo = accounts.post("/api/todos", headers=alice, json={"title": "Alice's task", "video_id": video["id"]}).json()

    assert accounts.get("/api/videos", headers=bob).json() == []
    assert accounts.get("/api/todos", headers=bob).json() == []
    assert accounts.get(f"/api/videos/{video['id']}", headers=bob).status_code == 404
    assert accounts.get(f"/api/videos/{video['id']}/pdf", headers=bob).status_code == 404
    assert accounts.get(f"/api/videos/{video['id']}/quiz-results", headers=bob).status_code == 404
    assert accounts.delete(f"/api/videos/{video['id']}", headers=bob).status_code == 404
    assert accounts.get(f"/api/todos/{todo['id']}", headers=bob).status_code == 404
    assert accounts.patch(f"/api/todos/{todo['id']}", headers=bob, json={"is_done": True}).status_code == 404
    assert accounts.delete(f"/api/todos/{todo['id']}", headers=bob).status_code == 404
    linked = accounts.post("/api/todos", headers=bob, json={"title": "Sneaky", "video_id": video["id"]})
    assert linked.status_code == 422

    # Alice's data is untouched, and the same video can be analyzed by Bob separately.
    assert accounts.get(f"/api/todos/{todo['id']}", headers=alice).json()["is_done"] is False
    bobs_video = accounts.post("/api/videos", headers=bob, json={"url": "https://youtu.be/aircAruvnKk"}).json()
    assert bobs_video["id"] != video["id"]
    assert len(accounts.get("/api/videos", headers=alice).json()) == 1


def test_quiz_results_are_scored_by_the_server(accounts, alice, bob, db):
    user_id = jwt.decode(alice["Authorization"][7:], options={"verify_signature": False})["sub"]
    video = Video(user_id=user_id, youtube_id="aircAruvnKk", url="u", title="T", status=VideoStatus.COMPLETED)
    db.add(video)
    db.flush()
    db.add_all(
        QuizQuestion(user_id=user_id, video_id=video.id, language="en", position=i, question=f"Q{i}",
                     options=["a", "b", "c", "d"], correct_index=i % 4, explanation="E")
        for i in range(4)
    )
    db.commit()
    path = f"/api/videos/{video.id}/quiz-results"

    saved = accounts.post(path, headers=alice, json={"language": "en", "answers": [0, 1, 0, None]})
    assert saved.status_code == 201
    assert (saved.json()["score"], saved.json()["total"]) == (2, 4)
    assert accounts.post(path, headers=alice, json={"language": "en", "answers": [0, 1]}).status_code == 422
    assert accounts.post(path, headers=alice, json={"language": "en", "answers": [9, 0, 0, 0]}).status_code == 422
    assert accounts.post(path, headers=alice, json={"language": "hinglish", "answers": [0]}).status_code == 422
    assert accounts.post(path, headers=bob, json={"language": "en", "answers": [0, 1, 2, 3]}).status_code == 404

    history = accounts.get(path, headers=alice).json()
    assert [(r["score"], r["total"], r["language"]) for r in history] == [(2, 4, "en")]
    assert accounts.get("/api/me", headers=alice).json()["stats"]["quizzes_taken"] == 1

    # Deleting the video removes its quiz history too.
    assert accounts.delete(f"/api/videos/{video.id}", headers=alice).status_code == 204
    assert accounts.get("/api/me", headers=alice).json()["stats"]["quizzes_taken"] == 0
