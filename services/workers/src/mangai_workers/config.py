from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from os import environ
from pathlib import Path


SERVICE_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class WorkerSettings:
    app_name: str = "MangAI Workers"
    environment: str = "development"
    data_dir: Path = SERVICE_ROOT / ".data"
    poll_interval_seconds: float = 2.0
    ocr_provider: str = "fallback"
    translation_provider: str = "fallback"
    strict_provider_selection: bool = False
    http_timeout_seconds: float = 30.0
    azure_vision_read_url: str | None = None
    azure_vision_api_key: str | None = None
    azure_vision_poll_interval_seconds: float = 1.0
    azure_translator_endpoint: str = "https://api.cognitive.microsofttranslator.com"
    azure_translator_api_key: str | None = None
    azure_translator_region: str | None = None
    deepl_api_base_url: str = "https://api-free.deepl.com/v2"
    deepl_api_key: str | None = None


@lru_cache(maxsize=1)
def get_settings() -> WorkerSettings:
    data_dir = Path(environ.get("MANGAI_DATA_DIR", str(SERVICE_ROOT / ".data")))
    poll_interval_seconds = float(environ.get("MANGAI_WORKER_POLL_INTERVAL_SECONDS", "2.0"))
    return WorkerSettings(
        app_name=environ.get("MANGAI_WORKERS_APP_NAME", "MangAI Workers"),
        environment=environ.get("MANGAI_ENVIRONMENT", "development"),
        data_dir=data_dir,
        poll_interval_seconds=poll_interval_seconds,
        ocr_provider=environ.get("MANGAI_OCR_PROVIDER", "fallback").strip().lower(),
        translation_provider=environ.get("MANGAI_TRANSLATION_PROVIDER", "fallback").strip().lower(),
        strict_provider_selection=environ.get("MANGAI_STRICT_PROVIDER_SELECTION", "false").strip().lower()
        in {"1", "true", "yes", "on"},
        http_timeout_seconds=float(environ.get("MANGAI_HTTP_TIMEOUT_SECONDS", "30.0")),
        azure_vision_read_url=_read_optional_env("MANGAI_AZURE_VISION_READ_URL"),
        azure_vision_api_key=_read_optional_env("MANGAI_AZURE_VISION_API_KEY"),
        azure_vision_poll_interval_seconds=float(
            environ.get("MANGAI_AZURE_VISION_POLL_INTERVAL_SECONDS", "1.0")
        ),
        azure_translator_endpoint=environ.get(
            "MANGAI_AZURE_TRANSLATOR_ENDPOINT",
            "https://api.cognitive.microsofttranslator.com",
        ).strip(),
        azure_translator_api_key=_read_optional_env("MANGAI_AZURE_TRANSLATOR_API_KEY"),
        azure_translator_region=_read_optional_env("MANGAI_AZURE_TRANSLATOR_REGION"),
        deepl_api_base_url=environ.get(
            "MANGAI_DEEPL_API_BASE_URL",
            "https://api-free.deepl.com/v2",
        ).strip(),
        deepl_api_key=_read_optional_env("MANGAI_DEEPL_API_KEY"),
    )


def clear_settings_cache() -> None:
    get_settings.cache_clear()


def _read_optional_env(name: str) -> str | None:
    value = environ.get(name)
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None
