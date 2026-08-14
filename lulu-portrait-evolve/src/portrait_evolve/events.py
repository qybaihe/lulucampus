"""Platform behavior events — the only learning channel that never goes stale."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

EVENT_TYPES = (
    "seed_academic",
    "seed_taste",
    "browse_competition",
    "open_competition",
    "post_intent",
    "seek_teammate",
    "join_team",
    "join_competition",
    "confirm_gathering",
    "complete_gathering",
    "recur_gathering",
    "late_exit",
)

# How strongly an event should move the lived layer.
# Browse is almost noise; completing and recurring a gathering is identity.
STRENGTH: dict[str, float] = {
    "seed_academic": 1.0,
    "seed_taste": 0.85,
    "browse_competition": 0.08,
    "open_competition": 0.12,
    "post_intent": 0.35,
    "seek_teammate": 0.40,
    "join_team": 0.55,
    "join_competition": 0.55,
    "confirm_gathering": 0.45,
    "complete_gathering": 0.80,
    "recur_gathering": 1.00,
    "late_exit": 0.20,
}

# Seeds write priors. Lived events write the evolving layer.
# late_exit shrinks the scene, it does not rewrite who the person is.
POLARITY: dict[str, float] = {
    "late_exit": -1.0,
}


@dataclass(frozen=True)
class BehaviorEvent:
    event_id: str
    user_id: str
    type: str
    occurred_at: str
    scene: str | None = None
    mode: str | None = None
    competition: str | None = None
    tracks: tuple[str, ...] = ()
    skills: tuple[str, ...] = ()
    roles_sought: tuple[str, ...] = ()
    roles_offered: tuple[str, ...] = ()
    domains: tuple[str, ...] = ()
    text: str = ""
    payload: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.type not in EVENT_TYPES:
            raise ValueError(f"unknown event type: {self.type}")
        if not self.event_id or not self.user_id:
            raise ValueError("event_id and user_id are required")

    @property
    def strength(self) -> float:
        return STRENGTH[self.type]

    @property
    def polarity(self) -> float:
        return POLARITY.get(self.type, 1.0)

    @property
    def is_seed(self) -> bool:
        return self.type.startswith("seed_")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> BehaviorEvent:
        def _tuple(key: str) -> tuple[str, ...]:
            value = raw.get(key) or ()
            return tuple(str(item) for item in value if str(item).strip())

        return cls(
            event_id=str(raw["event_id"]),
            user_id=str(raw["user_id"]),
            type=str(raw["type"]),
            occurred_at=str(raw["occurred_at"]),
            scene=_optional_str(raw.get("scene")),
            mode=_optional_str(raw.get("mode")),
            competition=_optional_str(raw.get("competition")),
            tracks=_tuple("tracks"),
            skills=_tuple("skills"),
            roles_sought=_tuple("roles_sought"),
            roles_offered=_tuple("roles_offered"),
            domains=_tuple("domains"),
            text=str(raw.get("text") or ""),
            payload=dict(raw.get("payload") or {}),
        )


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
