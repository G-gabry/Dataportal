"""
pipeline/step5_extract.py — Type-grouped Gemini extraction.

Solves:
  - Problem #2: Token overflow → token-aware batching (not page-count-based)
  - Problem #5: source_url contamination → use actual crawled URL, not root
  - Problem #6: Gemini hallucination → explicit null rules in prompt
  - Problem #7: JSON parse failures → robust extraction with fallback
"""

import asyncio
import json
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import google.generativeai as genai

from config import (
    GEMINI_API_KEY, GEMINI_MODEL,
    EXTRACTION_MAX_TOKENS_PER_BATCH, EXTRACTION_PARALLEL, EXTRACTION_RETRY_ATTEMPTS,
)
from pipeline.step0_sources import ItemSchemaConfig
from utils.logger import get_logger
from utils.normalizer import normalize_item
from utils.progress import save_extraction_batch

log = get_logger("step5_extract")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

_SCRAPED_AT = datetime.now(timezone.utc).isoformat()

_UNIVERSAL_PROMPT = """
You are extracting academic opportunities from the following web pages.
Each page may contain a SCHOLARSHIP, PROGRAM, CONFERENCE, or EXCHANGE.

For EACH opportunity found, determine its type using these PRIORITY RULES:
1. CONFERENCE: primary focus is a dated event people attend
2. EXCHANGE: primary focus is physical mobility between institutions
3. PROGRAM: leads to a degree or certificate (Master's, PhD, etc.)
4. SCHOLARSHIP: pure financial aid, no degree awarded by the scholarship itself

Return a JSON array. Each object must have "item_type" as the FIRST field,
followed by all relevant fields for that type.

CRITICAL: Return null for fields not explicitly mentioned. Never guess.
source_url must be the actual URL of the page where the data was found.
scraped_at: "{scraped_at}"

Pages:
{pages}

Return JSON array only. No explanation.
"""


def _estimate_tokens(text: str) -> int:
    """Estimate token count: ~4 chars per token."""
    return len(text) // 4


def _format_page(page: dict, idx: int) -> str:
    return f"--- PAGE {idx+1} ---\nURL: {page['url']}\n\n{page['markdown']}\n"


def _build_batches(
    pages: List[dict],
    max_tokens: int = EXTRACTION_MAX_TOKENS_PER_BATCH,
) -> List[List[dict]]:
    """
    Token-aware batching — solves Problem #2 (overflow).
    Groups pages until token budget is exhausted, then starts new batch.
    """
    batches: List[List[dict]] = []
    current_batch: List[dict] = []
    current_tokens = 0

    for page in pages:
        page_tokens = _estimate_tokens(page["markdown"])
        if current_batch and current_tokens + page_tokens > max_tokens:
            batches.append(current_batch)
            current_batch = []
            current_tokens = 0
        current_batch.append(page)
        current_tokens += page_tokens

    if current_batch:
        batches.append(current_batch)

    return batches


def _extract_json_array(raw: str) -> Optional[list]:
    """
    Robust JSON extraction — solves Problem #7.
    Handles: text before JSON, single object vs array, truncated JSON.
    """
    if not raw:
        return None

    # Try direct parse first
    try:
        data = json.loads(raw)
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            return [data]
    except json.JSONDecodeError:
        pass

    # Find first [ ... ] block
    match = re.search(r'\[[\s\S]*\]', raw)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            # Try to recover truncated JSON by finding last complete object
            text = match.group()
            last_brace = text.rfind("}")
            if last_brace > 0:
                try:
                    return json.loads(text[:last_brace + 1] + "]")
                except json.JSONDecodeError:
                    pass

    # Single object fallback
    match = re.search(r'\{[\s\S]*\}', raw)
    if match:
        try:
            return [json.loads(match.group())]
        except json.JSONDecodeError:
            pass

    log.warning(f"Could not parse Gemini response as JSON. Raw (first 200 chars): {raw[:200]!r}")
    return None


async def _call_gemini(prompt: str) -> Optional[str]:
    """Call Gemini with retry."""
    for attempt in range(EXTRACTION_RETRY_ATTEMPTS):
        try:
            model = genai.GenerativeModel(GEMINI_MODEL)
            response = await asyncio.to_thread(
                model.generate_content,
                prompt,
                generation_config={
                    "temperature": 0.1,
                    "max_output_tokens": 8192,
                },
            )
            return response.text
        except Exception as e:
            wait = 2 ** attempt * 5
            log.warning(f"Gemini call failed attempt {attempt+1}: {e}. Retry in {wait}s")
            await asyncio.sleep(wait)
    return None


