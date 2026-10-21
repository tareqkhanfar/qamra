# syntax=docker/dockerfile:1.7
# One image family for the Python services: `api` and `worker` (worker adds Chromium for PDFs).
FROM python:3.12-slim-bookworm AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH=/opt/venv/bin:$PATH QAMRA_CONTENT_DIR=/app/content
COPY --from=ghcr.io/astral-sh/uv:0.7.22 /uv /uvx /bin/
WORKDIR /app

# third-party dependencies first (cached unless the lockfile changes)
COPY pyproject.toml uv.lock ./
COPY packages/ai/pyproject.toml packages/ai/
COPY packages/pdf/pyproject.toml packages/pdf/
COPY packages/core/pyproject.toml packages/core/
COPY packages/workbook/pyproject.toml packages/workbook/
COPY apps/api/pyproject.toml apps/api/
COPY apps/worker/pyproject.toml apps/worker/
RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen --no-dev --no-install-workspace

COPY packages packages
COPY apps/api apps/api
COPY apps/worker apps/worker
COPY content content
RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen --no-dev \
 && useradd --system --uid 10001 --home /app qamra

FROM base AS api
USER qamra
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s --retries=6 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health/live', timeout=2)"
CMD ["uvicorn", "qamra_api.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*", "--no-server-header"]

FROM base AS worker
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
RUN playwright install --with-deps chromium && rm -rf /var/lib/apt/lists/*
# the cut-out's segmentation model (qamra_pdf.matte: U²-Net, Apache-2.0), fetched once and checked
ADD --chmod=0444 --checksum=sha256:8d10d2f3bb75ae3b6d527c77944fc5e7dcd94b29809d47a739a7a728a912b491 \
    https://github.com/danielgatis/rembg/releases/download/v0.0.0/u2net.onnx /opt/models/u2net.onnx
# a builder without BuildKit ignores --chmod on a remote ADD (the file stays 0600, unreadable to `qamra`)
RUN chmod 0755 /opt/models && chmod 0444 /opt/models/u2net.onnx
USER qamra
CMD ["sh", "-c", "exec rq worker --url \"$REDIS_URL\" --with-scheduler generation pdf maintenance default"]
