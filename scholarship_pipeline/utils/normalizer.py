"""
utils/normalizer.py — Post-extraction field normalization.

Solves Problem #10: date/amount inconsistency across sites.
Normalizes deadlines → ISO 8601, amounts → numeric string, lists → clean lists.
"""

import re
from typing import Optional, Any
from datetime import datetime

from dateutil import parser as dateutil_parser
from utils.logger import get_logger

log = get_logger("normalizer")

# Strings that mean "no fixed deadline"
_ROLLING_STRINGS = {
    "rolling", "ongoing", "open", "until filled", "until further notice",
    "no deadline", "continuous", "year-round", "anytime", "flexible",
}


def normalize_deadline(raw: Any) -> Optional[str]:
    """Convert any date string to ISO 8601 (YYYY-MM-DD) or None."""
    if raw is None:
        return None
    s = str(raw).strip().lower()
    if not s:
        return None
    if any(r in s for r in _ROLLING_STRINGS):
        return "rolling"
    try:
        dt = dateutil_parser.parse(str(raw), fuzzy=True)
        return dt.strftime("%Y-%m-%d")
    except Exception:
        log.debug(f"Could not parse date: {raw!r}")
        return str(raw)  # return as-is rather than losing the data


def normalize_amount(raw: Any) -> Optional[str]:
    """Normalize funding amounts to a consistent string."""
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None
    # Keep as descriptive string but strip excess whitespace
    return re.sub(r"\s+", " ", s)


def normalize_list(raw: Any) -> list:
    """Ensure a field is a clean list of non-empty strings."""
    if raw is None:
        return []
    if isinstance(raw, list):
        return [str(x).strip() for x in raw if str(x).strip()]
    if isinstance(raw, str):
        # Split by common delimiters if it's a comma/semicolon-separated string
        parts = re.split(r"[;,|]+", raw)
        return [p.strip() for p in parts if p.strip()]
    return [str(raw).strip()]


def normalize_item(item: dict) -> dict:
    """
    Apply all normalization rules to an extracted item dict.
    Operates on item["data"] fields.
    """
    data = item.get("data", {})

    # Date fields
    for field in ("application_deadline", "start_date", "end_date"):
        if field in data:
            data[field] = normalize_deadline(data[field])

    # Amount
    if "amount" in data:
        data["amount"] = normalize_amount(data["amount"])

    # List fields
    for field in (
        "eligible_countries", "eligible_degrees", "eligible_fields",
        "benefits", "required_documents", "tags",
    ):
        if field in data:
            data[field] = normalize_list(data[field])

    # Funding type — enforce enum
    ft = str(data.get("funding_type", "")).strip().lower().replace(" ", "_")
    if "fully" in ft or "full" in ft:
        data["funding_type"] = "fully_funded"
    elif "partial" in ft:
        data["funding_type"] = "partial"
    else:
        data["funding_type"] = "unknown"

    item["data"] = data
    return item
