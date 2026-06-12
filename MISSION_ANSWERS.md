# Day 12 Lab - Mission Answers

## Part 1: Localhost vs Production

### Exercise 1.1: Anti-patterns found
1. **API key hardcode trong code:** Lưu trữ trực tiếp khóa `OPENAI_API_KEY` và `DATABASE_URL` trong file code. Rất nguy hiểm vì khi push lên GitHub sẽ bị lộ ngay lập tức.
2. **Không có config management:** Cài đặt cứng các biến như `DEBUG = True` và `MAX_TOKENS = 500`. Thiếu sự linh hoạt khi muốn chuyển đổi giữa môi trường test và thật.
3. **Dùng hàm print() thay vì logging chuẩn:** In log bằng `print()` không phân loại được mức độ log (INFO, DEBUG, ERROR), không xuất ra định dạng JSON để hệ thống dễ đọc, và đặc biệt là in luôn cả API KEY ra màn hình console.
4. **Không có health check endpoint:** Không có các route như `/health` hay `/ready`. Nếu agent bị sập ngầm (treo tiến trình), hệ thống Cloud (Load Balancer) sẽ không biết để khởi động lại.
5. **Port và Host cố định (Cứng):** Chạy ở `host="localhost"` (chỉ nội bộ máy tính mới gọi được, khi đưa lên Docker hoặc Cloud thì bên ngoài không thể truy cập) và cắm cứng `port=8000` thay vì lấy từ biến môi trường của nền tảng Cloud (như Railway/Render).

### Exercise 1.3: Comparison table
| Feature | Develop (Basic) | Production (Advanced) | Tại sao quan trọng? |
|---------|---------|------------|----------------|
| **Config**  | Hardcode (Cắm cứng) | Env vars (Biến môi trường) | Bảo mật thông tin nhạy cảm (API Key), dễ thay đổi cấu hình không cần sửa code. |
| **Health check** | Không có | Có (`/health`, `/ready`) | Để hệ thống Cloud (Load Balancer/Kubernetes) biết lúc nào app sống/chết để tự restart. |
| **Logging** | Dùng `print()` (Văn bản thuần) | Dùng Thư viện `logging` (JSON) | Hệ thống quản lý log (Datadog/CloudWatch) dễ dàng parse và lọc lỗi. Tránh in nhầm API Key. |
| **Shutdown** | Đột ngột | Graceful (Xử lý SIGTERM) | Hoàn thành nốt các câu hỏi đang trả lời dở dang rồi mới tắt máy chủ, giúp user không bị đứt gãy giữa chừng. |
| **Networking** | `localhost:8000` | `0.0.0.0:$PORT` | `0.0.0.0` giúp app nhận traffic từ bên ngoài (Internet/Docker), `$PORT` linh hoạt theo cấp phát của Cloud. |

## Part 2: Docker Containerization

### Exercise 2.1: Dockerfile cơ bản
1. **Base image:** `python:3.11` (Bản Python đầy đủ, nặng khoảng ~1GB).
2. **Working directory:** `/app` (Mọi lệnh chạy sau đó sẽ lấy thư mục này làm gốc).
3. **Tại sao COPY requirements.txt trước?** Để tận dụng bộ đệm (Docker layer cache). Nếu file code thay đổi nhưng file yêu cầu thư viện (requirements.txt) không đổi, Docker sẽ không tốn thời gian tải và cài lại hàng trăm MB thư viện từ đầu.
4. **CMD vs ENTRYPOINT:** `CMD` cung cấp lệnh mặc định để chạy khi container khởi động (VD: `CMD ["python", "app.py"]`), người dùng có thể dễ dàng ghi đè (thay thế) lệnh này khi chạy `docker run`. Còn `ENTRYPOINT` thì đóng đinh container phải chạy lệnh đó, người dùng chỉ có thể truyền thêm tham số chứ khó ghi đè hơn.

### Exercise 2.3: Multi-stage build
1. **Stage 1 (Builder) làm gì?** Cài đặt các công cụ nặng nề (như `gcc`, `libpq-dev`) để tải và biên dịch các thư viện Python. Image này to, nặng và KHÔNG được dùng để chạy thật (deploy).
2. **Stage 2 (Runtime) làm gì?** Sử dụng hệ điều hành siêu nhẹ (`slim`), tạo một user không có quyền root (`appuser`) để bảo mật. Sau đó nó chỉ copy đúng phần thư viện đã được "nấu chín" từ Stage 1 sang, và copy mã nguồn vào.
3. **Tại sao image nhỏ hơn?** Vì Stage 2 hoàn toàn vứt bỏ đi các phần mềm thừa thãi ở Stage 1 (trình biên dịch, file rác, file cache tải về từ pip). Điều này giúp dung lượng image giảm từ ~1GB xuống dưới 500MB và cực kỳ an toàn.

## Part 3: Cloud Deployment

### Exercise 3.1: Railway deployment
- URL: [Bạn sẽ điền link vào đây sau khi deploy thành công]
- Screenshot: [Bạn sẽ điền link ảnh chụp màn hình vào đây]

## Part 4: API Security

### Exercise 4.1-4.3: Test results
- Thử nghiệm gọi API không truyền JWT/Key: [Thất bại - Báo lỗi 401 Unauthorized]
- Thử nghiệm gọi API đúng Key: [Thành công - Trả về 200 OK và answer]
- Thử nghiệm gọi quá giới hạn Rate Limiting (spam >10 req/min): [Thất bại - Báo lỗi 429 Too Many Requests]

### Exercise 4.4: Cost guard implementation
- Cơ chế bảo vệ chi phí hoạt động bằng cách: Giới hạn ngân sách hàng ngày (Ví dụ: $1/ngày). Mỗi khi gọi LLM, tính toán số token đầu vào/đầu ra, nhân với đơn giá (VD: $0.00015/1k token) rồi cộng dồn vào `_daily_cost`. Nếu vượt quá $1, hệ thống lập tức báo lỗi 503 Service Unavailable để tránh cạn kiệt tài khoản ngân hàng.

## Part 5: Scaling & Reliability

### Exercise 5.1-5.5: Implementation notes
- Việc sử dụng `docker-compose.yml` giúp mở rộng số lượng Agent (VD: 2 replicas) đằng sau Load Balancer (Nginx) dễ dàng.
- Để Agent A và Agent B đồng bộ với nhau (tránh spam hoặc tính sai cost), hệ thống cần chuyển `rate_limit` và `cost_guard` từ bộ nhớ RAM (In-memory) sang dùng chung một Redis. Redis đóng vai trò như bộ nhớ tập trung siêu tốc cho tất cả các bản sao Agent.
- Tính năng Health Check và Graceful Shutdown đảm bảo khi hệ thống bị quá tải hoặc cần update, nó không ngắt ngang yêu cầu của khách hàng đang gọi dở, mà chờ xử lý xong mới tự động tắt.
