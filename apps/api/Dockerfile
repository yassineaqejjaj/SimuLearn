FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev
COPY . .
ENV PATH="/app/.venv/bin:$PATH"
# Migrations puis API. Un seul worker : le runtime vocal garde l'état des sessions en mémoire (voir docs/architecture.md).
CMD ["sh", "-c", "alembic upgrade head && python scripts_seed.py && uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1"]
