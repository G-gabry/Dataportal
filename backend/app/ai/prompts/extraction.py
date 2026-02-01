from typing import Dict, Any
import json


def get_extraction_prompt(content: str, schema: Dict[str, Any], item_type: str) -> str:
    """Generate prompt for data extraction"""

    # Truncate content if too long
    max_content_length = 10000
    if len(content) > max_content_length:
        content = content[:max_content_length] + "\n\n[Content truncated...]"

    # Format schema fields for the prompt
    fields = schema.get("fields", {})
    fields_description = []
    for field_name, field_info in fields.items():
        field_type = field_info.get("type", "string")
        required = field_info.get("required", False)
        description = field_info.get("description", "")
        options = field_info.get("options", [])

        field_desc = f"- {field_name} ({field_type})"
        if required:
            field_desc += " [REQUIRED]"
        if description:
            field_desc += f": {description}"
        if options:
            field_desc += f" Options: {', '.join(options)}"

        fields_description.append(field_desc)

    fields_str = "\n".join(fields_description)

    return f"""Extract structured information from this webpage content.

Item Type: {item_type}

Fields to extract:
{fields_str}

Page content:
---
{content}
---

Extract all available information and respond with a JSON object:
{{
    "extracted_data": {{
        "field_name": "extracted value or null if not found"
    }},
    "confidence": 0.0 to 1.0 (overall extraction confidence),
    "field_status": {{
        "field_name": "EXTRACTED" | "NOT_AVAILABLE" | "UNKNOWN"
    }},
    "warnings": ["list of any issues or uncertainties"]
}}

Guidelines:
- Extract exact values when possible
- Use null for fields not found on the page
- Mark field_status as:
  - "EXTRACTED": Value was found and extracted
  - "NOT_AVAILABLE": The page explicitly states this info is not applicable
  - "UNKNOWN": Could not determine if the info exists
- For dates, use ISO format (YYYY-MM-DD)
- For currency, convert to USD if possible, or note original currency
- For arrays, include all items found
- For boolean fields, infer from context if not explicitly stated
- Include warnings for:
  - Uncertain extractions
  - Conflicting information
  - Values that seem outdated
  - Partial information

Be thorough but accurate - it's better to mark something as UNKNOWN than to extract incorrect information."""
