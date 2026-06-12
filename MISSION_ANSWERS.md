# Day 12 Lab — Mission Answers

> **Student Name:** Đặng Trần Đạt
> **Student ID:** 2A202600662
> **Khóa:** AICB-P1 · VinUniversity 2026
> **Repo:** https://github.com/dtrdat999/day12-agent-deployment

> Ghi chú: thuật ngữ tiếng Anh được giữ nguyên kèm giải thích tiếng Việt trong ngoặc.

---

## Part 1: Localhost vs Production (8đ)

### Exercise 1.1 — Anti-patterns trong `01-localhost-vs-production/develop/app.py`

Đọc kỹ file `develop/app.py`, tôi tìm được **8 anti-pattern** (mẫu thiết kế sai):

1. **Hardcoded secret** — `OPENAI_API_KEY = "sk-hardcoded-..."` và `DATABASE_URL` chứa user/password ghi thẳng trong code. Push lên GitHub là lộ key ngay; không xoay (rotate) được nếu rò rỉ.
2. **Log ra secret** — `print(f"[DEBUG] Using key: {OPENAI_API_KEY}")` in cả khóa bí mật ra log. Log thường bị thu thập tập trung → secret phát tán.
3. **Dùng `print()` thay logging** — không có level, không có timestamp, không phải JSON nên không thể parse/search/alert trong hệ thống tập trung.
4. **Không có health check** — thiếu endpoint `/health`. Platform (Railway/Render/K8s) không biết container sống hay chết để restart/định tuyến.
5. **Port & host cố định** — `host="localhost", port=8000`. `localhost` chỉ nhận traffic nội bộ container (phải là `0.0.0.0`); `PORT` phải đọc từ env vì cloud tự inject.
6. **`reload=True` trong run chính** — chế độ dev (auto-reload) tốn RAM, không an toàn, không dành cho production.
7. **Không có input validation** — `ask_agent(question: str)` nhận query param thô, không Pydantic model, không giới hạn độ dài → dễ bị abuse.
8. **`DEBUG = True` hardcode** — không tách cấu hình theo môi trường; lộ stack trace/chi tiết nội bộ ra ngoài.

> **First-principles:** gốc rễ của "it works on my machine" là **code bị trộn lẫn với cấu hình và môi trường**. Tách cấu hình ra khỏi code (12-Factor) là cách triệt tiêu nguyên nhân, không phải vá triệu chứng.

### Exercise 1.2 — Chạy basic version

```bash
cd 01-localhost-vs-production/develop
pip install -r requirements.txt
python app.py
# Test:
curl http://localhost:8000/ask -X POST -H "Content-Type: application/json" -d '{"question":"Hello"}'
```

**Quan sát:** chạy được, trả lời được — nhưng KHÔNG production-ready: không health check, secret lộ, không cấu hình theo env, không xử lý shutdown.

### Exercise 1.3 — Bảng so sánh Develop vs Production

| Feature | Develop (basic) | Production (advanced) | Tại sao quan trọng? |
|---------|-----------------|------------------------|----------------------|
| **Config** | Hardcode trong code | `os.getenv()` / Settings từ env | Cùng 1 image chạy mọi môi trường chỉ bằng đổi env; secret không bị commit; xoay key dễ (12-Factor III). |
| **Secrets** | Ghi thẳng + in ra log | Đọc từ env, không log | Tránh rò rỉ; tuân thủ bảo mật; có thể revoke/rotate. |
| **Health check** | ❌ Không có | ✅ `/health` (liveness) + `/ready` (readiness) | Platform biết khi nào **restart** (liveness) và khi nào **định tuyến traffic** (readiness) → tự phục hồi. |
| **Logging** | `print()` | JSON structured (level, ts, event) | Log có cấu trúc mới parse/search/alert được ở hệ thống tập trung (ELK, Loki). |
| **Host/Port** | `localhost:8000` cố định | `0.0.0.0` + `PORT` từ env | Container nhận traffic ngoài; cloud tự cấp PORT. |
| **Shutdown** | Đột ngột (kill) | Graceful (bắt SIGTERM, drain request) | Không mất request đang xử lý khi deploy/scale → không hỏng dữ liệu, UX ổn định. |
| **Validation** | Query param thô | Pydantic model + giới hạn | Chặn input xấu sớm (fail fast), trả 422 rõ ràng. |
| **Auth** | Không | API Key / JWT | URL public mà không auth = ai cũng gọi = cháy ví LLM. |

> **Systems thinking:** mỗi dòng là một **vòng phản hồi (feedback loop)** giúp hệ tự phục hồi: health check → orchestrator restart; readiness → load balancer ngừng gửi traffic vào instance chưa sẵn sàng; graceful shutdown → rolling deploy không rớt request.

