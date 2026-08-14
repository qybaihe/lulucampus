"""Package inventory: modules, models, event types, lines of code."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from portrait_evolve.events import EVENT_TYPES, STRENGTH
from portrait_evolve.models import ALL_MODELS, IN_LOOP, OPTIONAL, UPSTREAM
from portrait_evolve.taxonomy import DOMAIN_LABELS, SKILL_LABELS, TAG_DEFINITIONS


def _src_root() -> Path:
    return Path(__file__).resolve().parent


def count_loc() -> dict[str, int]:
    files = sorted(_src_root().glob("*.py"))
    per_file: dict[str, int] = {}
    total = 0
    for path in files:
        lines = [
            line
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
        per_file[path.name] = len(lines)
        total += len(lines)
    return {"total": total, "files": len(files), **per_file}


def inventory() -> dict[str, Any]:
    loc = count_loc()
    return {
        "package": "lulu-portrait-evolve",
        "version": "0.2.0",
        "model_version": "evolve-v2",
        "loc": {"source_nonblank": loc["total"], "modules": loc["files"]},
        "modules": sorted(path.name for path in _src_root().glob("*.py")),
        "event_types": list(EVENT_TYPES),
        "event_type_count": len(EVENT_TYPES),
        "evidence_strengths": STRENGTH,
        "taxonomy": {
            "persona_tags": len(TAG_DEFINITIONS),
            "domains": len(DOMAIN_LABELS),
            "skills": len(SKILL_LABELS),
        },
        "models": {
            "in_loop": [item.id for item in IN_LOOP],
            "upstream": [item.id for item in UPSTREAM],
            "optional": [item.id for item in OPTIONAL],
            "count": len(ALL_MODELS),
        },
        "outputs": [
            "living portrait card",
            "evolution trajectory",
            "explainability report",
            "pairwise affinity",
            "narrative / icebreakers",
        ],
    }
