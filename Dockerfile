FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1

WORKDIR /app
COPY --from=ghcr.io/astral-sh/uv:0.8.8 /uv /uvx /bin/
COPY pyproject.toml uv.lock README.md ./
COPY onemore ./onemore
COPY fixtures ./fixtures
COPY openapi ./openapi
COPY migrations ./migrations
COPY alembic.ini ./alembic.ini
RUN uv sync --frozen --no-dev

EXPOSE 8000
CMD ["sh", "-c", "uv run alembic upgrade head && exec uv run uvicorn onemore.main:app --host 0.0.0.0 --port 8000"]
