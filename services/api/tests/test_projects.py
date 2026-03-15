from fastapi.testclient import TestClient

from mangai_api.app import create_app


def test_create_project_normalizes_languages_and_defaults_direction() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/api/v1/projects",
        json={
            "name": "My Project",
            "source_language": "ja-jp",
            "target_language": "pt-br",
        },
    )

    assert response.status_code == 201
    payload = response.json()["project"]
    assert payload["name"] == "My Project"
    assert payload["schema_version"] == 1
    assert payload["status"] == "draft"
    assert payload["source_language"] == "ja-JP"
    assert payload["target_language"] == "pt-BR"
    assert payload["target_text_direction"] == "ltr"


def test_create_project_rejects_invalid_language_tag() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/api/v1/projects",
        json={
            "name": "My Project",
            "source_language": "??",
            "target_language": "pt-BR",
        },
    )

    assert response.status_code == 422
    payload = response.json()
    assert payload["error_code"] == "INVALID_REQUEST"
