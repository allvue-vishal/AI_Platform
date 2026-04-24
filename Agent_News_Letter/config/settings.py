import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# ── LLM (via LiteLLM proxy) ──────────────────────────────
LITELLM_API_KEY: str = os.getenv("LITELLM_API_KEY", "")
LITELLM_API_BASE: str = os.getenv("LITELLM_API_BASE", "")
LITELLM_MODEL: str = os.getenv("LITELLM_MODEL", "openai/claude-sonnet-4")

# ── Email ─────────────────────────────────────────────────
RECIPIENT_EMAIL: str = os.getenv("RECIPIENT_EMAIL", "")

# ── ArXiv ─────────────────────────────────────────────────
ARXIV_CATEGORIES: list[str] = ["cs.AI", "cs.LG", "cs.CL", "cs.CV"]
ARXIV_MAX_RESULTS: int = 30

# ── Google News search queries ───────────────────────────
GOOGLE_NEWS_QUERIES: list[str] = [
    "artificial intelligence breakthrough",
    "large language model new research",
    "AI advancement 2026",
]

# ── Logging ──────────────────────────────────────────────
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "ai_atlas.log"

# ── Templates ────────────────────────────────────────────
TEMPLATE_DIR = BASE_DIR / "templates"
