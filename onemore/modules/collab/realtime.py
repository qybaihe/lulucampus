from __future__ import annotations

from collections import defaultdict
from contextlib import suppress

from fastapi import WebSocket


class ChannelHub:
    def __init__(self) -> None:
        self.connections: dict[str, dict[WebSocket, str]] = defaultdict(dict)

    async def connect(
        self,
        channel_id: str,
        user_id: str,
        websocket: WebSocket,
        *,
        subprotocol: str | None = None,
    ) -> None:
        await websocket.accept(subprotocol=subprotocol)
        self.connections[channel_id][websocket] = user_id

    def disconnect(self, channel_id: str, websocket: WebSocket) -> None:
        self.connections[channel_id].pop(websocket, None)
        if not self.connections[channel_id]:
            self.connections.pop(channel_id, None)

    async def broadcast(
        self, channel_id: str, payload: dict, *, allowed_user_ids: set[str]
    ) -> None:
        stale: list[WebSocket] = []
        entries = tuple(self.connections.get(channel_id, {}).items())
        for websocket, user_id in entries:
            if user_id not in allowed_user_ids:
                with suppress(Exception):
                    await websocket.close(code=4403)
                stale.append(websocket)
                continue
            try:
                await websocket.send_json(payload)
            except Exception:
                stale.append(websocket)
        for websocket in stale:
            self.disconnect(channel_id, websocket)


hub = ChannelHub()
