# syntax=docker/dockerfile:1.7

# ─── Stage 1: frontend build (node + SvelteKit adapter-static) ───
FROM node:20-alpine AS frontend
WORKDIR /build
# 빌드 캐시 효율을 위해 lockfile 먼저 복사
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# ─── Stage 2: python runtime (uv + slim) ───
FROM python:3.12-slim AS runtime

# uv 바이너리만 가져옴 (full image 대비 최소)
COPY --from=ghcr.io/astral-sh/uv:0.5 /uv /uvx /usr/local/bin/

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH=/opt/venv/bin:$PATH

WORKDIR /app

# 의존성 layer (코드 변경과 분리)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# 앱 + 빌드된 프론트
COPY app/ ./app/
COPY --from=frontend /build/build ./frontend/build

# 비루트 실행
RUN useradd -m -u 1000 -s /usr/sbin/nologin p2p && \
    chown -R p2p:p2p /app
USER p2p

EXPOSE 8080
HEALTHCHECK --interval=15s --timeout=3s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request,sys; \
sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8080/api/health',timeout=2).status==200 else 1)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080", "--log-level", "info"]
