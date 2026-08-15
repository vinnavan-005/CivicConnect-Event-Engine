from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


SourceType = Literal["citizen", "worker", "official"]
ActionType = Literal["report", "assign", "resolve", "reopen", "comment"]


class Location(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)


class CivicEvent(BaseModel):
    event_id: str
    issue_id: str
    action: ActionType
    timestamp: datetime
    source_type: SourceType
    actor_id: str
    status: str = "open"
    assigned_worker_id: str | None = None
    comment: str | None = None
    location: Location
    metadata: dict[str, Any] = Field(default_factory=dict)


class EventInput(CivicEvent):
    pass


class AuditEntry(BaseModel):
    event_id: str
    action: ActionType
    timestamp: datetime
    source_type: SourceType
    decision_reason: str
    previous_state: dict[str, Any]
    new_state: dict[str, Any]


class IssueState(BaseModel):
    issue_id: str
    current_status: str
    assigned_worker_id: str | None
    history: list[CivicEvent]
    conflicts: list[dict[str, Any]]
    merged_issue_ids: list[str]
    audit: list[AuditEntry]


class ReplayRequest(BaseModel):
    as_of: datetime | None = None


class HealthResponse(BaseModel):
    status: str
    event_count: int
    issue_count: int
