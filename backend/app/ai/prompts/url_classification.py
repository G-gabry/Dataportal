from typing import List


def get_url_classification_prompt(urls: List[str], context: str) -> str:
    """Generate prompt for batch URL classification"""

    urls_list = "\n".join([f"- {url}" for url in urls])

    return f"""Analyze these URLs and determine which ones are likely to contain relevant information.

Context: {context}

URLs to classify:
{urls_list}

For each URL, determine if it's likely to contain relevant information based on:
1. URL path structure (e.g., /admissions/, /programs/, /scholarships/)
2. Keywords in the URL
3. Common patterns for educational/academic content

Respond with a JSON object in this exact format:
{{
    "results": [
        {{
            "url": "the full URL",
            "is_relevant": true or false,
            "confidence": 0.0 to 1.0,
            "reason": "brief explanation"
        }}
    ]
}}

Only include URLs that are likely to have substantive content. Exclude:
- News/blog posts
- Faculty/staff pages
- General about pages
- Login/admin pages
- Static assets (images, PDFs, CSS, JS)
- Event calendars
- Contact pages

Be conservative - it's better to include a potentially relevant URL than to miss important content."""
