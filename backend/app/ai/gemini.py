import json
import time
from typing import Optional
import google.generativeai as genai
from app.ai.base import AIProvider, AIResponse


class GeminiProvider(AIProvider):
    """Google Gemini AI provider"""

    def __init__(self, api_key: str, model: str = "gemini-1.5-flash"):
        super().__init__(api_key, model)
        self.provider_name = "gemini"
        genai.configure(api_key=api_key)
        self.client = genai.GenerativeModel(model)

    async def generate(self, prompt: str, system_prompt: str = None) -> AIResponse:
        """Generate a response from Gemini"""
        start_time = time.time()

        try:
            full_prompt = prompt
            if system_prompt:
                full_prompt = f"{system_prompt}\n\n{prompt}"

            response = self.client.generate_content(full_prompt)

            latency_ms = int((time.time() - start_time) * 1000)

            # Estimate tokens (Gemini doesn't always provide this)
            input_tokens = len(full_prompt.split()) * 1.3  # rough estimate
            output_tokens = len(response.text.split()) * 1.3 if response.text else 0

            return AIResponse(
                content=response.text if response.text else "",
                input_tokens=int(input_tokens),
                output_tokens=int(output_tokens),
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
        """Generate a JSON response from Gemini"""
        json_system = (system_prompt or "") + "\n\nRespond with valid JSON only. No markdown, no explanation."

        response = await self.generate(prompt, json_system)

        if response.error:
            return response

        try:
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
