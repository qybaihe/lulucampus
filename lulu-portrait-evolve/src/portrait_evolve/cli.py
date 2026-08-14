"""Replay a behavior timeline or serve the HTTP API."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from portrait_evolve.events import BehaviorEvent
from portrait_evolve.explain import explain
from portrait_evolve.store import PortraitStore


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="portrait-evolve")
    sub = parser.add_subparsers(dest="cmd", required=True)

    replay = sub.add_parser("replay", help="回放一份行为时间线，打印进化后的画像")
    replay.add_argument("path", type=Path)
    replay.add_argument("--json", action="store_true")

    serve = sub.add_parser("serve", help="启动 HTTP 服务")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8787)
    serve.add_argument("--db", default=":memory:")

    args = parser.parse_args(argv)
    if args.cmd == "replay":
        return _replay(args.path, as_json=args.json)
    return _serve(args.host, args.port, args.db)


def _replay(path: Path, *, as_json: bool) -> int:
    payload = json.loads(path.read_text(encoding="utf-8"))
    user_id = str(payload.get("user_id") or payload["events"][0]["user_id"])
    store = PortraitStore()
    events = [
        BehaviorEvent.from_dict({**raw, "user_id": raw.get("user_id") or user_id})
        for raw in payload["events"]
    ]
    store.ingest_many(events)
    portrait = store.get(user_id)
    assert portrait is not None
    report = {
        "display_name": payload.get("display_name"),
        "portrait": portrait.public_view(),
        "explain": explain(portrait, store.events(user_id)),
    }
    if as_json:
        json.dump(report, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
        return 0
    view = report["portrait"]
    print(f"{payload.get('display_name') or user_id}  ·  {view['primary_tag']}")
    print(view["summary"])
    print(f"confidence={view['confidence']}  events={view['event_count']}")
    print("domains:", ", ".join(item["label"] for item in view["interest_domains"]))
    print("offered:", ", ".join(item["label"] for item in view["roles_offered"]) or "—")
    print("sought: ", ", ".join(item["label"] for item in view["roles_sought"]) or "—")
    print("scenes: ", ", ".join(item["label"] for item in view["scenes"]) or "—")
    print("why:")
    for line in report["explain"]["why"]:
        print(f"  - {line}")
    return 0


def _serve(host: str, port: int, db: str) -> int:
    try:
        import uvicorn
    except ImportError:
        print("pip install .[api]", file=sys.stderr)
        return 1
    from portrait_evolve.api import create_app

    uvicorn.run(create_app(db), host=host, port=port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
