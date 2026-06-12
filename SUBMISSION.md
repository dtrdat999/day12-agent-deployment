# Day 12 Submission — Đặng Trần Đạt (2A202600662)

> Lab Day 12 — Cloud Infra & Production Deployment · AICB-P1, VinUniversity 2026.

## Links

| Item | URL |
|------|-----|
| GitHub repository | https://github.com/dtrdat999/day12-agent-deployment |
| Railway public URL | https://skillful-delight-production-b06b.up.railway.app/ |

## What To Grade

| Requirement | Location |
|-------------|----------|
| Part 1-5 written answers | `MISSION_ANSWERS.md` |
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
- Conversation history stored through a Redis-compatible store, with memory fallback for local tests.
- Stateless design suitable for multiple app instances behind Nginx.
- Structured JSON logging.
- Graceful shutdown on SIGTERM.
- Multi-stage Docker build with slim runtime and non-root user.

## Verified Locally

```text
test_security.py: 8 passed, 0 failed
check_production_ready.py: 20/20 checks passed (100%)
```

## Remaining Manual Proof

After Railway finishes the latest redeploy, capture screenshots into `screenshots/`:

- `dashboard.png`
- `health.png`
- `rate-limit.png`
- `env.png`
