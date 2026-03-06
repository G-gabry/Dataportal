"""
pipeline/step3_crawl.py — Native Crawl4AI DFS crawler.

Runs directly on the VM using the crawl4ai Python package.
NO HTTP API — uses AsyncWebCrawler + DFSDeepCrawlStrategy natively.

Design:
  - Uses Crawl4AI's built-in DFSDeepCrawlStrategy for root-level deep crawls
  - Falls back to arun_many() for individual pre-discovered URLs
  - Browser pool managed by Crawl4AI natively (no Docker shm issues)
  - Cache: markdown saved to crawl_cache/<url_hash>.md for resume support
"""

import asyncio
import hashlib
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set
from urllib.parse import urlparse

from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode
from crawl4ai.deep_crawling import DFSDeepCrawlStrategy

from config import (
    CRAWL_MAX_CONCURRENT, CRAWL_PAGE_TIMEOUT_MS,
    CRAWL_MAX_RETRIES, CRAWL_WORD_MIN,
    DFS_DEPTH_SAME_DOMAIN,
    CRAWL_CACHE_DIR,
)
from pipeline.step0_sources import SourceConfig
from utils.logger import get_logger
from utils.markdown_cleaner import clean
from utils.progress import upsert_url, get_crawled_urls

log = get_logger("step3_crawl")

CRAWL_CACHE_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class CrawlTask:
    url: str
    source_id: str
    depth: int = 0
    root_url: str = ""
    root_type: str = ""
    root_domain: str = ""
    max_depth: int = 1
    external_domains_seen: Set[str] = field(default_factory=set)


def _url_to_cache_path(url: str) -> Path:
    h = hashlib.sha256(url.encode()).hexdigest()[:16]
    return CRAWL_CACHE_DIR / f"{h}.md"


def _get_domain(url: str) -> str:
    try:
        host = urlparse(url).netloc.lower()
        return host[4:] if host.startswith("www.") else host
    except Exception:
        return ""


def _make_run_config(use_dfs: bool = False, max_depth: int = 1) -> CrawlerRunConfig:
    """Build a CrawlerRunConfig — with or without built-in DFS strategy."""
    kwargs = dict(
        cache_mode=CacheMode.BYPASS,
        page_timeout=CRAWL_PAGE_TIMEOUT_MS,
        delay_before_return_html=2.0,   # let JS-heavy pages settle
        word_count_threshold=CRAWL_WORD_MIN,
        excluded_tags=["nav", "footer", "header", "aside", "script", "style"],
        exclude_external_links=False,
        stream=False,
    )
    if use_dfs:
        kwargs["deep_crawl_strategy"] = DFSDeepCrawlStrategy(
            max_depth=max_depth,
            max_pages=200,           # cap per root URL
            include_external=False,
        )
    return CrawlerRunConfig(**kwargs)


async def _crawl_url(
    crawler: AsyncWebCrawler,
    url: str,
    semaphore: asyncio.Semaphore,
) -> Optional[dict]:
    """Crawl a single URL natively, with retries."""
    config = _make_run_config(use_dfs=False)

    async with semaphore:
        for attempt in range(CRAWL_MAX_RETRIES):
            try:
                result = await crawler.arun(url=url, config=config)
                if not result.success:
                    log.warning(f"Crawl4AI failed [{url}] attempt {attempt+1}: {result.error_message}")
                    await asyncio.sleep(2 ** attempt * 2)
                    continue

                markdown_raw = (
                    getattr(result.markdown, "raw_markdown", None)
                    or result.markdown
                    or result.html
                    or ""
                )
                markdown = clean(str(markdown_raw))
                if not markdown or len(markdown.split()) < CRAWL_WORD_MIN:
                    log.debug(f"Skipping near-empty page: {url}")
                    return None

                cache_path = _url_to_cache_path(url)
                cache_path.write_text(markdown, encoding="utf-8")
                rel = str(cache_path.relative_to(CRAWL_CACHE_DIR.parent))

                return {"url": url, "markdown": markdown, "cache_file": rel}

            except Exception as e:
                wait = 2 ** attempt * 2
                log.warning(f"Crawl failed [{url}] attempt {attempt+1}/{CRAWL_MAX_RETRIES}: "
                            f"{type(e).__name__}: {e!r}. Retry in {wait}s")
                await asyncio.sleep(wait)

    log.error(f"All retries exhausted for {url}")
    return None


