# ============================================================
# Production Dockerfile — Multi-stage, < 500 MB
# ============================================================

# Stage 1: Builder — cài đặt tất cả dependencies
FROM python:3.11-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Cài vào /install thay vì dùng --user (tránh path confusion)
RUN pip install --no-cache-dir -r requirements.txt --target=/install


# Stage 2: Runtime — chỉ copy những gì cần để CHẠY
FROM python:3.11-slim AS runtime

WORKDIR /app

# Copy packages từ builder
COPY --from=builder /install /app/packages

# Copy application
COPY app/ ./app/
COPY utils/ ./utils/

# Thêm packages vào PYTHONPATH để Python tìm được
ENV PYTHONPATH=/app/packages:/app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c \
    "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" \
    || exit 1

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
