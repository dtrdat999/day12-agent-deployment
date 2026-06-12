"""
Mock LLM — mô phỏng LLM, KHÔNG cần API key thật (chạy offline).

Bản nâng cấp: nhận thêm `history` (lịch sử hội thoại) để có khả năng
THAM CHIẾU NGỮ CẢNH — ví dụ user nói "My name is Alice" rồi hỏi
"What is my name?", agent tìm trong history và trả lời "Alice".
Đây là cách chứng minh tính năng conversation history hoạt động end-to-end.

Khi có OPENAI_API_KEY thật, thay hàm ask() bằng lời gọi API thật;
phần history truyền vào chính là `messages` gửi cho model.
"""
import re
import time
import random

MOCK_RESPONSES = {
    "default": [
        "Đây là câu trả lời từ AI agent (mock). Ở production, đây sẽ là response từ OpenAI/Anthropic.",
        "Agent đang hoạt động tốt! (mock response). Hỏi thêm câu hỏi nhé.",
        "Tôi là AI agent được deploy lên cloud. Câu hỏi của bạn đã được nhận.",
    ],
    "docker": ["Container là cách đóng gói app để chạy ở mọi nơi. Build once, run anywhere!"],
    "deploy": ["Deployment là quá trình đưa code từ máy bạn lên server để người khác dùng được."],
    "health": ["Agent đang hoạt động bình thường. All systems operational."],
}

# Các pattern khai báo thông tin để agent "nhớ".
_NAME_DECLARE = re.compile(r"\b(?:my name is|i am|i'm|tôi tên|tên tôi là)\s+([A-Za-zÀ-ỹ][\w'-]*)", re.IGNORECASE)
_NAME_ASK = re.compile(r"\b(what is my name|what'?s my name|tên tôi là gì|tôi tên gì)\b", re.IGNORECASE)
_RECALL_ASK = re.compile(r"\b(what did i (just )?say|i (just )?said|tôi vừa (nói|hỏi) gì)\b", re.IGNORECASE)


def _scan_name(history: list[dict] | None, question: str) -> str | None:
    """Tìm tên người dùng đã khai báo ở các lượt trước (mới nhất ưu tiên)."""
    texts = []
    if history:
        texts.extend(t.get("content", "") for t in history if t.get("role") == "user")
    texts.append(question)
    for text in reversed(texts):
        m = _NAME_DECLARE.search(text or "")
        if m:
            return m.group(1)
    return None


def ask(question: str, history: list[dict] | None = None, delay: float = 0.05) -> str:
    """
    Mock LLM call. `history` là list {role, content} của các lượt trước.
    """
    time.sleep(delay + random.uniform(0, 0.03))  # mô phỏng latency
    q = question.lower()

    # 1) Câu hỏi tham chiếu ngữ cảnh: tên người dùng.
    if _NAME_ASK.search(question):
        name = _scan_name(history, question)
        if name:
            return f"Tên của bạn là {name} (lấy từ lịch sử hội thoại)."
        return "Tôi chưa biết tên bạn. Bạn có thể nói 'My name is ...' để tôi nhớ."

    # 2) Câu hỏi 'tôi vừa nói gì' — lặp lại lượt user gần nhất.
    if _RECALL_ASK.search(question) and history:
        last_user = next(
            (t.get("content") for t in reversed(history) if t.get("role") == "user"),
            None,
        )
        if last_user:
            return f"Bạn vừa nói: \"{last_user}\"."

    # 3) Khớp keyword chủ đề.
    for keyword, responses in MOCK_RESPONSES.items():
        if keyword in q:
            return random.choice(responses)

    # 4) Mặc định — có nhắc số lượt context nếu có history.
    base = random.choice(MOCK_RESPONSES["default"])
    if history:
        base += f" (đang giữ {len(history)} lượt context)"
    return base


def ask_stream(question: str, history: list[dict] | None = None):
    """Mock streaming — yield từng từ."""
    for word in ask(question, history).split():
        time.sleep(0.03)
        yield word + " "
