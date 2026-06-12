# Railway deploy entrypoint for the final Day 12 app.
# The lab repo contains many exercises; the production service lives in 06-lab-complete.

FROM python:3.11-slim AS builder

WORKDIR /build
RUN apt-get update && apt-get install -y --no-install-recommends gcc \
    && rm -rf /var/lib/apt/lists/*

COPY 06-lab-complete/requirements.txt .
RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --no-cache-dir --upgrade pip \
    && /opt/venv/bin/pip install --no-cache-dir -r requirements.txt


FROM python:3.11-slim AS runtime

RUN groupadd -r agent && useradd -r -g agent -d /app agent

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
COPY 06-lab-complete/app/ ./app/
COPY 06-lab-complete/utils/ ./utils/

RUN chown -R agent:agent /app /opt/venv
USER agent

ENV PATH=/opt/venv/bin:$PATH \
    PYTHONPATH=/app \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:' + os.getenv('PORT', '8000') + '/health')" || exit 1

# 1 worker khi store = in-memory: rate limit / cost guard giữ state trong RAM của
# process, nhiều worker sẽ đếm riêng rẽ => 429 không kích hoạt đúng. Muốn scale
# nhiều worker/instance thì gắn Redis (đặt REDIS_URL) để chia sẻ state — code đã hỗ trợ.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1 --timeout-graceful-shutdown 30"]
