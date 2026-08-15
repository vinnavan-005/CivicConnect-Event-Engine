from __future__ import annotations

import os
from datetime import datetime

from fastapi import FastAPI, HTTPException, Query

from .models import CivicEvent, HealthResponse
from .service import CivicConnectEngine

app = FastAPI(title="CivicConnect Event Engine", version="1.0.0")
engine = CivicConnectEngine(os.getenv("CIVICCONNECT_DB", "civicconnect.db"))


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    states = engine.snapshot()
    return HealthResponse(status="ok", event_count=engine.store.count(), issue_count=len(states))


@app.post("/events", status_code=201)
def ingest_event(event: CivicEvent):
    try:
        engine.ingest(event)
    except Exception as exc:
        raise HTTPException(status_code=409, detail=f"could not ingest event: {exc}") from exc
    return {"accepted": True, "event_id": event.event_id}


@app.get("/issues")
def list_issues(as_of: datetime | None = Query(default=None)):
    return list(engine.snapshot(as_of).values())


@app.get("/issues/{issue_id}")
def get_issue(issue_id: str, as_of: datetime | None = Query(default=None)):
    state = engine.issue(issue_id, as_of)
    if state is None:
        raise HTTPException(status_code=404, detail="issue not found")
    return state


@app.get("/issues/{issue_id}/audit")
def get_audit(issue_id: str, as_of: datetime | None = Query(default=None)):
    state = engine.issue(issue_id, as_of)
    if state is None:
        raise HTTPException(status_code=404, detail="issue not found")
    return state.audit


@app.get("/events")
def list_events(as_of: datetime | None = Query(default=None)):
    return engine.events(as_of)
