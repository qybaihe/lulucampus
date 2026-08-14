"""Optional HTTP surface so the engine can run as its own service."""

from __future__ import annotations

from typing import Any

from portrait_evolve.events import BehaviorEvent
from portrait_evolve.explain import explain
from portrait_evolve.store import PortraitStore


def create_app(db_path: str = ":memory:") -> Any:
    try:
        from fastapi import FastAPI, HTTPException
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("install extras: pip install .[api]") from exc

    store = PortraitStore(db_path)
    app = FastAPI(
        title="lulu-portrait-evolve",
        description="自进化画像：每一次找搭子、参加比赛，都在校准这个人是谁。",
        version="0.1.0",
    )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "model": "evolve-v1"}

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
        results = []
        for raw in raw_events:
            event = BehaviorEvent.from_dict({**raw, "user_id": raw.get("user_id") or user_id})
            results.append(store.ingest(event).to_dict())
        portrait = store.get(user_id)
        return {
            "applied": sum(1 for item in results if item["applied"]),
            "duplicates": sum(1 for item in results if item["duplicate"]),
            "portrait": portrait.public_view() if portrait else None,
            "explain": explain(portrait, store.events(user_id)) if portrait else None,
        }

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

    @app.get("/v1/portraits/{user_id}/raw")
    def get_raw(user_id: str) -> dict[str, Any]:
        portrait = store.get(user_id)
        if portrait is None:
            raise HTTPException(status_code=404, detail="portrait not found")
        return portrait.to_dict()

    return app
