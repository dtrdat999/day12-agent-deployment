"""
Storage layer — lớp lưu trữ trừu tượng hóa Redis với cơ chế fallback.

Vì sao cần lớp này?
  - Thiết kế STATELESS (không trạng thái) yêu cầu state nằm ở store ngoài (Redis),
    KHÔNG nằm trong RAM của process. Nhờ vậy scale 3 instance vẫn chia sẻ state.
  - Nhưng khi deploy thử trên free tier chưa gắn Redis, app vẫn phải sống.
    => Nếu kết nối Redis thất bại, tự động fallback sang in-memory để không sập.

Mọi module khác chỉ gọi store.* mà không cần biết đang dùng Redis hay memory.
"""
import time
import json
import logging
from collections import defaultdict, deque
from threading import Lock

from app.config import settings

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────
# Thử kết nối Redis. Thất bại => degraded mode (in-memory).
# ─────────────────────────────────────────────────────────────
_redis = None
_backend = "memory"

if settings.redis_url:
    try:
        import redis  # type: ignore

        _redis = redis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2,
        )
        _redis.ping()
        _backend = "redis"
        logger.info(json.dumps({"event": "store_init", "backend": "redis"}))
    except Exception as e:  # noqa: BLE001
        logger.warning(json.dumps({
            "event": "store_fallback",
            "reason": str(e),
            "backend": "memory",
        }))
        _redis = None
        _backend = "memory"
else:
    logger.info(json.dumps({"event": "store_init", "backend": "memory"}))


def backend() -> str:
    """Trả về backend đang dùng: 'redis' hoặc 'memory'."""
    return _backend


def is_redis() -> bool:
    return _backend == "redis"


def ping() -> bool:
    """Dùng cho readiness probe. Memory mode luôn 'ready'."""
    if _redis is None:
        return True
    try:
        return bool(_redis.ping())
    except Exception:  # noqa: BLE001
        return False


# ─────────────────────────────────────────────────────────────
# In-memory fallback structures (thread-safe)
# ─────────────────────────────────────────────────────────────
_lock = Lock()
_mem_windows: dict[str, deque] = defaultdict(deque)   # rate limit timestamps
_mem_cost: dict[str, float] = defaultdict(float)      # cost theo "user:YYYY-MM"
_mem_history: dict[str, deque] = defaultdict(deque)   # conversation history


# ─────────────────────────────────────────────────────────────
# RATE LIMIT — sliding window (cửa sổ trượt)
# Đếm số request của user trong 60s gần nhất.
# ─────────────────────────────────────────────────────────────
def rate_count_and_add(key: str, window_seconds: int) -> int:
    """
    Ghi nhận 1 request và trả về SỐ REQUEST trong cửa sổ (đã gồm request này).
    Redis: dùng sorted set (ZSET) với score = timestamp.
    """
    now = time.time()
    cutoff = now - window_seconds

    if _redis is not None:
        try:
            zkey = f"rl:{key}"
            pipe = _redis.pipeline()
            pipe.zremrangebyscore(zkey, 0, cutoff)          # bỏ timestamp cũ
            pipe.zadd(zkey, {f"{now}:{time.time_ns()}": now})  # thêm request mới
            pipe.zcard(zkey)                                 # đếm còn lại
            pipe.expire(zkey, window_seconds + 1)
            _, _, count, _ = pipe.execute()
            return int(count)
        except Exception as e:  # noqa: BLE001
            logger.warning(json.dumps({"event": "rate_redis_error", "err": str(e)}))

    # Fallback in-memory
    with _lock:
        w = _mem_windows[key]
        while w and w[0] < cutoff:
            w.popleft()
        w.append(now)
        return len(w)


# ─────────────────────────────────────────────────────────────
# COST GUARD — ngân sách theo tháng
# ─────────────────────────────────────────────────────────────
def cost_get(month_key: str) -> float:
    if _redis is not None:
        try:
            return float(_redis.get(f"cost:{month_key}") or 0.0)
        except Exception:  # noqa: BLE001
            pass
    with _lock:
        return _mem_cost[month_key]


def cost_add(month_key: str, amount: float, ttl_seconds: int) -> float:
    if _redis is not None:
        try:
            new_val = _redis.incrbyfloat(f"cost:{month_key}", amount)
            _redis.expire(f"cost:{month_key}", ttl_seconds)
            return float(new_val)
        except Exception:  # noqa: BLE001
            pass
    with _lock:
        _mem_cost[month_key] += amount
        return _mem_cost[month_key]


# ─────────────────────────────────────────────────────────────
# CONVERSATION HISTORY — lịch sử hội thoại theo user
# Lưu danh sách các lượt {role, content}. Stateless: nằm ở Redis.
# ─────────────────────────────────────────────────────────────
def history_get(user_id: str, max_turns: int) -> list[dict]:
    hkey = f"history:{user_id}"
    if _redis is not None:
        try:
            raw = _redis.lrange(hkey, -max_turns, -1)
            return [json.loads(x) for x in raw]
        except Exception:  # noqa: BLE001
            pass
    with _lock:
        return list(_mem_history[user_id])[-max_turns:]


def history_append(user_id: str, turns: list[dict], max_turns: int, ttl_seconds: int) -> None:
    hkey = f"history:{user_id}"
    if _redis is not None:
        try:
            pipe = _redis.pipeline()
            for t in turns:
                pipe.rpush(hkey, json.dumps(t, ensure_ascii=False))
            pipe.ltrim(hkey, -max_turns, -1)   # chỉ giữ N lượt gần nhất
            pipe.expire(hkey, ttl_seconds)
            pipe.execute()
            return
        except Exception:  # noqa: BLE001
            pass
    with _lock:
        dq = _mem_history[user_id]
        for t in turns:
            dq.append(t)
        while len(dq) > max_turns:
            dq.popleft()


def history_clear(user_id: str) -> None:
    if _redis is not None:
        try:
            _redis.delete(f"history:{user_id}")
            return
        except Exception:  # noqa: BLE001
            pass
    with _lock:
        _mem_history.pop(user_id, None)
