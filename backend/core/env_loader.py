"""Load Steelera environment variables from .env files."""

from pathlib import Path

from dotenv import load_dotenv

_BACKEND_DIR = Path(__file__).resolve().parent.parent


def load_env() -> None:
    """Load root .env then backend/.env (backend wins)."""
    load_dotenv(_BACKEND_DIR.parent / ".env")
    load_dotenv(_BACKEND_DIR / ".env", override=True)
