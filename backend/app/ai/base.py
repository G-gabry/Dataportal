from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from enum import Enum


class TaskType(str, Enum):
    URL_CLASSIFICATION = "url_classification"
    CONTENT_CLASSIFICATION = "content_classification"
    EXTRACTION = "extraction"


@dataclass
class AIResponse:
    """Standard response from AI providers"""
    content: str
    parsed_json: Optional[Dict[str, Any]] = None
    input_tokens: int = 0
    output_tokens: int = 0
    model: str = ""
    provider: str = ""
    latency_ms: int = 0
    error: Optional[str] = None

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens

    @property
    def cost_usd(self) -> float:
        """Estimate cost based on model"""
        # Pricing per 1M tokens (input/output)
        pricing = {
            # Anthropic
            "claude-3-5-haiku-20241022": (0.25, 1.25),
            "claude-3-5-sonnet-20241022": (3.0, 15.0),
            # Gemini
            "gemini-1.5-flash": (0.075, 0.30),
            "gemini-1.5-pro": (1.25, 5.0),
            # OpenAI
            "gpt-4o-mini": (0.15, 0.60),
            "gpt-4o": (2.50, 10.0),
        }

        if self.model in pricing:
            input_price, output_price = pricing[self.model]
            return (self.input_tokens * input_price / 1_000_000) + \
                   (self.output_tokens * output_price / 1_000_000)
        return 0.0


@dataclass
class ClassificationResult:
    """Result of URL or content classification"""
    is_relevant: bool
    confidence: float
    reason: str
    page_type: Optional[str] = None
    detected_item_types: Optional[List[str]] = None
    content_tags: Optional[List[str]] = None
    priority: str = "MEDIUM"
    has_multiple_items: bool = False


@dataclass
class ExtractionResult:
    """Result of data extraction"""
    data: Dict[str, Any]
    confidence: float
    field_status: Dict[str, str]  # Field -> status mapping
    warnings: List[str] = None


class AIProvider(ABC):
    """Abstract base class for AI providers"""

    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model
        self.provider_name = "base"

    @abstractmethod
    async def generate(self, prompt: str, system_prompt: str = None) -> AIResponse:
        """Generate a response from the AI model"""
        pass

    @abstractmethod
    async def generate_json(self, prompt: str, system_prompt: str = None) -> AIResponse:
        """Generate a JSON response from the AI model"""
        pass

    async def classify_urls(self, urls: List[str], context: str) -> List[Dict[str, Any]]:
        """Classify a batch of URLs for relevance"""
        from app.ai.prompts.url_classification import get_url_classification_prompt

        prompt = get_url_classification_prompt(urls, context)
        response = await self.generate_json(prompt)

        if response.error:
            return [{"url": url, "is_relevant": False, "error": response.error} for url in urls]

        return response.parsed_json.get("results", [])

    async def classify_content(self, content: str, url: str, target_types: List[str]) -> ClassificationResult:
        """Classify page content"""
        from app.ai.prompts.content_classification import get_content_classification_prompt

        prompt = get_content_classification_prompt(content, url, target_types)
        response = await self.generate_json(prompt)

        if response.error or not response.parsed_json:
            return ClassificationResult(
                is_relevant=False,
                confidence=0,
                reason=response.error or "Failed to classify"
            )

        data = response.parsed_json
        return ClassificationResult(
            is_relevant=data.get("is_relevant", False),
            confidence=data.get("confidence", 0),
            reason=data.get("reason", ""),
            page_type=data.get("page_type"),
            detected_item_types=data.get("detected_item_types", []),
            content_tags=data.get("content_tags", []),
            priority=data.get("priority", "MEDIUM"),
            has_multiple_items=data.get("has_multiple_items", False)
        )

    async def extract_data(self, content: str, schema: Dict[str, Any], item_type: str) -> ExtractionResult:
        """Extract structured data from content"""
        from app.ai.prompts.extraction import get_extraction_prompt

        prompt = get_extraction_prompt(content, schema, item_type)
        response = await self.generate_json(prompt)

        if response.error or not response.parsed_json:
            return ExtractionResult(
                data={},
                confidence=0,
                field_status={},
                warnings=[response.error or "Failed to extract"]
            )

        data = response.parsed_json
        return ExtractionResult(
            data=data.get("extracted_data", {}),
            confidence=data.get("confidence", 0),
            field_status=data.get("field_status", {}),
            warnings=data.get("warnings", [])
        )
