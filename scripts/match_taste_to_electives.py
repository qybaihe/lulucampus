#!/usr/bin/env python3
"""Match Douyin taste persona to JWXT public electives (and related lists).

Examples:
  # Using live CLI (needs valid JWXT session):
  .venv/bin/python scripts/match_taste_to_electives.py \\
    --persona artifacts/taste/persona-demo.json --live --categories 公选,专选,跨专业选修

  # Using a pre-fetched course catalog JSON (items[] or raw list):
  .venv/bin/python scripts/match_taste_to_electives.py \\
    --persona artifacts/taste/persona-demo.json --catalog electives.json
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from onemore.modules.taste_profile.elective_match import (  # noqa: E402
    match_electives_to_persona,
)


def load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def extract_items(payload: object) -> list[dict]:
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    if isinstance(payload, dict):
        items = payload.get("items")
        if isinstance(items, list):
            return [row for row in items if isinstance(row, dict)]
    return []


def fetch_live_catalog(
    *,
    categories: list[str],
    keywords: list[str],
    page_size: int,
    cli: str,
) -> list[dict]:
    courses: list[dict] = []
    seen: set[str] = set()

    def add_items(items: list[dict]) -> None:
        for item in items:
            key = f"{item.get('code')}|{item.get('title')}|{item.get('time')}"
            if key in seen:
                continue
            seen.add(key)
            courses.append(item)

    for category in categories:
        cmd = [
            cli,
            "jwxt",
            "course-selection",
            "list",
            "--category",
            category,
            "--page",
            "1",
            "--size",
            str(page_size),
            "--json",
        ]
        print(f"[live] {' '.join(cmd)}", file=sys.stderr)
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if proc.returncode != 0:
            print(proc.stderr or proc.stdout, file=sys.stderr)
            continue
        try:
            payload = json.loads(proc.stdout)
        except json.JSONDecodeError:
            print(f"[live] bad json for category={category}", file=sys.stderr)
            continue
        add_items(extract_items(payload))
        print(
            f"[live] category={category} got {len(extract_items(payload))} window={payload.get('selectionWindow')}",
            file=sys.stderr,
        )

    # Keyword probes help when category lists are sparse / slow.
    for keyword in keywords:
        cmd = [
            cli,
            "jwxt",
            "course-selection",
            "list",
            "--keyword",
            keyword,
            "--page",
            "1",
            "--size",
            str(min(page_size, 30)),
            "--json",
        ]
        print(f"[live] keyword={keyword}", file=sys.stderr)
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if proc.returncode != 0:
            continue
        try:
            payload = json.loads(proc.stdout)
        except json.JSONDecodeError:
            continue
        add_items(extract_items(payload))

    return courses


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--persona", type=Path, required=True)
    parser.add_argument("--catalog", type=Path, default=None)
    parser.add_argument("--live", action="store_true")
    parser.add_argument(
        "--categories",
        default="公选,学院公选,专选,跨专业选修",
        help="comma-separated course-selection categories for --live",
    )
    parser.add_argument(
        "--keywords",
        default="人工智能,设计,摄影,创业,心理,运动,科技,媒体,创新",
        help="extra keyword probes for --live",
    )
    parser.add_argument("--cli", default="sysu-anything")
    parser.add_argument("--limit", type=int, default=12)
    parser.add_argument("--min-score", type=float, default=1.2)
    parser.add_argument("--page-size", type=int, default=50)
    parser.add_argument("-o", "--output", type=Path, default=None)
    args = parser.parse_args()

    persona_raw = load_json(args.persona)
    if not isinstance(persona_raw, dict):
        raise SystemExit("persona must be a JSON object")

    courses: list[dict] = []
    if args.catalog:
        courses.extend(extract_items(load_json(args.catalog)))
    if args.live:
        courses.extend(
            fetch_live_catalog(
                categories=[c.strip() for c in args.categories.split(",") if c.strip()],
                keywords=[k.strip() for k in args.keywords.split(",") if k.strip()],
                page_size=args.page_size,
                cli=args.cli,
            )
        )
    if not courses:
        raise SystemExit("no courses loaded; pass --catalog and/or --live")

    # Dedup after merge
    dedup: dict[str, dict] = {}
    for item in courses:
        key = f"{item.get('code')}|{item.get('title')}"
        dedup[key] = item
    courses = list(dedup.values())

    result = match_electives_to_persona(
        persona_raw,
        courses,
        limit=args.limit,
        min_score=args.min_score,
    )
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
        print(f"wrote {args.output}", file=sys.stderr)
    print(text)


if __name__ == "__main__":
    main()
