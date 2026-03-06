"""
pipeline/step6_dedup.py — Two-pass deduplication.

Pass 1: Exact application_link URL dedup
Pass 2: Fuzzy title similarity (>90%) + same-year guard

Cross-type safe: SCHOLARSHIP and PROGRAM with similar titles are NOT merged.
Null application_link handled: falls back to (title, host_institution, deadline) composite key.
"""

import re
from typing import List, Optional

from thefuzz import fuzz

from config import FUZZY_TITLE_THRESHOLD, YEAR_CHECK_ENABLED
from utils.logger import get_logger

log = get_logger("step6_dedup")


def _extract_year(text: Optional[str]) -> Optional[str]:
    """Extract first 4-digit year (2020-2030) from a string."""
    if not text:
        return None
    match = re.search(r'\b(20[2-3]\d)\b', str(text))
    return match.group(1) if match else None


def _composite_key(item: dict) -> Optional[str]:
    """
    Fallback dedup key when application_link is null.
    Uses: item_type + title (lowercase, stripped) + deadline_year.
    """
    data = item.get("data", {})
    title = str(data.get("title", "")).lower().strip()
    institution = str(data.get("host_institution", "")).lower().strip()
    year = _extract_year(data.get("application_deadline", "")) or \
           _extract_year(data.get("title", ""))
    if not title:
        return None
    return f"{item.get('item_type','')}|{title}|{institution}|{year or ''}"


def _completeness_score(item: dict) -> int:
    """Count non-null, non-empty fields in item["data"]."""
    data = item.get("data", {})
    return sum(
        1 for v in data.values()
        if v is not None and v != "" and v != [] and v != {}
    )


def _are_title_duplicates(a: dict, b: dict) -> bool:
    """
    Returns True if two items are likely the same opportunity.
    Requires: same item_type + year guard + title similarity > threshold.
    """
    if a.get("item_type") != b.get("item_type"):
        return False  # SCHOLARSHIP ≠ PROGRAM even if identical title

    da = a.get("data", {})
    db = b.get("data", {})

    title_a = str(da.get("title", "")).strip()
    title_b = str(db.get("title", "")).strip()

    if not title_a or not title_b:
        return False

    if YEAR_CHECK_ENABLED:
        year_a = _extract_year(title_a) or _extract_year(da.get("application_deadline", ""))
        year_b = _extract_year(title_b) or _extract_year(db.get("application_deadline", ""))
        # If both have a year and they differ → NOT duplicates
        if year_a and year_b and year_a != year_b:
            return False

    similarity = fuzz.token_sort_ratio(title_a, title_b)
    return similarity >= FUZZY_TITLE_THRESHOLD


def run(items: List[dict]) -> List[dict]:
    """
    Step 6: Deduplicate extracted items.

    Returns:
        Deduplicated list (most complete entry kept per duplicate group).
    """
    log.info(f"=== STEP 6: DEDUPLICATION ({len(items)} items) ===")

    # ── Pass 1: Exact application_link dedup ─────────────────────────────────
    seen_links = {}   # link → index in pass1_items
    seen_composite = {}  # composite_key → index
    pass1_items = []

    for item in items:
        data = item.get("data", {})
        link = data.get("application_link")

        if link:
            link_norm = link.strip().rstrip("/").lower()
            if link_norm in seen_links:
                # Keep more complete entry
                existing_idx = seen_links[link_norm]
                if _completeness_score(item) > _completeness_score(pass1_items[existing_idx]):
                    pass1_items[existing_idx] = item
            else:
                seen_links[link_norm] = len(pass1_items)
                pass1_items.append(item)
        else:
            # Fallback to composite key
            key = _composite_key(item)
            if key and key in seen_composite:
                existing_idx = seen_composite[key]
                if _completeness_score(item) > _completeness_score(pass1_items[existing_idx]):
                    pass1_items[existing_idx] = item
            else:
                if key:
                    seen_composite[key] = len(pass1_items)
                pass1_items.append(item)

    deduped_pass1 = len(items) - len(pass1_items)
    log.info(f"Pass 1 (exact URL): {deduped_pass1} duplicates removed, {len(pass1_items)} remain")

    # ── Pass 2: Fuzzy title + year guard ─────────────────────────────────────
    # Group by item_type first for efficiency (no cross-type comparison needed)
    by_type: dict = {}
    for item in pass1_items:
        t = item.get("item_type", "UNKNOWN")
        by_type.setdefault(t, []).append(item)

    pass2_items = []
    for item_type, group in by_type.items():
        deduped_group = []
        for item in group:
            is_dup = False
            for i, existing in enumerate(deduped_group):
                if _are_title_duplicates(item, existing):
                    # Keep more complete entry
                    if _completeness_score(item) > _completeness_score(existing):
                        deduped_group[i] = item
                    is_dup = True
                    break
            if not is_dup:
                deduped_group.append(item)
        pass2_items.extend(deduped_group)

    deduped_pass2 = len(pass1_items) - len(pass2_items)
    total_deduped = deduped_pass1 + deduped_pass2
    log.info(
        f"Pass 2 (fuzzy title): {deduped_pass2} duplicates removed\n"
        f"Step 6 complete: {total_deduped} total duplicates removed, "
        f"{len(pass2_items)} final items"
    )
    return pass2_items, total_deduped
