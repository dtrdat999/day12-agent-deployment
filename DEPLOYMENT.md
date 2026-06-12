# Deployment Information — Day 12 Agent

> **Student:** Đặng Trần Đạt — **ID:** 2A202600662
> **Repo:** https://github.com/dtrdat999/day12-agent-deployment

---

## Public URL

> ⚠️ ĐIỀN URL THẬT SAU KHI DEPLOY (xem hướng dẫn bên dưới):

```
https://day12-agent-<your>.onrender.com
```

## Platform

Render (Docker runtime + Key Value/Redis miễn phí) — cấu hình tại `06-lab-complete/render.yaml`.
(Railway cũng đã cấu hình sẵn tại `06-lab-complete/railway.toml`.)

---

## Cách deploy (Render — khuyến nghị vì có Redis free → stateless thật)

1. Push repo lên GitHub (đã có).
2. Vào https://render.com → **New** → **Blueprint** → chọn repo này.
3. Render đọc `06-lab-complete/render.yaml`:
   - Tạo service web `day12-agent` (Docker) + tự sinh `AGENT_API_KEY`, `JWT_SECRET`.
   - Tạo Key Value `day12-redis` và inject `REDIS_URL` vào agent → **stateless**.
   - **Lưu ý:** nếu Blueprint không tự nhận root path, set **Root Directory = `06-lab-complete`** trong Settings.
4. Mở service → tab **Environment** → copy giá trị `AGENT_API_KEY` (đã auto-generate) để test.
5. Đợi build xong → lấy URL public ở đầu trang → điền vào mục **Public URL** trên.

### Hoặc Railway

```bash
cd 06-lab-complete
railway init
railway add            # thêm Redis plugin -> tự set REDIS_URL
railway variables set AGENT_API_KEY=<khóa-mạnh> ENVIRONMENT=production \
                      RATE_LIMIT_PER_MINUTE=10 MONTHLY_BUDGET_USD=10.0
railway up
railway domain         # lấy public URL
```

---

## Environment Variables đã set

| Biến | Ý nghĩa |
|------|---------|
| `PORT` | Cloud tự inject; app đọc từ env |
| `ENVIRONMENT` | `production` |
| `AGENT_API_KEY` | Khóa xác thực (auto-generate / set tay) |
| `JWT_SECRET` | Khóa ký JWT |
| `REDIS_URL` | Kết nối Redis → stateless |
| `RATE_LIMIT_PER_MINUTE` | `10` |
| `MONTHLY_BUDGET_USD` | `10.0` |
| `OPENAI_API_KEY` | (để trống = dùng mock LLM) |

---

## Test Commands

Đặt biến cho gọn (thay URL + KEY thật):

```bash
URL="https://day12-agent-<your>.onrender.com"
KEY="<AGENT_API_KEY-từ-dashboard>"
```

### 1) Health check
```bash
curl $URL/health
# Kỳ vọng: {"status":"ok", "store":"redis", ...}
```

### 2) Readiness check
```bash
curl $URL/ready
# Kỳ vọng: {"ready":true,"store":"redis"}  (200)
```

### 3) Auth bắt buộc (không key → 401)
```bash
curl -i -X POST $URL/ask -H "Content-Type: application/json" \
  -d '{"question":"Hello"}'
# Kỳ vọng: HTTP/1.1 401 Unauthorized
```

### 4) Có key → 200
```bash
curl -X POST $URL/ask \
  -H "X-API-Key: $KEY" -H "Content-Type: application/json" \
  -d '{"user_id":"test","question":"Hello"}'
# Kỳ vọng: 200 + JSON answer
```

### 5) Conversation history (nhớ ngữ cảnh)
```bash
curl -X POST $URL/ask -H "X-API-Key: $KEY" -H "Content-Type: application/json" \
  -d '{"user_id":"alice","question":"My name is Alice"}'

curl -X POST $URL/ask -H "X-API-Key: $KEY" -H "Content-Type: application/json" \
  -d '{"user_id":"alice","question":"What is my name?"}'
# Kỳ vọng: answer có chứa "Alice"
```

### 6) Rate limiting (→ 429 sau 10 req/phút)
```bash
for i in $(seq 1 15); do
  curl -s -o /dev/null -w "%{http_code}\n" -X POST $URL/ask \
    -H "X-API-Key: $KEY" -H "Content-Type: application/json" \
    -d '{"user_id":"rl","question":"test"}'
done
# Kỳ vọng: 200 x10 rồi 429 x5
```

### 7) Validation (body sai → 422)
```bash
curl -i -X POST $URL/ask -H "X-API-Key: $KEY" \
  -H "Content-Type: application/json" -d '{"invalid":"data"}'
# Kỳ vọng: HTTP/1.1 422
```

---

## Screenshots

Đặt ảnh trong thư mục `screenshots/`:

- `screenshots/dashboard.png` — dashboard platform (service running)
- `screenshots/health.png` — kết quả `curl /health`
- `screenshots/rate-limit.png` — chuỗi 200 → 429
- `screenshots/env.png` — danh sách environment variables (che giá trị secret)

> Cách chụp nhanh: chạy block "Test Commands" trong terminal và chụp output; chụp trang service + tab Environment trên Render/Railway.

---

## Self-test trước khi nộp

```bash
cd 06-lab-complete
PYTHONPATH=. python test_security.py          # test local toàn bộ security/reliability
python check_production_ready.py               # phải 100%
```
