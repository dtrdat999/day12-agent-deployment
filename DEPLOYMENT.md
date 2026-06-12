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
- Root directory: leave empty / repository root
- Start command:

```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 2 --timeout-graceful-shutdown 30
```

- Healthcheck path: `/health`

## If Railway Still Returns 502

The latest GitHub commit contains the deploy fixes. In Railway, redeploy from
the latest `main` commit and verify these settings:

1. Open the Railway service → **Settings** → **Source**.
2. Confirm the connected repo is `dtrdat999/day12-agent-deployment`.
3. Confirm the branch is `main`.
4. Keep **Root Directory** empty, because the root `Dockerfile` is the Railway
   entrypoint for the monorepo.
5. Confirm **Dockerfile Path** is `Dockerfile`.
6. Open **Variables** and set at least:

```text
ENVIRONMENT=production
AGENT_API_KEY=<your-secret-api-key>
RATE_LIMIT_PER_MINUTE=10
MONTHLY_BUDGET_USD=10.0
```

Optional but recommended:

```text
REDIS_URL=<railway-redis-url>
OPENAI_API_KEY=
```

7. Trigger **Redeploy** on the latest commit.

Common 502 causes now covered by the repo:

- Railway routes to `$PORT`, but Docker CMD listens on `8000` only. Fixed by
  using `${PORT:-8000}` in both Dockerfiles.
- Railway builds from repository root while the app lives in `06-lab-complete`.
  Fixed by root `Dockerfile` and root `railway.toml`.
- Missing optional `JWT_SECRET` crashes startup. Fixed; the final app uses API
  key auth and no longer crashes for that optional secret.
- Missing `AGENT_API_KEY` no longer crashes `/health`; protected endpoints keep
  returning 401 until a real key is configured.

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
