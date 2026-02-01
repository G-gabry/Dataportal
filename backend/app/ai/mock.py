"""Mock AI provider for testing without API keys"""
from typing import List, Dict, Any
from app.ai.base import AIProvider, ClassificationResult, ExtractionResult


class MockAIProvider(AIProvider):
    """Mock AI provider that returns sample data for testing"""

    def __init__(self, **kwargs):
        self.provider_name = "mock"
        self.model = "mock-model"

    async def generate(self, prompt: str, system_prompt: str = None):
        """Return mock response"""
        from app.ai.base import AIResponse
        return AIResponse(
            content="Mock response",
            parsed_json=None,
            input_tokens=len(prompt),
            output_tokens=100,
            model=self.model,
            provider=self.provider_name
        )

    async def generate_json(self, prompt: str, system_prompt: str = None):
        """Return mock JSON response"""
        from app.ai.base import AIResponse
        return AIResponse(
            content="{}",
            parsed_json={},
            input_tokens=len(prompt),
            output_tokens=100,
            model=self.model,
            provider=self.provider_name
        )

    async def classify_urls(self, urls: List[str], context: str) -> List[Dict[str, Any]]:
        """Classify URLs - mark most as relevant for testing"""
        results = []
        for url in urls:
            url_lower = url.lower()
            # Mark URLs with keywords as relevant - be more lenient for testing
            is_relevant = any(kw in url_lower for kw in [
                'program', 'master', 'phd', 'admission', 'scholarship',
                'fellowship', 'exchange', 'international', 'graduate',
                'degree', 'course', 'study', 'conference', 'research',
                'financial', 'aid', 'tuition', 'apply', 'requirement'
            ])
            # Also mark root admission/program pages as relevant
            if any(path in url_lower for path in ['/admissions', '/programs', '/financial-aid']):
                is_relevant = True

            print(f"[Mock AI] Classifying URL: {url} -> relevant={is_relevant}")

            results.append({
                "url": url,
                "is_relevant": is_relevant,
                "confidence": 0.85 if is_relevant else 0.15,
                "reason": "Contains relevant keywords" if is_relevant else "Not relevant"
            })
        return results

    async def classify_content(
        self,
        content: str,
        url: str,
        target_types: List[str]
    ) -> ClassificationResult:
        """Classify content type"""
        url_lower = url.lower()
        content_lower = content.lower()

        # Detect types based on URL and content
        detected_types = []
        if any(kw in url_lower or kw in content_lower for kw in ['program', 'master', 'phd', 'degree', 'curriculum']):
            detected_types.append("PROGRAM")
        if any(kw in url_lower or kw in content_lower for kw in ['scholarship', 'fellowship', 'financial', 'award', 'grant']):
            detected_types.append("SCHOLARSHIP")
        if any(kw in url_lower or kw in content_lower for kw in ['conference', 'symposium', 'workshop', 'summit']):
            detected_types.append("CONFERENCE")
        if any(kw in url_lower or kw in content_lower for kw in ['exchange', 'abroad', 'erasmus', 'mobility']):
            detected_types.append("EXCHANGE")

        # Filter to target types
        detected_types = [t for t in detected_types if t in target_types] or []

        # Determine page type
        if 'list' in url_lower or len(detected_types) > 1:
            page_type = "listing"
        elif detected_types:
            page_type = "detail"
        else:
            page_type = "general"

        return ClassificationResult(
            is_relevant=bool(detected_types),
            confidence=0.8,
            reason="Mock classification based on keywords",
            page_type=page_type,
            detected_item_types=detected_types,
            has_multiple_items=page_type == "listing",
            content_tags=["education", "academic"],
            priority="HIGH" if detected_types else "LOW"
        )

    async def extract_data(
        self,
        content: str,
        schema: Dict[str, Any],
        item_type: str
    ) -> ExtractionResult:
        """Extract structured data from content"""
        # Parse markdown content to extract data
        lines = content.split('\n')
        data = {}

        # Extract title from first heading
        for line in lines:
            if line.startswith('# '):
                if item_type == "PROGRAM":
                    data["program_name"] = line[2:].strip()
                elif item_type == "SCHOLARSHIP":
                    data["scholarship_name"] = line[2:].strip()
                elif item_type == "CONFERENCE":
                    data["conference_name"] = line[2:].strip()
                elif item_type == "EXCHANGE":
                    data["name"] = line[2:].strip()
                break

        # Extract some common fields
        content_lower = content.lower()

        # Duration
        if "2 years" in content_lower or "2-year" in content_lower:
            data["duration_months"] = 24
        elif "1 year" in content_lower or "1-year" in content_lower:
            data["duration_months"] = 12
        elif "4 years" in content_lower:
            data["duration_months"] = 48

        # GPA
        if "gpa" in content_lower:
            import re
            gpa_match = re.search(r'gpa[:\s]+(\d+\.?\d*)', content_lower)
            if gpa_match:
                data["gpa_minimum"] = float(gpa_match.group(1))

        # Deadlines
        import re
        deadline_match = re.search(r'deadline[:\s]+(january|february|march|april|may|june|july|august|september|october|november|december)\s+\d+', content_lower)
        if deadline_match:
            data["deadline"] = deadline_match.group(0).replace("deadline:", "").strip()

        # Tuition/Amount
        amount_match = re.search(r'\$[\d,]+', content)
        if amount_match:
            amount_str = amount_match.group(0).replace('$', '').replace(',', '')
            if item_type == "SCHOLARSHIP":
                data["amount_usd"] = int(amount_str)
            elif item_type == "PROGRAM":
                data["tuition_usd"] = int(amount_str)

        # Description - first paragraph after title
        for i, line in enumerate(lines):
            if line.startswith('## ') and i + 1 < len(lines):
                desc_lines = []
                for j in range(i + 1, min(i + 5, len(lines))):
                    if lines[j].startswith('#') or not lines[j].strip():
                        break
                    desc_lines.append(lines[j])
                if desc_lines:
                    data["description"] = ' '.join(desc_lines).strip()
                break

        # Field status - mark all as extracted
        field_status = {k: "EXTRACTED" for k in data.keys()}

        return ExtractionResult(
            data=data,
            field_status=field_status,
            confidence=0.75,
            warnings=["Mock extraction - review required"]
        )
