"""
Rate limiter — giới hạn tần suất request, thuật toán Sliding Window
(cửa sổ trượt). State nằm ở store (Redis nếu có) => STATELESS, scale được.

Quá giới hạn -> 429 Too Many Requests, kèm header Retry-After.
"""
from fastapi import HTTPException

from app.config import settings
from app import store

WINDOW_SECONDS = 60


def check_rate_limit(user_id: str) -> None:
    """Raise 429 nếu user vượt RATE_LIMIT_PER_MINUTE trong 60s."""
    count = store.rate_count_and_add(user_id, WINDOW_SECONDS)
    if count > settings.rate_limit_per_minute:
        raise HTTPException(
            status_code=429,
            detail={
                "error": "Rate limit exceeded",
                "limit_per_minute": settings.rate_limit_per_minute,
                "window_seconds": WINDOW_SECONDS,
            },
            headers={
                "Retry-After": str(WINDOW_SECONDS),
                "X-RateLimit-Limit": str(settings.rate_limit_per_minute),
                "X-RateLimit-Remaining": "0",
            },
        )
