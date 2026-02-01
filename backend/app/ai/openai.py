import json
import time
from typing import Optional
from openai import OpenAI
from app.ai.base import AIProvider, AIResponse


class OpenAIProvider(AIProvider):
    """OpenAI GPT AI provider"""

    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        super().__init__(api_key, model)
        self.provider_name = "openai"
        self.client = OpenAI(api_key=api_key)

    async def generate(self, prompt: str, system_prompt: str = None) -> AIResponse:
        """Generate a response from OpenAI"""
        start_time = time.time()

        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=4096
            )

            latency_ms = int((time.time() - start_time) * 1000)

            content = response.choices[0].message.content if response.choices else ""

            return AIResponse(
                content=content,
                input_tokens=response.usage.prompt_tokens if response.usage else 0,
                output_tokens=response.usage.completion_tokens if response.usage else 0,
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
        """Generate a JSON response from OpenAI"""
        start_time = time.time()

        try:
            messages = []
            json_system = (system_prompt or "") + "\n\nRespond with valid JSON only."
            messages.append({"role": "system", "content": json_system})
            messages.append({"role": "user", "content": prompt})

            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=4096,
                response_format={"type": "json_object"}
            )

            latency_ms = int((time.time() - start_time) * 1000)

            content = response.choices[0].message.content if response.choices else ""

            ai_response = AIResponse(
                content=content,
                input_tokens=response.usage.prompt_tokens if response.usage else 0,
                output_tokens=response.usage.completion_tokens if response.usage else 0,
                model=self.model,
                provider=self.provider_name,
                latency_ms=latency_ms
            )

            # Parse JSON
            try:
                ai_response.parsed_json = json.loads(content)
            except json.JSONDecodeError as e:
                ai_response.error = f"JSON parse error: {str(e)}"

            return ai_response

        except Exception as e:
            return AIResponse(
                content="",
                error=str(e),
                model=self.model,
                provider=self.provider_name,
                latency_ms=int((time.time() - start_time) * 1000)
            )
