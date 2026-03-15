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


@lru_cache(maxsize=1)
def get_settings() -> WorkerSettings:
    data_dir = Path(environ.get("MANGAI_DATA_DIR", str(SERVICE_ROOT / ".data")))
    poll_interval_seconds = float(environ.get("MANGAI_WORKER_POLL_INTERVAL_SECONDS", "2.0"))
    return WorkerSettings(
        app_name=environ.get("MANGAI_WORKERS_APP_NAME", "MangAI Workers"),
        environment=environ.get("MANGAI_ENVIRONMENT", "development"),
        data_dir=data_dir,
        poll_interval_seconds=poll_interval_seconds,
    )


def clear_settings_cache() -> None:
    get_settings.cache_clear()
