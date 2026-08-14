"""Deterministic persona text. Optional LLM may rewrite, never score."""

from __future__ import annotations

from typing import Any

from portrait_evolve.metrics import STAGE_LABELS, infer_stage
from portrait_evolve.portrait import Portrait
from portrait_evolve.taxonomy import label_of


def _top(scores: dict[str, float], limit: int = 2) -> list[str]:
    ranked = sorted(
        ((key, score) for key, score in scores.items() if score >= 0.12),
        key=lambda item: (-item[1], item[0]),
    )
    return [key for key, _ in ranked[:limit]]


def render(portrait: Portrait) -> dict[str, Any]:
    primary = portrait.primary_tag.label if portrait.primary_tag else "还在观察中的同学"
    domains = _blend(portrait, "domains")
    domain_labels = [label_of("domain", key) for key in _top(domains, 3)]
    offered = [label_of("skill", key) for key in _top(portrait.lived.scores("roles_offered"), 2)]
    sought = [label_of("skill", key) for key in _top(portrait.lived.scores("roles_sought"), 2)]
    scenes = [label_of("scene", key) for key in _top(portrait.lived.scores("scenes"), 2)]
    stage = infer_stage(portrait)

    persona = _persona(primary, domain_labels, offered, sought, scenes, stage)
    hints = _hints(offered, sought, scenes, domain_labels)
    ice = _icebreakers(domain_labels, scenes, offered)
    return {
        "persona": persona,
        "matching_hints": hints,
        "icebreakers": ice,
        "stage": stage,
        "stage_label": STAGE_LABELS[stage],
        "source": "template",
    }


def _blend(portrait: Portrait, field_name: str) -> dict[str, float]:
    blended: dict[str, float] = {}
    for weight, layer in (
        (0.25, portrait.academic),
        (0.30, portrait.taste),
        (0.45, portrait.lived),
    ):
        for key, score in layer.scores(field_name).items():
            blended[key] = blended.get(key, 0.0) + weight * score
    return blended


def _persona(
    primary: str,
    domains: list[str],
    offered: list[str],
    sought: list[str],
    scenes: list[str],
    stage: str,
) -> str:
    head = f"更像一位{primary}。"
    if stage == "prior_only":
        return head + "现在还只是课表和口味先验，下一场成局才会开始改写这张卡。"
    body: list[str] = []
    if domains:
        body.append(f"最近把时间压在{'、'.join(domains)}")
    if offered:
        body.append(f"自己进局时常站{' / '.join(offered)}")
    if sought:
        body.append(f"组队时会去找{'、'.join(sought)}——缺的位置说明她怎么看一支队")
    if scenes:
        body.append(f"真正打完、愿意再来的是{'、'.join(scenes)}")
    return head + "；".join(body) + "。画像会跟着下一场局继续校准，不会在导入那天定终身。"


def _hints(
    offered: list[str], sought: list[str], scenes: list[str], domains: list[str]
) -> list[str]:
    hints: list[str] = []
    if offered and sought:
        hints.append(f"互补组队：她出{' / '.join(offered)}，缺口在{'、'.join(sought)}")
    if "比赛组队" in scenes:
        hints.append("适合再丢进比赛池，而不是再问一遍「你对什么感兴趣」")
    if "运动搭子" in scenes:
        hints.append("周期球局是她的弱关系入口，比冷启动私聊更自然")
    if domains:
        hints.append(f"破冰不要从专业开始，从「{domains[0]}」那类事开始")
    return hints[:4]


def _icebreakers(domains: list[str], scenes: list[str], offered: list[str]) -> list[str]:
    lines: list[str] = []
    if "比赛组队" in scenes and offered:
        lines.append(f"你们都把比赛当项目打，她这次站的是{offered[0]}。")
    if "运动搭子" in scenes:
        lines.append("英东那场不是社交，是把场次定死的人。")
    if domains:
        lines.append(f"共同话题先放在{domains[0]}，别从「交个朋友」开口。")
    if not lines:
        lines.append("先成局，再介绍人。")
    return lines[:3]