---

## Part 2: Docker (8đ)

### Exercise 2.1 — Câu hỏi Dockerfile (dựa trên `02-docker/develop/Dockerfile`)

1. **Base image:** `python:3.11` ở bản develop (~1GB, full distro); bản production dùng `python:3.11-slim` (~130MB, gọn). Base image = HĐH + Python runtime đóng sẵn.
2. **Working directory:** `WORKDIR /app` — thư mục mặc định trong container nơi chứa code; mọi lệnh tương đối tính từ đây.
3. **Tại sao COPY `requirements.txt` TRƯỚC code?** Tận dụng **Docker layer cache** (bộ nhớ đệm tầng): layer cài deps chỉ rebuild khi `requirements.txt` đổi. Nếu chỉ sửa code (`app.py`), Docker dùng lại layer deps đã cache → build nhanh hơn nhiều.
4. **CMD vs ENTRYPOINT:** `CMD` là lệnh mặc định, có thể **ghi đè** lúc `docker run`. `ENTRYPOINT` là lệnh **cố định** (thường để biến container thành 1 "executable"); tham số `docker run` được nối vào sau ENTRYPOINT.

### Exercise 2.2 — Build & run

```bash
cd /path/to/repo            # build context = project root (để copy được utils/)
docker build -f 02-docker/develop/Dockerfile -t my-agent:develop .
docker run -p 8000:8000 my-agent:develop
docker images my-agent:develop     # quan sát size
```
**Kết quả mong đợi:** image develop lớn (~1GB) vì dùng `python:3.11` full.

### Exercise 2.3 — Multi-stage build (`02-docker/production/Dockerfile`)

- **Stage 1 — `builder`:** cài `gcc`, `libpq-dev` và `pip install --user` toàn bộ deps. Stage này cần **build tools** để biên dịch package, nhưng **không dùng để deploy**.
- **Stage 2 — `runtime`:** chỉ `COPY --from=builder` phần site-packages đã cài + source code, chạy bằng non-root user. Không mang theo gcc/build cache.
- **Tại sao image nhỏ hơn?** Vì runtime **vứt bỏ** toàn bộ build tools và file rác của quá trình compile; base `slim` cũng nhỏ hơn full. Kết quả: giảm ~50–70% dung lượng.

| | Develop (single-stage) | Production (multi-stage) |
|---|---|---|
| Base | `python:3.11` (~1GB) | `python:3.11-slim` (~130MB) |
| Build tools trong image cuối | Có | **Không** |
| User | root | **non-root** (`agent`) |
| Healthcheck | Không | Có |
| **Size ước tính** | ~1.0 GB | **~200 MB** (< 500MB ✅) |

> Final project của tôi (`06-lab-complete`) dùng multi-stage + slim + non-root + HEALTHCHECK → image ≈ 200MB.

### Exercise 2.4 — Kiến trúc Docker Compose stack

`docker-compose.yml` (bản final của tôi) khởi động 3 service và scale agent:

```
                 ┌──────────────┐
   Client  ───▶  │ Nginx (LB)   │  cổng 80
                 └──────┬───────┘
            round-robin │  (Docker DNS)
          ┌─────────────┼─────────────┐
          ▼             ▼             ▼
      ┌────────┐   ┌────────┐   ┌────────┐
      │Agent 1 │   │Agent 2 │   │Agent 3 │  cổng 8000 (expose nội bộ)
      └────┬───┘   └────┬───┘   └────┬───┘
           └────────────┼────────────┘
                        ▼
                  ┌───────────┐
                  │   Redis   │  cổng 6379 (state dùng chung)
                  └───────────┘
```

- **Giao tiếp:** các service gọi nhau qua **service name** trên mạng nội bộ của Compose (`redis://redis:6379`, `http://agent:8000`). Nginx phân phối tải tới 3 agent; cả 3 agent đọc/ghi state ở **Redis dùng chung** → stateless, scale ngang được.
- Chạy: `docker compose up --build --scale agent=3` → test `curl http://localhost/health`.

---

## Part 3: Cloud Deployment (8đ)

### Exercise 3.1 — Railway

```bash
npm i -g @railway/cli
railway login
railway init
railway variables set AGENT_API_KEY=<khóa-mạnh>
railway variables set RATE_LIMIT_PER_MINUTE=10
railway variables set MONTHLY_BUDGET_USD=10.0
# (tùy chọn) thêm Redis plugin -> Railway tự set REDIS_URL
railway up
railway domain     # lấy public URL
```
- **Public URL:** _(điền sau khi deploy — xem `DEPLOYMENT.md`)_
- Railway tự inject `$PORT`; `railway.toml` đã cấu hình `startCommand` đọc `$PORT` + `healthcheckPath=/health`.

