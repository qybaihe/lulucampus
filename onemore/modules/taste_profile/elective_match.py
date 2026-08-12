"""Match campus electives to a Douyin / taste persona (pure scoring, no I/O)."""

from __future__ import annotations

import re
from typing import Any

# Persona facet → course-title keywords (Chinese + English).
PERSONA_KEYWORD_BAGS: dict[str, tuple[str, ...]] = {
    "ai_programming": (
        "人工智能",
        "大模型",
        "ai",
        "编程",
        "软件",
        "算法",
        "数据",
        "计算",
        "智能",
        "机器学习",
        "深度学习",
        "python",
        "开源",
        "信息",
        "网络",
        "系统",
        "区块链",
        "图形",
        "游戏",
        "数字图像",
    ),
    "tech_devices": (
        "科技",
        "数码",
        "电子",
        "硬件",
        "通信",
        "物联网",
        "机器人",
        "工程",
        "创新",
        "创客",
        "设计思维",
    ),
    "growth_career": (
        "创业",
        "职业",
        "领导",
        "管理",
        "商业",
        "创新创业",
        "沟通",
        "表达",
        "批判",
        "思维",
        "写作",
        "演讲",
        "项目",
        "产品",
    ),
    "knowledge_method": (
        "方法",
        "研究",
        "学术",
        "逻辑",
        "科学",
        "统计",
        "心理",
        "认知",
        "学习",
        "教育",
        "文献",
        "论文",
    ),
    "aesthetic": (
        "审美",
        "艺术",
        "设计",
        "摄影",
        "影像",
        "视觉",
        "电影",
        "美术",
        "音乐",
        "戏剧",
        "媒体",
        "传播",
        "创意",
        "建筑",
        "景观",
    ),
    "sports_health": (
        "体育",
        "运动",
        "跑步",
        "康复",
        "健康",
        "体能",
        "瑜伽",
        "球",
        "健身",
        "户外",
        "心理",
    ),
    "travel_media": (
        "旅行",
        "旅游",
        "地理",
        "文化",
        "城市",
        "自媒体",
        "新媒体",
        "短视频",
        "叙事",
        "纪录",
        "采访",
    ),
    "builder_hackathon": (
        "黑客",
        "实践",
        "实训",
        "创新",
        "创业",
        "项目",
        "工程",
        "开发",
        "制作",
        "工作坊",
        "workshop",
        "竞赛",
    ),
}

DOMAIN_LABEL_TO_BAG: dict[str, str] = {
    "成长/职业": "growth_career",
    "知识方法": "knowledge_method",
    "AI/编程": "ai_programming",
    "科技数码": "tech_devices",
    "AI / 编程 / 开源": "ai_programming",
    "科技 / 数码 / 设备": "tech_devices",
}


def _norm(text: str) -> str:
    return re.sub(r"\s+", "", text.casefold())


def build_signal_weights(persona: dict[str, Any]) -> dict[str, float]:
    """Expand persona fields into weighted keyword signals."""

    weights: dict[str, float] = {}

    def add(word: str, w: float) -> None:
        key = _norm(word)
        if len(key) < 2:
            return
        weights[key] = weights.get(key, 0.0) + w

    primary = persona.get("primary_tag") or persona.get("主标签") or ""
    if isinstance(primary, dict):
        add(str(primary.get("label") or primary.get("key") or ""), 2.2)
    else:
        add(str(primary), 2.2)
        # strip score suffix like （0.2963）
        add(re.sub(r"[（(][^）)]*[）)]", "", str(primary)), 2.0)

    for tag in persona.get("secondary_tags") or persona.get("副标签") or []:
        if isinstance(tag, dict):
            add(str(tag.get("label") or tag.get("key") or ""), 1.4)
        else:
            for part in re.split(r"[、,，/|]", str(tag)):
                add(part, 1.4)

    domains = persona.get("interest_domains") or persona.get("领域") or []
    if isinstance(domains, str):
        domains = re.split(r"[、,，/|]", domains)
    for domain in domains:
        label = domain.get("label") if isinstance(domain, dict) else str(domain)
        label = str(label).strip()
        add(label, 1.6)
        bag_key = DOMAIN_LABEL_TO_BAG.get(label)
        if bag_key:
            for kw in PERSONA_KEYWORD_BAGS[bag_key]:
                add(kw, 1.1)

    for facet in persona.get("interest_facets") or persona.get("子兴趣") or []:
        if isinstance(facet, dict):
            add(str(facet.get("label") or facet.get("facet") or ""), 1.8)
        else:
            for part in re.split(r"[、,，/|]", str(facet)):
                add(part, 1.8)

    for hint in persona.get("matching_hints") or persona.get("匹配提示") or []:
        for part in re.split(r"[、,，/|\s]+", str(hint)):
            add(part, 1.5)

    for field in ("summary", "摘要", "persona", "人设"):
        text = persona.get(field)
        if not text:
            continue
        # Pull meaningful 2-6 char Chinese chunks / known keywords only via bag overlap later;
        # also add a few explicit tokens from text by bag scan.
        blob = _norm(str(text))
        for bag in PERSONA_KEYWORD_BAGS.values():
            for kw in bag:
                if _norm(kw) in blob:
                    add(kw, 0.9)

    # Always inject builder / AI bags lightly when primary mentions Builder / 探索
    primary_text = _norm(str(primary))
    if "builder" in primary_text or "探索" in primary_text:
        for kw in PERSONA_KEYWORD_BAGS["builder_hackathon"]:
            add(kw, 0.8)
        for kw in PERSONA_KEYWORD_BAGS["ai_programming"]:
            add(kw, 0.7)
    if "策展" in primary_text or "审美" in _norm(str(persona.get("副标签") or "")):
        for kw in PERSONA_KEYWORD_BAGS["aesthetic"]:
            add(kw, 0.7)
    if "策略" in _norm(str(persona.get("副标签") or "")):
        for kw in PERSONA_KEYWORD_BAGS["growth_career"]:
            add(kw, 0.5)

    return weights