async def _dfs_crawl_root(
    crawler: AsyncWebCrawler,
    root_url: str,
    max_depth: int,
    semaphore: asyncio.Semaphore,
) -> List[dict]:
    """Run Crawl4AI's built-in DFS from a root URL, returning all crawled pages."""
    config = _make_run_config(use_dfs=True, max_depth=max_depth)
    results_out = []

    async with semaphore:
        try:
            pages = await crawler.arun(url=root_url, config=config)
            # arun() with DFSDeepCrawlStrategy returns a list of CrawlResult
            if not isinstance(pages, list):
                pages = [pages]

            for page in pages:
                if not page.success:
                    continue
                markdown_raw = (
                    getattr(page.markdown, "raw_markdown", None)
                    or page.markdown
                    or ""
                )
                markdown = clean(str(markdown_raw))
                if not markdown or len(markdown.split()) < CRAWL_WORD_MIN:
                    continue

                cache_path = _url_to_cache_path(page.url)
                cache_path.write_text(markdown, encoding="utf-8")
                rel = str(cache_path.relative_to(CRAWL_CACHE_DIR.parent))
                results_out.append({"url": page.url, "markdown": markdown, "cache_file": rel})

        except Exception as e:
            log.error(f"DFS crawl failed for {root_url}: {type(e).__name__}: {e!r}")

    return results_out


async def run(
    type_maps: Dict[str, Dict[str, str]],
    sources: List[SourceConfig],
    run_id: str,
    skip: bool = False,
) -> Dict[str, List[dict]]:
    """
    Step 3: Native Crawl4AI DFS crawler.

    Strategy:
      - For sources with dfs_depth > 0: use built-in DFSDeepCrawlStrategy on root URLs
      - For depth-0 (single pages): use arun() individually
    Returns:
        {source_id → list of {url, markdown, cache_file}}
    """
    if skip:
        log.info("Step 3 skipped — loading markdown from crawl cache")
        return {}

    log.info("=== STEP 3: CRAWL (Crawl4AI — native) ===")

    source_map = {s.id: s for s in sources}
    visited: Set[str] = get_crawled_urls(run_id)
    semaphore = asyncio.Semaphore(CRAWL_MAX_CONCURRENT)
    all_results: Dict[str, List[dict]] = defaultdict(list)

    async with AsyncWebCrawler() as crawler:
        for source_id, type_map in type_maps.items():
            source = source_map.get(source_id)
            if not source:
                continue

            urls = [u for u in type_map if u not in visited]
            if not urls:
                continue

            max_depth = getattr(source, "dfs_depth", 1)

            if max_depth > 0:
                # ── DFS mode: crawl each root URL with built-in DFS ──────────────
                log.info(f"[{source_id}] DFS crawl: {len(urls)} root URLs, depth={max_depth}")
                for url in urls:
                    if url in visited:
                        continue
                    visited.add(url)
                    pages = await _dfs_crawl_root(crawler, url, max_depth, semaphore)
                    for page in pages:
                        if page["url"] in visited:
                            continue
                        visited.add(page["url"])
                        all_results[source_id].append(page)
                        log.info(f"  ✓ {page['url']} → {len(page['markdown'].split())} words")
                        upsert_url(run_id=run_id, source_id=source_id,
                                   url=page["url"], crawl_status="done",
                                   cache_file=page["cache_file"], depth=0,
                                   root_url=url)
                    if not pages:
                        upsert_url(run_id=run_id, source_id=source_id,
                                   url=url, crawl_status="failed")
            else:
                # ── Flat mode: crawl each URL individually ────────────────────────
                log.info(f"[{source_id}] Flat crawl: {len(urls)} URLs")
                for url in urls:
                    result = await _crawl_url(crawler, url, semaphore)
                    if result:
                        visited.add(url)
                        all_results[source_id].append(result)
                        log.info(f"  ✓ {url} → {len(result['markdown'].split())} words")
                        upsert_url(run_id=run_id, source_id=source_id,
                                   url=url, crawl_status="done",
                                   cache_file=result["cache_file"], depth=0,
                                   root_url=url)
                    else:
                        upsert_url(run_id=run_id, source_id=source_id,
                                   url=url, crawl_status="failed")

    total = sum(len(v) for v in all_results.values())
    log.info(f"Step 3 complete: {total} pages crawled")
    return dict(all_results)
