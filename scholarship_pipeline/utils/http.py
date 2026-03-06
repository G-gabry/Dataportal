"""
utils/http.py — Async HTTP client with retry, timeout, and user-agent.
Used for Firecrawl API calls and portal API calls.
"""

import asyncio
from typing import Any, Optional

import httpx

from utils.logger import get_logger

log = get_logger("http")

_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"

_DEFAULT_HEADERS = {
    "User-Agent": _UA,
    "Accept": "application/json, text/html, */*",
    "Accept-Language": "en-US,en;q=0.9",
}


async def get_json(
    url: str,
    params: Optional[dict] = None,
    headers: Optional[dict] = None,
    timeout: int = 30,
    retries: int = 3,
) -> Optional[dict]:
    """GET request returning parsed JSON. Returns None on permanent failure."""
    merged_headers = {**_DEFAULT_HEADERS, **(headers or {})}
    for attempt in range(retries):
        try:
            async with httpx.AsyncClient(follow_redirects=True) as client:
                r = await client.get(url, params=params, headers=merged_headers, timeout=timeout)
                if r.status_code == 429:
                    wait = 2 ** attempt * 5
                    log.warning(f"Rate limited on {url}. Waiting {wait}s (attempt {attempt+1}/{retries})")
                    await asyncio.sleep(wait)
                    continue
                r.raise_for_status()
                return r.json()
        except httpx.HTTPStatusError as e:
            log.error(f"HTTP {e.response.status_code} on {url}")
            if e.response.status_code < 500:
                return None  # client error — don't retry
        except Exception as e:
            wait = 2 ** attempt * 2
            log.warning(f"Request failed [{url}] attempt {attempt+1}/{retries}: {e}. Retry in {wait}s")
            await asyncio.sleep(wait)
    log.error(f"All {retries} attempts failed for {url}")
    return None


async def post_json(
    url: str,
    payload: dict,
    headers: Optional[dict] = None,
    timeout: int = 60,
    retries: int = 3,
) -> Optional[dict]:
    """POST request returning parsed JSON."""
    merged_headers = {**_DEFAULT_HEADERS, **(headers or {})}
    for attempt in range(retries):
        try:
            async with httpx.AsyncClient(follow_redirects=True) as client:
                r = await client.post(url, json=payload, headers=merged_headers, timeout=timeout)
                if r.status_code == 429:
                    wait = 2 ** attempt * 5
                    log.warning(f"Rate limited on {url}. Waiting {wait}s")
                    await asyncio.sleep(wait)
                    continue
                r.raise_for_status()
                return r.json()
        except Exception as e:
            wait = 2 ** attempt * 2
            log.warning(f"POST failed [{url}] attempt {attempt+1}/{retries}: {e}. Retry in {wait}s")
            await asyncio.sleep(wait)
    return None
