import sqlite3
from datetime import datetime
from pathlib import Path

from app.core.config import DATA_DIR

BACKUP_DIR = DATA_DIR / "backups"


def backup_sqlite_database(source: Path, label: str) -> Path:
    """Copy a SQLite database to data/backups/ and return the copy's path.

    Uses SQLite's backup API, which makes a consistent copy even while the
    database is open. The original file is never modified.
    """
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    target = BACKUP_DIR / f"{source.stem}-{label}-{stamp}.db"
    copy_number = 1
    while target.exists():
        copy_number += 1
        target = BACKUP_DIR / f"{source.stem}-{label}-{stamp}-{copy_number}.db"
    with sqlite3.connect(f"file:{source}?mode=ro", uri=True) as src, sqlite3.connect(target) as dst:
        src.backup(dst)
    return target
