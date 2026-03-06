"""
utils/link_extractor.py — Extract and score outbound links from markdown.

Implements DFS link acceptance rules:
  - Same-domain: only follow if URL matches heuristic patterns
  - External domain: only follow if URL looks like an application portal
  - Always reject: pagination, social media, media files, anchors

Solves Problem: DFS snowballing (20-30 links per post → only 1-3 followed).
"""

import re
from urllib.parse import urlparse, urljoin
from typing import List, Set, Tuple

from config import (
    TYPE_URL_SIGNALS, PAGINATION_PATTERNS, ALWAYS_SKIP_DOMAINS,
    EXTERNAL_LINK_ACCEPT_KEYWORDS, URL_EXCLUDE_PATTERNS,
)
from utils.logger import get_logger

log = get_logger("link_extractor")

# Absolute URL pattern in markdown: [text](https://...)
_MD_LINK_RE = re.compile(r"\[([^\]]{0,200})\]\((https?://[^\)]{1,500})\)")

# Relative URL pattern: [text](/path/...)
_MD_REL_RE  = re.compile(r"\[([^\]]{0,200})\]\((/[^\)]{1,500})\)")

# File extensions to skip
_SKIP_EXTS = {".pdf", ".docx", ".doc", ".pptx", ".xlsx", ".zip",
              ".jpg", ".jpeg", ".png", ".gif", ".svg", ".mp4", ".mp3"}

_PAGINATON_RE = [re.compile(p) for p in PAGINATION_PATTERNS]

_ALL_URL_SIGNALS = [s for signals in TYPE_URL_SIGNALS.values() for s in signals]


def _get_domain(url: str) -> str:
    try:
        parsed = urlparse(url)
        host = parsed.netloc.lower()
        # Strip www.
        return host[4:] if host.startswith("www.") else host
    except Exception:
        return ""


def _is_pagination(url: str) -> bool:
    return any(p.search(url) for p in _PAGINATON_RE)


def _has_skip_ext(url: str) -> bool:
    path = urlparse(url).path.lower()
    return any(path.endswith(ext) for ext in _SKIP_EXTS)


def _is_blacklisted(url: str) -> bool:
    domain = _get_domain(url)
    return any(domain == skip or domain.endswith("." + skip) for skip in ALWAYS_SKIP_DOMAINS)


def _matches_include_heuristic(url: str) -> bool:
    slug = url.lower()
    return any(signal in slug for signal in _ALL_URL_SIGNALS)


def _is_useful_external(url: str) -> bool:
    slug = url.lower()
    return any(kw in slug for kw in EXTERNAL_LINK_ACCEPT_KEYWORDS)


def _is_excluded(url: str) -> bool:
    slug = url.lower()
    return any(ex in slug for ex in URL_EXCLUDE_PATTERNS)


def extract_links(
    markdown: str,
    page_url: str,
    root_domain: str,
    external_domains_seen: Set[str],
    max_ext_domains: int,
    max_pages_ext: int = 2,
) -> List[Tuple[str, bool]]:
    """
    Extract acceptable child links from a markdown page.

    Returns list of (url, is_external) tuples.
    Only returns links that pass the acceptance rules.

    Args:
        markdown:              Page content
        page_url:              Current page URL (for relative link resolution)
        root_domain:           Domain of the scholarship source site
        external_domains_seen: Domains already followed for this root post
        max_ext_domains:       Budget: max unique external domains
        max_pages_ext:         Budget: max pages per external domain
    """
    base = f"{urlparse(page_url).scheme}://{urlparse(page_url).netloc}"
    accepted: List[Tuple[str, bool]] = []
    seen_in_this_call: Set[str] = set()

    # Collect all links
    all_links: List[str] = []
    for _, url in _MD_LINK_RE.findall(markdown):
        all_links.append(url.split("#")[0].strip().rstrip("/") or url)
    for _, rel in _MD_REL_RE.findall(markdown):
        all_links.append(urljoin(base, rel).split("#")[0].strip().rstrip("/"))

    for url in all_links:
        if not url or url in seen_in_this_call:
            continue
        if "#" in url and url.endswith(url.split("#")[-1]):
            continue   # anchors
        seen_in_this_call.add(url)

        # Universal rejects
        if _is_pagination(url):
            continue
        if _has_skip_ext(url):
            continue
        if _is_blacklisted(url):
            continue
        if _is_excluded(url):
            continue

        domain = _get_domain(url)
        is_external = (domain != root_domain and root_domain not in domain)

        if not is_external:
            # Same-domain: only follow if URL looks like an opportunity post
            if _matches_include_heuristic(url):
                accepted.append((url, False))
        else:
            # External domain budget check
            if len(external_domains_seen) >= max_ext_domains:
                if domain not in external_domains_seen:
                    continue  # budget exhausted, new domain
            # Must look like an application portal
            if not _is_useful_external(url):
                continue
            accepted.append((url, True))

    log.debug(f"link_extractor: {len(all_links)} links found, {len(accepted)} accepted from {page_url}")
    return accepted
