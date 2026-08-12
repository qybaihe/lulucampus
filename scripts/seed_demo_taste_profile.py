#!/usr/bin/env python3
"""把剧组画像写入测试账号（走 service 正式落库路径）。

`onemore-seed` 已经会写入六人画像。本脚本用于单独重刷。

用法：
  uv run python scripts/seed_demo_taste_profile.py            # 写入/更新全部剧组
  uv run python scripts/seed_demo_taste_profile.py --stdout   # 打印林予安 API 视图
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from onemore.core.database import SessionLocal  # noqa: E402
from onemore.db.demo_cast import CAST_BY_ID, CAST_TASTE, LIN  # noqa: E402
from onemore.db.models import TasteImportSession  # noqa: E402
from onemore.modules.taste_profile import service  # noqa: E402


def main() -> None:
    stdout_only = "--stdout" in sys.argv
    db = SessionLocal()
    try:
        now = datetime.now(UTC)
        for user_id, result in CAST_TASTE.items():
            import_id = f"imp_cast_{user_id}"
            session = db.get(TasteImportSession, import_id)
            if session is None:
                session = TasteImportSession(
                    id=import_id,
                    user_id=user_id,
                    status=service.READY,
                    expires_at=now + timedelta(days=30),
                )
                db.add(session)
            session.status = service.READY
            session.authenticated_at = session.authenticated_at or now
            session.completed_at = now
            spec = CAST_BY_ID.get(user_id)
            session.source_profile = {
                "nickname": spec.display_name if spec else user_id,
                "avatar_url": None,
                "uid": f"cast-{user_id}",
            }
            sample = result.get("sample") or {}
            session.progress = {
                "phase": "ready",
                "current": sample.get("items") or 0,
                "total": sample.get("items") or 0,
                "percent": 100.0,
                "message": "画像已生成",
            }
            session.collection_summary = {
                "api_pages": 3,
                "items_collected": sample.get("items") or 0,
                "has_more": False,
            }
            session.questions = []
            session.result_snapshot = service.normalize_taste_result(result) or result
            profile = service.upsert_taste_profile(db, session, result)
            print(f"已写入 {user_id} 的演示画像：{profile.primary_tag.get('label')}")
        db.commit()
        if stdout_only:
            view = service.normalize_taste_result(CAST_TASTE[LIN])
            print(json.dumps(view, ensure_ascii=False, indent=2))
    finally:
        db.close()


if __name__ == "__main__":
    main()
