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

ENV UV_LINK_MODE=copy

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-dev --no-install-project

COPY --chown=appuser:appgroup . .

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-dev

RUN .venv/bin/python -m spacy download en_core_web_sm

RUN mkdir -p /app/run /app/logs \
 && chown -R appuser:appgroup /app/run /app/logs

USER appuser

ENV PATH="/app/.venv/bin:$PATH"
ENV UV_NO_CACHE=1

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=5s --retries=5 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]