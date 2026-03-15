from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


SERVICE_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    app_name: str = Field(default="MangAI API")
    environment: str = Field(default="development")
    api_host: str = Field(default="127.0.0.1")
    api_port: int = Field(default=8000)
    api_prefix: str = Field(default="/api/v1")
    default_ui_locale: str = Field(default="en-US")
    data_dir: Path = Field(default=SERVICE_ROOT / ".data")
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


def clear_settings_cache() -> None:
    get_settings.cache_clear()
