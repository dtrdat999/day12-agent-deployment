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
- **Public URL (đang chạy):** https://skillful-delight-production-b06b.up.railway.app/ — thực tế tôi deploy qua **GitHub** (push lên `main` → Railway tự build từ root `Dockerfile`), thay cho `railway up`.
- **PORT:** Railway tự inject `$PORT`. App lắng nghe `0.0.0.0:$PORT` nhờ `CMD` trong Dockerfile: `sh -c "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} ..."`. `healthcheckPath=/health`, `healthcheckTimeout=300` khai báo trong `railway.toml`.
- **🐞 Bài học gỡ lỗi thực tế (quan trọng):** ban đầu tôi đặt `startCommand` trong `railway.toml` là `uvicorn ... --port $PORT`. Railway chạy start command **KHÔNG qua shell** nên chuỗi `$PORT` **không được bung thành số** → uvicorn báo `Error: Invalid value for '--port': '$PORT' is not a valid integer` → app crash lặp lại → **healthcheck `/health` fail** → deploy FAILED. **Khắc phục:** **bỏ `startCommand`** để Railway dùng lại `CMD` của Dockerfile (đã bọc `sh -c` nên `${PORT:-8000}` bung đúng). Nguyên lý rút ra: **biến môi trường chỉ được expand bởi shell**; nếu runner không qua shell thì phải tự bọc `sh -c`.

### Exercise 3.2 — So sánh `render.yaml` vs `railway.toml`

| Tiêu chí | `railway.toml` | `render.yaml` (Blueprint) |
|----------|----------------|----------------------------|
| Định dạng | TOML | YAML |
| Trigger deploy | CLI `railway up` hoặc Git | Git push (Blueprint, autoDeploy) |
| Khai báo service | 1 service, cấu hình build/deploy | **Nhiều service** trong 1 file (web + keyvalue/Redis) |
| Quản lý secret | `railway variables set` / dashboard | `envVars` với `generateValue`, `sync:false`, `fromService` |
| Health check | `healthcheckPath` | `healthCheckPath` |
| Provision phụ thuộc | Thêm plugin riêng | Khai báo luôn Redis (`type: keyvalue`) trong cùng file |

> **Insight:** `render.yaml` thiên về **Infrastructure-as-Code khai báo** (cả stack trong 1 file, gồm Redis); `railway.toml` tối giản, hợp prototyping nhanh qua CLI/Git. **Tôi deploy thật lên Railway.** Bản cloud hiện chạy **in-memory store** với **1 worker** (đủ cho demo, và 1 worker là cấu hình ĐÚNG cho memory mode — xem ghi chú ở Part 5/6). Thiết kế đã sẵn sàng stateless: chỉ cần gắn Redis (đặt `REDIS_URL`) là chuyển sang state dùng chung cho nhiều worker/instance mà **không phải sửa code** (`store.py` tự nhận diện và fallback).

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
- **Đã chứng minh (local, có Redis):** `docker compose up --scale agent=3` với Redis dùng chung — ghi `My name is Bob` qua 1 instance, request sau (Nginx load-balance sang instance khác) vẫn recall đúng "Bob" vì history nằm ở Redis chứ không phải RAM.
- **Trên bản cloud (Railway, in-memory, 1 worker):** conversation history vẫn hoạt động trong phạm vi 1 instance — đã test live: khai báo tên rồi hỏi lại "what is my name" → server trả đúng tên.
- **🔎 Bằng chứng "stateless là bắt buộc khi scale" — gặp ngay trên production:** lúc đầu cloud chạy `--workers 2` + in-memory. Test 15 request liên tiếp **đều 200, KHÔNG có 429** vì 2 worker mỗi worker giữ bộ đếm rate-limit RIÊNG (state in-memory không chia sẻ). → Đúng y anti-pattern ở trên. **Khắc phục cho bản memory:** hạ về `--workers 1` (1 process = 1 bộ đếm) → rate-limit kích hoạt đúng (request 11+ trả 429). Muốn giữ nhiều worker/instance thì **bắt buộc** đẩy state sang Redis.

### Exercise 5.4 — Load balancing

```bash
docker compose up --build --scale agent=3
```
- Nginx (`nginx/nginx.conf`) làm **reverse proxy + load balancer**, phân phối request tới 3 agent qua Docker DNS round-robin; `proxy_next_upstream` cho **failover** khi 1 instance lỗi.

