FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    SLEEP_API_MODEL_DIR=/artifacts/model \
    SLEEP_API_UPLOAD_DIR=/app/storage/uploads

RUN apt-get update \
    && apt-get install --no-install-recommends -y libgomp1 curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build
COPY packages/sleep-staging ./packages/sleep-staging
COPY apps/api ./apps/api
RUN python -m pip install --no-cache-dir ./packages/sleep-staging[inference] \
    && python -m pip install --no-cache-dir ./apps/api

RUN useradd --create-home --uid 10001 appuser \
    && mkdir -p /app/storage/uploads /artifacts/model \
    && chown -R appuser:appuser /app /artifacts

USER appuser
WORKDIR /app
EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl --fail http://localhost:8080/health || exit 1

CMD ["uvicorn", "sleep_api.main:app", "--host", "0.0.0.0", "--port", "8080"]

