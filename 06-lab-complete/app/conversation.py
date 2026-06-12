"""
Conversation history — quản lý lịch sử hội thoại theo user (stateless qua store).

Mỗi lượt là dict {role: "user"|"assistant", content: str}.
Lưu/đọc qua store => khi scale nhiều instance, mọi instance thấy cùng lịch sử.
"""
from app.config import settings
from app import store


def get_history(user_id: str) -> list[dict]:
    return store.history_get(user_id, settings.max_history_turns)


def add_exchange(user_id: str, question: str, answer: str) -> None:
    store.history_append(
        user_id,
        [
            {"role": "user", "content": question},
            {"role": "assistant", "content": answer},
        ],
        max_turns=settings.max_history_turns,
        ttl_seconds=settings.history_ttl_seconds,
    )


def reset(user_id: str) -> None:
    store.history_clear(user_id)
