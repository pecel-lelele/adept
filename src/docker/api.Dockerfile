# API image. Build from the repository root: docker build -f src/docker/api.Dockerfile .
# Dependencies come from uv.lock (frozen), the same lockfile CI and Replit use.
FROM python:3.11-slim
COPY --from=ghcr.io/astral-sh/uv:0.12.10 /uv /usr/local/bin/uv
WORKDIR /workspace
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/workspace/src/api:/workspace/src \
    UV_PROJECT_ENVIRONMENT=/opt/venv UV_LINK_MODE=copy UV_COMPILE_BYTECODE=0 \
    PATH=/opt/venv/bin:$PATH
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project --python /usr/local/bin/python3.11
COPY src/api src/api
COPY src/pipelines src/pipelines
COPY src/db src/db
COPY src/data/seed src/data/seed
COPY docs/reference docs/reference
COPY src/docker/boot.py src/docker/boot.py
RUN useradd --create-home adept
USER adept
EXPOSE 8000
# Starts the API only. Migrations and seeds are a separate, explicit step:
#   docker compose --profile setup run --rm migrate
CMD ["python", "src/docker/boot.py"]
