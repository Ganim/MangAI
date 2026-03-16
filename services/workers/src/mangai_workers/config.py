from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from os import environ
from pathlib import Path


SERVICE_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = SERVICE_ROOT.parent.parent
DEFAULT_SHARED_DATA_DIR = REPO_ROOT / "services" / "api" / ".data"
DEFAULT_WORKER_CACHE_DIR = SERVICE_ROOT / ".cache"


@dataclass(frozen=True)
class WorkerSettings:
    app_name: str = "MangAI Workers"
    environment: str = "development"
    data_dir: Path = DEFAULT_SHARED_DATA_DIR
    cache_dir: Path = DEFAULT_WORKER_CACHE_DIR
    poll_interval_seconds: float = 2.0
    stalled_job_timeout_seconds: float = 30.0
    detection_provider: str = "ocr"
    ocr_provider: str = "fallback"
    translation_provider: str = "fallback"
    strict_provider_selection: bool = False
    http_timeout_seconds: float = 30.0
    comic_text_detector_model_path: Path | None = (
        DEFAULT_WORKER_CACHE_DIR / "comic-text-detector" / "comictextdetector.pt.onnx"
    )
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
    _load_local_env_file()
    data_dir = Path(environ.get("MANGAI_DATA_DIR", str(DEFAULT_SHARED_DATA_DIR)))
    cache_dir = Path(environ.get("MANGAI_WORKER_CACHE_DIR", str(DEFAULT_WORKER_CACHE_DIR)))
    poll_interval_seconds = float(environ.get("MANGAI_WORKER_POLL_INTERVAL_SECONDS", "2.0"))
    return WorkerSettings(
        app_name=environ.get("MANGAI_WORKERS_APP_NAME", "MangAI Workers"),
        environment=environ.get("MANGAI_ENVIRONMENT", "development"),
        data_dir=data_dir,
        cache_dir=cache_dir,
        poll_interval_seconds=poll_interval_seconds,
        stalled_job_timeout_seconds=float(
            environ.get("MANGAI_WORKER_STALLED_JOB_TIMEOUT_SECONDS", "30.0")
        ),
        detection_provider=environ.get("MANGAI_DETECTION_PROVIDER", "ocr").strip().lower(),
        ocr_provider=environ.get("MANGAI_OCR_PROVIDER", "fallback").strip().lower(),
        translation_provider=environ.get("MANGAI_TRANSLATION_PROVIDER", "fallback").strip().lower(),
        strict_provider_selection=environ.get("MANGAI_STRICT_PROVIDER_SELECTION", "false").strip().lower()
        in {"1", "true", "yes", "on"},
        http_timeout_seconds=float(environ.get("MANGAI_HTTP_TIMEOUT_SECONDS", "30.0")),
        comic_text_detector_model_path=_read_optional_path_env(
            "MANGAI_COMIC_TEXT_DETECTOR_MODEL_PATH",
            DEFAULT_WORKER_CACHE_DIR / "comic-text-detector" / "comictextdetector.pt.onnx",
        ),
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


def _load_local_env_file() -> None:
    env_file_override = environ.get("MANGAI_ENV_FILE")
    env_file_path = (
        Path(env_file_override).expanduser()
        if env_file_override
        else SERVICE_ROOT / ".env"
    )
    if not env_file_path.exists():
        return

    for raw_line in env_file_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if line == "" or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].strip()
        if "=" not in line:
            continue

        key, value = line.split("=", 1)
        env_key = key.strip()
        if env_key == "" or env_key in environ:
            continue

        normalized_value = value.strip()
        if len(normalized_value) >= 2 and normalized_value[0] == normalized_value[-1] and normalized_value[0] in {"'", '"'}:
            normalized_value = normalized_value[1:-1]
        environ[env_key] = normalized_value


def _read_optional_env(name: str) -> str | None:
    value = environ.get(name)
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _read_optional_path_env(name: str, default: Path | None = None) -> Path | None:
    value = _read_optional_env(name)
    if value is None:
        return default
    return Path(value).expanduser()
