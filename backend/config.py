"""
Configuration management using pydantic-settings.
Loads environment variables from .env file.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # OpenAI Configuration
    openai_api_key: str
    openai_model: str = "gpt-5.2"

    # Application Settings
    app_name: str = "ClauseFlow"
    app_version: str = "0.1.0"
    debug: bool = True

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"


# Global settings instance
settings = Settings()
