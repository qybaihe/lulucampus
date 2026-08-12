from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="ONEMORE_",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "onemore-server"
    env: Literal["development", "test", "production"] = "development"
    debug: bool = False
    database_url: str = "sqlite:///./onemore.db"
    redis_url: str = "redis://localhost:6379/0"
    distributed_locks_enabled: bool = True
    distributed_lock_timeout_seconds: int = 300
    distributed_lock_wait_seconds: int = 5
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"
    cors_origins: list[str] = Field(default_factory=list)

    dev_auth_enabled: bool = True
    admin_token: str = "change-me"
    auth_signing_key: str = "local-development-signing-key"
    # Separate keyed pseudonymization boundary for the campus login subject.
    # The raw NetID is used only in memory and is never persisted or logged.
    identity_hash_key: str | None = None
    access_token_ttl_seconds: int = 2_592_000
    public_web_base_url: str = "https://onemore.example"

    hermes_mode: Literal["fake", "real"] = "fake"
    sysu_cli: str = str(Path.home() / ".local/bin/sysu-anything")
    vault_root: Path = Path("./vaults")
    vault_master_key: str | None = None
    executor_global_slots: int = 32
    executor_per_user_per_minute: int = 20
    executor_read_timeout_seconds: int = 30
    executor_write_timeout_seconds: int = 60
    executor_login_timeout_seconds: int = 200

    auto_create_schema: bool = True
    seed_demo_data: bool = False
    competition_public_snapshot_version: str = "competition-radar-cn-v1.1-2026-08-11"
    media_root: Path = Path("./runtime/media")
    media_max_image_bytes: int = 10 * 1024 * 1024

    # APNs device tokens are recoverable only inside the delivery boundary.
    # Values are supplied as a JSON object, for example {"2026-08":"secret"},
    # so a deployment can retain old decrypt-only keys while rotating writes.
    push_mode: Literal["fake", "apns"] = "fake"
    push_token_key_id: str = "development-v1"
    push_token_encryption_keys: dict[str, str] = Field(default_factory=dict)
    apns_team_id: str | None = None
    apns_key_id: str | None = None
    apns_topic: str | None = None
    apns_private_key: str | None = None
    apns_environment: Literal["sandbox", "production"] = "sandbox"
    apns_timeout_seconds: float = 10.0

    douyin_import_enabled: bool = True
    douyin_mode: Literal["fake", "browser"] = "fake"
    douyin_browser_executable: str = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    douyin_browser_headless: bool = True
    douyin_runtime_root: Path = Path("./runtime/douyin")
    douyin_qr_timeout_seconds: int = 180
    douyin_collection_timeout_seconds: int = 1200
    douyin_max_parallel_imports: int = 2
    douyin_keep_raw_debug: bool = False

    # Douyin taste-profile AI narrative via OpenCode Go · DeepSeek V4 Flash.
    # Tag scoring remains deterministic; LLM only rewrites summary / facets.
    taste_llm_enabled: bool = True
    taste_llm_base_url: str = "https://opencode.ai/zen/go/v1"
    taste_llm_model: str = "deepseek-v4-flash"
    taste_llm_api_key: str = ""
    taste_llm_timeout_seconds: float = 45.0

    @field_validator("database_url")
    @classmethod
    def normalize_postgres_driver(cls, value: str) -> str:
        if value.startswith("postgres://"):
            return value.replace("postgres://", "postgresql+psycopg://", 1)
        if value.startswith("postgresql://"):
            return value.replace("postgresql://", "postgresql+psycopg://", 1)
        return value

    @property
    def is_production(self) -> bool:
        return self.env == "production"

    def validate_runtime(self) -> None:
        if not self.is_production:
            return
        issues: list[str] = []
        if self.database_url.startswith("sqlite"):
            issues.append("production requires PostgreSQL")
        if self.dev_auth_enabled:
            issues.append("ONEMORE_DEV_AUTH_ENABLED must be false")
        if self.admin_token == "change-me":
            issues.append("ONEMORE_ADMIN_TOKEN must be rotated")
        if self.auth_signing_key == "local-development-signing-key":
            issues.append("ONEMORE_AUTH_SIGNING_KEY must be rotated")
        if not self.identity_hash_key:
            issues.append("ONEMORE_IDENTITY_HASH_KEY is required")
        if not self.vault_master_key:
            issues.append("ONEMORE_VAULT_MASTER_KEY is required")
        if self.push_token_key_id not in self.push_token_encryption_keys:
            issues.append(
                "ONEMORE_PUSH_TOKEN_ENCRYPTION_KEYS must include ONEMORE_PUSH_TOKEN_KEY_ID"
            )
        if self.push_mode == "apns" and not all(
            (self.apns_team_id, self.apns_key_id, self.apns_topic, self.apns_private_key)
        ):
            issues.append("APNs mode requires team id, key id, topic and private key")
        if self.auto_create_schema:
            issues.append("ONEMORE_AUTO_CREATE_SCHEMA must be false; use Alembic")
        if issues:
            raise RuntimeError("Invalid production configuration: " + "; ".join(issues))


@lru_cache
def get_settings() -> Settings:
    return Settings()
