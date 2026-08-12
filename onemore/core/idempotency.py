from __future__ import annotations

import asyncio
import hashlib
import json
from collections import defaultdict
from datetime import UTC, datetime, timedelta

from fastapi import Request
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from starlette.responses import JSONResponse, Response

from onemore.core.auth import user_id_from_credentials
from onemore.core.database import SessionLocal
from onemore.db.models import IdempotencyRecord


class IdempotencyCoordinator:
    """Replay successful authenticated writes after a lost client response."""

    def __init__(self) -> None:
        self._guard = asyncio.Lock()
        self._locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

    async def _lock(self, key: str) -> asyncio.Lock:
        async with self._guard:
            return self._locks[key]

    async def handle(self, request: Request, call_next) -> Response:
        key = request.headers.get("Idempotency-Key")
        if request.method not in {"POST", "PATCH", "DELETE"} or not key:
            return await call_next(request)
        if not 8 <= len(key) <= 128:
            return self._error(request, "IDEMPOTENCY_KEY_INVALID", "幂等键长度必须为 8–128", 422)
        user_id = user_id_from_credentials(
            request.headers.get("Authorization"), request.headers.get("X-User-ID")
        )
        if not user_id:
            return await call_next(request)
        body = await request.body()
        request_hash = hashlib.sha256(body).hexdigest()
        request_path = request.url.path
        if request.url.query:
            request_path += f"?{request.url.query}"
        scope = f"{user_id}|{request.method}|{request_path}|{key}"
        lock = await self._lock(scope)
        async with lock:
            with SessionLocal() as db:
                now = datetime.now(UTC)
                # Only completed replay records expire. An interrupted or
                # in-progress operation must never disappear and become
                # executable again merely because its response was lost.
                db.execute(
                    delete(IdempotencyRecord).where(
                        IdempotencyRecord.expires_at <= now,
                        IdempotencyRecord.response_status > 0,
                    )
                )
                existing = db.scalar(
                    select(IdempotencyRecord).where(
                        IdempotencyRecord.user_id == user_id,
                        IdempotencyRecord.method == request.method,
                        IdempotencyRecord.path == request_path,
                        IdempotencyRecord.idempotency_key == key,
                    )
                )
                if existing:
                    if existing.request_hash != request_hash:
                        return self._error(
                            request,
                            "IDEMPOTENCY_KEY_REUSED",
                            "同一幂等键不能用于不同请求内容",
                            409,
                        )
                    if existing.response_status == 0:
                        created_at = existing.created_at
                        if created_at.tzinfo is None:
                            created_at = created_at.replace(tzinfo=UTC)
                        if created_at <= now - timedelta(minutes=2):
                            existing.response_status = -1
                            existing.response_body = ""
                            existing.expires_at = now + timedelta(days=3650)
                            db.commit()
                            return self._unknown(request, key, request.method, request_path)
                        db.close()
                        waited = await self._wait_for_completion(
                            user_id, request.method, request_path, key, request_hash
                        )
                        if waited is not None:
                            return waited
                        return self._error(request, "IDEMPOTENCY_IN_PROGRESS", "相同写操作仍在处理中", 409)
                    if existing.response_status < 0:
                        return self._unknown(request, key, request.method, request_path)
                    return Response(
                        content=existing.response_body,
                        status_code=existing.response_status,
                        media_type=existing.response_content_type,
                        headers={"X-Idempotency-Replayed": "true"},
                    )
                # Reserve before invoking business code. The unique row is the
                # cross-worker boundary; another worker observes IN_PROGRESS
                # instead of executing the side effect a second time.
                reservation = IdempotencyRecord(
                    user_id=user_id,
                    method=request.method,
                    path=request_path,
                    idempotency_key=key,
                    request_hash=request_hash,
                    response_status=0,
                    response_body="",
                    response_content_type="application/json",
                    expires_at=now + timedelta(hours=24),
                )
                db.add(reservation)
                try:
                    db.commit()
                except IntegrityError:
                    db.rollback()
                    db.close()
                    waited = await self._wait_for_completion(
                        user_id, request.method, request_path, key, request_hash
                    )
                    if waited is not None:
                        return waited
                    return self._error(request, "IDEMPOTENCY_IN_PROGRESS", "相同写操作仍在处理中", 409)

            try:
                response = await call_next(request)
            except BaseException:
                # The handler may already have committed its business
                # transaction before cancellation/worker interruption. Mark
                # the outcome UNKNOWN and fail closed; deleting the row here
                # would allow the same side effect to execute twice.
                with SessionLocal() as db:
                    stored = db.scalar(
                        select(IdempotencyRecord).where(
                            IdempotencyRecord.user_id == user_id,
                            IdempotencyRecord.method == request.method,
                            IdempotencyRecord.path == request_path,
                            IdempotencyRecord.idempotency_key == key,
                            IdempotencyRecord.response_status == 0,
                        )
                    )
                    if stored is not None:
                        stored.response_status = -1
                        stored.response_body = ""
                        stored.expires_at = datetime.now(UTC) + timedelta(days=3650)
                    db.commit()
                raise
            chunks = [chunk async for chunk in response.body_iterator]
            response_body = b"".join(chunks)
            headers = {
                name: value
                for name, value in response.headers.items()
                if name.lower() not in {"content-length", "content-type"}
            }
            content_type = (response.headers.get("content-type") or "application/json").split(
                ";", 1
            )[0]
            rebuilt = Response(
                content=response_body,
                status_code=response.status_code,
                headers=headers,
                media_type=content_type,
                background=response.background,
            )
            if 200 <= response.status_code < 300:
                try:
                    text = response_body.decode("utf-8")
                    json.loads(text)
                except (UnicodeDecodeError, json.JSONDecodeError):
                    return rebuilt
                with SessionLocal() as db:
                    stored = db.scalar(
                        select(IdempotencyRecord).where(
                            IdempotencyRecord.user_id == user_id,
                            IdempotencyRecord.method == request.method,
                            IdempotencyRecord.path == request_path,
                            IdempotencyRecord.idempotency_key == key,
                        )
                    )
                    if stored is not None:
                        stored.response_status = response.status_code
                        stored.response_body = text
                        stored.response_content_type = content_type
                        stored.expires_at = datetime.now(UTC) + timedelta(hours=24)
                        db.commit()
            else:
                with SessionLocal() as db:
                    db.execute(
                        delete(IdempotencyRecord).where(
                            IdempotencyRecord.user_id == user_id,
                            IdempotencyRecord.method == request.method,
                            IdempotencyRecord.path == request_path,
                            IdempotencyRecord.idempotency_key == key,
                            IdempotencyRecord.response_status == 0,
                        )
                    )
                    db.commit()
            return rebuilt

    async def _wait_for_completion(
        self,
        user_id: str,
        method: str,
        path: str,
        key: str,
        request_hash: str,
    ) -> Response | None:
        for _ in range(100):
            await asyncio.sleep(0.05)
            with SessionLocal() as db:
                record = db.scalar(
                    select(IdempotencyRecord).where(
                        IdempotencyRecord.user_id == user_id,
                        IdempotencyRecord.method == method,
                        IdempotencyRecord.path == path,
                        IdempotencyRecord.idempotency_key == key,
                    )
                )
                if record is None:
                    return None
                if record.request_hash != request_hash:
                    return None
                if record.response_status != 0:
                    if record.response_status < 0:
                        return JSONResponse(
                            status_code=409,
                            content={
                                "error": {
                                    "code": "IDEMPOTENCY_RESULT_UNKNOWN",
                                    "message": "写操作可能已完成，请刷新服务端状态后再决定下一步",
                                    "details": {"idempotency_key": key, "method": method, "path": path},
                                    "request_id": None,
                                }
                            },
                        )
                    return Response(
                        content=record.response_body,
                        status_code=record.response_status,
                        media_type=record.response_content_type,
                        headers={"X-Idempotency-Replayed": "true"},
                    )
        return None

    @staticmethod
    def _unknown(request: Request, key: str, method: str, path: str) -> JSONResponse:
        return JSONResponse(
            status_code=409,
            content={
                "error": {
                    "code": "IDEMPOTENCY_RESULT_UNKNOWN",
                    "message": "写操作可能已完成，请刷新服务端状态后再决定下一步",
                    "details": {"idempotency_key": key, "method": method, "path": path},
                    "request_id": getattr(request.state, "request_id", None),
                }
            },
        )

    @staticmethod
    def _error(request: Request, code: str, message: str, status_code: int) -> JSONResponse:
        return JSONResponse(
            status_code=status_code,
            content={
                "error": {
                    "code": code,
                    "message": message,
                    "details": {},
                    "request_id": getattr(request.state, "request_id", None),
                }
            },
        )


idempotency_coordinator = IdempotencyCoordinator()
