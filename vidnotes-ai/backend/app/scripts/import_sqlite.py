"""Copy notes and tasks from the local SQLite database into your Supabase account.

Usage (from the backend folder, with DATABASE_URL pointing at Supabase):

    python -m app.scripts.import_sqlite --email you@example.com --dry-run
    python -m app.scripts.import_sqlite --email you@example.com

Safety:
- The SQLite file is backed up to data/backups/ first and opened read-only,
  so local data always stays recoverable.
- Videos the account already has (same YouTube video) and tasks that were
  already imported are skipped, so running it twice creates no duplicates.
- Everything is written as the signed-in user, so Row Level Security applies.
- --dry-run shows what would be imported and changes nothing.
"""

import argparse
import json
import sqlite3
import sys
from datetime import date, datetime
from pathlib import Path

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.database import SessionLocal
from app.models import QAPair, QuizQuestion, QuizResult, StudyMaterial, Todo, UserPreferences, Video, VideoStatus
from app.models.types import UTCDateTime
from app.utils.sqlite_backup import backup_sqlite_database

_to_datetime = UTCDateTime().process_result_value


def _rows(source: sqlite3.Connection, table: str, where: str = "", params: tuple = ()) -> list[sqlite3.Row]:
    exists = source.execute("select 1 from sqlite_master where type = 'table' and name = ?", (table,)).fetchone()
    return source.execute(f"select * from {table} {where}", params).fetchall() if exists else []


def _json(value):
    return json.loads(value) if isinstance(value, str) else value


def _timestamp(value):
    return _to_datetime(datetime.fromisoformat(value), None) if value else None


def _date(value):
    return date.fromisoformat(value) if value else None


def find_user_id(db: Session, email: str) -> str | None:
    return db.scalar(text("select id::text from auth.users where lower(email) = lower(:email)"), {"email": email})


def import_database(source_path: Path, user_id: str, db: Session) -> dict[str, int]:
    """Copy all completed videos and all tasks for one user. Returns counts."""
    source = sqlite3.connect(f"file:{source_path}?mode=ro", uri=True)
    source.row_factory = sqlite3.Row
    counts = dict.fromkeys(
        ["videos", "videos_skipped_existing", "videos_skipped_unfinished", "tasks", "tasks_skipped_existing",
         "quiz_results"], 0)
    video_ids: dict[int, int] = {}

    for row in _rows(source, "videos", "order by id"):
        existing = db.scalar(select(Video.id).where(Video.user_id == user_id, Video.youtube_id == row["youtube_id"]))
        if existing is not None:
            video_ids[row["id"]] = existing
            counts["videos_skipped_existing"] += 1
            continue
        if row["status"] != VideoStatus.COMPLETED:
            counts["videos_skipped_unfinished"] += 1
            continue

        video = Video(
            user_id=user_id,
            **{key: row[key] for key in ("youtube_id", "url", "title", "channel_name", "thumbnail_url",
                                         "duration_seconds", "transcript_language", "quiz_count", "status",
                                         "progress", "progress_message")},
            created_at=_timestamp(row["created_at"]),
            updated_at=_timestamp(row["updated_at"]),
        )
        db.add(video)
        db.flush()
        video_ids[row["id"]] = video.id
        counts["videos"] += 1

        for item in _rows(source, "study_materials", "where video_id = ?", (row["id"],)):
            db.add(StudyMaterial(user_id=user_id, video_id=video.id, language=item["language"],
                                 summary=_json(item["summary"]), notes=_json(item["notes"]),
                                 timestamps=_json(item["timestamps"]), created_at=_timestamp(item["created_at"])))
        for item in _rows(source, "quiz_questions", "where video_id = ? order by position", (row["id"],)):
            db.add(QuizQuestion(user_id=user_id, video_id=video.id, language=item["language"],
                                position=item["position"], question=item["question"],
                                options=_json(item["options"]), correct_index=item["correct_index"],
                                explanation=item["explanation"]))
        for item in _rows(source, "qa_pairs", "where video_id = ? order by position", (row["id"],)):
            db.add(QAPair(user_id=user_id, video_id=video.id, language=item["language"], position=item["position"],
                          question=item["question"], answer=item["answer"]))
        for item in _rows(source, "quiz_results", "where video_id = ?", (row["id"],)):
            db.add(QuizResult(user_id=user_id, video_id=video.id, language=item["language"], score=item["score"],
                              total=item["total"], answers=_json(item["answers"]),
                              created_at=_timestamp(item["created_at"])))
            counts["quiz_results"] += 1

    for row in _rows(source, "todos", "order by id"):
        created_at = _timestamp(row["created_at"])
        duplicate = db.scalar(
            select(Todo.id).where(Todo.user_id == user_id, Todo.title == row["title"], Todo.created_at == created_at)
        )
        if duplicate is not None:
            counts["tasks_skipped_existing"] += 1
            continue
        db.add(Todo(user_id=user_id, title=row["title"], is_done=bool(row["is_done"]),
                    due_date=_date(row["due_date"]), video_id=video_ids.get(row["video_id"]),
                    created_at=created_at, updated_at=_timestamp(row["updated_at"])))
        counts["tasks"] += 1

    preferences = _rows(source, "user_preferences")
    if preferences and db.get(UserPreferences, user_id) is None:
        row = preferences[0]
        db.add(UserPreferences(user_id=user_id, theme=row["theme"], default_language=row["default_language"],
                               default_quiz_count=row["default_quiz_count"]))

    source.close()
    return counts


def main(argv: list[str] | None = None) -> int:
    settings = get_settings()
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--email", help="Email of the Supabase account to import into")
    parser.add_argument("--user-id", help="Supabase user ID (instead of --email)")
    parser.add_argument("--source", type=Path, default=settings.database_path, help="SQLite file to import")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be imported without saving")
    args = parser.parse_args(argv)

    if not settings.uses_postgres:
        print("DATABASE_URL is not set to your Supabase database in backend/.env. Nothing to import into.")
        return 1
    if not args.source.is_file():
        print(f"SQLite database not found: {args.source}")
        return 1
    if not (args.email or args.user_id):
        parser.error("give --email or --user-id")

    backup = backup_sqlite_database(args.source, "before-cloud-import")
    print(f"Backup of the local database: {backup}")

    if args.user_id:
        user_id = args.user_id
    else:
        with SessionLocal() as lookup:
            user_id = find_user_id(lookup, args.email)
    if not user_id:
        print(f"No Supabase account found for {args.email}. Sign up in VidNotes AI first, then run this again.")
        return 1

    # Written as the user, so Row Level Security checks every inserted row.
    db = SessionLocal(info={"user_id": user_id})
    try:
        counts = import_database(args.source, user_id, db)
        if args.dry_run:
            db.rollback()
        else:
            db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    print(("Dry run — nothing was saved. Would import:" if args.dry_run else "Imported:"))
    print(f"  videos: {counts['videos']} (already in account: {counts['videos_skipped_existing']}, "
          f"unfinished, not imported: {counts['videos_skipped_unfinished']})")
    print(f"  quiz results: {counts['quiz_results']}")
    print(f"  tasks: {counts['tasks']} (already imported: {counts['tasks_skipped_existing']})")
    print("Your local database was not changed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
