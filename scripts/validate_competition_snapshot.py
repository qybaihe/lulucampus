from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from onemore.modules.competitions.schemas import CompetitionSnapshot


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="校验可入库赛事快照")
    parser.add_argument("path", type=Path)
    parser.add_argument(
        "--as-of",
        type=datetime.fromisoformat,
        default=None,
        help="验收时点，ISO 8601；用于检查报名截止是否仍有效",
    )
    return parser.parse_args()


def validate(path: Path, as_of: datetime | None) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    snapshot = CompetitionSnapshot.model_validate(payload)
    keys = [item.external_key for item in snapshot.items]
    duplicates = sorted(key for key, count in Counter(keys).items() if count > 1)
    if duplicates:
        raise ValueError(f"external_key 重复: {duplicates}")

    stage_timestamps = 0
    for item in snapshot.items:
        for field_name in ("source_url", "registration_url"):
            url = str(getattr(item, field_name))
            if urlparse(url).scheme != "https":
                raise ValueError(f"{item.external_key}.{field_name} 不是 HTTPS")
        if not item.registration_instructions:
            raise ValueError(f"{item.external_key} 缺少报名操作说明")
        if item.verified_at is None:
            raise ValueError(f"{item.external_key} 缺少 verified_at")
        if as_of and item.registration_deadline and item.registration_deadline <= as_of:
            raise ValueError(f"{item.external_key} 在验收时点已过报名截止")
        for stage in item.stages:
            start = stage.get("start_at")
            end = stage.get("end_at")
            for value in (start, end):
                if value is None:
                    continue
                parsed = datetime.fromisoformat(value)
                if parsed.tzinfo is None:
                    raise ValueError(f"{item.external_key} 赛程时间缺少时区: {value}")
                stage_timestamps += 1
            if start and end and datetime.fromisoformat(start) > datetime.fromisoformat(end):
                raise ValueError(f"{item.external_key} 赛程开始时间晚于结束时间")

    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return {
        "snapshot_version": snapshot.snapshot_version,
        "items": len(snapshot.items),
        "external_key_duplicates": len(duplicates),
        "stage_timestamps": stage_timestamps,
        "team_forming": sum(item.team_size_max > 1 for item in snapshot.items),
        "prep_partner": sum(item.team_size_max == 1 for item in snapshot.items),
        "recommendation_tiers": dict(
            sorted(Counter(item.recommendation_tier for item in snapshot.items).items())
        ),
        "sha256": digest,
    }


if __name__ == "__main__":
    args = parse_args()
    print(json.dumps(validate(args.path, args.as_of), ensure_ascii=False, indent=2))