### Exercise 5.5 — Test stateless

- Nguyên tắc test (`test_stateless.py` của lab): tạo conversation → kill 1 instance ngẫu nhiên → gọi tiếp → history **vẫn còn** vì nằm ở Redis chứ không phải RAM của instance đã chết.

> **Checkpoint 5 — Trade-off:** stateless đổi lấy thêm 1 hop mạng tới Redis (latency nhỏ) nhưng nhận lại khả năng scale ngang + rolling deploy không mất state. Với hệ nhiều user, đây là đánh đổi gần như luôn đáng.

---

## Part 6: Final Project (60 phút)

> **Sản phẩm cuối:** một AI agent production-ready, gói toàn bộ concept Part 1→5, nằm ở `06-lab-complete/`, **đã deploy thật và đang chạy** tại
> https://skillful-delight-production-b06b.up.railway.app/

### 6.1 — Cấu trúc dự án

```
06-lab-complete/
├── app/
│   ├── main.py          # FastAPI app: endpoints, middleware, lifespan, SIGTERM
│   ├── config.py        # Settings 12-Factor đọc từ env
│   ├── auth.py          # API key auth (hmac.compare_digest chống timing attack)
│   ├── rate_limiter.py  # Sliding window, 429 + Retry-After
│   ├── cost_guard.py    # Ngân sách $/user/tháng, 402 khi vượt
│   ├── conversation.py  # Lịch sử hội thoại theo user
│   └── store.py         # Lớp store: Redis nếu có REDIS_URL, fallback in-memory
├── Dockerfile           # Multi-stage (builder + runtime slim, non-root)
├── docker-compose.yml   # agent (scale=3) + redis + nginx (LB)
├── nginx/nginx.conf     # reverse proxy + round-robin + failover
├── requirements.txt
├── test_security.py     # 8 test bảo mật/chức năng
└── check_production_ready.py  # 20 check production-readiness
```

Root repo có thêm `Dockerfile` + `railway.toml` làm **entrypoint deploy** cho Railway (monorepo build từ gốc, chỉ copy `06-lab-complete/app` + `utils` + `requirements.txt`).

### 6.2 — Đối chiếu yêu cầu Final Project (Requirements ✅)

**Functional**

| Yêu cầu | Trạng thái | Nơi triển khai / bằng chứng |
|---|---|---|
| Agent trả lời câu hỏi qua REST API | ✅ | `POST /ask` → trả JSON `answer` |
| Conversation history | ✅ | `conversation.py` + `store.history_*`; test live recall đúng tên |
| Streaming responses | ⚪ optional | Chưa làm (đề ghi optional); kiến trúc sẵn sàng mở rộng |

**Non-functional**

| Yêu cầu | Trạng thái | Nơi triển khai / bằng chứng |
|---|---|---|
| Dockerized — multi-stage build | ✅ | `Dockerfile` (builder→runtime slim, non-root `agent`) |
| Config từ environment variables | ✅ | `config.py` (`os.getenv`, không hardcode) — 12-Factor III |
| API key authentication | ✅ | `auth.py`; live test: thiếu key → **401** |
| Rate limiting 10 req/min/user | ✅ | `rate_limiter.py` (sliding window); live test: req 11+ → **429** |
| Cost guard $10/month/user | ✅ | `cost_guard.py`; vượt ngân sách → **402** |
| Health check endpoint | ✅ | `GET /health` → 200 |
| Readiness check endpoint | ✅ | `GET /ready` → 200 (check store) |
| Graceful shutdown | ✅ | SIGTERM handler + lifespan drain (`--timeout-graceful-shutdown 30`) |
| Stateless design (state ở Redis) | ✅ | `store.py` trừu tượng Redis/memory; chứng minh LB+Redis ở local (Part 5.3) |
| Structured JSON logging | ✅ | hàm `log()` in JSON (ts, event, …) |
| Deploy Railway/Render | ✅ | Railway, build Dockerfile từ GitHub |
| Public URL hoạt động | ✅ | https://skillful-delight-production-b06b.up.railway.app/ |

