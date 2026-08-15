from __future__ import annotations

import argparse
import json
from datetime import datetime

from .models import CivicEvent
from .service import CivicConnectEngine


def main() -> None:
    parser = argparse.ArgumentParser(description="CivicConnect deterministic event engine")
    parser.add_argument("--db", default="civicconnect.db")
    sub = parser.add_subparsers(dest="command", required=True)
    ingest = sub.add_parser("ingest")
    ingest.add_argument("file")
    snapshot = sub.add_parser("snapshot")
    snapshot.add_argument("--as-of")
    issue = sub.add_parser("issue")
    issue.add_argument("issue_id")
    issue.add_argument("--as-of")
    args = parser.parse_args()
    engine = CivicConnectEngine(args.db)

    if args.command == "ingest":
        with open(args.file, encoding="utf-8") as fh:
            payload = json.load(fh)
        events = payload if isinstance(payload, list) else [payload]
        for raw in events:
            engine.ingest(CivicEvent.model_validate(raw))
        print(f"ingested {len(events)} event(s)")
    elif args.command == "snapshot":
        as_of = datetime.fromisoformat(args.as_of) if args.as_of else None
        print(json.dumps({k: v.model_dump(mode="json") for k, v in engine.snapshot(as_of).items()}, indent=2))
    elif args.command == "issue":
        as_of = datetime.fromisoformat(args.as_of) if args.as_of else None
        state = engine.issue(args.issue_id, as_of)
        if state is None:
            raise SystemExit("issue not found")
        print(json.dumps(state.model_dump(mode="json"), indent=2))


if __name__ == "__main__":
    main()
