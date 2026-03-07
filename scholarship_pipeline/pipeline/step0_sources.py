"""
pipeline/step0_sources.py — Load SourceConfig + ItemSchema from the data portal API.

Solves Problem #11: portal API cold-start by caching last-successful response.
Sources are NEVER hardcoded — they come from the portal UI.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from config import (
    PORTAL_API_BASE, PORTAL_API_TOKEN, SOURCES_CACHE_FILE,
    DFS_DEFAULT_DEPTH,
)
from utils.logger import get_logger
from utils.http import get_json

log = get_logger("step0_sources")

# Defaults used when a source has no include/exclude patterns configured in the portal UI
DEFAULT_URL_KEYWORDS_INCLUDE = [
    "scholarship", "fellowship", "grant", "funding",
    "opportunity", "programme", "program", "application", "award",
]
DEFAULT_URL_KEYWORDS_EXCLUDE = [
    "login", "register", "privacy", "terms", "contact",
    "about", "sitemap", "tags", "author", "wp-admin",
    "wp-content", "feed", "comment",
]


@dataclass
class SourceConfig:
    id: str
    name: str
    base_url: str
    sitemap_url: Optional[str]            # from sitemap_url
    dfs_depth: int                        # from dfs_depth
    max_urls_per_run: Optional[int]       # from max_urls_per_run
    include_patterns: List[str]
    exclude_patterns: List[str]
    target_item_types: List[str]          # ["SCHOLARSHIP", "PROGRAM", ...]


@dataclass
class ItemSchemaConfig:
    item_type: str
    schema_fields: dict                   # field definitions
    extraction_prompt: str                # Gemini extraction prompt
    classification_prompt: str            # Gemini classification prompt


def _auth_header() -> dict:
    headers = {"bypass-tunnel-reminders": "true"}
    if PORTAL_API_TOKEN:
        headers["Authorization"] = f"Bearer {PORTAL_API_TOKEN}"
    return headers


async def load_sources(skip_api: bool = False) -> List[SourceConfig]:
    """
    Fetch active sources from portal API.
    Falls back to local cache if API is unreachable.
    """
    sources = []

    if not skip_api:
        url = f"{PORTAL_API_BASE}/api/v1/sources"
        data = await get_json(url, params={"is_active": "true", "page_size": 100},
                              headers=_auth_header(), timeout=15)
        if data and "items" in data:
            sources = data["items"]
            # Cache successful response
            SOURCES_CACHE_FILE.write_text(
                json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
            )
            log.info(f"Loaded {len(sources)} sources from portal API")
        else:
            log.warning("Portal API returned no sources — trying cache")

    if not sources and SOURCES_CACHE_FILE.exists():
        try:
            cached = json.loads(SOURCES_CACHE_FILE.read_text(encoding="utf-8-sig"))
            sources = cached.get("items", [])
            log.warning(f"Using cached sources ({len(sources)} entries). Portal API may be down.")
        except Exception as e:
            log.error(f"Failed to read sources cache: {e}")

    if not sources:
        raise RuntimeError(
            "No sources available. Start the portal API or provide a sources_cache.json."
        )

    return [_to_source_config(s) for s in sources]


def _to_source_config(s: dict) -> SourceConfig:
    return SourceConfig(
        id              = str(s["id"]),
        name            = s.get("name", "unknown"),
        base_url        = s.get("base_url", "").rstrip("/"),
        sitemap_url     = s.get("sitemap_url"),
        dfs_depth       = int(s.get("dfs_depth") if s.get("dfs_depth") is not None else DFS_DEFAULT_DEPTH),
        max_urls_per_run = s.get("max_urls_per_run"),
        include_patterns = s.get("include_patterns") or DEFAULT_URL_KEYWORDS_INCLUDE,
        exclude_patterns = s.get("exclude_patterns") or DEFAULT_URL_KEYWORDS_EXCLUDE,
        target_item_types = [t for t in (s.get("target_item_types") or [])],
    )


async def load_item_schemas() -> dict:
    """
    Fetch ItemSchema records from portal API.
    Returns dict: {item_type: ItemSchemaConfig}
    """
    url = f"{PORTAL_API_BASE}/api/v1/schemas"
    data = await get_json(url, headers=_auth_header(), timeout=15)

    schemas = {}
    if data:
        for s in (data if isinstance(data, list) else data.get("items", [])):
            item_type = s.get("item_type", "").upper()
            schemas[item_type] = ItemSchemaConfig(
                item_type            = item_type,
                schema_fields        = s.get("schema_json", {}).get("fields", {}),
                extraction_prompt    = s.get("extraction_prompt") or _default_extraction_prompt(item_type),
                classification_prompt = s.get("classification_prompt") or "",
            )
    else:
        log.warning("Could not load ItemSchemas from portal — using built-in defaults")

    # Fill in missing types with defaults
    for t in ("SCHOLARSHIP", "PROGRAM", "CONFERENCE", "EXCHANGE"):
        if t not in schemas:
            schemas[t] = ItemSchemaConfig(
                item_type             = t,
                schema_fields         = {},
                extraction_prompt     = _default_extraction_prompt(t),
                classification_prompt = "",
            )

    log.info(f"Loaded schemas for: {list(schemas.keys())}")
    return schemas


def _default_extraction_prompt(item_type: str) -> str:
    """Built-in fallback extraction prompt per type."""
    shared = """
CRITICAL RULES:
- Return null for any field not explicitly stated in the content. Do NOT guess or infer.
- "eligible_countries": null unless explicitly stated. "All" only if page says "open to all nationalities".
- "application_deadline": ISO 8601 (YYYY-MM-DD) or "rolling" if stated. null if not mentioned.
- "funding_type": "fully_funded" | "partial" | "unknown" — based on explicit statements only.
- url: must be the exact URL where the data was found.
- Return a JSON ARRAY only. No explanation text before or after.
"""
    if item_type == "SCHOLARSHIP":
        return f"""You are extracting scholarship data from the following web pages.
For EACH scholarship found, return a JSON object with these fields:
name, scholarship_name, summary, url, country, host_institution, host_organization,
eligible_countries (list), eligible_degrees (list), eligible_fields (list),
funding_type, amount, benefits (list), application_deadline, start_date,
duration, link, required_documents (list), scraped_at.
{shared}"""

    if item_type == "PROGRAM":
        return f"""You are extracting academic program data from the following web pages.
For EACH program found, return a JSON object with these fields:
name, program_name, summary, url, country, host_institution,
degree_type, fields_of_study (list), duration, language_of_instruction,
tuition_fee, scholarship_available, application_deadline, start_date,
link, requirements (list), scraped_at.
{shared}"""

    if item_type == "CONFERENCE":
        return f"""You are extracting conference/event data from the following web pages.
For EACH conference found, return a JSON object with these fields:
name, conference_name, summary, url, country, venue, organizer,
event_date, submission_deadline, registration_deadline, topics (list),
attendance_type (in-person/virtual/hybrid), registration_fee,
travel_grant_available, link, scraped_at.
{shared}"""

    if item_type == "EXCHANGE":
        return f"""You are extracting exchange/mobility program data from the following web pages.
For EACH exchange program found, return a JSON object with these fields:
name, summary, url, country, host_institution,
partner_countries (list), eligible_nationalities (list), level_of_study (list),
duration, funding_available, stipend_amount, application_deadline,
start_date, mobility_type, link, requirements (list), scraped_at.
{shared}"""

    return f"Extract all {item_type} opportunities from these pages as a JSON array."
