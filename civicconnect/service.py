from __future__ import annotations

from datetime import datetime
from pathlib import Path

from .engine import reconstruct
from .models import CivicEvent
from .store import EventStore


class CivicConnectEngine:
    def __init__(self, db_path: str | Path = "civicconnect.db"):
        self.store = EventStore(db_path)

    def ingest(self, event: CivicEvent) -> None:
        self.store.append(event)

    def events(self, as_of: datetime | None = None) -> list[CivicEvent]:
        return self.store.all(as_of)

    def snapshot(self, as_of: datetime | None = None):
        return reconstruct(self.events(as_of))

    def issue(self, issue_id: str, as_of: datetime | None = None):
        states = self.snapshot(as_of)
        if issue_id in states:
            return states[issue_id]
        for state in states.values():
            if issue_id in state.merged_issue_ids:
                return state
        return None
