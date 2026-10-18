"""Central configuration loaded from environment variables (.env)."""
import os

from dotenv import load_dotenv

load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
LLM_MAX_RETRIES = int(os.getenv("LLM_MAX_RETRIES", "2"))


def require_api_key() -> str:
    if not GOOGLE_API_KEY or GOOGLE_API_KEY.startswith("your-"):
        raise RuntimeError(
            "GOOGLE_API_KEY is not set. Copy .env.example to .env and add your Gemini key."
        )
    return GOOGLE_API_KEY
