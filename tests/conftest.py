from __future__ import annotations

import os
from pathlib import Path

os.environ["ONEMORE_ENV"] = "test"
os.environ["ONEMORE_DATABASE_URL"] = "sqlite:///./test_onemore.db"
os.environ["ONEMORE_HERMES_MODE"] = "fake"
os.environ["ONEMORE_DEV_AUTH_ENABLED"] = "true"
os.environ["ONEMORE_ADMIN_TOKEN"] = "test-admin"
os.environ["ONEMORE_AUTO_CREATE_SCHEMA"] = "false"
os.environ["ONEMORE_VAULT_ROOT"] = "./test-vaults"
os.environ["ONEMORE_DOUYIN_MODE"] = "fake"
os.environ["ONEMORE_DOUYIN_IMPORT_ENABLED"] = "true"
os.environ["ONEMORE_DOUYIN_RUNTIME_ROOT"] = "./test-runtime/douyin"
os.environ["ONEMORE_TASTE_LLM_ENABLED"] = "false"

import shutil
import time

import pytest
from fastapi.testclient import TestClient

from onemore.core.config import get_settings
from onemore.core.database import SessionLocal, reset_database_for_tests
from onemore.db.seed import seed_demo_data
from onemore.main import app


@pytest.fixture(autouse=True)
def drain_orchestrator():
    from onemore.modules.taste_profile.orchestrator import taste_orchestrator

    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        if taste_orchestrator.active_count() == 0:
            break
        time.sleep(0.05)
    yield


@pytest.fixture(autouse=True)
def clean_database(drain_orchestrator):
    reset_database_for_tests()
    with SessionLocal() as db:
        seed_demo_data(db, root=Path.cwd())
    yield


@pytest.fixture(autouse=True)
def clean_runtime_dir():
    runtime_root = get_settings().douyin_runtime_root
    if runtime_root.exists():
        shutil.rmtree(runtime_root, ignore_errors=True)
    yield
    if runtime_root.exists():
        shutil.rmtree(runtime_root, ignore_errors=True)


@pytest.fixture
def client():
    with TestClient(app) as value:
        yield value


@pytest.fixture
def auth_headers():
    return {"X-User-ID": "u_demo_1"}


@pytest.fixture
def admin_headers():
    return {"X-Admin-Token": "test-admin"}
