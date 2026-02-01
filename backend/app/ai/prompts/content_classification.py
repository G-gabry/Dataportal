from typing import List


def get_content_classification_prompt(content: str, url: str, target_types: List[str]) -> str:
    """Generate prompt for content classification"""

    # Truncate content if too long
    max_content_length = 8000
    if len(content) > max_content_length:
        content = content[:max_content_length] + "\n\n[Content truncated...]"

    types_str = ", ".join(target_types)

    return f"""Analyze this webpage content and classify it.

URL: {url}

Target item types we're looking for: {types_str}

Page content:
---
{content}
---

Analyze the content and respond with a JSON object:
{{
    "is_relevant": true/false (does this page contain information about any target item types?),
    "confidence": 0.0 to 1.0,
    "reason": "brief explanation of why this is or isn't relevant",
    "page_type": "one of: PROGRAM_PAGE, LISTING_PAGE, REQUIREMENTS_PAGE, DEADLINE_PAGE, SCHOLARSHIP_PAGE, CONFERENCE_PAGE, EXCHANGE_PAGE, GENERAL_INFO, OTHER",
    "detected_item_types": ["list of item types found on this page"],
    "content_tags": ["list of what information is available, e.g., requirements, deadlines, tuition, eligibility"],
    "priority": "HIGH, MEDIUM, or LOW based on information density and relevance",
    "has_multiple_items": true/false (does this page list multiple programs/scholarships/etc?)
}}

Guidelines:
- PROGRAM_PAGE: Specific program details (MSc, PhD, etc.)
- LISTING_PAGE: List of multiple programs/scholarships
- REQUIREMENTS_PAGE: Admission requirements, eligibility
- DEADLINE_PAGE: Application deadlines
- SCHOLARSHIP_PAGE: Scholarship/funding information
- CONFERENCE_PAGE: Conference details
- EXCHANGE_PAGE: Exchange program information
- GENERAL_INFO: General university/organization info
- OTHER: Doesn't fit other categories

Set priority to HIGH if:
- Contains specific, detailed information
- Has deadlines, requirements, or application details
- Is a primary source for the information

Set priority to MEDIUM if:
- Contains partial information
- Is a listing or overview page

Set priority to LOW if:
- Contains minimal relevant information
- Is outdated or generic"""
