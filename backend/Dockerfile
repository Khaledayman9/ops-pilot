FROM python:3.11-slim

ARG UID=10001
ARG GID=10001

# Install system deps
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

RUN pip install uv --no-cache-dir

RUN groupadd --gid $GID appgroup \
 && useradd --uid $UID --gid appgroup --create-home appuser

WORKDIR /app

# Copy dependency files first (better layer caching)
COPY pyproject.toml uv.lock* ./

# Cache uv packages between builds
ENV UV_CACHE_DIR=/root/.cache/uv
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-dev --no-install-project

# Copy rest of source
COPY --chown=appuser:appgroup . .

# Install the project itself (fast, no re-downloading deps)
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-dev

RUN chown -R appuser:appgroup /app

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=5s --retries=5 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]