from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from redis import Redis
from redis.exceptions import RedisError
from sqlalchemy import text

from onemore import __version__
from onemore.core.config import get_settings
from onemore.core.database import SessionLocal, create_schema
from onemore.core.errors import AppError
from onemore.core.http import install_http_infrastructure
from onemore.core.idempotency_api import router as idempotency_router
from onemore.db.seed import seed_demo_data, seed_reference_data
from onemore.modules.actions.api import router as actions_router
from onemore.modules.campus.api import router as campus_router
from onemore.modules.collab.api import router as collab_router
from onemore.modules.competitions.api import router as competitions_router
from onemore.modules.gathering.api import router as gathering_router
from onemore.modules.gathering.organizer_api import internal_router as organizer_internal_router
from onemore.modules.gathering.organizer_api import router as organizer_router
from onemore.modules.identity.account_api import router as account_router
from onemore.modules.identity.api import router as identity_router
from onemore.modules.intent.api import router as intent_router
from onemore.modules.matching.api import router as matching_router
from onemore.modules.media.api import router as media_router
from onemore.modules.notify.api import router as notify_router
from onemore.modules.profile.api import router as profile_router
from onemore.modules.schedule.api import router as schedule_router
from onemore.modules.taste_profile.api import router as taste_profile_router
from onemore.modules.trust.api import internal_router as trust_internal_router
from onemore.modules.trust.api import router as trust_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    settings.validate_runtime()
    if settings.auto_create_schema:
        create_schema()
    with SessionLocal() as db:
        seed_reference_data(db)
        if settings.seed_demo_data:
            seed_demo_data(db)
    from onemore.modules.taste_profile.service import mark_interrupted_imports_failed

    with SessionLocal() as db:
        failed = mark_interrupted_imports_failed(db)
        if failed:
            print(f"[startup] marked {failed} interrupted taste import(s) as failed")
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="噜噜成局 API",
        version=__version__,
        description=(
            "校园成局业务服务。隐私约束由接口与数据模型强制：不下发他人课表、"
            "不下发他人等级、不提供用户搜索、共同经历不含评价字段。"
        ),
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )
    if settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    install_http_infrastructure(app)
    for router in (
        identity_router,
        account_router,
        profile_router,
        schedule_router,
        campus_router,
        intent_router,
        matching_router,
        media_router,
        gathering_router,
        organizer_router,
        organizer_internal_router,
        trust_router,
        trust_internal_router,
        collab_router,
        competitions_router,
        actions_router,
        notify_router,
        taste_profile_router,
        idempotency_router,
    ):
        app.include_router(router)

    @app.get("/", tags=["system"])
    def root() -> dict:
        return {
            "service": settings.app_name,
            "version": __version__,
            "docs": "/docs",
            "openapi": "/openapi.json",
        }

    @app.get("/health/live", tags=["system"])
    def health_live() -> dict:
        return {"status": "ok"}

    @app.get("/health/ready", tags=["system"])
    def health_ready() -> dict:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
        redis_status = "disabled"
        if settings.distributed_locks_enabled:
            try:
                Redis.from_url(
                    settings.redis_url,
                    socket_connect_timeout=0.15,
                    socket_timeout=0.5,
                ).ping()
                redis_status = "ok"
            except RedisError as exc:
                if settings.is_production:
                    raise AppError("REDIS_UNAVAILABLE", "Redis 暂时不可用", 503) from exc
                redis_status = "degraded_local_fallback"
        cli_status = "not_required"
        if settings.hermes_mode == "real":
            cli_status = "ok" if Path(settings.sysu_cli).is_file() else "missing"
            if settings.is_production and cli_status == "missing":
                raise AppError("HERMES_CLI_MISSING", "Hermes CLI 未就绪", 503)
        return {
            "status": "ready",
            "database": "ok",
            "redis": redis_status,
            "hermes_mode": settings.hermes_mode,
            "hermes_cli": cli_status,
        }

    return app


app = create_app()


def run() -> None:
    uvicorn.run("onemore.main:app", host="0.0.0.0", port=8000, reload=False)


if __name__ == "__main__":
    run()
