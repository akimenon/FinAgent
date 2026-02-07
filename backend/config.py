import os
from pathlib import Path
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Base directory
    BASE_DIR: Path = Path(__file__).parent

    # Database
    DATABASE_URL: str = f"sqlite+aiosqlite:///{Path(__file__).parent / 'financial_analysis.db'}"

    # FMP API
    FMP_API_KEY: str = ""
    FMP_BASE_URL: str = "https://financialmodelingprep.com/api/v3"

    # Ollama (Local LLM)
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen2.5:14b"

    # Claude API (Deep Insights feature flag)
    ANTHROPIC_API_KEY: str = ""
    USE_CLAUDE_FOR_DEEP_INSIGHTS: bool = False

    # Tradier API (free sandbox for live options pricing)
    TRADIER_API_KEY: str = ""

    # Application
    DEBUG: bool = False
    CORS_ORIGINS: list = ["http://localhost:5173", "http://localhost:3000"]

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
