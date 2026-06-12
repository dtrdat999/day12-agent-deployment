FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/
COPY utils/ ./utils/
COPY start.py .

ENV PYTHONPATH=/app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# KHÔNG DÙNG EXPOSE 8000 - để Railway tự quyết định PORT và map đúng
CMD ["python", "start.py"]
