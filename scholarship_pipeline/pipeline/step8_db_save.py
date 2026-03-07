"""
pipeline/step8_db_save.py — Save extracted items to Cloud SQL via the backend API.

Calls POST /api/v1/items for each extracted item.
The backend's Item model stores all extracted data in a flexible JSONB `data` column,
so any fields extracted by Gemini are saved as-is — no schema mismatch possible.

Structure of each API call:
    {
        "source_id": "<uuid>",
        "item_type": "SCHOLARSHIP" | "PROGRAM" | "CONFERENCE" | "EXCHANGE",
        "data": { ...all extracted fields from Gemini... }
    }
"""

import asyncio
import httpx
from typing import List

from config import PORTAL_API_BASE, PORTAL_API_TOKEN
from utils.logger import get_logger

log = get_logger("step8_db_save")

_TIMEOUT = 60  # seconds per request - increased for localtunnel
_CONCURRENCY = 2  # parallel saves - reduced for localtunnel stability


def _auth_headers() -> dict:
    headers = {
        "bypass-tunnel-reminders": "true",  # Essential for localtunnel API access
    }
    if PORTAL_API_TOKEN:
        headers["Authorization"] = f"Bearer {PORTAL_API_TOKEN}"
    return headers


async def _save_one(
    client: httpx.AsyncClient,
    item: dict,
    semaphore: asyncio.Semaphore,
    source_id_map: dict,
) -> bool:
    """Send one item to the backend API. Returns True on success."""
    item_type = item.get("item_type", "").upper()
    data = item.get("data", item)  # support both wrapped {item_type, data} and flat
    if not data:
        return False

    # Resolve source_id — use the one embedded in the item, or fall back to the first source
    source_id = data.pop("source_id_override", None) or list(source_id_map.values())[0]

    payload = {
        "source_id": str(source_id),
        "item_type": item_type,
        "data": data,
    }

    async with semaphore:
        for attempt in range(3):
            try:
                resp = await client.post(
                    f"{PORTAL_API_BASE}/api/v1/items",
                    json=payload,
                    headers=_auth_headers(),
                    timeout=_TIMEOUT,
                )
                if resp.status_code in (200, 201):
                    return True
                elif resp.status_code == 401:
                    log.error("Unauthorized — check PORTAL_API_TOKEN in .env.vm")
                    return False
                else:
                    log.warning(f"Save failed ({resp.status_code}): {resp.text[:200]}")
            except Exception as e:
                wait = 2 ** attempt
                log.warning(f"Save attempt {attempt+1} failed: {e}. Retry in {wait}s")
                await asyncio.sleep(wait)
    return False


async def run(
    items: List[dict],
    sources: list,
    skip: bool = False,
) -> dict:
    """
    Step 8: Bulk-save all extracted items to the backend database.

    Returns:
        {"saved": int, "failed": int}
    """
    if skip:
        log.info("Step 8 skipped — items not saved to database")
        return {"saved": 0, "failed": 0}

    if not items:
        log.info("Step 8: No items to save")
        return {"saved": 0, "failed": 0}

    log.info(f"=== STEP 8: SAVE TO DATABASE ({len(items)} items) ===")

    # Build source_id map: {source_name → source_id}
    source_id_map = {s.name: s.id for s in sources}

    semaphore = asyncio.Semaphore(_CONCURRENCY)
    saved = 0
    failed = 0

    async with httpx.AsyncClient() as client:
        # Attach the right source_id per item based on source_url domain matching
        tasks = []
        for item in items:
            tasks.append(_save_one(client, item, semaphore, source_id_map))

        results = await asyncio.gather(*tasks, return_exceptions=True)

    for r in results:
        if r is True:
            saved += 1
        else:
            failed += 1

    log.info(f"Step 8 complete: {saved} saved to database, {failed} failed")
    return {"saved": saved, "failed": failed}
