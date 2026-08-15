from __future__ import annotations

from datetime import datetime, timezone
from math import asin, cos, radians, sin, sqrt
from typing import Any, Iterable

from .models import AuditEntry, CivicEvent, IssueState

SOURCE_PRIORITY = {"citizen": 1, "worker": 2, "official": 3}
MERGE_DISTANCE_METERS = 100.0
MERGE_WINDOW_SECONDS = 3600.0


def utc(dt: datetime) -> datetime:
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)


def distance_meters(a: CivicEvent, b: CivicEvent) -> float:
    lat1, lon1, lat2, lon2 = map(radians, [a.location.lat, a.location.lon, b.location.lat, b.location.lon])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    h = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return 2 * 6_371_000 * asin(sqrt(h))


class UnionFind:
    def __init__(self, values: Iterable[str]):
        self.parent = {value: value for value in values}

    def find(self, value: str) -> str:
        root = value
        while self.parent[root] != root:
            root = self.parent[root]
        while self.parent[value] != value:
            nxt = self.parent[value]
            self.parent[value] = root
            value = nxt
        return root

    def union(self, left: str, right: str) -> None:
        a, b = self.find(left), self.find(right)
        if a == b:
            return
        if a < b:
            self.parent[b] = a
        else:
            self.parent[a] = b


def resolve_identity(events: list[CivicEvent]) -> dict[str, str]:
    issue_ids = sorted({event.issue_id for event in events})
    uf = UnionFind(issue_ids)
    reports = sorted(
        [e for e in events if e.action == "report" and e.source_type == "citizen"],
        key=lambda e: (utc(e.timestamp), e.event_id),
    )
    for i, left in enumerate(reports):
        for right in reports[i + 1 :]:
            seconds = abs((utc(right.timestamp) - utc(left.timestamp)).total_seconds())
            if seconds > MERGE_WINDOW_SECONDS:
                if utc(right.timestamp) > utc(left.timestamp):
                    break
                continue
            if left.issue_id != right.issue_id and distance_meters(left, right) <= MERGE_DISTANCE_METERS:
                uf.union(left.issue_id, right.issue_id)
    return {issue_id: uf.find(issue_id) for issue_id in issue_ids}


def choose_winner(events: list[CivicEvent]) -> CivicEvent | None:
    if not events:
        return None
    return sorted(
        events,
        key=lambda e: (-SOURCE_PRIORITY[e.source_type], -utc(e.timestamp).timestamp(), e.event_id),
    )[0]


def reconstruct(events: list[CivicEvent]) -> dict[str, IssueState]:
    if not events:
        return {}
    aliases = resolve_identity(events)
    grouped: dict[str, list[CivicEvent]] = {}
    for event in events:
        grouped.setdefault(aliases[event.issue_id], []).append(event)

    states: dict[str, IssueState] = {}
    for canonical_id, group in sorted(grouped.items()):
        history = sorted(group, key=lambda e: (utc(e.timestamp), e.event_id))
        assignment_events = [e for e in history if e.action == "assign" and e.assigned_worker_id]
        status_winner = choose_winner(history)
        assignment_winner = choose_winner(assignment_events)
        previous = {"current_status": None, "assigned_worker_id": None}
        audit: list[AuditEntry] = []

        for index, event in enumerate(history):
            prefix = history[: index + 1]
            pw_status = choose_winner(prefix)
            pw_assign = choose_winner([e for e in prefix if e.action == "assign" and e.assigned_worker_id])
            new = {
                "current_status": pw_status.status if pw_status else None,
                "assigned_worker_id": pw_assign.assigned_worker_id if pw_assign else None,
            }
            if new != previous:
                reason = "state update applied deterministically by source priority, timestamp, then event_id"
                if event.action == "assign":
                    reason = "assignment applied using official > worker > citizen, then latest timestamp, then lower event_id"
                elif event.action == "resolve":
                    reason = "resolution event applied using deterministic event precedence"
                if aliases[event.issue_id] != event.issue_id:
                    reason += "; report identity-merged into canonical issue"
                audit.append(
                    AuditEntry(
                        event_id=event.event_id,
                        action=event.action,
                        timestamp=event.timestamp,
                        source_type=event.source_type,
                        decision_reason=reason,
                        previous_state=previous.copy(),
                        new_state=new.copy(),
                    )
                )
            previous = new

        conflicts: list[dict[str, Any]] = []
        workers = sorted({e.assigned_worker_id for e in assignment_events if e.assigned_worker_id})
        if len(workers) > 1 and assignment_winner:
            conflicts.append({
                "type": "assignment",
                "candidates": workers,
                "winner_event_id": assignment_winner.event_id,
                "winner_worker_id": assignment_winner.assigned_worker_id,
                "reason": "official source preferred, then latest timestamp, then lower event_id",
            })
        statuses = sorted({e.status for e in history})
        if len(statuses) > 1 and status_winner:
            conflicts.append({
                "type": "status",
                "candidates": statuses,
                "winner_event_id": status_winner.event_id,
                "winner_status": status_winner.status,
                "reason": "official source preferred, then latest timestamp, then lower event_id",
            })

        states[canonical_id] = IssueState(
            issue_id=canonical_id,
            current_status=previous["current_status"] or "open",
            assigned_worker_id=previous["assigned_worker_id"],
            history=history,
            conflicts=conflicts,
            merged_issue_ids=sorted({event.issue_id for event in group}),
            audit=audit,
        )
    return states
