"""
pipeline/step2_classify.py — 3-tier URL classification.

Tier 1: URL heuristic (zero AI cost) — classifies ~93% of URLs instantly
Tier 2: Content-peek (post-crawl, 1500 chars + Gemini) — handles ~6%
Tier 3: Universal extraction (Step 5 fallback) — handles remaining <1%
"""

import re
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse

from config import TYPE_URL_SIGNALS, URL_EXCLUDE_PATTERNS, PAGINATION_PATTERNS
from pipeline.step0_sources import SourceConfig
from utils.logger import get_logger
from utils.progress import upsert_url

log = get_logger("step2_classify")

_PAGINATION_RE = [re.compile(p) for p in PAGINATION_PATTERNS]


# ── Tier 1: URL Heuristic ─────────────────────────────────────────────────────

def _classify_url_heuristic(url: str) -> Optional[str]:
    """
    Classify a URL based on keyword signals in its path/slug.
    Returns item_type string or None (AMBIGUOUS).

    Priority order matches the classification prompt rules:
    CONFERENCE > EXCHANGE > PROGRAM > SCHOLARSHIP
    """
    slug = url.lower()

    # Exclusion check first
    if any(ex in slug for ex in URL_EXCLUDE_PATTERNS):
        return "EXCLUDE"
    if any(p.search(slug) for p in _PAGINATION_RE):
        return "EXCLUDE"

    # Skip media/static files
    path = urlparse(url).path.lower()
    if any(path.endswith(e) for e in (".pdf", ".jpg", ".png", ".zip", ".doc", ".docx")):
        return "EXCLUDE"

    # Classification — in priority order
    for item_type in ("CONFERENCE", "EXCHANGE", "PROGRAM", "SCHOLARSHIP"):
        if any(signal in slug for signal in TYPE_URL_SIGNALS[item_type]):
            return item_type

    return None  # AMBIGUOUS


def classify_urls(
    urls: List[str],
    source: SourceConfig,
    run_id: str,
) -> Tuple[Dict[str, str], List[str]]:
    """
    Tier 1 classification for a list of discovered URLs.

    Returns:
        type_map: {url → detected_type}
        ambiguous: list of URLs that need Tier 2 (content-peek)
    """
    # Also override with source's target_item_types filter
    # (if source targets only SCHOLARSHIP, AMBIGUOUS can still become any type)
    include_kw = [k.lower() for k in source.include_patterns]
    exclude_kw = [k.lower() for k in source.exclude_patterns]

    type_map: Dict[str, str] = {}
    ambiguous: List[str] = []

    for url in urls:
        slug = url.lower()

        # Source-level exclude patterns override
        if any(ex in slug for ex in exclude_kw):
            continue  # drop entirely

        result = _classify_url_heuristic(url)

        if result == "EXCLUDE":
            continue  # drop

        if result is None:
            # Check source-level include patterns before marking AMBIGUOUS
            if include_kw and any(kw in slug for kw in include_kw):
                # Source says this looks relevant but we don't know type
                type_map[url] = "AMBIGUOUS"
                ambiguous.append(url)
            elif not include_kw:
                # No source filter — it's genuinely ambiguous
                type_map[url] = "AMBIGUOUS"
                ambiguous.append(url)
            # else: source has include patterns and this URL doesn't match → skip
        else:
            type_map[url] = result

    # Persist to DB
    for url, detected_type in type_map.items():
        upsert_url(
            run_id=run_id,
            source_id=source.id,
            url=url,
            detected_type=detected_type,
            classify_method="heuristic",
            confidence=1.0 if detected_type != "AMBIGUOUS" else None,
            crawl_status="pending",
            depth=0,
            root_url=url,
        )

    typed_count = sum(1 for t in type_map.values() if t != "AMBIGUOUS")
    log.info(
        f"[{source.name}] Classified {len(type_map)} URLs: "
        f"{typed_count} typed, {len(ambiguous)} AMBIGUOUS"
    )
    return type_map, ambiguous


def run(
    discovered: Dict[str, List[str]],
    sources: List[SourceConfig],
    run_id: str,
    skip: bool = False,
) -> Dict[str, Dict[str, str]]:
    """
    Step 2: Classify all discovered URLs (Tier 1 heuristic).

    Returns:
        {source_id → {url → detected_type}}
    """
    if skip:
        log.info("Step 2 skipped — loading from progress DB")
        return {}

    log.info(f"=== STEP 2: URL CLASSIFICATION ===")
    source_map = {s.id: s for s in sources}
    all_type_maps: Dict[str, Dict[str, str]] = {}

    for source_id, urls in discovered.items():
        source = source_map.get(source_id)
        if not source:
            continue
        try:
            type_map, _ = classify_urls(urls, source, run_id)
            all_type_maps[source_id] = type_map
        except Exception as e:
            log.error(f"[{source_id}] Classification failed: {e}")
            all_type_maps[source_id] = {}

    total_typed = sum(
        sum(1 for t in tm.values() if t != "AMBIGUOUS")
        for tm in all_type_maps.values()
    )
    total_ambig = sum(
        sum(1 for t in tm.values() if t == "AMBIGUOUS")
        for tm in all_type_maps.values()
    )
    log.info(f"Step 2 complete: {total_typed} typed, {total_ambig} AMBIGUOUS")
    return all_type_maps
