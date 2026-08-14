"""Portrait as a path, not a point: snapshot after every applied event."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from portrait_evolve.engine import LivingPortraitEngine
from portrait_evolve.events import BehaviorEvent
from portrait_evolve.metrics import infer_stage, lived_mass
from portrait_evolve.portrait import Portrait


@dataclass(frozen=True)
class Snapshot:
    index: int
    event_id: str
    event_type: str
    occurred_at: str
    primary_key: str | None
    primary_label: str | None
    primary_score: float
    confidence: float
    stage: str
    lived_mass: float
    top_domain: str | None
    changed: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def trace(user_id: str, events: list[BehaviorEvent]) -> tuple[Portrait, list[Snapshot]]:
    engine = LivingPortraitEngine()
    portrait = Portrait(user_id=user_id)
    frames: list[Snapshot] = []
    ordered = sorted(events, key=lambda item: (item.occurred_at, item.event_id))
    for index, event in enumerate(ordered):
        if event.user_id != user_id:
            continue
        result = engine.apply(portrait, event)
        if result.duplicate:
            continue
        primary = portrait.primary_tag
        domains = portrait.lived.scores("domains") or _blend_domains(portrait)
        top = max(domains, key=domains.get) if domains else None
        frames.append(
            Snapshot(
                index=index,
                event_id=event.event_id,
                event_type=event.type,
                occurred_at=event.occurred_at,
                primary_key=primary.key if primary else None,
                primary_label=primary.label if primary else None,
                primary_score=primary.score if primary else 0.0,
                confidence=portrait.confidence,
                stage=infer_stage(portrait),
                lived_mass=round(lived_mass(portrait), 4),
                top_domain=top,
                changed=result.changed,
            )
        )
    return portrait, frames


def _blend_domains(portrait: Portrait) -> dict[str, float]:
    merged: dict[str, float] = {}
    for layer in (portrait.academic, portrait.taste, portrait.lived):
        for key, score in layer.scores("domains").items():
            merged[key] = max(merged.get(key, 0.0), score)
    return merged


def flips(frames: list[Snapshot]) -> list[dict[str, Any]]:
    changes: list[dict[str, Any]] = []
    previous: str | None = None
    for frame in frames:
        if frame.primary_key and frame.primary_key != previous and previous is not None:
            changes.append(
                {
                    "at": frame.occurred_at,
                    "from": previous,
                    "to": frame.primary_key,
                    "event_id": frame.event_id,
                    "event_type": frame.event_type,
                }
            )
        if frame.primary_key:
            previous = frame.primary_key
    return changes
