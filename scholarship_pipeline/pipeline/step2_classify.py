"""
pipeline/step2_classify.py — 3-tier URL classification.

Tier 1: URL heuristic (zero AI cost) — classifies ~93% of URLs instantly
Tier 2: Content-peek (post-crawl, 1500 chars + Gemini) — handles ~6%
Tier 3: Universal extraction (Step 5 fallback) — handles remaining <1%
"""

import asyncio
import json
import re
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse

import google.generativeai as genai

from config import (
    TYPE_URL_SIGNALS, URL_EXCLUDE_PATTERNS, PAGINATION_PATTERNS,
    GEMINI_API_KEY, GEMINI_MODEL
)
from pipeline.step0_sources import SourceConfig
from utils.logger import get_logger
from utils.progress import upsert_url

log = get_logger("step2_classify")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

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


_URL_CLASSIFY_PROMPT = """
You are a URL classifier for an academic data pipeline.
Given the following list of URLs, classify each URL into EXACTLY ONE of these types:
- SCHOLARSHIP
- PROGRAM
- CONFERENCE
- EXCHANGE
- EXCLUDE (for login, news, authors, irrelevant pages, or bare domains with no path)
- AMBIGUOUS (if it looks relevant but the type isn't clear from the URL)

Focus ONLY on the URL path structure.
URLs:
{urls}

Return a valid JSON object ONLY. Keys must be the exact URLs provided, values must be the type string.
"""

async def _classify_urls_with_ai_batched(urls: List[str]) -> Dict[str, str]:
    if not urls or not GEMINI_API_KEY:
        return {u: "AMBIGUOUS" for u in urls}
        
    results = {}
    chunk_size = 50
    chunks = [urls[i:i + chunk_size] for i in range(0, len(urls), chunk_size)]
    
    async def process_chunk(chunk):
        prompt = _URL_CLASSIFY_PROMPT.format(urls="\n".join(chunk))
        for attempt in range(3):
            try:
                model = genai.GenerativeModel(GEMINI_MODEL)
                response = await asyncio.to_thread(
                    model.generate_content,
                    prompt,
                    generation_config={"temperature": 0.1, "max_output_tokens": 2048},
                )
                raw = response.text.strip()
                match = re.search(r'\{[\s\S]+\}', raw)
                if match:
                    data = json.loads(match.group())
                    return {u: data.get(u, "AMBIGUOUS").upper().strip() for u in chunk}
                break
            except Exception as e:
                log.warning(f"AI URL classify failed attempt {attempt+1}: {e}")
                await asyncio.sleep(2)
        return {u: "AMBIGUOUS" for u in chunk}

    tasks = [process_chunk(c) for c in chunks]
    chunk_results = await asyncio.gather(*tasks)
    
    for res in chunk_results:
        results.update(res)
        
    return results

async def classify_urls(
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
    needs_ai = []

    for url in urls:
        slug = url.lower()

        # Source-level exclude patterns override
        if any(ex in slug for ex in exclude_kw):
            continue  # drop entirely

        result = _classify_url_heuristic(url)

        if result == "EXCLUDE":
            continue  # drop

        if result is None:
            # Check source-level include patterns
            if include_kw and any(kw in slug for kw in include_kw):
                needs_ai.append(url)
            elif not include_kw:
                needs_ai.append(url)
            # else: skip
        else:
            type_map[url] = result

    if needs_ai:
        log.info(f"[{source.name}] Sending {len(needs_ai)} unrecognized URLs to Gemini for AI filtering...")
        ai_results = await _classify_urls_with_ai_batched(needs_ai)
        for url, ai_type in ai_results.items():
            if ai_type == "EXCLUDE" or ai_type == "NOT_RELEVANT":
                continue # drop
            elif ai_type in ("SCHOLARSHIP", "PROGRAM", "CONFERENCE", "EXCHANGE"):
                type_map[url] = ai_type
            else:
                type_map[url] = "AMBIGUOUS"
                ambiguous.append(url)

    # Persist to DB
    for url, detected_type in type_map.items():
        classify_method = "ai_filter" if url in needs_ai else "heuristic"
        upsert_url(
            run_id=run_id,
            source_id=source.id,
            url=url,
            detected_type=detected_type,
            classify_method=classify_method,
            confidence=1.0 if detected_type != "AMBIGUOUS" else None,
            crawl_status="pending",
            depth=0,
            root_url=url,
        )

    typed_count = sum(1 for t in type_map.values() if t != "AMBIGUOUS")
    log.info(
        f"[{source.name}] Classified {len(urls)} URLs: "
        f"{typed_count} typed, {len(ambiguous)} AMBIGUOUS, {len(urls) - len(type_map)} EXCLUDED"
    )
    return type_map, ambiguous


async def run(
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
            type_map, _ = await classify_urls(urls, source, run_id)
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
