#!/usr/bin/env python3
"""把演示画像写入测试账号 u_demo_1（走 service 正式落库路径）。

直接调用 `service.upsert_taste_profile`，保证行结构、sample_summary 打包、
以及 Profile 上 taste:* 标签同步与真实扫码导入完全一致。

用法：
  uv run python scripts/seed_demo_taste_profile.py            # 写入/更新
  uv run python scripts/seed_demo_taste_profile.py --stdout   # 打印 API 视图
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
from onemore.db.models import TasteImportSession  # noqa: E402
from onemore.modules.taste_profile import service  # noqa: E402

DEMO_IMPORT_ID = "imp_demo_persona"
DEMO_USER_ID = "u_demo_1"

# 演示画像（用户提供的真实形象；副标签/领域分数为占位权重，主标签分数字段如实）。
DEMO_RESULT: dict = {
    "status": service.READY,
    "primary_tag": {"key": "explorer_builder", "label": "探索型 Builder", "score": 0.2963},
    "secondary_tags": [
        {"key": "knowledge_curator", "label": "知识策展人", "score": 0.24},
        {"key": "aesthetic_observer", "label": "审美观察者", "score": 0.21},
        {"key": "strategy_player", "label": "策略玩家", "score": 0.18},
    ],
    "interest_domains": [
        {"key": "career_growth", "label": "成长/职业", "score": 0.32},
        {"key": "knowledge_method", "label": "知识方法", "score": 0.27},
        {"key": "ai_programming", "label": "AI/编程", "score": 0.24},
        {"key": "tech_devices", "label": "科技数码", "score": 0.20},
    ],
    "interest_facets": [
        {"domain": "ai_programming", "facet": "hackathon_ai", "label": "黑客松/AI创变"},
        {"domain": "tech_devices", "facet": "huaqiangbei_hardware", "label": "华强北硬件"},
        {"domain": "health_sports", "facet": "sports_rehab", "label": "运动康复"},
        {"domain": "visual_creation", "facet": "creator_ip", "label": "自媒体 IP"},
    ],
    "dimensions": {
        "career_growth": 0.32,
        "knowledge_method": 0.27,
        "ai_programming": 0.24,
        "tech_devices": 0.20,
    },
    "summary": "一个把兴趣当项目来做的探索者：热衷黑客松与AI实践，也享受跑步康复和旅行取景……",
    "persona": "他是一位自带节奏的实践者。在黑客松里享受极限开发……",
    "matching_hints": ["组队黑客松", "跑步康复", "编程工具", "逛科技市集"],
    "confidence": 0.86,
    "calibrated": False,
    # 与 analyzer 真实输出一致：persona / matching_hints / interest_facets 收在 sample 里，
    # _profile_result 从 sample_summary 读取它们。
    "sample": {
        "items": 260,
        "unique_authors": 20,
        "api_pages": 3,
        "generation": "llm",
        "llm_provider": "opencode-go",
        "llm_model": "deepseek-v4-flash",
        "persona": "他是一位自带节奏的实践者。在黑客松里享受极限开发……",
        "matching_hints": ["组队黑客松", "跑步康复", "编程工具", "逛科技市集"],
        "interest_facets": [
            {"domain": "ai_programming", "facet": "hackathon_ai", "label": "黑客松/AI创变"},
            {"domain": "tech_devices", "facet": "huaqiangbei_hardware", "label": "华强北硬件"},
            {"domain": "health_sports", "facet": "sports_rehab", "label": "运动康复"},
            {"domain": "visual_creation", "facet": "creator_ip", "label": "自媒体 IP"},
        ],
    },
    "model_version": "taste-v2",
    "visibility": "members",
}


def main() -> None:
    stdout_only = "--stdout" in sys.argv
    db = SessionLocal()
    try:
        now = datetime.now(UTC)
        session = db.get(TasteImportSession, DEMO_IMPORT_ID)
        if session is None:
            session = TasteImportSession(
                id=DEMO_IMPORT_ID,
                user_id=DEMO_USER_ID,
                status=service.READY,
                expires_at=now + timedelta(days=1),
            )
            db.add(session)
        session.status = service.READY
        session.authenticated_at = session.authenticated_at or now
        session.completed_at = now
        session.source_profile = {
            "nickname": "演示用户",
            "avatar_url": None,
            "uid": "3913884925184093",
        }
        session.progress = {
            "phase": "ready",
            "current": 260,
            "total": 260,
            "percent": 100.0,
            "message": "画像已生成",
        }
        session.collection_summary = {
            "api_pages": 3,
            "items_collected": 260,
            "has_more": False,
        }
        session.questions = []
        session.result_snapshot = service.normalize_taste_result(DEMO_RESULT) or DEMO_RESULT

        profile = service.upsert_taste_profile(db, session, DEMO_RESULT)
        db.commit()

        view = service.normalize_taste_result(DEMO_RESULT)
        print(f"已写入 {DEMO_USER_ID} 的演示画像：{profile.primary_tag.get('label')}")
        if stdout_only:
            print(json.dumps(view, ensure_ascii=False, indent=2))
    finally:
        db.close()


if __name__ == "__main__":
    main()
