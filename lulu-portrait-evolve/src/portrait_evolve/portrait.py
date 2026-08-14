"""Living portrait state: priors stay, the lived layer keeps moving."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

MODEL_VERSION = "evolve-v1"


@dataclass
class Evidence:
    score: float = 0.0
    mass: float = 0.0
    last_at: str | None = None
    as_of: str | None = None
    hits: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, raw: dict[str, Any] | None) -> Evidence:
        raw = raw or {}
        return cls(
            score=float(raw.get("score") or 0.0),
            mass=float(raw.get("mass") or 0.0),
            last_at=raw.get("last_at"),
            as_of=raw.get("as_of") or raw.get("last_at"),
            hits=int(raw.get("hits") or 0),
        )


def _bag(raw: dict[str, Any] | None) -> dict[str, Evidence]:
    return {str(key): Evidence.from_dict(value) for key, value in (raw or {}).items()}


def _dump_bag(bag: dict[str, Evidence]) -> dict[str, dict[str, Any]]:
    return {key: value.to_dict() for key, value in bag.items()}


@dataclass
class Layer:
    domains: dict[str, Evidence] = field(default_factory=dict)
    skills: dict[str, Evidence] = field(default_factory=dict)
    signals: dict[str, Evidence] = field(default_factory=dict)
    scenes: dict[str, Evidence] = field(default_factory=dict)
    roles_offered: dict[str, Evidence] = field(default_factory=dict)
    roles_sought: dict[str, Evidence] = field(default_factory=dict)
    tags: dict[str, Evidence] = field(default_factory=dict)
    facets: list[str] = field(default_factory=list)

    def scores(self, field_name: str) -> dict[str, float]:
        bag: dict[str, Evidence] = getattr(self, field_name)
        return {key: item.score for key, item in bag.items() if item.score > 0}

    def to_dict(self) -> dict[str, Any]:
        return {
            "domains": _dump_bag(self.domains),
            "skills": _dump_bag(self.skills),
            "signals": _dump_bag(self.signals),
            "scenes": _dump_bag(self.scenes),
            "roles_offered": _dump_bag(self.roles_offered),
            "roles_sought": _dump_bag(self.roles_sought),
            "tags": _dump_bag(self.tags),
            "facets": list(self.facets),
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any] | None) -> Layer:
        raw = raw or {}
        return cls(
            domains=_bag(raw.get("domains")),
            skills=_bag(raw.get("skills")),
            signals=_bag(raw.get("signals")),
            scenes=_bag(raw.get("scenes")),
            roles_offered=_bag(raw.get("roles_offered")),
            roles_sought=_bag(raw.get("roles_sought")),
            tags=_bag(raw.get("tags")),
            facets=list(raw.get("facets") or []),
        )


@dataclass
class DerivedTag:
    key: str
    label: str
    score: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, raw: dict[str, Any] | None) -> DerivedTag | None:
        if not raw or not raw.get("key"):
            return None
        return cls(
            key=str(raw["key"]),
            label=str(raw.get("label") or raw["key"]),
            score=float(raw.get("score") or 0.0),
        )


@dataclass
class Portrait:
    user_id: str
    model_version: str = MODEL_VERSION
    updated_at: str | None = None
    event_count: int = 0
    academic: Layer = field(default_factory=Layer)
    taste: Layer = field(default_factory=Layer)
    lived: Layer = field(default_factory=Layer)
    primary_tag: DerivedTag | None = None
    secondary_tags: list[DerivedTag] = field(default_factory=list)
    confidence: float = 0.0
    summary: str = ""
    last_event_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "model_version": self.model_version,
            "updated_at": self.updated_at,
            "event_count": self.event_count,
            "academic": self.academic.to_dict(),
            "taste": self.taste.to_dict(),
            "lived": self.lived.to_dict(),
            "primary_tag": self.primary_tag.to_dict() if self.primary_tag else None,
            "secondary_tags": [tag.to_dict() for tag in self.secondary_tags],
            "confidence": self.confidence,
            "summary": self.summary,
            "last_event_id": self.last_event_id,
        }

    def public_view(self) -> dict[str, Any]:
        """Compact card used by matching / demo — not the raw evidence bags."""
        return {
            "user_id": self.user_id,
            "model_version": self.model_version,
            "updated_at": self.updated_at,
            "event_count": self.event_count,
            "confidence": round(self.confidence, 4),
            "primary_tag": self.primary_tag.to_dict() if self.primary_tag else None,
            "secondary_tags": [tag.to_dict() for tag in self.secondary_tags],
            "interest_domains": _top_scores(
                _blend_scores(self, "domains"),
                labels_from="domain",
            ),
            "skills": _top_scores(_blend_scores(self, "skills"), labels_from="skill"),
            "scenes": _top_scores(self.lived.scores("scenes"), labels_from="scene"),
            "roles_offered": _top_scores(
                self.lived.scores("roles_offered"), labels_from="skill"
            ),
            "roles_sought": _top_scores(
                self.lived.scores("roles_sought"), labels_from="skill"
            ),
            "summary": self.summary,
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> Portrait:
        return cls(
            user_id=str(raw["user_id"]),
            model_version=str(raw.get("model_version") or MODEL_VERSION),
            updated_at=raw.get("updated_at"),
            event_count=int(raw.get("event_count") or 0),
            academic=Layer.from_dict(raw.get("academic")),
            taste=Layer.from_dict(raw.get("taste")),
            lived=Layer.from_dict(raw.get("lived")),
            primary_tag=DerivedTag.from_dict(raw.get("primary_tag")),
            secondary_tags=[
                tag
                for item in (raw.get("secondary_tags") or [])
                if (tag := DerivedTag.from_dict(item))
            ],
            confidence=float(raw.get("confidence") or 0.0),
            summary=str(raw.get("summary") or ""),
            last_event_id=raw.get("last_event_id"),
        )


def _blend_scores(portrait: Portrait, field_name: str) -> dict[str, float]:
    blended: dict[str, float] = {}
    for weight, layer in (
        (0.25, portrait.academic),
        (0.30, portrait.taste),
        (0.45, portrait.lived),
    ):
        for key, score in layer.scores(field_name).items():
            blended[key] = blended.get(key, 0.0) + weight * score
    return blended


def _top_scores(
    scores: dict[str, float], *, labels_from: str, limit: int = 6
) -> list[dict[str, Any]]:
    from portrait_evolve.taxonomy import label_of

    ranked = sorted(scores.items(), key=lambda item: (-item[1], item[0]))
    return [
        {
            "key": key,
            "label": label_of(labels_from, key),
            "score": round(score, 4),
        }
        for key, score in ranked[:limit]
        if score >= 0.08
    ]
