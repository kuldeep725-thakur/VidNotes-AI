"""Row Level Security tests against a real Supabase Postgres database.

Skipped unless TEST_SUPABASE_DB_URL is set. Point it at a local Supabase
(`supabase start`) whose schema was created from supabase/migrations, e.g.

    TEST_SUPABASE_DB_URL=postgresql://postgres:postgres@127.0.0.1:54322/postgres

Two throwaway users are created in auth.users and deleted afterwards.
Never point this at your production project.
"""

import json
import os
import uuid

import pytest

psycopg = pytest.importorskip("psycopg")

DB_URL = os.environ.get("TEST_SUPABASE_DB_URL")
pytestmark = pytest.mark.skipif(not DB_URL, reason="TEST_SUPABASE_DB_URL is not set")

OWNED_TABLES = ["videos", "study_materials", "quiz_questions", "qa_pairs", "quiz_results", "todos", "user_preferences"]


def insert(cursor, table: str, **values) -> int | None:
    columns = ", ".join(values)
    placeholders = ", ".join(["%s"] * len(values))
    params = [json.dumps(v) if isinstance(v, (dict, list)) else v for v in values.values()]
    returning = " returning id" if table not in ("user_preferences", "profiles") else ""
    cursor.execute(f"insert into public.{table} ({columns}) values ({placeholders}){returning}", params)
    return cursor.fetchone()[0] if returning else None


def seed_user(cursor, user_id: str) -> dict:
    cursor.execute(
        "insert into auth.users (id, email, aud, role) values (%s, %s, 'authenticated', 'authenticated')",
        (user_id, f"rls-{user_id[:8]}@example.com"),
    )
    insert(cursor, "profiles", id=user_id, email=f"rls-{user_id[:8]}@example.com", full_name="Test")
    insert(cursor, "user_preferences", user_id=user_id, theme="light")
    video = insert(cursor, "videos", user_id=user_id, youtube_id="aircAruvnKk", url="https://youtu.be/x",
                   status="completed")
    insert(cursor, "study_materials", user_id=user_id, video_id=video, language="en", summary={}, notes={},
           timestamps=[])
    insert(cursor, "quiz_questions", user_id=user_id, video_id=video, language="en", position=0, question="Q",
           options=["a", "b", "c", "d"], correct_index=0, explanation="E")
    insert(cursor, "qa_pairs", user_id=user_id, video_id=video, language="en", position=0, question="Q", answer="A")
    insert(cursor, "quiz_results", user_id=user_id, video_id=video, language="en", score=1, total=1, answers=[0])
    todo = insert(cursor, "todos", user_id=user_id, title="Revise", video_id=video)
    return {"id": user_id, "video": video, "todo": todo}


@pytest.fixture
def users():
    a, b = str(uuid.uuid4()), str(uuid.uuid4())
    with psycopg.connect(DB_URL, autocommit=True) as admin:
        with admin.cursor() as cursor:
            seeded = {"a": seed_user(cursor, a), "b": seed_user(cursor, b)}
        yield seeded
        # Deleting the auth users removes all their rows through the cascades.
        admin.execute("delete from auth.users where id in (%s, %s)", (a, b))


def as_user(connection, user_id: str):
    """Start a transaction that runs exactly like the backend's user requests."""
    claims = json.dumps({"sub": user_id, "role": "authenticated"})
    connection.execute("select set_config('request.jwt.claims', %s, true)", (claims,))
    connection.execute("set local role authenticated")


@pytest.fixture
def connection():
    with psycopg.connect(DB_URL) as conn:
        yield conn
        conn.rollback()


@pytest.mark.parametrize("table", OWNED_TABLES + ["profiles"])
def test_users_only_see_their_own_rows(users, connection, table):
    owner_column = "id" if table == "profiles" else "user_id"
    as_user(connection, users["a"]["id"])
    owners = {
        str(row[0])
        for row in connection.execute(f"select {owner_column} from public.{table} where {owner_column} in (%s, %s)",
                                      (users["a"]["id"], users["b"]["id"]))
    }
    assert owners == {users["a"]["id"]}


@pytest.mark.parametrize("table", ["videos", "todos", "quiz_results", "study_materials"])
def test_users_cannot_change_or_delete_other_users_rows(users, connection, table):
    as_user(connection, users["a"]["id"])
    updated = connection.execute(
        f"update public.{table} set updated_at = now() where user_id = %s", (users["b"]["id"],)
    ).rowcount
    deleted = connection.execute(f"delete from public.{table} where user_id = %s", (users["b"]["id"],)).rowcount
    assert (updated, deleted) == (0, 0)


def test_users_cannot_insert_rows_for_someone_else(users, connection):
    as_user(connection, users["a"]["id"])
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        connection.execute("insert into public.todos (user_id, title) values (%s, 'sneaky')", (users["b"]["id"],))


def test_users_cannot_move_their_rows_to_someone_else(users, connection):
    as_user(connection, users["a"]["id"])
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        connection.execute("update public.todos set user_id = %s where id = %s", (users["b"]["id"], users["a"]["todo"]))


def test_tasks_cannot_link_to_another_users_video(users, connection):
    as_user(connection, users["a"]["id"])
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        connection.execute(
            "update public.todos set video_id = %s where id = %s", (users["b"]["video"], users["a"]["todo"])
        )


def test_signed_out_visitors_have_no_access(users, connection):
    connection.execute("set local role anon")
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        connection.execute("select count(*) from public.videos")


def test_deleting_a_video_cascades_and_unlinks_tasks(users, connection):
    as_user(connection, users["a"]["id"])
    connection.execute("delete from public.videos where id = %s", (users["a"]["video"],))
    for table in ("study_materials", "quiz_questions", "qa_pairs", "quiz_results"):
        count = connection.execute(f"select count(*) from public.{table} where video_id = %s",
                                   (users["a"]["video"],)).fetchone()[0]
        assert count == 0, table
    todo = connection.execute(
        "select video_id, title from public.todos where id = %s", (users["a"]["todo"],)
    ).fetchone()
    assert todo == (None, "Revise")
