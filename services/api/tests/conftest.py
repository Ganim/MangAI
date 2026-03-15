from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from mangai_api.app import create_app
from mangai_api.config import clear_settings_cache


@pytest.fixture()
def api_data_dir(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    data_dir = tmp_path / "api-data"
    monkeypatch.setenv("MANGAI_DATA_DIR", str(data_dir))
    clear_settings_cache()
    yield data_dir
    clear_settings_cache()


@pytest.fixture()
def client(api_data_dir: Path) -> TestClient:
    with TestClient(create_app()) as test_client:
        yield test_client
