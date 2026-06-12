"""
test_security.py — Test tự động cho agent (chạy local, không cần deploy).

Chạy:
    pip install -r requirements.txt httpx
    PYTHONPATH=. python test_security.py

Kiểm tra: auth (401/200), validation (422), conversation history,
rate limit (429), endpoint bảo vệ.
"""
import os
os.environ.setdefault("AGENT_API_KEY", "secret-test-key")
os.environ.setdefault("RATE_LIMIT_PER_MINUTE", "10")
os.environ.setdefault("ENVIRONMENT", "development")

from fastapi.testclient import TestClient
from app.main import app

KEY = os.environ["AGENT_API_KEY"]
H = {"X-API-Key": KEY}
passed = failed = 0


def check(name, cond):
    global passed, failed
    if cond:
        passed += 1; print(f"  PASS  {name}")
    else:
        failed += 1; print(f"  FAIL  {name}")


with TestClient(app) as c:
    check("/health -> 200", c.get("/health").status_code == 200)
    check("/ready -> 200", c.get("/ready").status_code == 200)
    check("no API key -> 401", c.post("/ask", json={"question": "hi"}).status_code == 401)
    check("valid key -> 200",
          c.post("/ask", headers=H, json={"user_id": "u", "question": "Hi"}).status_code == 200)
    check("invalid body -> 422",
          c.post("/ask", headers=H, json={"bad": "x"}).status_code == 422)

    # Conversation history
    c.post("/ask", headers=H, json={"user_id": "alice", "question": "My name is Alice"})
    r = c.post("/ask", headers=H, json={"user_id": "alice", "question": "What is my name?"})
    check("conversation history nhớ tên", "Alice" in r.json().get("answer", ""))

    # Rate limit
    last = None
    for i in range(15):
        last = c.post("/ask", headers=H, json={"user_id": "rl", "question": f"q{i}"})
    check("rate limit -> 429", last.status_code == 429)

    check("/metrics cần key (401)", c.get("/metrics").status_code == 401)

print(f"\n{passed} passed, {failed} failed")
raise SystemExit(0 if failed == 0 else 1)
