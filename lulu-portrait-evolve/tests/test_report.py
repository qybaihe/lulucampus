from __future__ import annotations

import json
from pathlib import Path

from portrait_evolve.events import BehaviorEvent
from portrait_evolve.inventory import inventory
from portrait_evolve.models import model_card
from portrait_evolve.report import build_report, render_markdown
from portrait_evolve.trajectory import trace

ROOT = Path(__file__).resolve().parents[1]
LIN = ROOT / "fixtures" / "linyuan_timeline.json"
ZHOU = ROOT / "fixtures" / "zhouheng_timeline.json"


def _events(path: Path) -> tuple[str, list[BehaviorEvent]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload["user_id"], [BehaviorEvent.from_dict(raw) for raw in payload["events"]]


def test_linyuan_report_reaches_living_stage():
    user_id, events = _events(LIN)
    report = build_report(user_id, events, display_name="林予安")
    assert report["metrics"]["stage"] in {"converging", "living"}
    assert report["portrait"]["primary_tag"]["key"] in {"explorer_builder", "ai_practitioner"}
    assert report["models"]["llm_in_learning_loop"] is False
    assert any(spec["id"] == "hea-v1" for spec in report["models"]["in_loop"])
    markdown = render_markdown(report)
    assert "自进化画像报告" in markdown
    assert "Hierarchical Evidence Accumulator" in markdown or "hea-v1" in markdown


def test_affinity_rewards_complementary_roles():
    from portrait_evolve.affinity import score_pair

    left, _ = trace(*_events(LIN))
    right, _ = trace(*_events(ZHOU))
    result = score_pair(left, right)
    assert result["score"] >= 0.35
    assert result["mode"] == "complementary"
    assert result["parts"]["complement"] > 0 or result["parts"]["peer"] > 0


def test_model_card_keeps_llm_out_of_the_loop():
    card = model_card()
    assert card["llm_in_learning_loop"] is False
    assert all(not spec["writes_scores"] for spec in card["optional"])
    assert all(spec["writes_scores"] for spec in card["in_loop"] if spec["id"] != "lived-affinity-v1")


def test_inventory_lists_new_modules():
    inv = inventory()
    assert inv["loc"]["source_nonblank"] >= 900
    assert inv["event_type_count"] >= 16
    assert "models.py" in inv["modules"]
    assert "report.py" in inv["modules"]