### Exercise 3.2 — So sánh `render.yaml` vs `railway.toml`

| Tiêu chí | `railway.toml` | `render.yaml` (Blueprint) |
|----------|----------------|----------------------------|
| Định dạng | TOML | YAML |
| Trigger deploy | CLI `railway up` hoặc Git | Git push (Blueprint, autoDeploy) |
| Khai báo service | 1 service, cấu hình build/deploy | **Nhiều service** trong 1 file (web + keyvalue/Redis) |
| Quản lý secret | `railway variables set` / dashboard | `envVars` với `generateValue`, `sync:false`, `fromService` |
| Health check | `healthcheckPath` | `healthCheckPath` |
| Provision phụ thuộc | Thêm plugin riêng | Khai báo luôn Redis (`type: keyvalue`) trong cùng file |

> **Insight:** `render.yaml` thiên về **Infrastructure-as-Code khai báo** (cả stack trong 1 file, gồm Redis); `railway.toml` tối giản, hợp prototyping nhanh qua CLI. Tôi chọn Render để có Redis miễn phí → chứng minh stateless thật trên cloud.

### Exercise 3.3 — (Optional) GCP Cloud Run CI/CD

`cloudbuild.yaml` định nghĩa pipeline: **build** image → **push** lên Artifact Registry → **deploy** lên Cloud Run. `service.yaml` mô tả service (image, env, autoscaling, concurrency). Ưu điểm Cloud Run: scale-to-zero (không request = không tốn tiền), tự autoscale theo request, tích hợp CI/CD qua Cloud Build trigger trên mỗi commit.

---

## Part 4: API Security (8đ)

### Exercise 4.1 — API Key authentication (`04-api-gateway/develop`)

- Key được check bằng dependency đọc header `X-API-Key` và so với giá trị từ env.
- Sai/thiếu key → **401 Unauthorized**.
- **Rotate key:** đổi biến môi trường `AGENT_API_KEY` rồi cấp lại cho client; vì key không hardcode nên xoay không cần sửa code/redeploy lại image. (Trong final project tôi dùng `hmac.compare_digest` để chống **timing attack** — tấn công đo thời gian so sánh chuỗi.)

### Exercise 4.2 — JWT authentication (`04-api-gateway/production/auth.py`)

- **Flow:** `POST /token` (username/password) → server ký JWT (HS256) chứa `sub`, `role`, `iat`, `exp` → client gửi `Authorization: Bearer <token>` ở các request sau.
- **Stateless:** server chỉ verify chữ ký + hạn (`exp`), **không cần tra DB** mỗi request → scale tốt. Đánh đổi: thu hồi token trước hạn khó hơn (cần blacklist).

### Exercise 4.3 — Rate limiting (`04-api-gateway/production/rate_limiter.py`)

- **Algorithm:** **Sliding Window Counter** (cửa sổ trượt) — mỗi user 1 `deque` timestamp; loại timestamp ngoài cửa sổ 60s; đếm số còn lại.
- **Limit:** mặc định **10 req/phút** cho user; admin **100 req/phút** (2 instance singleton khác nhau).
- **Bypass cho admin:** dùng `rate_limiter_admin` với hạn mức cao hơn dựa trên `role` trong JWT.
- Vượt hạn → **429 Too Many Requests** kèm header `Retry-After`.

> Trong final project, tôi nâng cấp sang **Redis sorted set (ZSET)** để rate limit **stateless** dùng chung cho nhiều instance (in-memory deque sẽ sai khi scale vì mỗi instance đếm riêng).

### Exercise 4.4 — Cost guard

Logic tôi triển khai trong `06-lab-complete/app/cost_guard.py`:

```python
def check_budget(user_id: str) -> None:
    spent = store.cost_get(f"{user_id}:{this_month}")   # đọc từ Redis
    if spent >= settings.monthly_budget_usd:            # $10/user/tháng
        raise HTTPException(402, "Monthly budget exceeded")

def record_cost(user_id, in_tok, out_tok):
    cost = in_tok/1000*0.00015 + out_tok/1000*0.0006     # giá gpt-4o-mini
    store.cost_add(f"{user_id}:{this_month}", cost, ttl=32*86400)  # tự reset đầu tháng
```

