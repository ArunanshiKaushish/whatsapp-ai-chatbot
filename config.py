"""Application configuration loaded from environment variables."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"
PROMPTS_DIR = BASE_DIR / "prompts"

DATA_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)
PROMPTS_DIR.mkdir(exist_ok=True)

SYSTEM_PROMPT_FILE = PROMPTS_DIR / "system_prompt.txt"

DEFAULT_SYSTEM_PROMPT = (
    "You are a helpful, friendly, conversational WhatsApp AI assistant with "
    "persistent memory. You remember important facts users share and can continue "
    "conversations naturally over long periods."
)


def get_system_prompt() -> str:
    """Load system prompt from file or return default."""
    if SYSTEM_PROMPT_FILE.exists():
        return SYSTEM_PROMPT_FILE.read_text(encoding="utf-8").strip()
    SYSTEM_PROMPT_FILE.write_text(DEFAULT_SYSTEM_PROMPT, encoding="utf-8")
    return DEFAULT_SYSTEM_PROMPT


def _env(name: str, default: str = "") -> str:
    """Read env var and strip invisible whitespace (common Railway paste issue)."""
    return os.getenv(name, default).strip().strip('"').strip("'")


class Config:
    """Central configuration object."""

    # LLM provider: "gemini" (free, no card) or "anthropic"
    LLM_PROVIDER: str = _env("LLM_PROVIDER", "anthropic").lower()

    ANTHROPIC_API_KEY: str = _env("ANTHROPIC_API_KEY")
    GEMINI_API_KEY: str = _env("GEMINI_API_KEY")
    TWILIO_ACCOUNT_SID: str = _env("TWILIO_ACCOUNT_SID")
    TWILIO_AUTH_TOKEN: str = _env("TWILIO_AUTH_TOKEN")
    TWILIO_WHATSAPP_NUMBER: str = _env("TWILIO_WHATSAPP_NUMBER")
    CLAUDE_MODEL: str = _env("CLAUDE_MODEL", "claude-sonnet-4-6")
    GEMINI_MODEL: str = _env("GEMINI_MODEL", "gemini-2.0-flash")
    FLASK_ENV: str = os.getenv("FLASK_ENV", "production")
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", f"sqlite:///{DATA_DIR / 'chatbot.db'}"
    )
    MAX_HISTORY_MESSAGES: int = int(os.getenv("MAX_HISTORY_MESSAGES", "20"))
    MAX_MEMORIES_TO_INJECT: int = int(os.getenv("MAX_MEMORIES_TO_INJECT", "10"))
    PORT: int = int(os.getenv("PORT", "5000"))

    @classmethod
    def validate(cls) -> list[str]:
        """Return list of missing required configuration keys."""
        missing = []
        if cls.LLM_PROVIDER == "gemini":
            if not cls.GEMINI_API_KEY:
                missing.append("GEMINI_API_KEY")
        elif cls.LLM_PROVIDER == "anthropic":
            if not cls.ANTHROPIC_API_KEY:
                missing.append("ANTHROPIC_API_KEY")
        else:
            missing.append("LLM_PROVIDER (must be 'gemini' or 'anthropic')")
        if not cls.TWILIO_ACCOUNT_SID:
            missing.append("TWILIO_ACCOUNT_SID")
        if not cls.TWILIO_AUTH_TOKEN:
            missing.append("TWILIO_AUTH_TOKEN")
        if not cls.TWILIO_WHATSAPP_NUMBER:
            missing.append("TWILIO_WHATSAPP_NUMBER")
        return missing
