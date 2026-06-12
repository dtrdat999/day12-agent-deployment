# ============================================================
# Production Dockerfile — Multi-stage, < 500 MB, non-root user
# Stage 1 (builder): cài deps cần build tools.
# Stage 2 (runtime): chỉ copy site-packages + code => image nhỏ, sạch, an toàn.
# ============================================================

# ── Stage 1: Builder ──────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build
RUN apt-get update && apt-get install -y --no-install-recommends gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt


# ── Stage 2: Runtime ──────────────────────────────────────
FROM python:3.11-slim AS runtime

# Non-root user (chạy root trong container là bad practice về bảo mật).
RUN groupadd -r agent && useradd -r -g agent -d /app agent

WORKDIR /app

# Copy packages đã cài từ builder.
COPY --from=builder /root/.local /home/agent/.local

# Copy source code.
COPY app/ ./app/
COPY utils/ ./utils/

RUN chown -R agent:agent /app
USER agent

ENV PATH=/home/agent/.local/bin:$PATH \
    PYTHONPATH=/app \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

EXPOSE 8000

# Healthcheck: Docker tự đánh dấu unhealthy/restart nếu /health fail.
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:' + os.getenv('PORT', '8000') + '/health')" || exit 1

# 2 worker; uvicorn xử lý SIGTERM -> graceful shutdown (drain request đang chạy).
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2", "--timeout-graceful-shutdown", "30"]
