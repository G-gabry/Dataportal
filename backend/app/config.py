from pydantic_settings import BaseSettings
from typing import Optional
from functools import lru_cache
from pathlib import Path

# Get the path to the .env file in the project root (parent of backend/)
ENV_FILE = Path(__file__).resolve().parent.parent.parent / ".env"


class Settings(BaseSettings):
    # App
    APP_NAME: str = "Data Portal"
    DEBUG: bool = False

    # CORS - comma-separated list of allowed origins
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:3001"

    # Database
    DATABASE_URL: str = "postgresql://dataportal:dataportal123@localhost:5432/dataportal"
    CLOUD_SQL_CONNECTION_NAME: Optional[str] = None  # For Cloud Run: project:region:instance

    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 365  # 1 year
    ALGORITHM: str = "HS256"

    # AI Providers
    ANTHROPIC_API_KEY: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None

    # Default AI Settings
    DEFAULT_AI_PROVIDER: str = "anthropic"
    DEFAULT_AI_MODEL: str = "claude-3-5-haiku-20241022"

    # Firecrawl VM Configuration
    FIRECRAWL_API_KEY: Optional[str] = None
    FIRECRAWL_BASE_URL: str = "http://localhost:3002"
    FIRECRAWL_VM_IP: Optional[str] = None  # Fallback IP when GCP API unavailable

    # GCP Configuration for Firecrawl VM
    GCP_PROJECT_ID: str = "uniapply-486919"
    GCP_ZONE: str = "me-central1-b"
    FIRECRAWL_VM_NAME: str = "firecrawl"

    # Scraping
    MAX_URLS_PER_SOURCE: int = 1000
    SCRAPE_DELAY_MS: int = 1000
    AI_BATCH_SIZE: int = 50

    class Config:
        env_file = str(ENV_FILE)
        case_sensitive = True
        extra = "ignore"  # Ignore extra env variables not defined in Settings


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
