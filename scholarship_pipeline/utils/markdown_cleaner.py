"""
utils/markdown_cleaner.py — Strip boilerplate before sending to Gemini.

Reduces average page from ~8k tokens → ~2k tokens by removing:
  - Navigation menus
  - Footer content
  - Social share sections
  - "Related posts" / "You may also like" blocks
  - Comment sections
  - Cookie notices
"""

import re
from utils.logger import get_logger

log = get_logger("markdown_cleaner")

# Regex patterns for common boilerplate sections in markdown
_BOILERPLATE_PATTERNS = [
    # Navigation / menu blocks (repeated link lists at top)
    r"^\s*\[.{1,60}\]\(https?://[^\)]+\)\s*\|.*$",       # pipe-separated nav link rows
    r"^#{1,3}\s*(Navigation|Menu|Header|Footer|Sidebar)\b.*",

    # Social share sections
    r"(?i)(share this|share on|tweet this|facebook|whatsapp|linkedin).{0,100}",
    r"(?i)(follow us|subscribe|newsletter).{0,200}",

    # Related posts
    r"(?i)#{1,3}\s*(related|you might also|see also|more like this|popular posts).{0,400}",

    # Comment sections
    r"(?i)#{1,3}\s*(comments?|leave a (comment|reply)|discussion).{0,2000}",

    # Cookie / GDPR notices
    r"(?i)(we use cookies|cookie (policy|notice|consent)).{0,300}",

    # WordPress boilerplate
    r"(?i)(posted (in|by|on)|filed under|tagged (with|as)).{0,200}",
    r"(?i)(read more|continue reading|click here to read).{0,100}",

    # Repeated empty lines (3+ blank lines → 1)
    r"\n{3,}",
]

_COMPILED = [(re.compile(p, re.MULTILINE), p) for p in _BOILERPLATE_PATTERNS]


def clean(markdown: str, max_chars: int = 30_000) -> str:
    """
    Clean a markdown string by removing boilerplate blocks.

    Args:
        markdown: Raw markdown from Crawl4AI
        max_chars: Truncate at this length (default 30k chars ≈ 7.5k tokens)

    Returns:
        Cleaned, truncated markdown
    """
    if not markdown:
        return ""

    text = markdown

    for pattern, _ in _COMPILED:
        try:
            if r"\n{3,}" in pattern.pattern:
                text = pattern.sub("\n\n", text)
            else:
                text = pattern.sub("", text)
        except Exception:
            pass

    # Strip excessive leading/trailing whitespace per line
    lines = [line.rstrip() for line in text.splitlines()]
    text = "\n".join(lines).strip()

    # Truncate
    if len(text) > max_chars:
        text = text[:max_chars] + "\n\n[... content truncated ...]"
        log.debug(f"Truncated page to {max_chars} chars")

    return text


def get_peek(markdown: str, chars: int = 1500) -> str:
    """Return first `chars` characters of cleaned markdown for content-peek classification."""
    cleaned = clean(markdown, max_chars=chars * 2)
    return cleaned[:chars]
