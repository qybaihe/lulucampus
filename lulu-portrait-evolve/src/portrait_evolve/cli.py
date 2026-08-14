"""Replay, report, compare, list models, or serve the HTTP API."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from portrait_evolve.affinity import score_pair
from portrait_evolve.events import BehaviorEvent
from portrait_evolve.explain import explain
from portrait_evolve.inventory import inventory
from portrait_evolve.models import model_card
from portrait_evolve.report import build_report, render_markdown
from portrait_evolve.store import PortraitStore
from portrait_evolve.trajectory import trace


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="portrait-evolve")
    sub = parser.add_subparsers(dest="cmd", required=True)

    replay = sub.add_parser("replay", help="回放时间线，打印进化后的画像卡")
    replay.add_argument("path", type=Path)
    replay.add_argument("--json", action="store_true")

    report = sub.add_parser("report", help="输出完整进化报告（轨迹 / 模型 / 体量）")
    report.add_argument("path", type=Path)
    report.add_argument("--json", action="store_true")
    report.add_argument("--llm", action="store_true", help="尝试用可选 LLM 改写叙事，失败回退模板")

    compare = sub.add_parser("compare", help="对照两份时间线的亲和分数")
    compare.add_argument("left", type=Path)
    compare.add_argument("right", type=Path)
    compare.add_argument("--json", action="store_true")

    sub.add_parser("models", help="打印闭环内 / 上游 / 可选模型清单")
    sub.add_parser("inventory", help="打印模块、事件、代码体量")

    serve = sub.add_parser("serve", help="启动 HTTP 服务")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8787)
    serve.add_argument("--db", default=":memory:")

    args = parser.parse_args(argv)
    if args.cmd == "replay":
        return _replay(args.path, as_json=args.json)
    if args.cmd == "report":
        return _report(args.path, as_json=args.json, use_llm=args.llm)
    if args.cmd == "compare":
        return _compare(args.left, args.right, as_json=args.json)
    if args.cmd == "models":
        json.dump(model_card(), sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
        return 0
    if args.cmd == "inventory":
        json.dump(inventory(), sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
        return 0
    return _serve(args.host, args.port, args.db)


def _load_timeline(path: Path) -> tuple[str, str | None, list[BehaviorEvent]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    user_id = str(payload.get("user_id") or payload["events"][0]["user_id"])
    events = [
        BehaviorEvent.from_dict({**raw, "user_id": raw.get("user_id") or user_id})
        for raw in payload["events"]
    ]
    return user_id, payload.get("display_name"), events


def _replay(path: Path, *, as_json: bool) -> int:
    user_id, name, events = _load_timeline(path)
    store = PortraitStore()
    store.ingest_many(events)
    portrait = store.get(user_id)
    assert portrait is not None
    report = {
        "display_name": name,
        "portrait": portrait.public_view(),
        "explain": explain(portrait, store.events(user_id)),
    }
    if as_json:
        json.dump(report, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
        return 0
    view = report["portrait"]
    print(f"{name or user_id}  ·  {view['primary_tag']}  ·  {view.get('stage')}")
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


def _report(path: Path, *, as_json: bool, use_llm: bool) -> int:
    user_id, name, events = _load_timeline(path)
    report = build_report(user_id, events, display_name=name, use_llm=use_llm)
    if as_json:
        json.dump(report, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
        return 0
    sys.stdout.write(render_markdown(report))
    if not report["portrait"]["summary"].endswith("\n"):
        sys.stdout.write("\n")
    return 0


def _compare(left_path: Path, right_path: Path, *, as_json: bool) -> int:
    left_id, left_name, left_events = _load_timeline(left_path)
    right_id, right_name, right_events = _load_timeline(right_path)
    left, _ = trace(left_id, left_events)
    right, _ = trace(right_id, right_events)
    result = {
        "left": {"user_id": left_id, "display_name": left_name, "portrait": left.public_view()},
        "right": {"user_id": right_id, "display_name": right_name, "portrait": right.public_view()},
        "affinity": score_pair(left, right),
    }
    if as_json:
        json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
        return 0
    aff = result["affinity"]
    print(f"{left_name}  ×  {right_name}")
    print(f"affinity={aff['score']}  mode={aff['mode']}")
    for reason in aff["reasons"]:
        print(f"  - {reason}")
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
