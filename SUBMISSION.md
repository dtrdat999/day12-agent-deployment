# Day 12 Submission — Đặng Trần Đạt (2A202600662)

> Lab Day 12 — Cloud Infra & Production Deployment · AICB-P1, VinUniversity 2026.

## Links

| Item | URL |
|------|-----|
| GitHub repository | https://github.com/dtrdat999/Day12_DangTranDat_2A202600662 |
| Railway public URL | https://skillful-delight-production-b06b.up.railway.app/ |

## What To Grade

| Requirement | Location |
|-------------|----------|
| Part 1-6 written answers (gồm Final Project) | `MISSION_ANSWERS.md` |
| Final production agent | `06-lab-complete/` |
| Railway deploy entrypoint | root `Dockerfile`, root `railway.toml` |
| Deployment guide and test commands | `DEPLOYMENT.md` |
| Delivery checklist | `DAY12_DELIVERY_CHECKLIST.md` |

## Final Project Highlights

- REST API with `/ask`, `/health`, `/ready`, `/metrics`, `/usage/{user_id}`, and `/history/{user_id}`.
- API key authentication with constant-time comparison.
- Pydantic validation with clear 422 responses.
- Rate limiting at 10 requests per minute per user.
- Cost guard at $10 per user per month.
- Conversation history through a Redis-compatible store, with in-memory fallback (cloud hiện chạy in-memory + 1 worker).
- Stateless-ready design: gắn `REDIS_URL` là chạy đa-instance sau Nginx (chứng minh ở stack local).
- Structured JSON logging.
- Graceful shutdown on SIGTERM.
- Multi-stage Docker build with slim runtime and non-root user.

## Verified Locally

```text
test_security.py: 8 passed, 0 failed
check_production_ready.py: 20/20 checks passed (100%)
```

## Deployment Proof (screenshots/)

- `railway-dashboard.png` — Railway service ACTIVE / Online (deploy successful)
- `public-url.png` — public URL trả JSON trên trình duyệt
