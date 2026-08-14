"""Turn evidence bags into a short Chinese explanation."""

from __future__ import annotations

from portrait_evolve.events import BehaviorEvent, STRENGTH
from portrait_evolve.portrait import Portrait
from portrait_evolve.taxonomy import label_of


def explain(portrait: Portrait, events: list[BehaviorEvent] | None = None) -> dict:
    events = events or []
    lived_events = [event for event in events if not event.is_seed]
    return {
        "user_id": portrait.user_id,
        "headline": portrait.summary,
        "primary_tag": portrait.primary_tag.to_dict() if portrait.primary_tag else None,
        "confidence": portrait.confidence,
        "why": _why(portrait, lived_events),
        "recent_behaviors": [
            {
                "event_id": event.event_id,
                "type": event.type,
                "at": event.occurred_at,
                "text": event.text or event.competition or event.scene or event.type,
                "strength": STRENGTH[event.type],
            }
            for event in lived_events[-8:]
        ],
    }


def _why(portrait: Portrait, events: list[BehaviorEvent]) -> list[str]:
    reasons: list[str] = []
    if portrait.academic.skills or portrait.academic.domains:
        reasons.append("冷启动先用了课表和培养方案，这是学校记录，不是自我介绍。")
    if portrait.taste.domains or portrait.taste.tags:
        reasons.append("抖音兴趣给了一张初始口味卡，之后只作为先验，不再锁死标签。")

    scenes = _ranked(portrait.lived.scores("scenes"))
    if scenes:
        labels = "、".join(label_of("scene", key) for key, _ in scenes[:2])
        reasons.append(f"真正改变画像的是后来打完的局：{labels}。")

    offered = _ranked(portrait.lived.scores("roles_offered"))
    sought = _ranked(portrait.lived.scores("roles_sought"))
    if offered and sought:
        reasons.append(
            f"找搭子时自己常站{label_of('skill', offered[0][0])}，"
            f"缺的是{label_of('skill', sought[0][0])}——互补比自述更能说明这个人。"
        )
    elif offered:
        reasons.append(f"反复以{label_of('skill', offered[0][0])}身份进局，这项能力被行为校准上去了。")

    competitions = [event.competition for event in events if event.competition]
    unique = list(dict.fromkeys(competitions))
    if unique:
        reasons.append(f"参加过的比赛在说话：{'、'.join(unique[:3])}。")

    if portrait.confidence < 0.35:
        reasons.append("行为还不够多，标签会跟着下一次成局继续校准，不会一次定终身。")
    else:
        reasons.append("置信度来自累计行为质量，不是来自填过多少问卷。")
    return reasons


def _ranked(scores: dict[str, float]) -> list[tuple[str, float]]:
    return sorted(
        ((key, score) for key, score in scores.items() if score >= 0.12),
        key=lambda item: (-item[1], item[0]),
    )
