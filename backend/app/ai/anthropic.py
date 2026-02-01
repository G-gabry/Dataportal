import json
import time
from typing import Optional
import anthropic
from app.ai.base import AIProvider, AIResponse


class AnthropicProvider(AIProvider):
    """Anthropic Claude AI provider"""

    def __init__(self, api_key: str, model: str = "claude-3-5-haiku-20241022"):
        super().__init__(api_key, model)
        self.provider_name = "anthropic"
        self.client = anthropic.Anthropic(api_key=api_key)

    async def generate(self, prompt: str, system_prompt: str = None) -> AIResponse:
        """Generate a response from Claude"""
        start_time = time.time()

        try:
            messages = [{"role": "user", "content": prompt}]

            kwargs = {
                "model": self.model,
                "max_tokens": 4096,
                "messages": messages
            }

            if system_prompt:
                kwargs["system"] = system_prompt

            response = self.client.messages.create(**kwargs)

            latency_ms = int((time.time() - start_time) * 1000)

            content = response.content[0].text if response.content else ""

            return AIResponse(
                content=content,
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
                model=self.model,
                provider=self.provider_name,
                latency_ms=latency_ms
            )

        except Exception as e:
            return AIResponse(
                content="",
                error=str(e),
                model=self.model,
                provider=self.provider_name,
                latency_ms=int((time.time() - start_time) * 1000)
            )

    async def generate_json(self, prompt: str, system_prompt: str = None) -> AIResponse:
        """Generate a JSON response from Claude"""
        # Add JSON instruction to system prompt
        json_system = (system_prompt or "") + "\n\nYou must respond with valid JSON only. No markdown, no explanation, just the JSON object."

        response = await self.generate(prompt, json_system)

        if response.error:
            return response

        # Parse JSON from response
        try:
            # Try to extract JSON from the response
            content = response.content.strip()

            # Handle markdown code blocks
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]

            content = content.strip()
            parsed = json.loads(content)
            response.parsed_json = parsed

        except json.JSONDecodeError as e:
            response.error = f"JSON parse error: {str(e)}"

        return response
