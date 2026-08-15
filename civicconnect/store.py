from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from threading import Lock

from .models import CivicEvent


class EventStore:
    def __init__(self, path: str | Path = "civicconnect.db"):
        self.path = str(path)
        self._lock = Lock()
        Path(self.path).parent.mkdir(parents=True, exist_ok=True) if Path(self.path).parent != Path(".") else None
        with self._connect() as db:
            db.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    event_id TEXT PRIMARY KEY,
                    issue_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    payload TEXT NOT NULL
                )
            """)
            db.execute("CREATE INDEX IF NOT EXISTS idx_events_issue ON events(issue_id)")
            db.execute("CREATE INDEX IF NOT EXISTS idx_events_time ON events(timestamp)")

    def _connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.path)
        db.row_factory = sqlite3.Row
        return db

    def append(self, event: CivicEvent) -> None:
        payload = event.model_dump(mode="json")
        with self._lock, self._connect() as db:
            db.execute(
                "INSERT INTO events(event_id, issue_id, timestamp, payload) VALUES (?, ?, ?, ?)",
                (event.event_id, event.issue_id, event.timestamp.isoformat(), json.dumps(payload, sort_keys=True)),
            )

    def all(self, as_of: datetime | None = None) -> list[CivicEvent]:
        with self._connect() as db:
            if as_of is None:
                rows = db.execute("SELECT payload FROM events ORDER BY timestamp, event_id").fetchall()
            else:
                rows = db.execute(
                    "SELECT payload FROM events WHERE timestamp <= ? ORDER BY timestamp, event_id",
                    (as_of.isoformat(),),
                ).fetchall()
        return [CivicEvent.model_validate(json.loads(row["payload"])) for row in rows]

    def count(self) -> int:
        with self._connect() as db:
            return int(db.execute("SELECT COUNT(*) FROM events").fetchone()[0])
