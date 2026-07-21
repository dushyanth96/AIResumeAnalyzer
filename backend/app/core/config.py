import os
from dataclasses import dataclass
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "../../../.env"))

@dataclass(frozen=True)
class Settings:
    app_env: str
    database_url: str
    embedding_dimensions: int
    cors_origins: list[str]
    enable_openai: bool
    openai_model: str
    ai_provider: str
    hf_token: str | None
    gemini_api_key: str | None

@lru_cache
def get_settings() -> Settings:
    origins = os.getenv("CORS_ORIGINS", "*")
    return Settings(
        app_env=os.getenv("APP_ENV", "development"),
        database_url=os.getenv("DATABASE_URL", "sqlite:///./phase6_analyses.db"),
        embedding_dimensions=int(os.getenv("EMBEDDING_DIMENSIONS", "128")),
        cors_origins=[origin.strip() for origin in origins.split(",")],
        enable_openai=os.getenv("ENABLE_OPENAI", "true").lower() in {"1", "true", "yes", "on"},
        openai_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        ai_provider=os.getenv("AI_PROVIDER", "gemini").lower(),
        hf_token=os.getenv("HF_TOKEN"),
        gemini_api_key=os.getenv("GEMINI_API_KEY"),
    )
