.PHONY: install migrate capabilities openapi seed dev hermes stack test lint worker beat competitions-validate competitions-ingest sysu-reference-build sysu-reference-validate

COMPETITION_SNAPSHOT ?= fixtures/competition_snapshot_2026-08-11_v1.1.json

install:
	uv sync --dev

seed:
	uv run onemore-seed

migrate:
	uv run alembic upgrade head

capabilities:
	uv run onemore-generate-capabilities

openapi:
	uv run onemore-export-openapi

dev:
	uv run uvicorn onemore.main:app --reload --host 0.0.0.0 --port 8000

hermes:
	uv run uvicorn onemore.hermes.agent_server:app --host 127.0.0.1 --port 8642

stack:
	$(MAKE) -j2 dev hermes

test:
	uv run pytest

lint:
	uv run ruff check onemore tests migrations

worker:
	uv run celery -A onemore.tasks.celery_app:celery_app worker -l INFO

beat:
	uv run celery -A onemore.tasks.celery_app:celery_app beat -l INFO

competitions-validate:
	uv run python scripts/validate_competition_snapshot.py $(COMPETITION_SNAPSHOT)

competitions-ingest: competitions-validate migrate
	uv run onemore-ingest-competitions $(COMPETITION_SNAPSHOT)

sysu-reference-build:
	uv run python scripts/build_sysu_south_bundle.py

sysu-reference-validate:
	uv run python scripts/validate_sysu_reference.py
