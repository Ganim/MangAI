from mangai_workers.config import clear_settings_cache, get_settings


def test_worker_settings_read_environment(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("MANGAI_DATA_DIR", str(tmp_path / "worker-data"))
    monkeypatch.setenv("MANGAI_WORKER_POLL_INTERVAL_SECONDS", "5.5")
    monkeypatch.setenv("MANGAI_WORKERS_APP_NAME", "MangAI Worker Test")
    monkeypatch.setenv("MANGAI_OCR_PROVIDER", "paddleocr")
    monkeypatch.setenv("MANGAI_TRANSLATION_PROVIDER", "deepl")
    monkeypatch.setenv("MANGAI_STRICT_PROVIDER_SELECTION", "true")
    monkeypatch.setenv("MANGAI_HTTP_TIMEOUT_SECONDS", "45")
    monkeypatch.setenv(
        "MANGAI_AZURE_VISION_READ_URL",
        "https://example.cognitiveservices.azure.com/vision/v3.2/read/analyze",
    )
    monkeypatch.setenv("MANGAI_AZURE_VISION_API_KEY", "vision-key")
    monkeypatch.setenv("MANGAI_AZURE_TRANSLATOR_API_KEY", "translator-key")
    monkeypatch.setenv("MANGAI_AZURE_TRANSLATOR_REGION", "brazilsouth")
    monkeypatch.setenv("MANGAI_DEEPL_API_KEY", "deepl-key")
    clear_settings_cache()

    settings = get_settings()

    assert settings.app_name == "MangAI Worker Test"
    assert settings.data_dir == tmp_path / "worker-data"
    assert settings.poll_interval_seconds == 5.5
    assert settings.ocr_provider == "paddleocr"
    assert settings.translation_provider == "deepl"
    assert settings.strict_provider_selection is True
    assert settings.http_timeout_seconds == 45
    assert settings.azure_vision_api_key == "vision-key"
    assert settings.azure_translator_region == "brazilsouth"
    assert settings.deepl_api_key == "deepl-key"

    clear_settings_cache()
