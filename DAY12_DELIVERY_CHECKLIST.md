# Day 12 Delivery Checklist

> **Student Name:** Đặng Trần Đạt  
> **Student ID:** 2A202600662  
> **Date:** 12/06/2026  
> **Repository:** https://github.com/dtrdat999/day12-agent-deployment  
> **Public URL:** https://skillful-delight-production-b06b.up.railway.app/

## Deliverables

| Requirement | Status | Evidence |
|-------------|--------|----------|
| Mission answers for Part 1-5 | Done | `MISSION_ANSWERS.md` |
| Final production source code | Done | `06-lab-complete/` |
| Root deploy configuration for Railway | Done | `Dockerfile`, `railway.toml` |
| Docker multi-stage build | Done | `06-lab-complete/Dockerfile`, root `Dockerfile` |
| API key authentication | Done | `06-lab-complete/app/auth.py` |
| Rate limiting, 10 req/min/user | Done | `06-lab-complete/app/rate_limiter.py` |
| Cost guard, $10/user/month | Done | `06-lab-complete/app/cost_guard.py` |
| Health and readiness checks | Done | `/health`, `/ready` in `06-lab-complete/app/main.py` |
| Graceful shutdown | Done | SIGTERM handler and lifespan drain in `06-lab-complete/app/main.py` |
| Stateless design | Done | Redis-backed store in `06-lab-complete/app/store.py` |
| Structured JSON logging | Done | `log()` helper in `06-lab-complete/app/main.py` |
| Deployment guide | Done | `DEPLOYMENT.md` |
| Submission summary | Done | `SUBMISSION.md` |

## Local Test Results

Commands:

```bash
cd 06-lab-complete
PYTHONUTF8=1 PYTHONPATH=. python test_security.py
PYTHONUTF8=1 python check_production_ready.py
```

Results:

```text
test_security.py: 8 passed, 0 failed
check_production_ready.py: 20/20 checks passed (100%)
```

## Pre-Submission Checklist

- [x] Repository is pushed to GitHub
- [x] `MISSION_ANSWERS.md` completed with all exercises
- [x] `DEPLOYMENT.md` contains the Railway public URL
- [x] All final source code is in `06-lab-complete/app`
- [x] Root `Dockerfile` allows Railway to deploy from repository root
- [x] Root `railway.toml` defines Docker builder, start command, and healthcheck
- [x] `README.md` has setup instructions
- [x] No `.env` file is committed
- [x] No hardcoded production secret is committed
- [x] Local security/functionality tests pass
- [x] Production readiness checker passes
- [x] Public Railway URL verified after latest redeploy
- [ ] Screenshots added to `screenshots/` after Railway redeploy is green

## Public Deployment Self-Test

```bash
URL="https://skillful-delight-production-b06b.up.railway.app"
KEY="$AGENT_API_KEY"

curl "$URL/health"

curl -i -X POST "$URL/ask" \
  -H "Content-Type: application/json" \
  -d '{"question":"Hello"}'

curl -X POST "$URL/ask" \
  -H "X-API-Key: $KEY" \
  -H "Content-Type: application/json" \
  -d '{"user_id":"test","question":"Hello"}'

for i in $(seq 1 15); do
  curl -s -o /dev/null -w "%{http_code}\n" -X POST "$URL/ask" \
    -H "X-API-Key: $KEY" \
    -H "Content-Type: application/json" \
    -d '{"user_id":"rl","question":"test"}'
done
```

Expected:

- `/health` returns 200
- `/ask` without `X-API-Key` returns 401
- `/ask` with valid key returns 200
- repeated requests eventually return 429

## Submission URL

```text
https://github.com/dtrdat999/day12-agent-deployment
```
