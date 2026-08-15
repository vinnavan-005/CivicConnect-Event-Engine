from datetime import datetime, timezone

from civicconnect.engine import distance_meters, reconstruct
from civicconnect.models import CivicEvent, Location


def event(eid, issue, action, source, ts, lat=13.0827, lon=80.2707, status="open", worker=None):
    return CivicEvent(
        event_id=eid, issue_id=issue, action=action,
        timestamp=datetime.fromisoformat(ts).replace(tzinfo=timezone.utc),
        source_type=source, actor_id=source, status=status,
        assigned_worker_id=worker, location=Location(lat=lat, lon=lon),
    )


def test_official_assignment_beats_worker_and_citizen():
    events = [
        event("1", "I", "assign", "citizen", "2026-08-15T10:00:00", worker="A"),
        event("2", "I", "assign", "worker", "2026-08-15T10:01:00", worker="B"),
        event("3", "I", "assign", "official", "2026-08-15T09:00:00", worker="C"),
    ]
    state = reconstruct(events)["I"]
    assert state.assigned_worker_id == "C"
    assert state.conflicts[0]["winner_event_id"] == "3"


def test_identity_merge_within_threshold():
    events = [
        event("1", "A", "report", "citizen", "2026-08-15T10:00:00"),
        event("2", "B", "report", "citizen", "2026-08-15T10:30:00", lat=13.0828),
    ]
    states = reconstruct(events)
    assert len(states) == 1
    assert states["A"].merged_issue_ids == ["A", "B"]


def test_identity_does_not_merge_outside_distance():
    events = [
        event("1", "A", "report", "citizen", "2026-08-15T10:00:00"),
        event("2", "B", "report", "citizen", "2026-08-15T10:30:00", lat=13.1),
    ]
    assert len(reconstruct(events)) == 2


def test_reconstruction_is_order_independent():
    events = [
        event("1", "I", "report", "citizen", "2026-08-15T10:00:00"),
        event("2", "I", "resolve", "worker", "2026-08-15T11:00:00", status="resolved"),
        event("3", "I", "reopen", "official", "2026-08-15T12:00:00", status="open"),
    ]
    a = reconstruct(events)["I"].model_dump(mode="json")
    b = reconstruct(list(reversed(events)))["I"].model_dump(mode="json")
    assert a == b


def test_time_travel_excludes_future_events():
    events = [
        event("1", "I", "report", "citizen", "2026-08-15T10:00:00"),
        event("2", "I", "resolve", "official", "2026-08-15T12:00:00", status="resolved"),
    ]
    state = reconstruct([e for e in events if e.timestamp <= datetime.fromisoformat("2026-08-15T11:00:00+00:00")])["I"]
    assert state.current_status == "open"


def test_distance_is_in_meters():
    a = event("1", "A", "report", "citizen", "2026-08-15T10:00:00")
    b = event("2", "B", "report", "citizen", "2026-08-15T10:00:00", lat=13.0828)
    assert 0 < distance_meters(a, b) < 100
