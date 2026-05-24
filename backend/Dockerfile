FROM python:3.11-slim

ARG UID=10001
ARG GID=10001

RUN groupadd --gid $GID appgroup \
 && useradd --uid $UID --gid appgroup --create-home appuser

WORKDIR /app

COPY . .

RUN chown -R appuser:appgroup /app

USER appuser

RUN pip install uv --no-cache-dir
RUN uv sync

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]