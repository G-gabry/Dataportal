"""
utils/sitemap.py — Sitemap index + sub-sitemap fetcher with lastmod filtering.

Solves Problem #1: stale sitemap posts (expired scholarships).
Filters by <lastmod> to only keep URLs newer than SITEMAP_MAX_AGE_DAYS.
"""

import asyncio
import re
from datetime import datetime, timezone, timedelta
from typing import List, Optional
from xml.etree import ElementTree as ET

import httpx

from config import SITEMAP_MAX_AGE_DAYS
from utils.logger import get_logger

log = get_logger("sitemap")

_NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
_CUTOFF = datetime.now(timezone.utc) - timedelta(days=SITEMAP_MAX_AGE_DAYS)


async def _fetch(client: httpx.AsyncClient, url: str) -> Optional[str]:
    try:
        r = await client.get(url, timeout=20, follow_redirects=True)
        r.raise_for_status()
        return r.text
    except Exception as e:
        log.warning(f"Sitemap fetch failed [{url}]: {e}")
        return None


def _parse_lastmod(raw: Optional[str]) -> Optional[datetime]:
    if not raw:
        return None
    raw = raw.strip()
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(raw[:19] + ("+00:00" if "Z" in raw else ""), fmt)
            return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt
        except ValueError:
            continue
    return None


def _is_recent(lastmod_str: Optional[str]) -> bool:
    """Return True if lastmod is within SITEMAP_MAX_AGE_DAYS, or if unknown."""
    dt = _parse_lastmod(lastmod_str)
    if dt is None:
        return True   # no date → include (don't silently drop)
    return dt >= _CUTOFF


def _extract_urls_from_xml(xml_text: str) -> List[dict]:
    """Parse a single sitemap XML and return list of {loc, lastmod}."""
    results = []
    try:
        # Strip CDATA artifacts if any
        xml_text = re.sub(r"<!\[CDATA\[([^\]]*)\]\]>", r"\1", xml_text)
        root = ET.fromstring(xml_text)
    except ET.ParseError as e:
        log.warning(f"XML parse error: {e}")
        return results

    # Could be sitemapindex or urlset
    for url_el in root.findall(".//sm:url", _NS) or root.findall(".//url"):
        loc_el = url_el.find("sm:loc", _NS) or url_el.find("loc")
        mod_el = url_el.find("sm:lastmod", _NS) or url_el.find("lastmod")
        if loc_el is not None and loc_el.text:
            results.append({
                "loc": loc_el.text.strip(),
                "lastmod": mod_el.text.strip() if mod_el is not None and mod_el.text else None,
            })
    return results


def _extract_sub_sitemaps(xml_text: str) -> List[str]:
    """If this XML is a sitemapindex, return list of sub-sitemap URLs."""
    sub = []
    try:
        xml_text = re.sub(r"<!\[CDATA\[([^\]]*)\]\]>", r"\1", xml_text)
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return sub

    for sm_el in root.findall(".//sm:sitemap", _NS) or root.findall(".//sitemap"):
        loc_el = sm_el.find("sm:loc", _NS) or sm_el.find("loc")
        if loc_el is not None and loc_el.text:
            sub.append(loc_el.text.strip())
    return sub


async def fetch_all_urls(sitemap_url: str) -> List[str]:
    """
    Top-level entry: given a sitemap URL (index or single),
    return all post URLs passing the lastmod recency filter.
    """
    async with httpx.AsyncClient(
        headers={"User-Agent": "Mozilla/5.0 (compatible; ScholarshipBot/1.0)"},
        follow_redirects=True,
    ) as client:
        raw = await _fetch(client, sitemap_url)
        if not raw:
            return []

        # Is this a sitemap index?
        sub_sitemaps = _extract_sub_sitemaps(raw)
        if sub_sitemaps:
            log.info(f"Sitemap index found: {len(sub_sitemaps)} sub-sitemaps")
            # Only keep post-related sitemaps
            sub_sitemaps = [s for s in sub_sitemaps if "post" in s or "sitemap" in s]
            # Fetch all sub-sitemaps in parallel
            tasks = [_fetch(client, s) for s in sub_sitemaps]
            results = await asyncio.gather(*tasks)
            all_entries = []
            for sub_xml in results:
                if sub_xml:
                    all_entries.extend(_extract_urls_from_xml(sub_xml))
        else:
            # Single sitemap
            all_entries = _extract_urls_from_xml(raw)

    # Apply lastmod filter
    recent = [e["loc"] for e in all_entries if _is_recent(e["lastmod"])]
    skipped = len(all_entries) - len(recent)
    log.info(f"Sitemap {sitemap_url}: {len(all_entries)} total, "
             f"{len(recent)} recent (skipped {skipped} old posts)")
    return recent
