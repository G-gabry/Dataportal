"""
pipeline/step7_save.py — Save final items to JSON (grouped by type) and CSV.

CSV: list fields joined with "; " separator.
JSON: full structure grouped by item_type with run metadata.
"""

import csv
import json
from datetime import datetime
from pathlib import Path
from typing import List

from config import OUTPUT_DIR
from utils.logger import get_logger

log = get_logger("step7_save")

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def _flatten_for_csv(item: dict) -> dict:
    """Flatten item + data into one dict for CSV, joining lists with '; '."""
    row = {
        "item_type": item.get("item_type", ""),
        "classification_method": item.get("classification_method", ""),
    }
    data = item.get("data", {})
    for k, v in data.items():
        if isinstance(v, list):
            row[k] = "; ".join(str(x) for x in v if x)
        elif v is None:
            row[k] = ""
        else:
            row[k] = str(v)
    return row


def _collect_csv_headers(items: List[dict]) -> List[str]:
    """Collect all unique field names across all items for CSV header."""
    seen = ["item_type", "classification_method"]
    for item in items:
        for k in item.get("data", {}).keys():
            if k not in seen:
                seen.append(k)
    return seen


def run(items: List[dict], summary: dict, run_id: str) -> dict:
    """
    Step 7: Save output as JSON + CSV.

    Returns:
        {"json_path": ..., "csv_path": ...}
    """
    log.info(f"=== STEP 7: SAVE ({len(items)} items) ===")

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Group by type for JSON
    grouped: dict = {"SCHOLARSHIP": [], "PROGRAM": [], "CONFERENCE": [], "EXCHANGE": [], "OTHER": []}
    for item in items:
        t = item.get("item_type", "OTHER")
        grouped.setdefault(t, []).append(item)

    output = {
        "run_id": run_id,
        "generated_at": ts,
        "summary": summary,
        "counts": {t: len(v) for t, v in grouped.items() if v},
        "items": {t: v for t, v in grouped.items() if v},
    }

    # JSON output
    json_path = OUTPUT_DIR / f"items_{ts}.json"
    json_path.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
    log.info(f"JSON saved: {json_path}")

    # CSV output
    csv_path = OUTPUT_DIR / f"items_{ts}.csv"
    headers = _collect_csv_headers(items)
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers, extrasaction="ignore")
        writer.writeheader()
        for item in items:
            writer.writerow(_flatten_for_csv(item))
    log.info(f"CSV saved: {csv_path}")

    return {"json_path": str(json_path), "csv_path": str(csv_path)}
