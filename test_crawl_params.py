import requests
import json

CRAWL4AI_BASE_URL = "http://34.18.85.76:11235"

params_to_test = [
    ("headless", True),
    ("text_mode", True),
    ("light_mode", True),
    ("cache_mode", "enabled"),
    ("word_count_threshold", 50),
    ("excluded_tags", ["nav", "footer"]),
    ("exclude_external_images", True),
    ("wait_for_images", False),
    ("page_timeout", 30000),
]

current_payload = {
    "urls": ["https://opportunitiescorners.com/ares-belgium-scholarships"],
    "headless": True,
    "text_mode": True,
    "light_mode": True,
    "cache_mode": "enabled",
    "word_count_threshold": 50,
    "excluded_tags": ["nav", "footer", "header", "aside", "script", "style", "noscript"],
    "exclude_external_images": True,
    "wait_for_images": False,
    "page_timeout": 30000,
}

print(f"Testing URL: {current_payload['urls'][0]}...")
try:
    response = requests.post(f"{CRAWL4AI_BASE_URL}/crawl", json=current_payload, timeout=60)
    print(f"  Result: {response.status_code}")
    if response.status_code != 200:
        print(f"  Error: {response.text}")
except Exception as e:
    print(f"  Exception: {e}")
