import os
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    database_url: str = "sqlite:///./carrershunt.db"
    redis_url: str = "redis://localhost:6379/0"

    ai_provider: str = "auto"
    ai_primary_provider: str = "gemini"
    ai_fallback_enabled: bool = True
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    xai_api_key: str = ""
    xai_model: str = "grok-3-mini"
    openai_api_key: str = ""
    openai_model: str = "gpt-5.6"

    serper_api_key: str = ""
    github_token: str = ""
    github_max_repositories: int = 25

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
