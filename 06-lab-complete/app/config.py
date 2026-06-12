"""
Cấu hình ứng dụng — tuân thủ 12-Factor App.

12-Factor (https://12factor.net) — nguyên tắc III "Config":
  Mọi cấu hình (config) phải nằm trong BIẾN MÔI TRƯỜNG (environment variables),
  KHÔNG hardcode trong code. Nhờ vậy cùng 1 image chạy được ở dev/staging/prod
  chỉ bằng cách đổi env, và secret (khóa bí mật) không bao giờ bị commit lên Git.
"""
import os
import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class Settings:
    # ── Server ──────────────────────────────────────────────
    # host=0.0.0.0 để container nhận traffic từ bên ngoài (không phải localhost).
    host: str = field(default_factory=lambda: os.getenv("HOST", "0.0.0.0"))
    # PORT đọc từ env vì Railway/Render TỰ inject PORT — không được hardcode.
    port: int = field(default_factory=lambda: int(os.getenv("PORT", "8000")))
    environment: str = field(default_factory=lambda: os.getenv("ENVIRONMENT", "development"))
    debug: bool = field(default_factory=lambda: os.getenv("DEBUG", "false").lower() == "true")

    # ── App metadata ────────────────────────────────────────
    app_name: str = field(default_factory=lambda: os.getenv("APP_NAME", "Production AI Agent"))
    app_version: str = field(default_factory=lambda: os.getenv("APP_VERSION", "1.0.0"))

    # ── LLM ─────────────────────────────────────────────────
    openai_api_key: str = field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    llm_model: str = field(default_factory=lambda: os.getenv("LLM_MODEL", "gpt-4o-mini"))

    # ── Security ────────────────────────────────────────────
    # agent_api_key: khóa để xác thực (authentication). Bắt buộc đổi ở production.
    agent_api_key: str = field(default_factory=lambda: os.getenv("AGENT_API_KEY", "dev-key-change-me"))
    jwt_secret: str = field(default_factory=lambda: os.getenv("JWT_SECRET", "dev-jwt-secret"))
    allowed_origins: list = field(
        default_factory=lambda: os.getenv("ALLOWED_ORIGINS", "*").split(",")
    )

    # ── Rate limiting (giới hạn tần suất) ───────────────────
    # 10 req/phút/user theo yêu cầu Final Project.
    rate_limit_per_minute: int = field(
        default_factory=lambda: int(os.getenv("RATE_LIMIT_PER_MINUTE", "10"))
    )

    # ── Cost guard (bảo vệ ngân sách) ───────────────────────
    # Ngân sách tháng / user = $10 theo yêu cầu Final Project.
    monthly_budget_usd: float = field(
        default_factory=lambda: float(os.getenv("MONTHLY_BUDGET_USD", "10.0"))
    )

    # ── Conversation history (lịch sử hội thoại) ────────────
    # Số lượt hội thoại tối đa lưu lại mỗi user (để giữ context mà không phình bộ nhớ).
    max_history_turns: int = field(
        default_factory=lambda: int(os.getenv("MAX_HISTORY_TURNS", "20"))
    )
    # TTL (time-to-live) cho lịch sử, giây. Mặc định 24h.
    history_ttl_seconds: int = field(
        default_factory=lambda: int(os.getenv("HISTORY_TTL_SECONDS", str(24 * 3600)))
    )

    # ── Storage ─────────────────────────────────────────────
    # REDIS_URL rỗng => app tự fallback sang in-memory (vẫn chạy được khi deploy
    # nơi chưa gắn Redis). Có REDIS_URL => stateless, scale nhiều instance được.
    redis_url: str = field(default_factory=lambda: os.getenv("REDIS_URL", ""))

    def validate(self) -> "Settings":
        """Kiểm tra cấu hình; chặn deploy production với secret mặc định."""
        if self.environment == "production":
            if self.agent_api_key == "dev-key-change-me":
                raise ValueError("AGENT_API_KEY phải được set ở production!")
            if self.jwt_secret == "dev-jwt-secret":
                raise ValueError("JWT_SECRET phải được set ở production!")
        if not self.openai_api_key:
            logger.warning("OPENAI_API_KEY chưa set — dùng mock LLM (offline).")
        return self


settings = Settings().validate()
