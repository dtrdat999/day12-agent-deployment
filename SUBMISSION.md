# 📦 Day 12 Submission — Đặng Trần Đạt (2A202600662)

> Bài nộp Lab Day 12 — Cloud Infra & Production Deployment · AICB-P1, VinUniversity 2026.

## Cần chấm gì ở đâu

| Hạng mục | Điểm | Vị trí |
|----------|------|--------|
| **Part 1–5 Exercises** | 40 | [`MISSION_ANSWERS.md`](MISSION_ANSWERS.md) |
| **Part 6 Final Project (source)** | 60 | [`06-lab-complete/`](06-lab-complete/) |
| **Deployment / Public URL** | (trong Part 6) | [`DEPLOYMENT.md`](DEPLOYMENT.md) |

## Final Project highlights (`06-lab-complete/`)

- **Functional:** `/ask` trả lời + **conversation history** (nhớ ngữ cảnh, stateless qua Redis) + error handling (401/402/422/429/500).
- **Docker:** Multi-stage, `python:3.11-slim`, non-root, HEALTHCHECK → image ≈ 200MB (< 500MB).
- **Security:** API Key auth (hmac), rate limit 10/phút (sliding window/Redis), cost guard $10/user/tháng (402), không hardcode secret.
- **Reliability:** `/health` (liveness), `/ready` (readiness + Redis ping), graceful shutdown (SIGTERM drain).
- **Scalability:** Stateless (state ở Redis) + Nginx load balancer, `docker compose up --scale agent=3`.
- **Deployment:** `railway.toml` + `render.yaml` (Render kèm Redis free).

## Đã tự kiểm thử (PASS)

```
06-lab-complete/check_production_ready.py   → 20/20 (100%)
06-lab-complete/test_security.py            → tất cả PASS
  health 200 · ready 200 · no-key 401 · key 200 · bad-body 422
  conversation history nhớ tên · rate limit 429 · metrics 401
```

## Việc bạn (Đạt) cần làm tay trước khi nộp cuối

1. Deploy theo `DEPLOYMENT.md` (Render khuyến nghị) → lấy **Public URL** → điền vào `DEPLOYMENT.md`.
2. Chụp screenshots vào `screenshots/` (dashboard, /health, rate-limit 429, env vars).
3. `git add . && git commit -m "Day 12: production agent" && git push`.
4. Đảm bảo repo public hoặc cấp quyền cho giảng viên.