async def _extract_batch(
    pages: List[dict],
    item_type: str,
    schema: ItemSchemaConfig,
    batch_index: int,
    source_id: str,
    run_id: str,
    semaphore: asyncio.Semaphore,
) -> List[dict]:
    """Extract items from a single batch using the type-specific prompt."""
    if not pages:
        return []

    async with semaphore:
        # Build prompt
        if item_type == "AMBIGUOUS":
            prompt = _UNIVERSAL_PROMPT.format(
                scraped_at=_SCRAPED_AT,
                pages="\n\n".join(_format_page(p, i) for i, p in enumerate(pages)),
            )
        else:
            # Build field list from schema
            field_list = "\n".join(
                f"- {name}: {defn.get('description', '')}"
                for name, defn in schema.schema_fields.items()
            ) if schema.schema_fields else ""

            prompt_template = schema.extraction_prompt
            if "{schema_fields}" in prompt_template:
                prompt_template = prompt_template.replace("{schema_fields}", field_list)

            prompt_template += f'\n\nscrape_at: "{_SCRAPED_AT}"'
            prompt_template += "\n\nPages:\n" + "\n\n".join(
                _format_page(p, i) for i, p in enumerate(pages)
            )
            prompt = prompt_template

        raw = await _call_gemini(prompt)
        if not raw:
            log.error(f"Gemini returned nothing for batch {batch_index} ({item_type})")
            return []

        items = _extract_json_array(raw)
        if items is None:
            return []

        # Post-process each item
        enriched = []
        for item in items:
            if not isinstance(item, dict):
                continue

            # Ensure item_type is set
            if "item_type" not in item:
                item["item_type"] = item_type

            # Wrap data fields into {"item_type": ..., "data": {...}} structure
            # if the model returned flat structure
            if "data" not in item:
                it = item.pop("item_type", item_type)
                item = {"item_type": it, "data": item}

            # Ensure source_url is the actual crawled URL (not root URL)
            # This is critical — fixes Problem #5
            data = item.get("data", {})
            if not data.get("source_url"):
                # Try to find matching page URL
                for page in pages:
                    data["source_url"] = page["url"]
                    break

            item["data"] = data
            item = normalize_item(item)
            enriched.append(item)

        # Save batch to DB
        save_extraction_batch(run_id, source_id, item_type, batch_index, enriched)
        log.info(f"Extracted {len(enriched)} items from batch {batch_index} ({item_type})")
        return enriched


async def run(
    crawl_results: Dict[str, List[dict]],
    resolved_types: Dict[str, str],
    schemas: Dict[str, ItemSchemaConfig],
    sources,
    run_id: str,
    skip: bool = False,
) -> List[dict]:
    """
    Step 5: Type-grouped Gemini extraction.

    Groups pages by detected_type → one batch pool per type.
    Each batch processed with the matching extraction prompt.
    AMBIGUOUS pages go through universal prompt.
    """
    if skip:
        log.info("Step 5 skipped — loading from DB")
        from utils.progress import get_all_extracted_items
        return get_all_extracted_items(run_id)

    log.info("=== STEP 5: EXTRACTION ===")

    # Merge resolved types from Step 4 content-peek
    def get_type(page: dict) -> str:
        task = page.get("task")
        url = page.get("url", "")
        # Step 4 may have resolved this URL's type
        if url in resolved_types:
            return resolved_types[url]
        if task:
            return task.root_type or "AMBIGUOUS"
        return "AMBIGUOUS"

    # Group pages by type across all sources
    pages_by_type: Dict[str, List[dict]] = {
        "SCHOLARSHIP": [], "PROGRAM": [],
        "CONFERENCE": [], "EXCHANGE": [], "AMBIGUOUS": [],
    }

    source_map = {}
    for source in sources:
        source_map[source.id] = source

    for source_id, pages in crawl_results.items():
        for page in pages:
            if page.get("markdown"):
                item_type = get_type(page)
                if item_type in ("SKIP", "NOT_RELEVANT"):
                    continue
                bucket = item_type if item_type in pages_by_type else "AMBIGUOUS"
                pages_by_type[bucket].append(page)

    # Log distribution
    for t, pages in pages_by_type.items():
        log.info(f"  {t}: {len(pages)} pages")

    semaphore = asyncio.Semaphore(EXTRACTION_PARALLEL)
    all_tasks = []
    batch_counter = 0

    for item_type, pages in pages_by_type.items():
        if not pages:
            continue
        schema = schemas.get(item_type) or schemas.get("SCHOLARSHIP")
        batches = _build_batches(pages)

        for batch in batches:
            # Determine source_id for first page in batch
            task = batch[0].get("task")
            source_id = task.source_id if task else "unknown"

            all_tasks.append(
                _extract_batch(batch, item_type, schema, batch_counter, source_id, run_id, semaphore)
            )
            batch_counter += 1

    log.info(f"Running {len(all_tasks)} extraction batches ({EXTRACTION_PARALLEL} parallel)")
    results = await asyncio.gather(*all_tasks, return_exceptions=True)

    all_items = []
    for r in results:
        if isinstance(r, Exception):
            log.error(f"Extraction batch error: {r}")
        elif r:
            all_items.extend(r)

    log.info(f"Step 5 complete: {len(all_items)} items extracted")
    return all_items
