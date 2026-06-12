"""
Cost guard — bảo vệ ngân sách LLM theo THÁNG (mỗi user $MONTHLY_BUDGET_USD).

Tránh "bill bất ngờ": khi tổng chi phí ước tính của user trong tháng vượt
ngân sách -> 402 Payment Required. State (số tiền đã tiêu) lưu ở store/Redis,
key theo "user:YYYY-MM", tự reset đầu tháng nhờ TTL.

Giá token tham khảo theo gpt-4o-mini (USD / 1K tokens).
"""
from datetime import datetime, timezone
from fastapi import HTTPException

from app.config import settings
from app import store

PRICE_PER_1K_INPUT = 0.00015   # $0.15 / 1M input tokens
PRICE_PER_1K_OUTPUT = 0.0006   # $0.60 / 1M output tokens
# TTL 32 ngày để chắc chắn phủ hết 1 tháng rồi tự hết hạn (reset).
_TTL = 32 * 24 * 3600


def _month_key(user_id: str) -> str:
    month = datetime.now(timezone.utc).strftime("%Y-%m")
    return f"{user_id}:{month}"


def estimate_cost(input_tokens: int, output_tokens: int) -> float:
    return (input_tokens / 1000) * PRICE_PER_1K_INPUT + \
           (output_tokens / 1000) * PRICE_PER_1K_OUTPUT


def check_budget(user_id: str) -> None:
    """Raise 402 nếu user đã vượt ngân sách tháng. Gọi TRƯỚC khi gọi LLM."""
    spent = store.cost_get(_month_key(user_id))
    if spent >= settings.monthly_budget_usd:
        raise HTTPException(
            status_code=402,  # Payment Required
            detail={
                "error": "Monthly budget exceeded",
                "spent_usd": round(spent, 6),
                "budget_usd": settings.monthly_budget_usd,
                "resets_at": "đầu tháng (UTC)",
            },
        )


def record_cost(user_id: str, input_tokens: int, output_tokens: int) -> float:
    """Cộng dồn chi phí sau khi gọi LLM. Trả về tổng đã tiêu trong tháng."""
    cost = estimate_cost(input_tokens, output_tokens)
    return store.cost_add(_month_key(user_id), cost, _TTL)


def get_usage(user_id: str) -> dict:
    spent = store.cost_get(_month_key(user_id))
    return {
        "user_id": user_id,
        "spent_usd": round(spent, 6),
        "budget_usd": settings.monthly_budget_usd,
        "remaining_usd": round(max(0.0, settings.monthly_budget_usd - spent), 6),
        "used_pct": round(spent / settings.monthly_budget_usd * 100, 2),
    }