- **Cách tiếp cận:** track chi phí lũy kế theo key `user:YYYY-MM` trong Redis; check **trước** khi gọi LLM (chặn 402 nếu vượt), ghi nhận **sau** khi gọi. TTL 32 ngày để key tự hết hạn → tự reset đầu tháng.
- **Vì sao 402 (Payment Required):** ngữ nghĩa đúng cho "vượt ngân sách" (khác 429 rate limit).

---

## Part 5: Scaling & Reliability (8đ)

### Exercise 5.1 — Health & Readiness checks

```python
@app.get("/health")   # Liveness: process còn sống? -> luôn 200 nếu app chạy
def health(): return {"status": "ok", ...}

@app.get("/ready")    # Readiness: sẵn sàng nhận traffic? (check Redis)
def ready():
    if not _state["ready"] or _state["shutting_down"]:
        raise HTTPException(503, "Not ready")
    if not store.ping():
        raise HTTPException(503, "Store không phản hồi")
    return {"ready": True}
```
- **Phân biệt:** *liveness* sai → orchestrator **restart container**; *readiness* sai → load balancer **ngừng gửi traffic** vào instance đó (không restart). Tách 2 khái niệm tránh restart oan khi chỉ là dependency tạm chưa sẵn sàng.

### Exercise 5.2 — Graceful shutdown

```python
def _handle_sigterm(signum, frame):
    _state["shutting_down"] = True
    log("graceful_shutdown_signal", signum=signum)   # log chứa 'graceful'
signal.signal(signal.SIGTERM, _handle_sigterm)
```
- Khi nhận **SIGTERM** (tín hiệu dừng từ orchestrator): bật cờ shutting_down → ngừng nhận request mới (`/ask` trả 503), **drain** (chờ) các request đang chạy hoàn tất (tối đa ~25s qua lifespan), rồi mới thoát. Uvicorn chạy với `--timeout-graceful-shutdown 30`; Compose đặt `stop_grace_period: 30s`.
- **Test:** `docker compose kill -s TERM agent` → `docker compose logs agent | grep -i graceful`.

### Exercise 5.3 — Stateless design

- **Anti-pattern:** `conversation_history = {}` trong RAM → khi scale 3 instance, mỗi instance có bộ nhớ riêng → user bị "mất trí nhớ" tùy instance nào nhận request.
- **Đúng:** lưu history/rate-limit/cost ở **Redis** (key `history:{user_id}`, `rl:{user_id}`, `cost:{user_id}:{month}`). Mọi instance đọc cùng nguồn → state nhất quán.
- **Đã chứng minh:** chạy thật với Redis, ghi `My name is Bob` ở 1 request, đọc lại history trực tiếp từ Redis ở "instance khác" và recall đúng "Bob".

### Exercise 5.4 — Load balancing

```bash
docker compose up --build --scale agent=3
```
- Nginx (`nginx/nginx.conf`) làm **reverse proxy + load balancer**, phân phối request tới 3 agent qua Docker DNS round-robin; `proxy_next_upstream` cho **failover** khi 1 instance lỗi.

### Exercise 5.5 — Test stateless

- Nguyên tắc test (`test_stateless.py` của lab): tạo conversation → kill 1 instance ngẫu nhiên → gọi tiếp → history **vẫn còn** vì nằm ở Redis chứ không phải RAM của instance đã chết.

> **Checkpoint 5 — Trade-off:** stateless đổi lấy thêm 1 hop mạng tới Redis (latency nhỏ) nhưng nhận lại khả năng scale ngang + rolling deploy không mất state. Với hệ nhiều user, đây là đánh đổi gần như luôn đáng.

---

## Cross-domain Insight

Bộ "health check + readiness + graceful shutdown + stateless" thực chất là cùng một nguyên lý với **resilience engineering** trong vận hành và cả trong **growth/marketing ops**: tách *trạng thái* khỏi *tính toán*, để mọi node có thể thay thế nhau (fungible). Trong marketing automation, đây là lý do ta đẩy state (user journey, attribution) về data layer dùng chung thay vì giữ trong từng tool — giống hệt việc đẩy conversation history về Redis.

## 3 Câu hỏi đào sâu

1. **Sliding window vs Token bucket:** khi nào token bucket (cho phép burst) phù hợp hơn sliding window cho API LLM đắt tiền, và đánh đổi về trải nghiệm người dùng là gì?
2. **Stateless vs sticky session:** với streaming response dài, giữ stateless hoàn toàn qua Redis có còn tối ưu, hay cần sticky session + checkpoint? Ranh giới nằm ở đâu?
3. **Cost guard ở tầng nào:** chặn ngân sách ở application layer (như hiện tại) đủ chưa, hay nên đẩy lên API gateway/billing layer để bảo vệ xuyên nhiều service?
