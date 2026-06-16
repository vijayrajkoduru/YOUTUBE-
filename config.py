"""Central configuration. Loads .env and exposes typed constants.

Secrets are NEVER hardcoded. Everything comes from the environment / .env file.
DRY_RUN defaults to TRUE so the app is fully runnable with zero paid keys.
"""
import os

from dotenv import load_dotenv

# Load .env from the project root (no-op if the file is absent).
load_dotenv()


def _as_bool(value, default=True):
    if value is None:
        return default
    return str(value).strip().lower() in ("1", "true", "yes", "on")


def _as_float(value, default):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _as_int(value, default):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


# --- Core mode -------------------------------------------------------------
# When DRY_RUN is True, NOTHING posts and NOTHING spends. Providers return
# mock/placeholder data and publishers only log what they WOULD send.
DRY_RUN = _as_bool(os.getenv("DRY_RUN"), default=True)

# --- Generation (Gemini / Veo) --------------------------------------------
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "").strip()
VEO_MODEL = os.getenv("VEO_MODEL", "veo-3.1-fast-generate-preview").strip()
VEO_MONTHLY_USD_CAP = _as_float(os.getenv("VEO_MONTHLY_USD_CAP"), 20.0)
VEO_DAILY_CLIP_CAP = _as_int(os.getenv("VEO_DAILY_CLIP_CAP"), 10)
# Approximate Veo cost per second of generated video (USD). Used by the
# cost guard and accounting. Adjust to match Google's current pricing.
VEO_USD_PER_SECOND = _as_float(os.getenv("VEO_USD_PER_SECOND"), 0.40)

# Text models (free tier when GOOGLE_API_KEY is present).
GEMINI_TEXT_MODEL = os.getenv("GEMINI_TEXT_MODEL", "gemini-2.5-flash").strip()

# --- Social aggregator (Upload-Post) --------------------------------------
UPLOAD_POST_API_KEY = os.getenv("UPLOAD_POST_API_KEY", "").strip()

# --- Blog publishing creds -------------------------------------------------
WORDPRESS_URL = os.getenv("WORDPRESS_URL", "").strip().rstrip("/")
WORDPRESS_USER = os.getenv("WORDPRESS_USER", "").strip()
WORDPRESS_APP_PASSWORD = os.getenv("WORDPRESS_APP_PASSWORD", "").strip()
DEVTO_API_KEY = os.getenv("DEVTO_API_KEY", "").strip()
HASHNODE_TOKEN = os.getenv("HASHNODE_TOKEN", "").strip()
HASHNODE_PUBLICATION_ID = os.getenv("HASHNODE_PUBLICATION_ID", "").strip()


def keys_status():
    """Return a dict describing which keys/creds are configured.

    Used by the dashboard and settings page. Values are booleans only;
    the actual secret values are never exposed.
    """
    return {
        "GOOGLE_API_KEY": bool(GOOGLE_API_KEY),
        "UPLOAD_POST_API_KEY": bool(UPLOAD_POST_API_KEY),
        "WORDPRESS": bool(WORDPRESS_URL and WORDPRESS_USER and WORDPRESS_APP_PASSWORD),
        "DEVTO_API_KEY": bool(DEVTO_API_KEY),
        "HASHNODE": bool(HASHNODE_TOKEN and HASHNODE_PUBLICATION_ID),
    }
