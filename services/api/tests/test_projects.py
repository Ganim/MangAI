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
    assert payload["page_count"] == 0
    assert payload["created_at"].endswith("Z")


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


def test_create_project_rejects_unsupported_source_language() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/api/v1/projects",
        json={
            "name": "My Project",
            "source_language": "pt-BR",
            "target_language": "en-US",
        },
    )

    assert response.status_code == 422
    payload = response.json()
    assert payload["error_code"] == "INVALID_REQUEST"


def test_create_project_rejects_unsupported_target_language() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/api/v1/projects",
        json={
            "name": "My Project",
            "source_language": "ja-JP",
            "target_language": "ko-KR",
        },
    )

    assert response.status_code == 422
    payload = response.json()
    assert payload["error_code"] == "INVALID_REQUEST"


def test_list_projects_returns_created_projects() -> None:
    client = TestClient(create_app())

    client.post(
        "/api/v1/projects",
        json={
            "name": "Project A",
            "source_language": "ja-JP",
            "target_language": "en-US",
        },
    )

    response = client.get("/api/v1/projects")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["projects"]) == 1
    assert payload["projects"][0]["name"] == "Project A"
    assert payload["projects"][0]["page_count"] == 0


def test_register_project_pages_updates_page_count() -> None:
    client = TestClient(create_app())

    create_response = client.post(
        "/api/v1/projects",
        json={
            "name": "Upload Project",
            "source_language": "ja-JP",
            "target_language": "pt-BR",
        },
    )
    project_id = create_response.json()["project"]["id"]

    response = client.post(
        f"/api/v1/projects/{project_id}/pages",
        json={
            "pages": [
                {
                    "file_name": "001.png",
                    "mime_type": "image/png",
                    "size_bytes": 4096,
                    "width": None,
                    "height": None,
                },
                {
                    "file_name": "002.png",
                    "mime_type": "image/png",
                    "size_bytes": 8192,
                    "width": 1600,
                    "height": 2400,
                },
            ]
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["project"]["page_count"] == 2
    assert len(payload["pages"]) == 2
    assert payload["pages"][0]["index"] == 1
    assert payload["pages"][1]["index"] == 2
    assert payload["pages"][1]["width"] == 1600


def test_register_project_pages_returns_not_found() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/api/v1/projects/11111111-1111-4111-8111-111111111111/pages",
        json={
            "pages": [
                {
                    "file_name": "001.png",
                    "mime_type": "image/png",
                    "size_bytes": 4096,
                    "width": None,
                    "height": None,
                }
            ]
        },
    )

    assert response.status_code == 404
    payload = response.json()
    assert payload["error_code"] == "PROJECT_NOT_FOUND"
