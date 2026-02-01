from typing import Optional
from sqlalchemy.orm import Session
from app.ai.base import AIProvider, TaskType
from app.ai.anthropic import AnthropicProvider
from app.ai.gemini import GeminiProvider
from app.ai.openai import OpenAIProvider
from app.ai.mock import MockAIProvider
from app.config import settings
from app.models.setting import Setting


class AIProviderFactory:
    """Factory for creating AI providers based on configuration"""

    _providers = {
        "anthropic": AnthropicProvider,
        "gemini": GeminiProvider,
        "openai": OpenAIProvider,
        "mock": MockAIProvider
    }

    @classmethod
    def get_api_key(cls, provider: str) -> Optional[str]:
        """Get API key for a provider"""
        key_map = {
            "anthropic": settings.ANTHROPIC_API_KEY,
            "gemini": settings.GEMINI_API_KEY,
            "openai": settings.OPENAI_API_KEY,
            "mock": "mock"  # Mock provider doesn't need a real key
        }
        return key_map.get(provider)

    @classmethod
    def create(cls, provider: str, model: str) -> AIProvider:
        """Create an AI provider instance"""
        if provider not in cls._providers:
            raise ValueError(f"Unknown provider: {provider}")

        api_key = cls.get_api_key(provider)
        if not api_key:
            # Fall back to mock provider if no API key
            print(f"No API key for {provider}, using mock provider")
            return MockAIProvider()

        provider_class = cls._providers[provider]
        return provider_class(api_key=api_key, model=model)

    @classmethod
    def from_config(cls, db: Session, task_type: TaskType = None) -> AIProvider:
        """Create an AI provider from database configuration"""
        # Get AI config from database
        setting = db.query(Setting).filter(Setting.key == "ai_config").first()

        if not setting:
            # Fall back to environment defaults or mock
            try:
                return cls.create(
                    settings.DEFAULT_AI_PROVIDER,
                    settings.DEFAULT_AI_MODEL
                )
            except ValueError:
                return MockAIProvider()

        config = setting.value

        # If task type specified, use task-specific config
        if task_type and task_type.value in config.get("task_config", {}):
            task_config = config["task_config"][task_type.value]
            provider = task_config.get("provider", config["default_provider"])
            model = task_config.get("model", config["default_model"])
        else:
            provider = config.get("default_provider", settings.DEFAULT_AI_PROVIDER)
            model = config.get("default_model", settings.DEFAULT_AI_MODEL)

        try:
            return cls.create(provider, model)
        except ValueError:
            # Fall back to mock if API key not available
            return MockAIProvider()


def get_ai_provider(db: Session, task_type: TaskType = None) -> AIProvider:
    """Convenience function to get AI provider"""
    return AIProviderFactory.from_config(db, task_type)