> **Lưu ý thiết kế (chặt chẽ):** bản cloud đang dùng **in-memory store + 1 worker**, là cấu hình **đúng** cho chế độ không-Redis (nhiều worker/instance với in-memory sẽ đếm rate-limit sai — đã kiểm chứng ở Part 5.3). Tính **stateless với Redis** được chứng minh đầy đủ ở stack local (`docker compose --scale agent=3` + Redis + Nginx). Để bản cloud cũng stateless đa-instance: thêm Redis service trên Railway và đặt `REDIS_URL` — code không phải đổi.

### 6.3 — Kết quả Validation (chạy local)

```bash
cd 06-lab-complete
PYTHONUTF8=1 PYTHONPATH=. python test_security.py
PYTHONUTF8=1 python check_production_ready.py
```

```text
test_security.py          : 8 passed, 0 failed
check_production_ready.py : 20/20 checks passed (100%)
```

`test_security.py` xác nhận: `/health`→200, `/ready`→200, thiếu key→401, đúng key→200, body sai→422, nhớ hội thoại, rate limit→429, `/metrics` cần key→401.

### 6.4 — Kiểm thử trên URL công khai (bằng chứng deploy thật)

```text
GET  /health            -> 200  {"status":"ok","environment":"production","store":"memory",...}
GET  /ready             -> 200  {"ready":true,"store":"memory"}
POST /ask (không key)   -> 401
POST /ask (đúng key)    -> 200  {"answer":"...","model":"gpt-4o-mini",...}
POST /ask (body sai)    -> 422
POST /ask x13 (1 user)  -> 200×10 rồi 429×3   (rate limit 10/phút hoạt động)
Conversation memory     -> khai báo tên "Alice" → hỏi lại → "Tên của bạn là Alice"
```

### 6.5 — Tự chấm theo Grading Rubric (đề ra /100)

| Criteria | Điểm | Tự đánh giá | Lý do |
|---|---|---|---|
| Functionality | 20 | 20 | `/ask` + history hoạt động đúng trên cả local lẫn cloud |
| Docker | 15 | 15 | Multi-stage, slim, non-root, HEALTHCHECK, `.dockerignore` |
| Security | 20 | 20 | API key (hmac) + rate limit (429) + cost guard (402) đều hoạt động |
| Reliability | 20 | 20 | `/health` + `/ready` + graceful shutdown (SIGTERM drain) |
| Scalability | 15 | 15 | Stateless qua `store.py`; LB Nginx + Redis chứng minh ở local |
| Deployment | 10 | 10 | Public URL Railway hoạt động, đã test đủ endpoint |
| **Total** | **100** | **100** | |

### 6.6 — Quyết định kỹ thuật & đánh đổi (Next Steps)

- **Mock LLM** thay OpenAI thật: chạy offline, không tốn tiền, không cần key (đề cho phép). Bật LLM thật chỉ cần set `OPENAI_API_KEY`.
- **In-memory + 1 worker trên cloud**: đơn giản, đủ minh chứng tính năng; đánh đổi là không chia sẻ state khi scale → đã ghi rõ đường nâng cấp (Redis + nhiều worker).
- **Hướng phát triển tiếp:** thêm Redis trên cloud (stateless thật đa-instance) → monitoring Prometheus/Grafana → CI/CD GitHub Actions auto-deploy → Kubernetes.

---

## Cross-domain Insight

Bộ "health check + readiness + graceful shutdown + stateless" thực chất là cùng một nguyên lý với **resilience engineering** trong vận hành và cả trong **growth/marketing ops**: tách *trạng thái* khỏi *tính toán*, để mọi node có thể thay thế nhau (fungible). Trong marketing automation, đây là lý do ta đẩy state (user journey, attribution) về data layer dùng chung thay vì giữ trong từng tool — giống hệt việc đẩy conversation history về Redis.

## 3 Câu hỏi đào sâu

1. **Sliding window vs Token bucket:** khi nào token bucket (cho phép burst) phù hợp hơn sliding window cho API LLM đắt tiền, và đánh đổi về trải nghiệm người dùng là gì?
2. **Stateless vs sticky session:** với streaming response dài, giữ stateless hoàn toàn qua Redis có còn tối ưu, hay cần sticky session + checkpoint? Ranh giới nằm ở đâu?
3. **Cost guard ở tầng nào:** chặn ngân sách ở application layer (như hiện tại) đủ chưa, hay nên đẩy lên API gateway/billing layer để bảo vệ xuyên nhiều service?
