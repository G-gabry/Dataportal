"""
utils/progress.py — SQLite-backed progress tracker.

Uses SQLite instead of JSON to avoid:
  - Race conditions from concurrent Crawl4AI workers
  - Size explosion (100MB+ JSON for 10k URLs)
  - File corruption from partial writes

All writes are atomic via SQLite transactions.
"""

import sqlite3
import json
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from config import PROGRESS_DB_PATH, CRAWL_CACHE_DIR

# Thread-local connections (one per thread, safe for concurrent use)
_local = threading.local()


def _get_conn() -> sqlite3.Connection:
    if not hasattr(_local, "conn") or _local.conn is None:
        _local.conn = sqlite3.connect(str(PROGRESS_DB_PATH), check_same_thread=False)
        _local.conn.execute("PRAGMA journal_mode=WAL")   # allow concurrent readers
        _local.conn.execute("PRAGMA synchronous=NORMAL")
    return _local.conn


def init_db(run_id: str) -> None:
    """Create all tables and record the run start."""
    CRAWL_CACHE_DIR.mkdir(exist_ok=True)
    conn = _get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS runs (
            run_id      TEXT PRIMARY KEY,
            started_at  TEXT NOT NULL,
            finished_at TEXT
        );

        CREATE TABLE IF NOT EXISTS sources (
            source_id   TEXT NOT NULL,
            run_id      TEXT NOT NULL,
            name        TEXT,
            base_url    TEXT,
            status      TEXT DEFAULT 'pending',
            PRIMARY KEY (source_id, run_id)
        );

        CREATE TABLE IF NOT EXISTS urls (
            url             TEXT NOT NULL,
            source_id       TEXT NOT NULL,
            run_id          TEXT NOT NULL,
            detected_type   TEXT,           -- SCHOLARSHIP/PROGRAM/CONFERENCE/EXCHANGE/AMBIGUOUS
            classify_method TEXT,           -- heuristic / content_peek / ai_extraction
            confidence      REAL,
            crawl_status    TEXT DEFAULT 'pending',  -- pending/done/failed/skipped
            cache_file      TEXT,           -- relative path inside crawl_cache/
            depth           INTEGER DEFAULT 0,
            root_url        TEXT,
            error_msg       TEXT,
            crawled_at      TEXT,
            PRIMARY KEY (url, run_id)
        );

        CREATE TABLE IF NOT EXISTS extractions (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id          TEXT NOT NULL,
            source_id       TEXT NOT NULL,
            item_type       TEXT NOT NULL,
            status          TEXT DEFAULT 'pending',
            batch_index     INTEGER,
            items_json      TEXT,           -- JSON array of extracted items
            extracted_at    TEXT
        );

        CREATE TABLE IF NOT EXISTS run_meta (
            run_id          TEXT PRIMARY KEY,
            total_discovered INTEGER DEFAULT 0,
            total_filtered  INTEGER DEFAULT 0,
            total_crawled   INTEGER DEFAULT 0,
            total_extracted INTEGER DEFAULT 0,
            total_dupes     INTEGER DEFAULT 0,
            total_final     INTEGER DEFAULT 0
        );
    """)
    conn.execute(
        "INSERT OR IGNORE INTO runs (run_id, started_at) VALUES (?, ?)",
        (run_id, datetime.now(timezone.utc).isoformat()),
    )
    conn.execute(
        "INSERT OR IGNORE INTO run_meta (run_id) VALUES (?)", (run_id,)
    )
    conn.commit()


@contextmanager
def transaction():
    conn = _get_conn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise


# ── URL tracking ──────────────────────────────────────────────────────────────

def upsert_url(
    run_id: str,
    source_id: str,
    url: str,
    detected_type: Optional[str] = None,
    classify_method: Optional[str] = None,
    confidence: Optional[float] = None,
    crawl_status: Optional[str] = None,
    cache_file: Optional[str] = None,
    depth: int = 0,
    root_url: Optional[str] = None,
    error_msg: Optional[str] = None,
) -> None:
    conn = _get_conn()
    conn.execute("""
        INSERT INTO urls
            (url, source_id, run_id, detected_type, classify_method,
             confidence, crawl_status, cache_file, depth, root_url, error_msg, crawled_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?, CURRENT_TIMESTAMP)
        ON CONFLICT(url, run_id) DO UPDATE SET
            detected_type   = COALESCE(excluded.detected_type, detected_type),
            classify_method = COALESCE(excluded.classify_method, classify_method),
            confidence      = COALESCE(excluded.confidence, confidence),
            crawl_status    = COALESCE(excluded.crawl_status, crawl_status),
            cache_file      = COALESCE(excluded.cache_file, cache_file),
            error_msg       = COALESCE(excluded.error_msg, error_msg),
            crawled_at      = CURRENT_TIMESTAMP
    """, (url, source_id, run_id, detected_type, classify_method,
          confidence, crawl_status, cache_file, depth, root_url, error_msg))
    conn.commit()


def get_crawled_urls(run_id: str) -> set:
    """Return set of URLs already crawled (for resume support)."""
    conn = _get_conn()
    rows = conn.execute(
        "SELECT url FROM urls WHERE run_id=? AND crawl_status='done'", (run_id,)
    ).fetchall()
    return {r[0] for r in rows}


def get_pending_urls(run_id: str, source_id: str) -> list:
    """Return URLs for a source not yet crawled."""
    conn = _get_conn()
    rows = conn.execute(
        """SELECT url, detected_type, depth, root_url
           FROM urls WHERE run_id=? AND source_id=? AND crawl_status='pending'""",
        (run_id, source_id),
    ).fetchall()
    return [{"url": r[0], "detected_type": r[1], "depth": r[2], "root_url": r[3]}
            for r in rows]


def mark_source_done(run_id: str, source_id: str, step: str) -> None:
    conn = _get_conn()
    conn.execute(
        "UPDATE sources SET status=? WHERE run_id=? AND source_id=?",
        (step, run_id, source_id),
    )
    conn.commit()


# ── Extraction tracking ───────────────────────────────────────────────────────

def save_extraction_batch(
    run_id: str, source_id: str, item_type: str, batch_index: int, items: list
) -> None:
    conn = _get_conn()
    conn.execute("""
        INSERT INTO extractions (run_id, source_id, item_type, status, batch_index, items_json, extracted_at)
        VALUES (?,?,?,'done',?,?,CURRENT_TIMESTAMP)
    """, (run_id, source_id, item_type, batch_index, json.dumps(items, ensure_ascii=False)))
    conn.commit()


def get_all_extracted_items(run_id: str) -> list:
    conn = _get_conn()
    rows = conn.execute(
        "SELECT items_json FROM extractions WHERE run_id=? AND status='done'", (run_id,)
    ).fetchall()
    items = []
    for (j,) in rows:
        try:
            items.extend(json.loads(j))
        except Exception:
            pass
    return items


# ── Meta / summary ────────────────────────────────────────────────────────────

def update_meta(run_id: str, **kwargs) -> None:
    if not kwargs:
        return
    sets = ", ".join(f"{k}=?" for k in kwargs)
    conn = _get_conn()
    conn.execute(f"UPDATE run_meta SET {sets} WHERE run_id=?",
                 (*kwargs.values(), run_id))
    conn.commit()


def get_meta(run_id: str) -> dict:
    conn = _get_conn()
    row = conn.execute("SELECT * FROM run_meta WHERE run_id=?", (run_id,)).fetchone()
    if not row:
        return {}
    cols = [d[0] for d in conn.execute("SELECT * FROM run_meta LIMIT 0").description]
    return dict(zip(cols, row))


def finish_run(run_id: str) -> None:
    conn = _get_conn()
    conn.execute(
        "UPDATE runs SET finished_at=? WHERE run_id=?",
        (datetime.now(timezone.utc).isoformat(), run_id),
    )
    conn.commit()


# ── Resume: load classified URLs from DB after --skip-discover ────────────────

def get_type_maps_from_db(run_id: str, sources) -> dict:
    """
    Reconstruct {source_id → {url → detected_type}} from the DB.
    Called when --skip-discover is used (URLs were saved from a previous run).
    """
    conn = _get_conn()
    rows = conn.execute(
        """SELECT url, source_id, detected_type FROM urls
           WHERE run_id=? AND crawl_status='pending' AND detected_type IS NOT NULL
           AND detected_type != 'NOT_RELEVANT'""",
        (run_id,)
    ).fetchall()

    type_maps: dict = {}
    for url, source_id, detected_type in rows:
        type_maps.setdefault(source_id, {})
        type_maps[source_id][url] = detected_type

    total = sum(len(v) for v in type_maps.values())
    import logging
    logging.getLogger("progress").info(
        f"Loaded {total} classified URLs from DB for {len(type_maps)} sources"
    )
    return type_maps


# ── Resume: load crawl markdown from cache after --skip-crawl ─────────────────

def get_crawl_results_from_cache(run_id: str) -> dict:
    """
    Reconstruct {source_id → [{url, markdown, task, cache_file}]} from cached files.
    Called when --skip-crawl is used.
    """
    from pathlib import Path
    from config import CRAWL_CACHE_DIR

    conn = _get_conn()
    rows = conn.execute(
        """SELECT url, source_id, detected_type, depth, root_url, cache_file
           FROM urls WHERE run_id=? AND crawl_status='done' AND cache_file IS NOT NULL""",
        (run_id,)
    ).fetchall()

    crawl_results: dict = {}

    for url, source_id, detected_type, depth, root_url, cache_file in rows:
        cache_path = CRAWL_CACHE_DIR.parent / cache_file if cache_file else None
        if not cache_path or not cache_path.exists():
            continue

        markdown = cache_path.read_text(encoding="utf-8", errors="ignore")

        # Reconstruct a minimal task-like object as a plain dict
        task_stub = type("CrawlTask", (), {
            "url": url, "source_id": source_id, "depth": depth or 0,
            "root_url": root_url or url, "root_type": detected_type or "AMBIGUOUS",
            "root_domain": "", "external_domains_seen": set(),
        })()

        crawl_results.setdefault(source_id, []).append({
            "url": url,
            "markdown": markdown,
            "task": task_stub,
            "cache_file": cache_file,
        })

    total = sum(len(v) for v in crawl_results.values())
    import logging
    logging.getLogger("progress").info(
        f"Loaded {total} cached pages from disk for {len(crawl_results)} sources"
    )
    return crawl_results
