# CivicConnect Event Engine

A standalone deterministic civic-issue event engine. It is intentionally independent of `SIH_v8`.

## What is implemented

- Append-only SQLite event store
- Deterministic reconstruction from event history
- Source precedence: `official > worker > citizen`
- Deterministic timestamp and event-id tie breakers
- Citizen-report identity merging within 100m / 1 hour
- Assignment and status conflict records
- Explainable audit trail
- Time-travel replay with `as_of`
- FastAPI API
- CLI
- Pytest coverage for core deterministic behavior

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn civicconnect.api:app --reload
```

API docs appear at `/docs`.

## CLI

```bash
python -m civicconnect.cli ingest fixtures/sample_events.json
python -m civicconnect.cli snapshot
python -m civicconnect.cli issue ISSUE-1
```

## Event example

```json
{
  "event_id": "evt-001",
  "issue_id": "ISSUE-1",
  "action": "report",
  "timestamp": "2026-08-15T09:00:00Z",
  "source_type": "citizen",
  "actor_id": "citizen-1",
  "status": "open",
  "assigned_worker_id": null,
  "comment": "Streetlight is out",
  "location": {"lat": 13.0827, "lon": 80.2707},
  "metadata": {}
}
```

## API

- `GET /health`
- `POST /events`
- `GET /events`
- `GET /issues`
- `GET /issues/{issue_id}`
- `GET /issues/{issue_id}/audit`

Every read can accept `?as_of=<ISO timestamp>` for deterministic replay.
