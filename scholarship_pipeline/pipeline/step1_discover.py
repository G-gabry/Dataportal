"""
pipeline/step1_discover.py — URL collection per source.

Strategy: sitemap-first → Firecrawl /v1/map fallback.
Sitemap results filtered by lastmod (SITEMAP_MAX_AGE_DAYS).
"""

import asyncio
from typing import Dict, List

from config import FIRECRAWL_BASE_URL, FIRECRAWL_MAP_LIMIT
from pipeline.step0_sources import SourceConfig
from utils.logger import get_logger
from utils.sitemap import fetch_all_urls
from utils.http import post_json, get_json
from utils.progress import upsert_url, mark_source_done

log = get_logger("step1_discover")


async def _discover_via_sitemap(source: SourceConfig) -> List[str]:
    """Fetch URLs from sitemap (with lastmod filtering)."""
    log.info(f"[{source.name}] Using sitemap: {source.sitemap_url}")
    urls = await fetch_all_urls(source.sitemap_url)
    log.info(f"[{source.name}] Sitemap returned {len(urls)} recent URLs")
    return urls


async def _discover_via_firecrawl_map(source: SourceConfig) -> List[str]:
    """Fetch URLs via Firecrawl /v1/map endpoint."""
    log.info(f"[{source.name}] Using Firecrawl map for {source.base_url}")
    endpoint = f"{FIRECRAWL_BASE_URL}/v1/map"
    payload = {
        "url": source.base_url,
        "limit": FIRECRAWL_MAP_LIMIT,
        "includeSubdomains": False,
    }
    result = await post_json(endpoint, payload, timeout=120)
    if not result:
        log.error(f"[{source.name}] Firecrawl map returned nothing")
        return []

    urls = result.get("links", result.get("urls", []))
    log.info(f"[{source.name}] Firecrawl map returned {len(urls)} URLs")
    return urls


async def discover_source(source: SourceConfig, run_id: str) -> List[str]:
    """Discover all URLs for a single source, try sitemap first."""
    urls: List[str] = []

    if source.sitemap_url:
        try:
            urls = await _discover_via_sitemap(source)
        except Exception as e:
            log.warning(f"[{source.name}] Sitemap failed: {e} — falling back to map")

    if not urls and source.base_url:
        try:
            urls = await _discover_via_firecrawl_map(source)
        except Exception as e:
            log.error(f"[{source.name}] Firecrawl map failed: {e}")

    # Deduplicate
    urls = list(dict.fromkeys(u.strip().rstrip("/") for u in urls if u.strip()))
    
    # Enforce UI-configured maximum URLs per scrape
    if source.max_urls_per_run and len(urls) > source.max_urls_per_run:
        log.warning(f"[{source.name}] Capping discovered URLs from {len(urls)} to {source.max_urls_per_run}")
        urls = urls[:source.max_urls_per_run]
        
    log.info(f"[{source.name}] Total discovered: {len(urls)} unique URLs")
    return urls


async def run(
    sources: List[SourceConfig],
    run_id: str,
    skip: bool = False,
) -> Dict[str, List[str]]:
    """
    Step 1: Discover URLs for all sources.

    Args:
        sources: List of SourceConfig objects
        run_id:  Current pipeline run ID
        skip:    If True, load from DB (resume mode)

    Returns:
        Dict mapping source_id → list of raw discovered URLs
    """
    if skip:
        log.info("Step 1 skipped — loading discovered URLs from progress DB")
        # Caller (main.py) will load from DB
        return {}

    log.info(f"=== STEP 1: URL DISCOVERY ({len(sources)} sources) ===")
    results: Dict[str, List[str]] = {}

    for source in sources:
        try:
            urls = await discover_source(source, run_id)
            results[source.id] = urls
            mark_source_done(run_id, source.id, "discovered")
        except Exception as e:
            log.error(f"[{source.name}] Discovery failed completely: {e}")
            results[source.id] = []

    total = sum(len(v) for v in results.values())
    log.info(f"Step 1 complete: {total} URLs discovered across {len(sources)} sources")
    return results
