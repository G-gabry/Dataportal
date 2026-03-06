"""
config.py — Single source of truth for all pipeline constants.
All configurable values live here. No hardcoded sites or prompts.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# ── Load from .env ────────────────────────────────────────────────────────────
_ENV_PATH = Path(__file__).parent.parent / ".env"
if _ENV_PATH.exists():
    load_dotenv(_ENV_PATH)

# ── Infrastructure ────────────────────────────────────────────────────────────
FIRECRAWL_BASE_URL: str  = os.getenv("FIRECRAWL_BASE_URL", "http://localhost:3002")
# Crawl4AI server on same VM as Firecrawl (default port 11235)
CRAWL4AI_BASE_URL: str   = os.getenv("CRAWL4AI_BASE_URL", "http://localhost:11235")
GEMINI_API_KEY: str      = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL: str       = "gemini-2.0-flash"

# ── Data Portal API (sources loaded from here, NOT hardcoded) ─────────────────
# PORTAL_API_BASE: backend URL the pipeline calls to get sources.
# - Outside Docker (local dev): http://localhost:8001  (backend container port)
# - Inside Docker:              http://backend:8000    (set via docker-compose env)
PORTAL_API_BASE: str  = os.getenv("PORTAL_API_BASE",
                                   os.getenv("NEXT_PUBLIC_API_URL", "http://localhost:8001"))
PORTAL_API_TOKEN: str = os.getenv("PORTAL_API_TOKEN", "")
SOURCES_CACHE_FILE    = Path(__file__).parent / "sources_cache.json"

# ── Sitemap / Discovery ───────────────────────────────────────────────────────
SITEMAP_MAX_AGE_DAYS: int  = 540    # skip posts older than 18 months
FIRECRAWL_MAP_LIMIT: int   = 5000   # max URLs per /v1/map call

# ── URL Classification — Tier 1 Heuristics ───────────────────────────────────
TYPE_URL_SIGNALS: dict = {
    "SCHOLARSHIP": [
        "scholarship", "fellowship", "grant", "bursary", "award",
        "funded", "funding", "stipend", "bourse",
    ],
    "PROGRAM": [
        "program", "programme", "degree", "master", "phd", "msc",
        "mba", "bachelor", "course", "curriculum", "study",
    ],
    "CONFERENCE": [
        "conference", "symposium", "workshop", "congress",
        "seminar", "summit", "event", "call-for-papers",
    ],
    "EXCHANGE": [
        "exchange", "mobility", "erasmus", "study-abroad",
        "internship", "rotation", "visiting", "abroad",
    ],
}

URL_EXCLUDE_PATTERNS: list = [
    "/login", "/register", "/privacy", "/terms", "/contact",
    "/about", "/sitemap", "/tag/", "/author/", "/wp-admin",
    "/wp-content", "/feed", "/comment", "?p=",
]

PAGINATION_PATTERNS: list = [
    r"/page/\d+",
    r"[?&]paged?=\d+",
    r"[?&]p=\d+",
]

# ── DFS Configuration ─────────────────────────────────────────────────────────
DFS_DEFAULT_DEPTH: int               = 3
DFS_DEPTH_SAME_DOMAIN: int           = 3
DFS_DEPTH_EXTERNAL_DOMAIN: int       = 2
MAX_EXTERNAL_DOMAINS_PER_ROOT: int   = 2
MAX_PAGES_PER_EXTERNAL_DOMAIN: int   = 2

# Only follow external links containing these keywords
EXTERNAL_LINK_ACCEPT_KEYWORDS: list = [
    "apply", "application", "portal", "admission",
    "register", "scholarship", "fellowship", "grant",
]

# Never follow these external domains
ALWAYS_SKIP_DOMAINS: set = {
    "twitter.com", "x.com", "facebook.com", "instagram.com",
    "linkedin.com", "youtube.com", "tiktok.com", "reddit.com",
    "whatsapp.com", "telegram.org", "pinterest.com",
    "google.com", "google.co", "medium.com", "substack.com",
}

# ── Crawl4AI Settings ─────────────────────────────────────────────────────────
CRAWL_MAX_CONCURRENT: int    = 1      # MemoryAdaptiveDispatcher max sessions
CRAWL_MEMORY_THRESHOLD: float = 85.0  # throttle when RAM > 85%
CRAWL_PAGE_TIMEOUT_MS: int   = 30_000 # 30s per page
CRAWL_MEAN_DELAY: float      = 0.7    # politeness delay between requests
CRAWL_MAX_RETRIES: int       = 3
CRAWL_WORD_MIN: int          = 50     # skip near-empty pages

# ── Content-Peek Classification (Tier 2) ─────────────────────────────────────
PEEK_CHARS: int             = 1500    # chars used for content-peek
PEEK_CONFIDENCE_THRESHOLD   = 0.80   # below this → stays AMBIGUOUS
PEEK_CONCURRENCY: int       = 8      # parallel Gemini classification calls

# ── Extraction (Gemini Batching) ─────────────────────────────────────────────
EXTRACTION_MAX_TOKENS_PER_BATCH: int = 80_000  # safe ceiling for Flash
EXTRACTION_PARALLEL: int             = 4       # concurrent Gemini extract calls
EXTRACTION_RETRY_ATTEMPTS: int       = 3

# ── Deduplication ─────────────────────────────────────────────────────────────
FUZZY_TITLE_THRESHOLD: int  = 90     # % title similarity to flag as duplicate
YEAR_CHECK_ENABLED: bool    = True   # require same year before fuzzy-dedup

# ── Progress DB (SQLite — concurrent-safe, no JSON race conditions) ───────────
PROGRESS_DB_PATH            = Path(__file__).parent / "progress.db"
CRAWL_CACHE_DIR             = Path(__file__).parent / "crawl_cache"

# ── Output ────────────────────────────────────────────────────────────────────
OUTPUT_DIR                  = Path(__file__).parent / "output" / "final"