def enrich_competition(course: dict[str, Any]) -> dict[str, Any]:
    """Derive selected / fill rate / competition label from capacity+remaining."""

    capacity = course.get("capacity")
    remaining = course.get("remaining")
    selected = course.get("selected")
    if not isinstance(selected, (int, float)):
        selected = None
    if (
        selected is None
        and isinstance(capacity, (int, float))
        and isinstance(remaining, (int, float))
    ):
        selected = max(0, int(capacity) - int(remaining))

    fill_rate: float | None = None
    if isinstance(capacity, (int, float)) and capacity > 0 and selected is not None:
        fill_rate = round(min(1.0, max(0.0, float(selected) / float(capacity))), 4)

    if fill_rate is None:
        level, label = "unknown", "名额未知"
    elif fill_rate >= 1.0 or (
        isinstance(remaining, (int, float)) and remaining <= 0
    ):
        level, label = "full", "已满"
    elif fill_rate >= 0.85:
        level, label = "high", "竞争激烈"
    elif fill_rate >= 0.55:
        level, label = "medium", "中等竞争"
    elif fill_rate >= 0.2:
        level, label = "low", "竞争温和"
    else:
        level, label = "empty", "几乎没人选"

    return {
        "selected": int(selected) if selected is not None else None,
        "capacity": int(capacity) if isinstance(capacity, (int, float)) else None,
        "remaining": int(remaining) if isinstance(remaining, (int, float)) else None,
        "fill_rate": fill_rate,
        "competition_level": level,
        "competition_label": label,
    }


def score_course(
    course: dict[str, Any],
    signal_weights: dict[str, float],
) -> tuple[float, list[str]]:
    hay = _norm(
        " ".join(
            str(course.get(k) or "")
            for k in ("code", "title", "category", "college", "campus", "teacher", "time")
        )
        + " "
        + " ".join(str(t) for t in (course.get("tags") or []) if t)
    )
    score = 0.0
    reasons: list[str] = []
    for token, weight in sorted(signal_weights.items(), key=lambda x: -x[1]):
        if token in hay:
            score += weight
            if len(reasons) < 4:
                reasons.append(token)

    competition = enrich_competition(course)
    remaining = competition.get("remaining")
    fill_rate = competition.get("fill_rate")
    # Soft preference for still-open seats; mild penalty when nearly full.
    if isinstance(remaining, int) and remaining > 0:
        score += 0.15
    if isinstance(fill_rate, float):
        if fill_rate >= 0.95:
            score -= 0.35
        elif fill_rate >= 0.85:
            score -= 0.15
        elif 0.15 <= fill_rate <= 0.7:
            # Some demand validates the course without being too risky.
            score += 0.05
    if course.get("selectable") is True:
        score += 0.1
    # Prefer public electives slightly when matching 公选 intent.
    category = str(course.get("category") or "")
    if "公选" in category or "通识" in category:
        score += 0.2

    return score, reasons


def match_electives_to_persona(
    persona: dict[str, Any],
    courses: list[dict[str, Any]],
    *,
    limit: int = 12,
    min_score: float = 1.2,
) -> dict[str, Any]:
    signals = build_signal_weights(persona)
    ranked: list[dict[str, Any]] = []
    for course in courses:
        score, reasons = score_course(course, signals)
        if score < min_score:
            continue
        competition = enrich_competition(course)
        ranked.append(
            {
                **course,
                "selected": competition["selected"],
                "fill_rate": competition["fill_rate"],
                "competition_level": competition["competition_level"],
                "competition_label": competition["competition_label"],
                "match_score": round(score, 3),
                "match_reasons": reasons,
            }
        )
    def _remaining_sort_key(row: dict[str, Any]) -> float:
        remaining = row.get("remaining")
        return -float(remaining) if isinstance(remaining, (int, float)) else 1.0

    ranked.sort(
        key=lambda row: (
            -float(row["match_score"]),
            _remaining_sort_key(row),
            str(row.get("code") or ""),
        )
    )
    top = ranked[:limit]
    levels: dict[str, int] = {}
    for row in ranked:
        lvl = str(row.get("competition_level") or "unknown")
        levels[lvl] = levels.get(lvl, 0) + 1
    return {
        "ok": True,
        "source": "taste_elective_match",
        "persona_signals": len(signals),
        "courses_scored": len(courses),
        "matched": len(ranked),
        "competition_summary": levels,
        "items": top,
        "search_hints": _search_hints(signals),
    }


def _search_hints(signals: dict[str, float], limit: int = 12) -> list[str]:
    # Prefer human-readable tokens for JWXT keyword search.
    ordered = sorted(signals.items(), key=lambda x: -x[1])
    hints: list[str] = []
    for token, _ in ordered:
        # skip pure ascii noise shorter than 3 except ai
        if token.isascii() and token not in {"ai", "python", "llm", "gpt"} and len(token) < 4:
            continue
        if token not in hints:
            hints.append(token)
        if len(hints) >= limit:
            break
    return hints
