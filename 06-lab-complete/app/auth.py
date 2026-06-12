"""
Authentication — xác thực bằng API Key.

Cơ chế: client gửi header `X-API-Key: <key>`. Server so khớp với
settings.agent_api_key (đọc từ env, KHÔNG hardcode).
  - Thiếu/sai key  -> 401 Unauthorized.
  - Đúng key       -> cho qua.

So sánh dùng hmac.compare_digest để chống "timing attack"
(tấn công đo thời gian so sánh chuỗi để đoán key).
"""
import hmac
from fastapi import Security, HTTPException
from fastapi.security.api_key import APIKeyHeader

from app.config import settings

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def verify_api_key(api_key: str = Security(api_key_header)) -> str:
    """FastAPI dependency: trả về API key hợp lệ, hoặc raise 401."""
    if (
        not settings.agent_api_key
        or not api_key
        or not hmac.compare_digest(api_key, settings.agent_api_key)
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing API key. Header bắt buộc: X-API-Key: <key>",
        )
    return api_key
