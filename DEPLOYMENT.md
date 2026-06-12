# Deployment Information — Day 12 Agent

> **Student:** Đặng Trần Đạt — **ID:** 2A202600662  
> **Repo:** https://github.com/dtrdat999/day12-agent-deployment

## Public URL

```text
https://day12-agent-deployment-production-5cb8.up.railway.app/
```

## Platform

Railway, Docker runtime.

The repository is a lab monorepo. The deployable production agent lives in
`06-lab-complete/`, while the root `Dockerfile` and `railway.toml` are provided
so Railway can build correctly from the GitHub repository root.

## Environment Variables

| Variable | Value / note |
|----------|--------------|
| `PORT` | Injected automatically by Railway |
| `ENVIRONMENT` | `production` |
| `AGENT_API_KEY` | Set in Railway Variables, keep secret |
| `JWT_SECRET` | Set in Railway Variables, keep secret |
| `REDIS_URL` | Railway Redis/Key Value URL, recommended for stateless scaling |
| `RATE_LIMIT_PER_MINUTE` | `10` |
| `MONTHLY_BUDGET_USD` | `10.0` |
| `OPENAI_API_KEY` | Optional; empty means the app uses mock LLM offline |

## Railway Settings

- Repository: `dtrdat999/day12-agent-deployment`
- Branch: `main`
- Builder: Dockerfile
- Dockerfile path: `Dockerfile`
- Start command:

```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 2 --timeout-graceful-shutdown 30
```

- Healthcheck path: `/health`

## Test Commands

Bash:

```bash
URL="https://day12-agent-deployment-production-5cb8.up.railway.app"
KEY="$AGENT_API_KEY"
```

PowerShell:

```powershell
$URL = "https://day12-agent-deployment-production-5cb8.up.railway.app"
$KEY = $env:AGENT_API_KEY
```

### 1. Health Check

```bash
curl "$URL/health"
```

Expected: HTTP 200 and JSON containing `"status":"ok"`.

### 2. Readiness Check

```bash
curl "$URL/ready"
```

Expected: HTTP 200 and JSON containing `"ready":true`.

### 3. Authentication Required

```bash
curl -i -X POST "$URL/ask" \
  -H "Content-Type: application/json" \
  -d '{"question":"Hello"}'
```

Expected: HTTP 401 because `X-API-Key` is missing.

### 4. Authenticated Agent Request

```bash
curl -X POST "$URL/ask" \
  -H "X-API-Key: $KEY" \
  -H "Content-Type: application/json" \
  -d '{"user_id":"test","question":"Hello"}'
```

Expected: HTTP 200 with a JSON answer.

### 5. Conversation History

```bash
curl -X POST "$URL/ask" \
  -H "X-API-Key: $KEY" \
  -H "Content-Type: application/json" \
  -d '{"user_id":"alice","question":"My name is Alice"}'

curl -X POST "$URL/ask" \
  -H "X-API-Key: $KEY" \
  -H "Content-Type: application/json" \
  -d '{"user_id":"alice","question":"What is my name?"}'
```

Expected: the second answer contains `Alice`.

### 6. Rate Limiting

```bash
for i in $(seq 1 15); do
  curl -s -o /dev/null -w "%{http_code}\n" -X POST "$URL/ask" \
    -H "X-API-Key: $KEY" \
    -H "Content-Type: application/json" \
    -d '{"user_id":"rl","question":"test"}'
done
```

Expected: requests eventually return HTTP 429.

### 7. Validation

```bash
curl -i -X POST "$URL/ask" \
  -H "X-API-Key: $KEY" \
  -H "Content-Type: application/json" \
  -d '{"invalid":"data"}'
```

Expected: HTTP 422.

## Local Verification

```bash
cd 06-lab-complete
PYTHONUTF8=1 PYTHONPATH=. python test_security.py
PYTHONUTF8=1 python check_production_ready.py
```

Latest local results:

```text
test_security.py: 8 passed, 0 failed
check_production_ready.py: 20/20 checks passed (100%)
```

## Screenshots

Store deployment proof in `screenshots/`:

- `screenshots/dashboard.png` — Railway service running
- `screenshots/health.png` — public `/health` response
- `screenshots/rate-limit.png` — rate limit test showing 429
- `screenshots/env.png` — Railway variables list with secret values hidden
