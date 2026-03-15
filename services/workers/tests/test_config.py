from mangai_workers.config import clear_settings_cache, get_settings


def test_worker_settings_read_environment(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("MANGAI_DATA_DIR", str(tmp_path / "worker-data"))
    monkeypatch.setenv("MANGAI_WORKER_POLL_INTERVAL_SECONDS", "5.5")
    monkeypatch.setenv("MANGAI_WORKERS_APP_NAME", "MangAI Worker Test")
    clear_settings_cache()

    settings = get_settings()

    assert settings.app_name == "MangAI Worker Test"
    assert settings.data_dir == tmp_path / "worker-data"
    assert settings.poll_interval_seconds == 5.5

    clear_settings_cache()
