from fastapi.testclient import TestClient

from mangai_api.app import create_app


def test_system_meta_exposes_schema_and_locales() -> None:
    client = TestClient(create_app())

    response = client.get("/api/v1/system/meta")

    assert response.status_code == 200
    payload = response.json()
    assert payload["schema_version"] == 1
    assert payload["supported_ui_locales"] == ["en-US", "pt-BR"]
    assert payload["supported_text_directions"] == ["ltr", "rtl", "ttb"]
