from __future__ import annotations

import logging
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from starlette.responses import Response

from onemore.core.errors import AppError
from onemore.core.idempotency import idempotency_coordinator

logger = logging.getLogger("onemore.http")
REQUESTS = Counter(
    "onemore_http_requests_total",
    "HTTP requests by route, method and status",
    ["route", "method", "status"],
)
LATENCY = Histogram(
    "onemore_http_request_duration_seconds",
    "HTTP request latency by route and method",
    ["route", "method"],
)


def install_http_infrastructure(app: FastAPI) -> None:
    @app.middleware("http")
    async def request_context(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id
        started = time.perf_counter()
        try:
            response = await idempotency_coordinator.handle(request, call_next)
        except Exception:
            logger.exception("unhandled request error", extra={"request_id": request_id})
            raise
        route = request.scope.get("route")
        route_path = getattr(route, "path", "unmatched")
        elapsed = time.perf_counter() - started
        REQUESTS.labels(route_path, request.method, str(response.status_code)).inc()
        LATENCY.labels(route_path, request.method).observe(elapsed)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-API-Version"] = "2026-08-11"
        return response

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "details": exc.details or {},
                    "request_id": getattr(request.state, "request_id", None),
                }
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        issues = []
        for raw_issue in exc.errors():
            issue = dict(raw_issue)
            if "ctx" in issue:
                issue["ctx"] = {key: str(value) for key, value in issue["ctx"].items()}
            issues.append(issue)
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "请求参数校验失败",
                    "details": {"issues": issues},
                    "request_id": getattr(request.state, "request_id", None),
                }
            },
        )

    @app.get("/metrics", include_in_schema=False)
    def metrics() -> Response:
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
