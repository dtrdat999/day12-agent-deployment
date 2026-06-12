# Production AI Agent — Final Project (Day 12)

> **Student:** Đặng Trần Đạt — **ID:** 2A202600662
> Production-ready AI agent: Docker multi-stage, API key auth, rate limiting,
> cost guard, health/readiness, graceful shutdown, **stateless** (Redis), JSON logging.

## Cấu trúc

```
06-lab-complete/
├── app/
│   ├── main.py          # FastAPI app: /ask /health /ready /metrics + pipeline
│   ├── config.py        # Cấu hình từ env (12-Factor)
│   ├── auth.py          # API Key authentication (hmac compare)
│   ├── rate_limiter.py  # Sliding window (qua store/Redis)
│   ├── cost_guard.py    # Ngân sách $10/user/tháng (qua store/Redis)
│   ├── conversation.py  # Lịch sử hội thoại (stateless)
│   └── store.py         # Redis client + fallback in-memory
├── utils/mock_llm.py    # Mock LLM context-aware (không cần API key)
├── nginx/nginx.conf     # Load balancer
├── Dockerfile           # Multi-stage, slim, non-root, healthcheck (<500MB)
├── docker-compose.yml   # nginx + agent(x3) + redis
├── requirements.txt
├── .env.example
├── railway.toml / render.yaml
├── test_security.py     # Test tự động (local)
└── check_production_ready.py
```

## Chạy local (in-memory, không cần Redis)

```bash
pip install -r requirements.txt
cp .env.example .env.local        # sửa AGENT_API_KEY
export AGENT_API_KEY=secret-key
PYTHONPATH=. uvicorn app.main:app --reload
curl http://localhost:8000/health
```

## Chạy full stack (Docker, stateless + load balanced)

```bash
cp .env.example .env.local        # set AGENT_API_KEY thật
docker compose up --build --scale agent=3
curl http://localhost/health
```

## Test

```bash
PYTHONPATH=. python test_security.py   # auth/validation/history/rate-limit
python check_production_ready.py        # 20/20 (100%)
```

## API

| Method | Endpoint | Mô tả | Auth |
|--------|----------|-------|------|
| POST | `/ask` | Hỏi agent `{user_id, question}` | X-API-Key |
| GET | `/health` | Liveness | — |
| GET | `/ready` | Readiness (check Redis) | — |
| GET | `/metrics` | Metrics | X-API-Key |
| DELETE | `/history/{user_id}` | Xóa lịch sử | X-API-Key |
| GET | `/usage/{user_id}` | Chi phí đã dùng | X-API-Key |

Deploy: xem `../DEPLOYMENT.md`.
