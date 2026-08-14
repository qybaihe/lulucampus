"""Optional HTTP surface so the engine can run as its own service."""

from __future__ import annotations

from typing import Any

from portrait_evolve.affinity import score_pair
from portrait_evolve.events import BehaviorEvent
from portrait_evolve.explain import explain
from portrait_evolve.inventory import inventory
from portrait_evolve.models import model_card
from portrait_evolve.report import build_report
from portrait_evolve.store import PortraitStore


def create_app(db_path: str = ":memory:") -> Any:
    try:
        from fastapi import FastAPI, HTTPException
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("install extras: pip install .[api]") from exc

    store = PortraitStore(db_path)
    app = FastAPI(
        title="lulu-portrait-evolve",
        description="自进化画像：层次先验 × 行为证据累积 × 滞回稳态。学习闭环不调用大模型。",
        version="0.2.0",
    )

    @app.get("/health")
    def health() -> dict[str, Any]:
        return {"status": "ok", "model": "evolve-v2", "llm_in_learning_loop": False}

    @app.get("/v1/models")
    def models() -> dict[str, Any]:
        return model_card()

    @app.get("/v1/inventory")
    def package_inventory() -> dict[str, Any]:
        return inventory()

    @app.post("/v1/events")
    def ingest_event(payload: dict[str, Any]) -> dict[str, Any]:
        try:
            event = BehaviorEvent.from_dict(payload)
        except (KeyError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return store.ingest(event).to_dict()

    @app.post("/v1/replay")
    def replay(payload: dict[str, Any]) -> dict[str, Any]:
        user_id = str(payload.get("user_id") or "")
        raw_events = payload.get("events") or []
        if not user_id:
            raise HTTPException(status_code=400, detail="user_id required")
        events = [
            BehaviorEvent.from_dict({**raw, "user_id": raw.get("user_id") or user_id})
            for raw in raw_events
        ]
        for event in events:
            store.ingest(event)
        return build_report(
            user_id,
            store.events(user_id),
            display_name=payload.get("display_name"),
            use_llm=bool(payload.get("use_llm")),
        )

    @app.post("/v1/compare")
    def compare(payload: dict[str, Any]) -> dict[str, Any]:
        left_id = str(payload.get("left_user_id") or "")
        right_id = str(payload.get("right_user_id") or "")
        left = store.get(left_id)
        right = store.get(right_id)
        if left is None or right is None:
            raise HTTPException(status_code=404, detail="both portraits required")
        return {"affinity": score_pair(left, right)}

    @app.get("/v1/portraits/{user_id}")
    def get_portrait(user_id: str) -> dict[str, Any]:
        portrait = store.get(user_id)
        if portrait is None:
            raise HTTPException(status_code=404, detail="portrait not found")
        return portrait.public_view()

    @app.get("/v1/portraits/{user_id}/explain")
    def get_explain(user_id: str) -> dict[str, Any]:
        portrait = store.get(user_id)
        if portrait is None:
            raise HTTPException(status_code=404, detail="portrait not found")
        return explain(portrait, store.events(user_id))

    @app.get("/v1/portraits/{user_id}/report")
    def get_report(user_id: str) -> dict[str, Any]:
        portrait = store.get(user_id)
        if portrait is None:
            raise HTTPException(status_code=404, detail="portrait not found")
        return build_report(user_id, store.events(user_id))

    @app.get("/v1/portraits/{user_id}/raw")
    def get_raw(user_id: str) -> dict[str, Any]:
        portrait = store.get(user_id)
        if portrait is None:
            raise HTTPException(status_code=404, detail="portrait not found")
        return portrait.to_dict()

    return app
