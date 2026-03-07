"""
pipeline/step4_resolve.py — Post-crawl AMBIGUOUS URL resolution (Tier 2).

For URLs classified as AMBIGUOUS after Tier 1 (URL heuristic),
this step sends the first 1500 chars of content to Gemini
with the precise classification prompt.

Only runs on AMBIGUOUS pages — cheap (1500 chars vs full page).
8 concurrent calls for speed.
"""

import asyncio
import json
import re
from typing import Dict, List, Optional, Tuple

from google import genai
from google.genai import types

from config import (
    GEMINI_API_KEY, GEMINI_MODEL,
    PEEK_CHARS, PEEK_CONFIDENCE_THRESHOLD, PEEK_CONCURRENCY,
)
from utils.logger import get_logger
from utils.markdown_cleaner import get_peek
from utils.progress import upsert_url

log = get_logger("step4_resolve")

GLOBAL_GENAI_CLIENT = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None

_CLASSIFICATION_PROMPT = """
You are classifying a web page into exactly ONE of 4 types, or NOT_RELEVANT.

PRIORITY ORDER — apply the FIRST rule that fits:

RULE 1 — CONFERENCE:
If the page is primarily about a DATED EVENT (conference, symposium, workshop,
congress, seminar, summit) that people attend → CONFERENCE.
Even if it offers a travel grant — if attending an EVENT is the primary purpose → CONFERENCE.

RULE 2 — EXCHANGE:
If the page is about a MOBILITY PROGRAM where a student or researcher physically
MOVES between two institutions (Erasmus, study abroad, visiting researcher) → EXCHANGE.
The mobility itself is the opportunity, not a degree or pure funding.

RULE 3 — PROGRAM:
If the page is about an academic program leading to a DEGREE or CERTIFICATE
(Master's, PhD, Bachelor's, MBA, diploma). May include funding, but the DEGREE
structure (credits, curriculum) is primary → PROGRAM.

RULE 4 — SCHOLARSHIP:
If the page is about FINANCIAL AID where the scholar applies separately from any
university. No degree awarded by the scholarship itself. Pure money: tuition waiver,
stipend, bursary, fellowship, award → SCHOLARSHIP.

RULE 5 — NOT_RELEVANT:
Navigation, author bio, tag listing, cookie policy, generic news, login page → NOT_RELEVANT.

DISAMBIGUATION EXAMPLES:
  "Chevening Scholarship"          → SCHOLARSHIP  (money, apply separately from Oxford)
  "Fulbright Program"              → SCHOLARSHIP  (funding despite "program" in name)
  "Erasmus+ Study Abroad"          → EXCHANGE     (physical mobility)
  "MIT PhD Program (funded)"       → PROGRAM      (degree-granting)
  "ICSB Conference + Travel Grant" → CONFERENCE   (event is primary purpose)
  "Summer Research Fellowship"     → SCHOLARSHIP  (no degree, pure funding)
  "DAAD Research Exchange"         → EXCHANGE     (physical move required)
  "DAAD Scholarship"               → SCHOLARSHIP  (no mobility required)

Content:
{content}

Return exactly this JSON (no other text):
{{"type": "SCHOLARSHIP", "confidence": 0.92, "reason": "one sentence"}}
"""


async def _classify_one(
    url: str,
    markdown: str,
    semaphore: asyncio.Semaphore,
) -> Tuple[str, Optional[str], Optional[float]]:
    """
    Classify a single page via content-peek.
    Returns (url, detected_type | None, confidence).
    """
    peek = get_peek(markdown, chars=PEEK_CHARS)
    if not peek.strip():
        return url, None, None

    prompt = _CLASSIFICATION_PROMPT.format(content=peek)

    async with semaphore:
        for attempt in range(3):
            try:
                if not GLOBAL_GENAI_CLIENT:
                    raise ValueError("GEMINI_API_KEY not configured")
                response = await asyncio.to_thread(
                    GLOBAL_GENAI_CLIENT.models.generate_content,
                    model=GEMINI_MODEL,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.1,
                        max_output_tokens=100,
                    ),
                )
                raw = response.text.strip()

                # Parse JSON response
                match = re.search(r'\{[^}]+\}', raw)
                if match:
                    data = json.loads(match.group())
                    detected = data.get("type", "").upper().strip()
                    confidence = float(data.get("confidence", 0))

                    if detected in ("SCHOLARSHIP", "PROGRAM", "CONFERENCE", "EXCHANGE"):
                        if confidence >= PEEK_CONFIDENCE_THRESHOLD:
                            return url, detected, confidence
                        else:
                            log.debug(f"Low confidence ({confidence:.2f}) for {url}: {detected}")
                            return url, None, confidence  # stays AMBIGUOUS

                    if detected == "NOT_RELEVANT":
                        return url, "SKIP", 1.0

                break  # bad response format — don't retry parse errors

            except Exception as e:
                wait = 2 ** attempt * 3
                log.warning(f"Peek classify failed [{url}] attempt {attempt+1}: {e}. Retry in {wait}s")
                await asyncio.sleep(wait)

    return url, None, None  # stays AMBIGUOUS


async def run(
    crawl_results: Dict[str, List[dict]],
    run_id: str,
    skip: bool = False,
) -> Dict[str, str]:
    """
    Step 4: Resolve AMBIGUOUS pages via content-peek classification.

    Args:
        crawl_results: {source_id → [{url, markdown, task, ...}]}
        run_id: current run ID

    Returns:
        resolved_types: {url → detected_type}  (only newly resolved ones)
    """
    if skip or not GEMINI_API_KEY:
        if not GEMINI_API_KEY:
            log.warning("GEMINI_API_KEY not set — skipping Tier 2 content-peek")
        return {}

    log.info("=== STEP 4: AMBIGUOUS RESOLUTION (content-peek) ===")

    # Collect all AMBIGUOUS pages
    ambiguous_pages: List[Tuple[str, str, str]] = []  # (url, source_id, markdown)
    for source_id, pages in crawl_results.items():
        for page in pages:
            task = page.get("task")
            if task and task.root_type == "AMBIGUOUS":
                ambiguous_pages.append((page["url"], source_id, page["markdown"]))

    if not ambiguous_pages:
        log.info("No AMBIGUOUS pages to resolve")
        return {}

    log.info(f"Resolving {len(ambiguous_pages)} AMBIGUOUS pages via content-peek")
    semaphore = asyncio.Semaphore(PEEK_CONCURRENCY)

    tasks = [
        _classify_one(url, markdown, semaphore)
        for url, _, markdown in ambiguous_pages
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    resolved: Dict[str, str] = {}
    still_ambiguous = 0
    skipped = 0

    for (url, source_id, _), result in zip(ambiguous_pages, results):
        if isinstance(result, Exception):
            log.error(f"Classification error for {url}: {result}")
            continue

        _, detected_type, confidence = result

        if detected_type == "SKIP":
            upsert_url(run_id=run_id, source_id=source_id, url=url,
                       crawl_status="skipped", detected_type="NOT_RELEVANT")
            skipped += 1
        elif detected_type:
            resolved[url] = detected_type
            upsert_url(run_id=run_id, source_id=source_id, url=url,
                       detected_type=detected_type, classify_method="content_peek",
                       confidence=confidence)
        else:
            still_ambiguous += 1
            log.debug(f"Still AMBIGUOUS after peek: {url}")

    log.info(
        f"Step 4 complete: {len(resolved)} resolved, "
        f"{still_ambiguous} still AMBIGUOUS (→ Tier 3 in Step 5), "
        f"{skipped} NOT_RELEVANT (skipped)"
    )
    return resolved
