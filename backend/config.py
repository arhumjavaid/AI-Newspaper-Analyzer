"""Central configuration loaded from environment / .env.

All tunables (API key, model, client context, AVE multipliers) live here so the
rest of the codebase never reads os.environ directly.
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env from the project root (one level above backend/).
BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
load_dotenv(PROJECT_ROOT / ".env")

# --- Gemini via Vertex AI -----------------------------------------------------
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
# Model name used in the Vertex AI publisher path (no "google/" prefix needed).
MODEL: str = os.getenv("MODEL", "gemini-3.5-flash-lite")
# Backup model used automatically when the primary returns a transient 5xx/429
# (e.g. 503 "model overloaded"), so a demand spike can't break analysis.
FALLBACK_MODEL: str = os.getenv("FALLBACK_MODEL", "gemini-3.5-flash")

APP_TITLE: str = os.getenv("APP_TITLE", "AI Newspaper Analyzer")
APP_URL: str = os.getenv("APP_URL", "http://localhost:5173")

# --- Client being monitored ---------------------------------------------------
CLIENT_NAME: str = os.getenv("CLIENT_NAME", "K-Electric (KE)")
CLIENT_ALIASES: list[str] = [
    a.strip()
    for a in os.getenv("CLIENT_ALIASES", "KE,K-Electric,K Electric,KESC").split(",")
    if a.strip()
]
CLIENT_DESCRIPTION: str = os.getenv(
    "CLIENT_DESCRIPTION",
    "K-Electric (KE) is the sole vertically-integrated power utility supplying "
    "electricity to Karachi and surrounding areas in Pakistan. It frequently "
    "appears in the press around load-shedding, tariffs/NEPRA, billing, outages, "
    "safety incidents and infrastructure investment.",
)

# --- Storage ------------------------------------------------------------------
DATA_DIR = BASE_DIR / "data"
UPLOADS_DIR = DATA_DIR / "uploads"
INDEX_FILE = DATA_DIR / "index.json"

# --- Extraction tuning --------------------------------------------------------
# A page with fewer than this many characters of selectable text is treated as a
# scan and rendered to an image instead.
MIN_TEXT_CHARS_PER_PAGE: int = int(os.getenv("MIN_TEXT_CHARS_PER_PAGE", "120"))
# DPI used when rasterising scanned pages for the vision model.
RENDER_DPI: int = int(os.getenv("RENDER_DPI", "150"))
# Cap the longest side (px) and JPEG quality so a high-res scan doesn't produce a
# multi-MB image that breaks the API request. ~2200px keeps newspaper text legible.
MAX_IMAGE_PX: int = int(os.getenv("MAX_IMAGE_PX", "3000"))
IMAGE_QUALITY: int = int(os.getenv("IMAGE_QUALITY", "80"))
# Safety cap so a huge PDF can't explode cost/latency in the demo.
MAX_PAGES: int = int(os.getenv("MAX_PAGES", "30"))

# --- AVE (Advertising Value Equivalent) rough multipliers ($) -----------------
# Front-page coverage is worth far more than a buried inner-page mention.
AVE_BASE_USD: float = float(os.getenv("AVE_BASE_USD", "500"))
AVE_PROMINENCE_MULTIPLIER = {
    "front_page": 6.0,
    "prominent": 3.0,
    "standard": 1.5,
    "minor": 0.5,
}


def is_configured() -> bool:
    """True when a Gemini API key is present."""
    return bool(GEMINI_API_KEY)
