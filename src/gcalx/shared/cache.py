"""SQLite-based response cache for API data."""

from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Any

# TTLs in seconds
TTL_CAL_LIST = 24 * 60 * 60  # 24 h — calendar list rarely changes
TTL_EVENTS = 5 * 60          # 5 min — balance freshness vs speed
TTL_TASK_LISTS = 24 * 60 * 60  # 24 h
TTL_TASKS = 2 * 60           # 2 min — tasks change more frequently

_SCHEMA = """
CREATE TABLE IF NOT EXISTS cache (
    key       TEXT PRIMARY KEY,
    value     TEXT NOT NULL,
    expires   REAL NOT NULL,
    created   REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS task_positions (
    list_id   TEXT NOT NULL,
    position  INTEGER NOT NULL,
    task_id   TEXT NOT NULL,
    title     TEXT NOT NULL,
    PRIMARY KEY (list_id, position)
);
"""


class Cache:
    """Simple key-value cache backed by SQLite."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(str(db_path))
        self.db.execute("PRAGMA journal_mode=WAL")
        self._init_tables()

    def _init_tables(self) -> None:
        self.db.executescript(_SCHEMA)

    # ── generic get / set ──────────────────────────────────────────

    def get(self, key: str) -> Any | None:
        """Return cached value if not expired, else None."""
        row = self.db.execute(
            "SELECT value FROM cache WHERE key = ? AND expires > ?",
            (key, time.time()),
        ).fetchone()
        return json.loads(row[0]) if row else None

    def set(self, key: str, value: Any, ttl: int) -> None:
        """Store *value* under *key* with a TTL in seconds."""
        now = time.time()
        self.db.execute(
            "INSERT OR REPLACE INTO cache (key, value, expires, created) "
            "VALUES (?, ?, ?, ?)",
            (key, json.dumps(value, default=str), now + ttl, now),
        )
        self.db.commit()

    # ── invalidation ───────────────────────────────────────────────

    def invalidate(self, prefix: str) -> None:
        """Delete all keys that begin with *prefix*."""
        self.db.execute(
            "DELETE FROM cache WHERE key LIKE ?", (prefix + "%",)
        )
        self.db.commit()

    def delete(self, key: str) -> None:
        """Delete a single key."""
        self.db.execute("DELETE FROM cache WHERE key = ?", (key,))
        self.db.commit()

    def clear(self) -> None:
        """Nuke the entire cache."""
        self.db.execute("DELETE FROM cache")
        self.db.execute("DELETE FROM task_positions")
        self.db.commit()

    # ── task position helpers ──────────────────────────────────────

    def save_task_positions(
        self, list_id: str, tasks: list[dict[str, str]]
    ) -> None:
        """Persist the display ordering from the last `task ls`.

        Args:
            list_id: Google Tasks list ID.
            tasks: Ordered list of dicts with at least ``id`` and ``title``.
        """
        self.db.execute(
            "DELETE FROM task_positions WHERE list_id = ?", (list_id,)
        )
        self.db.executemany(
            "INSERT INTO task_positions (list_id, position, task_id, title) "
            "VALUES (?, ?, ?, ?)",
            [
                (list_id, idx + 1, t["id"], t.get("title", ""))
                for idx, t in enumerate(tasks)
            ],
        )
        self.db.commit()

    def resolve_task_position(
        self, list_id: str, position: int
    ) -> str | None:
        """Map a 1-based display position to a task ID.

        Returns None if no mapping exists.
        """
        row = self.db.execute(
            "SELECT task_id FROM task_positions "
            "WHERE list_id = ? AND position = ?",
            (list_id, position),
        ).fetchone()
        return row[0] if row else None

    # ── lifecycle ──────────────────────────────────────────────────

    def close(self) -> None:
        self.db.close()

    def __enter__(self) -> "Cache":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
