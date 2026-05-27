FROM python:3.11-slim

ARG UID=10001
ARG GID=10001

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN pip install uv --no-cache-dir

RUN groupadd --gid $GID appgroup \
 && useradd --uid $UID --gid appgroup --create-home appuser

WORKDIR /app

COPY pyproject.toml uv.lock* ./

# Use a cache dir that appuser can access at runtime
ENV UV_CACHE_DIR=/app/.cache/uv
ENV UV_LINK_MODE=copy

RUN --mount=type=cache,target=/app/.cache/uv \
    uv sync --no-dev --no-install-project

COPY --chown=appuser:appgroup . .

RUN --mount=type=cache,target=/app/.cache/uv \
    uv sync --no-dev

# Give appuser ownership of cache dir
RUN mkdir -p /app/.cache && chown -R appuser:appgroup /app/.cache

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=5s --retries=5 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]