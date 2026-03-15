from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = Field(default="MangAI API")
    environment: str = Field(default="development")
    api_host: str = Field(default="127.0.0.1")
    api_port: int = Field(default=8000)
    api_prefix: str = Field(default="/api/v1")
    default_ui_locale: str = Field(default="en-US")
    cors_allowed_origins: tuple[str, ...] = Field(
        default=("http://127.0.0.1:3000", "http://localhost:3000"),
    )

    model_config = SettingsConfigDict(
        env_prefix="MANGAI_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
