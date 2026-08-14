"""Self-evolving portrait engine.

The production prototype in 噜噜成局 could initialize a portrait, but the
follow-up learning pass did not fire reliably after launch. This engine treats
every platform action as an append-only event and projects a living portrait:

- academic / taste priors are never wiped by later jobs
- lived evidence decays, then saturates toward 1
- primary tag only flips with hysteresis, so the card does not flicker
- ingest is idempotent on event_id, so retries are safe
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from portrait_evolve.events import BehaviorEvent
from portrait_evolve.portrait import DerivedTag, Evidence, Layer, Portrait
from portrait_evolve.taxonomy import (
    SCENE_PRIORS,
    TAG_DEFINITIONS,
    infer_domains,
    infer_scene,
    label_of,
    normalize_role,
    skill_domain,
)

HALF_LIFE_DAYS = {
    "academic": 365.0,
    "taste": 180.0,
    "lived": 60.0,
}
ALPHA = 0.55
PRIMARY_MARGIN = 0.06
EMIT_EPS = 0.01
BREADTH_REF = 8.0


def parse_time(value: str | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    text = value.replace("Z", "+00:00")
    moment = datetime.fromisoformat(text)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc)


def decay(score: float, last_at: str | None, now: datetime, half_life: float) -> float:
    if score <= 0 or not last_at:
        return score
    dt_days = max(0.0, (now - parse_time(last_at)).total_seconds() / 86400.0)
    return score * (0.5 ** (dt_days / half_life))


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return min(high, max(low, value))


@dataclass
class IngestResult:
    applied: bool
    changed: bool
    duplicate: bool
    portrait: Portrait
    delta: dict[str, float]

    def to_dict(self) -> dict[str, Any]:
        return {
            "applied": self.applied,
            "changed": self.changed,
            "duplicate": self.duplicate,
            "delta": self.delta,
            "portrait": self.portrait.public_view(),
        }


class LivingPortraitEngine:
    def apply(self, portrait: Portrait, event: BehaviorEvent) -> IngestResult:
        if portrait.last_event_id == event.event_id:
            return IngestResult(False, False, True, portrait, {})

        before = _fingerprint(portrait)
        now = parse_time(event.occurred_at)
        self._decay_layer(portrait.academic, now, HALF_LIFE_DAYS["academic"])
        self._decay_layer(portrait.taste, now, HALF_LIFE_DAYS["taste"])
        self._decay_layer(portrait.lived, now, HALF_LIFE_DAYS["lived"])
        for item in portrait.peers.values():
            item.score = decay(item.score, item.as_of or item.last_at, now, HALF_LIFE_DAYS["lived"])
            item.as_of = now.isoformat()

        if event.type == "seed_academic":
            self._seed(portrait.academic, event, now)
            self._nudge_lived_from_seed(portrait.lived, event, now, scale=0.28)
        elif event.type == "seed_taste":
            self._seed(portrait.taste, event, now)
            self._nudge_lived_from_seed(portrait.lived, event, now, scale=0.22)
        else:
            self._learn_lived(portrait.lived, event, now)

        for peer_id in event.peer_ids:
            if peer_id and peer_id != event.user_id:
                _learn(portrait.peers, peer_id, event.strength * 0.55, 1.0, now.isoformat())

        self._recompute(portrait, now.isoformat(), event.event_id)
        after = _fingerprint(portrait)
        delta = _delta(before, after)
        changed = any(abs(value) >= EMIT_EPS for value in delta.values()) or (
            before.get("_primary") != after.get("_primary")
        )
        return IngestResult(True, changed, False, portrait, delta)

    def replay(self, user_id: str, events: list[BehaviorEvent]) -> Portrait:
        portrait = Portrait(user_id=user_id)
        for event in sorted(events, key=lambda item: (item.occurred_at, item.event_id)):
            if event.user_id != user_id:
                continue
            self.apply(portrait, event)
        return portrait

    def _seed(self, layer: Layer, event: BehaviorEvent, now: datetime) -> None:
        stamp = now.isoformat()
        for key, weight in _event_domains(event).items():
            _write(layer.domains, key, weight, stamp, mass=event.strength)
        for skill in _offered(event):
            _write(layer.skills, skill, 0.85, stamp, mass=event.strength)
            domain = skill_domain(skill)
            if domain:
                _write(layer.domains, domain, 0.45, stamp, mass=event.strength * 0.4)
        for key, weight in (event.payload.get("signals") or {}).items():
            _write(layer.signals, str(key), float(weight), stamp, mass=event.strength)
        for key, weight in (event.payload.get("tags") or {}).items():
            _write(layer.tags, str(key), float(weight), stamp, mass=event.strength)
        facets = event.payload.get("facets") or []
        for facet in facets:
            text = str(facet).strip()
            if text and text not in layer.facets:
                layer.facets.append(text)

    def _nudge_lived_from_seed(
        self, lived: Layer, event: BehaviorEvent, now: datetime, *, scale: float
    ) -> None:
        stamp = now.isoformat()
        for key, weight in _event_domains(event).items():
            _learn(lived.domains, key, event.strength * scale * weight, 1.0, stamp)
        for skill in _offered(event):
            _learn(lived.skills, skill, event.strength * scale, 1.0, stamp)

    def _learn_lived(self, lived: Layer, event: BehaviorEvent, now: datetime) -> None:
        stamp = now.isoformat()
        strength = event.strength
        polarity = event.polarity
        scene = event.scene or infer_scene(event.text, event.competition)
        if scene:
            _learn(lived.scenes, scene, strength, polarity, stamp)
            prior = SCENE_PRIORS.get(scene, {})
            for key, weight in prior.get("domains", {}).items():
                _learn(lived.domains, key, strength * weight, polarity, stamp)
            for key, weight in prior.get("signals", {}).items():
                _learn(lived.signals, key, strength * weight, polarity, stamp)

        for key, weight in _event_domains(event).items():
            _learn(lived.domains, key, strength * weight, polarity, stamp)

        for skill in _offered(event):
            _learn(lived.roles_offered, skill, strength, polarity, stamp)
            _learn(lived.skills, skill, strength * 0.85, polarity, stamp)
            domain = skill_domain(skill)
            if domain:
                _learn(lived.domains, domain, strength * 0.35, polarity, stamp)

        # Seeking a role describes the team they want, not a skill they have.
        for skill in _sought(event):
            _learn(lived.roles_sought, skill, strength, 1.0, stamp)
            _learn(lived.signals, "action_oriented", strength * 0.15, 1.0, stamp)

        if event.mode == "complementary":
            _learn(lived.signals, "competitive", strength * 0.25, polarity, stamp)
        elif event.mode == "similar":
            _learn(lived.signals, "light_entertainment", strength * 0.12, polarity, stamp)

        if event.competition or event.tracks:
            _learn(lived.signals, "competitive", strength * 0.20, polarity, stamp)

        if event.type == "book_gym":
            _learn(lived.domains, "health_sports", strength, polarity, stamp)
            _learn(lived.scenes, "运动搭子", strength * 0.6, polarity, stamp)
        elif event.type == "enroll_elective":
            _learn(lived.signals, "action_oriented", strength * 0.35, polarity, stamp)
        elif event.type == "ask_hermes":
            _learn(lived.signals, "action_oriented", strength * 0.2, polarity, stamp)
        elif event.type == "share_gap":
            _learn(lived.signals, "competitive", strength * 0.2, polarity, stamp)

    def _decay_layer(self, layer: Layer, now: datetime, half_life: float) -> None:
        for bag in (
            layer.domains,
            layer.skills,
            layer.signals,
            layer.scenes,
            layer.roles_offered,
            layer.roles_sought,
            layer.tags,
        ):
            for item in bag.values():
                item.score = decay(item.score, item.as_of or item.last_at, now, half_life)
                item.as_of = now.isoformat()

    def _recompute(self, portrait: Portrait, stamp: str, event_id: str) -> None:
        domains = _blend(portrait, "domains")
        signals = _blend(portrait, "signals")
        breadth = min(1.0, len([score for score in domains.values() if score >= 0.12]) / BREADTH_REF)
        ranked = _score_tags(domains, signals, breadth)
        portrait.primary_tag = _stable_primary(portrait.primary_tag, ranked)
        portrait.secondary_tags = [
            tag for tag in ranked if portrait.primary_tag and tag.key != portrait.primary_tag.key
        ][:2]
        portrait.confidence = _confidence(portrait)
        portrait.summary = _summarize(portrait)
        portrait.updated_at = stamp
        portrait.last_event_id = event_id
        portrait.event_count += 1
        portrait.model_version = portrait.model_version or "evolve-v1"


def _event_domains(event: BehaviorEvent) -> dict[str, float]:
    weights = infer_domains(event.text, event.competition, " ".join(event.tracks))
    for key in event.domains:
        weights[key] = max(weights.get(key, 0.0), 0.70)
    for key, value in (event.payload.get("domains") or {}).items():
        weights[str(key)] = max(weights.get(str(key), 0.0), float(value))
    return weights


def _offered(event: BehaviorEvent) -> list[str]:
    seen: list[str] = []
    for raw in (*event.roles_offered, *event.skills):
        key = normalize_role(raw)
        if key and key not in seen:
            seen.append(key)
    return seen


def _sought(event: BehaviorEvent) -> list[str]:
    seen: list[str] = []
    for raw in event.roles_sought:
        key = normalize_role(raw)
        if key and key not in seen:
            seen.append(key)
    return seen


def _write(bag: dict[str, Evidence], key: str, score: float, stamp: str, *, mass: float) -> None:
    item = bag.setdefault(key, Evidence())
    item.score = max(item.score, clamp(score))
    item.mass += mass
    item.last_at = stamp
    item.as_of = stamp
    item.hits += 1


def _learn(
    bag: dict[str, Evidence],
    key: str,
    strength: float,
    polarity: float,
    stamp: str,
) -> None:
    if strength <= 0:
        return
    item = bag.setdefault(key, Evidence())
    if polarity >= 0:
        item.score = clamp(item.score + ALPHA * strength * (1.0 - item.score))
    else:
        item.score = clamp(item.score * (1.0 - ALPHA * strength))
    item.mass += strength
    item.last_at = stamp
    item.as_of = stamp
    item.hits += 1


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


def _score_tags(
    domains: dict[str, float], signals: dict[str, float], breadth: float
) -> list[DerivedTag]:
    ranked: list[DerivedTag] = []
    for tag in TAG_DEFINITIONS:
        domain_part = sum(domains.get(key, 0.0) * weight for key, weight in tag.domains.items())
        signal_part = sum(signals.get(key, 0.0) * weight for key, weight in tag.signals.items())
        total = sum(tag.domains.values()) + sum(tag.signals.values()) + tag.breadth
        score = (domain_part + signal_part + breadth * tag.breadth) / total if total else 0.0
        ranked.append(DerivedTag(tag.key, tag.label, round(clamp(score), 4)))
    ranked.sort(key=lambda item: (-item.score, item.key))
    return ranked


def _stable_primary(current: DerivedTag | None, ranked: list[DerivedTag]) -> DerivedTag | None:
    if not ranked:
        return current
    leader = ranked[0]
    if current is None:
        return leader
    challenger = next((item for item in ranked if item.key == current.key), None)
    if challenger is None:
        return leader if leader.score >= current.score + PRIMARY_MARGIN else current
    if leader.key != current.key and leader.score >= challenger.score + PRIMARY_MARGIN:
        return leader
    return DerivedTag(current.key, current.label, challenger.score)


def _confidence(portrait: Portrait) -> float:
    lived_mass = sum(item.mass for item in portrait.lived.domains.values())
    lived_mass += sum(item.mass for item in portrait.lived.scenes.values())
    prior = 0.18 if portrait.academic.skills or portrait.academic.domains else 0.0
    prior += 0.18 if portrait.taste.domains or portrait.taste.tags else 0.0
    return round(clamp(prior + (1.0 - math.exp(-lived_mass / 3.2))), 4)


def _summarize(portrait: Portrait) -> str:
    primary = portrait.primary_tag.label if portrait.primary_tag else "还在观察中的同学"
    domains = _blend(portrait, "domains")
    top_domains = [label_of("domain", key) for key, _ in _top(domains, 2)]
    scenes = [label_of("scene", key) for key, _ in _top(portrait.lived.scores("scenes"), 2)]
    offered = [label_of("skill", key) for key, _ in _top(portrait.lived.scores("roles_offered"), 2)]
    sought = [label_of("skill", key) for key, _ in _top(portrait.lived.scores("roles_sought"), 2)]
    bits = [f"更像一位{primary}"]
    if top_domains:
        bits.append(f"最近把时间花在{'、'.join(top_domains)}")
    if offered:
        bits.append(f"自己常站{(' / ').join(offered)}")
    if sought:
        bits.append(f"组队时会去找{'、'.join(sought)}")
    if scenes:
        bits.append(f"真正打完的局是{'、'.join(scenes)}")
    return "；".join(bits) + "。"


def _top(scores: dict[str, float], limit: int) -> list[tuple[str, float]]:
    return sorted(
        ((key, score) for key, score in scores.items() if score >= 0.12),
        key=lambda item: (-item[1], item[0]),
    )[:limit]


def _fingerprint(portrait: Portrait) -> dict[str, float | str | None]:
    snap: dict[str, float | str | None] = {
        "_primary": portrait.primary_tag.key if portrait.primary_tag else None
    }
    for prefix, scores in (
        ("d", _blend(portrait, "domains")),
        ("s", _blend(portrait, "skills")),
        ("c", portrait.lived.scores("scenes")),
    ):
        for key, score in scores.items():
            snap[f"{prefix}:{key}"] = round(score, 4)
    return snap


def _delta(
    before: dict[str, float | str | None], after: dict[str, float | str | None]
) -> dict[str, float]:
    keys = {key for key in (*before, *after) if key != "_primary"}
    delta: dict[str, float] = {}
    for key in keys:
        left = float(before.get(key) or 0.0)
        right = float(after.get(key) or 0.0)
        change = round(right - left, 4)
        if abs(change) >= EMIT_EPS:
            delta[key] = change
    return dict(sorted(delta.items(), key=lambda item: (-abs(item[1]), item[0])))
