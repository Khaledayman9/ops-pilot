FROM python:3.11-slim

ARG UID=10001
ARG GID=10001

# Install system deps and uv AS ROOT before switching user
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

RUN pip install uv --no-cache-dir

RUN groupadd --gid $GID appgroup \
 && useradd --uid $UID --gid appgroup --create-home appuser

WORKDIR /app

# Copy dependency files first for layer caching
COPY pyproject.toml requirements.txt ./

# Install deps as root so uv lands in /usr/local (accessible to all users)
RUN uv sync --no-dev

# Copy application code
COPY . .

RUN chown -R appuser:appgroup /app

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=5s --retries=5 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]