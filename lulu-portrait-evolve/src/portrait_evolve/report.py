"""End-to-end evolution report — the thing you show, not just a vector."""

from __future__ import annotations

from typing import Any

from portrait_evolve.affinity import score_pair
from portrait_evolve.events import BehaviorEvent
from portrait_evolve.explain import explain
from portrait_evolve.inventory import inventory
from portrait_evolve.llm import enrich
from portrait_evolve.metrics import STAGE_LABELS, measure
from portrait_evolve.models import model_card
from portrait_evolve.narrative import render
from portrait_evolve.portrait import Portrait
from portrait_evolve.trajectory import flips, trace


def build_report(
    user_id: str,
    events: list[BehaviorEvent],
    *,
    display_name: str | None = None,
    peer: Portrait | None = None,
    use_llm: bool = False,
) -> dict[str, Any]:
    portrait, frames = trace(user_id, events)
    narrative = enrich(portrait) if use_llm else render(portrait)
    metrics = measure(portrait)
    view = portrait.public_view()
    view["stage"] = metrics["stage"]
    view["stage_label"] = STAGE_LABELS[metrics["stage"]]
    view["metrics"] = metrics
    view["narrative"] = narrative
    payload: dict[str, Any] = {
        "display_name": display_name or user_id,
        "portrait": view,
        "explain": explain(portrait, events),
        "trajectory": [frame.to_dict() for frame in frames],
        "primary_flips": flips(frames),
        "metrics": metrics,
        "narrative": narrative,
        "models": model_card(),
        "inventory": inventory(),
    }
    if peer is not None:
        payload["affinity"] = score_pair(portrait, peer)
    return payload


def render_markdown(report: dict[str, Any]) -> str:
    view = report["portrait"]
    primary = view.get("primary_tag") or {}
    metrics = report["metrics"]
    narrative = report["narrative"]
    lines = [
        f"# {report['display_name']} · 自进化画像报告",
        "",
        f"**{primary.get('label', '未定')}**  ·  "
        f"{narrative.get('stage_label')}  ·  "
        f"confidence {view.get('confidence')}",
        "",
        narrative.get("persona", view.get("summary", "")),
        "",
        "## 效果",
        "",
        f"- 主标签：{primary.get('label')}（{primary.get('score')}）",
        f"- 兴趣域：{_join(view.get('interest_domains'))}",
        f"- 自己常站：{_join(view.get('roles_offered')) or '—'}",
        f"- 组队在找：{_join(view.get('roles_sought')) or '—'}",
        f"- 打完的局：{_join(view.get('scenes')) or '—'}",
        f"- 阶段：{STAGE_LABELS.get(metrics['stage'], metrics['stage'])}，"
        f"lived mass {metrics['lived_mass']}，覆盖 {metrics['coverage']}",
        "",
        "## 为什么是这张脸",
        "",
    ]
    for reason in report["explain"]["why"]:
        lines.append(f"- {reason}")
    if report.get("primary_flips"):
        lines += ["", "## 主标签翻转", ""]
        for item in report["primary_flips"]:
            lines.append(
                f"- {item['at']}  {item['from']} → {item['to']}  （{item['event_type']}）"
            )
    lines += ["", "## 破冰", ""]
    for hint in narrative.get("icebreakers") or []:
        lines.append(f"- {hint}")
    if report.get("affinity"):
        aff = report["affinity"]
        lines += ["", "## 与对照用户的亲和", "", f"- score {aff['score']} · {aff['mode']}"]
        for reason in aff["reasons"]:
            lines.append(f"- {reason}")
    card = report["models"]
    lines += [
        "",
        "## 本报告引用的模型",
        "",
        f"学习闭环 **不调用大模型**（`llm_in_learning_loop={card['llm_in_learning_loop']}`）。",
        "",
    ]
    for section, title in (
        ("in_loop", "闭环内"),
        ("upstream", "上游冷启动"),
        ("optional", "可选叙事"),
    ):
        lines.append(f"### {title}")
        lines.append("")
        for spec in card[section]:
            mark = "写分数" if spec["writes_scores"] else "不写分数"
            lines.append(f"- `{spec['id']}` **{spec['name']}**（{mark}）— {spec['role']}")
        lines.append("")
    inv = report["inventory"]
    lines += [
        "## 代码体量",
        "",
        f"- 源码非空行：{inv['loc']['source_nonblank']}（{inv['loc']['modules']} 个模块）",
        f"- 事件类型：{inv['event_type_count']}",
        f"- 人格标签 / 域 / 技能：{inv['taxonomy']['persona_tags']} / "
        f"{inv['taxonomy']['domains']} / {inv['taxonomy']['skills']}",
        f"- 命名模型：{inv['models']['count']}",
        "",
    ]
    return "\n".join(lines)


def _join(items: list[dict[str, Any]] | None) -> str:
    return "、".join(
        f"{item.get('label')} {item.get('score')}" for item in (items or [])[:4]
    )
