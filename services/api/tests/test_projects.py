import base64
from pathlib import Path

from fastapi.testclient import TestClient

from mangai_api.app import create_app
from mangai_api.config import clear_settings_cache


PNG_1X1_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+lm3sAAAAASUVORK5CYII="
)


def create_project(client: TestClient, *, target_language: str = "pt-BR") -> str:
    response = client.post(
        "/api/v1/projects",
        json={
            "name": "Upload Project",
            "source_language": "ja-JP",
            "target_language": target_language,
        },
    )
    assert response.status_code == 201
    return response.json()["project"]["id"]


def upload_single_page(client: TestClient, project_id: str) -> dict:
    response = client.post(
        f"/api/v1/projects/{project_id}/pages/upload",
        files=[("files", ("001.png", PNG_1X1_BYTES, "image/png"))],
    )
    assert response.status_code == 201
    return response.json()["pages"][0]


def test_create_project_normalizes_languages_and_defaults_direction(client: TestClient) -> None:
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


def test_create_project_rejects_invalid_language_tag(client: TestClient) -> None:
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


def test_create_project_rejects_unsupported_source_language(client: TestClient) -> None:
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


def test_create_project_rejects_unsupported_target_language(client: TestClient) -> None:
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


def test_list_projects_returns_created_projects(client: TestClient) -> None:
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


def test_register_project_pages_updates_page_count(client: TestClient) -> None:
    project_id = create_project(client)

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
    assert payload["pages"][0]["original_asset_path"].endswith("/original")


def test_register_project_pages_returns_not_found(client: TestClient) -> None:
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


def test_upload_project_pages_persists_files_and_project_detail(
    client: TestClient,
    api_data_dir: Path,
) -> None:
    project_id = create_project(client)

    response = client.post(
        f"/api/v1/projects/{project_id}/pages/upload",
        files=[
            ("files", ("001.png", PNG_1X1_BYTES, "image/png")),
            ("files", ("002.webp", b"fake-webp-binary", "image/webp")),
        ],
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["project"]["page_count"] == 2
    assert len(payload["pages"]) == 2

    detail_response = client.get(f"/api/v1/projects/{project_id}")
    assert detail_response.status_code == 200
    detail_payload = detail_response.json()
    assert len(detail_payload["pages"]) == 2
    assert detail_payload["pages"][0]["file_name"] == "001.png"

    asset_response = client.get(detail_payload["pages"][0]["original_asset_path"])
    assert asset_response.status_code == 200
    assert asset_response.content == PNG_1X1_BYTES

    state_file = api_data_dir / "state.json"
    assert state_file.exists()
    assert (api_data_dir / "assets").exists()


def test_upload_project_pages_infers_png_dimensions(client: TestClient) -> None:
    project_id = create_project(client)

    response = client.post(
        f"/api/v1/projects/{project_id}/pages/upload",
        files=[("files", ("001.png", PNG_1X1_BYTES, "image/png"))],
    )

    assert response.status_code == 201
    page_payload = response.json()["pages"][0]
    assert page_payload["width"] == 1
    assert page_payload["height"] == 1

    detail_response = client.get(f"/api/v1/projects/{project_id}")
    assert detail_response.status_code == 200
    detail_page = detail_response.json()["pages"][0]
    assert detail_page["width"] == 1
    assert detail_page["height"] == 1


def test_upload_project_pages_rejects_unsupported_type(client: TestClient) -> None:
    project_id = create_project(client, target_language="en-US")

    response = client.post(
        f"/api/v1/projects/{project_id}/pages/upload",
        files=[
            ("files", ("notes.txt", b"plain-text", "text/plain")),
        ],
    )

    assert response.status_code == 422
    payload = response.json()
    assert payload["error_code"] == "INVALID_UPLOAD"


def test_page_regions_can_be_created_listed_and_updated(client: TestClient) -> None:
    project_id = create_project(client)
    page_payload = upload_single_page(client, project_id)
    page_id = page_payload["id"]

    create_response = client.post(
        f"/api/v1/projects/{project_id}/pages/{page_id}/regions",
        json={
            "type": "speech_balloon",
            "bounding_box": {
                "x": 24,
                "y": 18,
                "width": 120,
                "height": 80,
            },
        },
    )

    assert create_response.status_code == 201
    created_region = create_response.json()["region"]
    assert created_region["origin"] == "user_created"
    assert created_region["state"] == "draft"

    list_response = client.get(f"/api/v1/projects/{project_id}/pages/{page_id}/regions")
    assert list_response.status_code == 200
    listed_regions = list_response.json()["regions"]
    assert len(listed_regions) == 1
    assert listed_regions[0]["id"] == created_region["id"]

    update_response = client.patch(
        f"/api/v1/projects/{project_id}/pages/{page_id}/regions/{created_region['id']}",
        json={
            "state": "approved",
            "bounding_box": {
                "x": 30,
                "y": 22,
                "width": 132,
                "height": 88,
            },
        },
    )

    assert update_response.status_code == 200
    updated_region = update_response.json()["region"]
    assert updated_region["state"] == "approved"
    assert updated_region["bounding_box"]["x"] == 30
    assert updated_region["shape"]["points"][1]["x"] == 162


def test_update_page_region_returns_not_found_for_unknown_region(client: TestClient) -> None:
    project_id = create_project(client)
    page_payload = upload_single_page(client, project_id)
    page_id = page_payload["id"]

    response = client.patch(
        f"/api/v1/projects/{project_id}/pages/{page_id}/regions/11111111-1111-4111-8111-111111111111",
        json={"state": "reviewed"},
    )

    assert response.status_code == 404
    payload = response.json()
    assert payload["error_code"] == "REGION_NOT_FOUND"


def test_project_data_persists_across_app_restarts(
    api_data_dir: Path,
    client: TestClient,
    monkeypatch,
) -> None:
    create_response = client.post(
        "/api/v1/projects",
        json={
            "name": "Persisted Project",
            "source_language": "en-US",
            "target_language": "pt-BR",
        },
    )
    project_id = create_response.json()["project"]["id"]

    upload_response = client.post(
        f"/api/v1/projects/{project_id}/pages/upload",
        files=[("files", ("001.png", PNG_1X1_BYTES, "image/png"))],
    )
    assert upload_response.status_code == 201
    page_id = upload_response.json()["pages"][0]["id"]

    region_response = client.post(
        f"/api/v1/projects/{project_id}/pages/{page_id}/regions",
        json={
            "type": "speech_balloon",
            "bounding_box": {
                "x": 10,
                "y": 10,
                "width": 50,
                "height": 40,
            },
        },
    )
    assert region_response.status_code == 201

    monkeypatch.setenv("MANGAI_DATA_DIR", str(api_data_dir))
    clear_settings_cache()
    with TestClient(create_app()) as restarted_client:
        list_response = restarted_client.get("/api/v1/projects")
        assert list_response.status_code == 200
        assert list_response.json()["projects"][0]["name"] == "Persisted Project"

        detail_response = restarted_client.get(f"/api/v1/projects/{project_id}")
        assert detail_response.status_code == 200
        assert len(detail_response.json()["pages"]) == 1

        regions_response = restarted_client.get(
            f"/api/v1/projects/{project_id}/pages/{page_id}/regions"
        )
        assert regions_response.status_code == 200
        assert len(regions_response.json()["regions"]) == 1
