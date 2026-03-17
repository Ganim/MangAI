import base64
from pathlib import Path

from fastapi.testclient import TestClient

from mangai_api.app import create_app
from mangai_api.config import clear_settings_cache


PNG_1X1_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+lm3sAAAAASUVORK5CYII="
)


def create_project(
    client: TestClient,
    *,
    source_language: str = "ja-JP",
    target_language: str = "pt-BR",
    reading_profile: str | None = None,
) -> str:
    payload = {
        "name": "Upload Project",
        "source_language": source_language,
        "target_language": target_language,
    }
    if reading_profile is not None:
        payload["reading_profile"] = reading_profile

    response = client.post(
        "/api/v1/projects",
        json=payload,
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


def create_region(client: TestClient, project_id: str, page_id: str) -> dict:
    response = client.post(
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
    assert response.status_code == 201
    return response.json()["region"]


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
    assert payload["reading_profile"] == "manga"
    assert payload["target_language"] == "pt-BR"
    assert payload["target_text_direction"] == "ltr"
    assert payload["page_count"] == 0
    assert payload["created_at"].endswith("Z")


def test_create_project_defaults_manhwa_profile_for_korean_source(client: TestClient) -> None:
    response = client.post(
        "/api/v1/projects",
        json={
            "name": "Korean Project",
            "source_language": "ko-KR",
            "target_language": "pt-BR",
        },
    )

    assert response.status_code == 201
    payload = response.json()["project"]
    assert payload["source_language"] == "ko-KR"
    assert payload["reading_profile"] == "manhwa"


def test_create_project_accepts_explicit_reading_profile(client: TestClient) -> None:
    response = client.post(
        "/api/v1/projects",
        json={
            "name": "Explicit Reading",
            "source_language": "ja-JP",
            "reading_profile": "manhwa",
            "target_language": "pt-BR",
        },
    )

    assert response.status_code == 201
    payload = response.json()["project"]
    assert payload["reading_profile"] == "manhwa"


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
    assert payload["projects"][0]["reading_profile"] == "manga"


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
    assert detail_page["active_cleaned_asset_path"] is None


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

    created_region = create_region(client, project_id, page_id)
    assert created_region["origin"] == "user_created"
    assert created_region["state"] == "draft"
    assert created_region["text_area"]["width"] == created_region["bounding_box"]["width"]
    assert created_region["context_area"]["width"] == created_region["bounding_box"]["width"]
    assert created_region["panel_area"]["width"] == created_region["bounding_box"]["width"]
    assert created_region["panel_order"] is None
    assert created_region["balloon_group_order"] is None
    assert created_region["order_in_balloon_group"] is None
    assert created_region["order_in_panel"] is None
    assert created_region["global_reading_order"] is None

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
    assert updated_region["text_area"]["x"] == 30
    assert updated_region["context_area"]["x"] == 30
    assert updated_region["panel_area"]["x"] == 30
    assert updated_region["shape"]["points"][1]["x"] == 162

    split_update_response = client.patch(
        f"/api/v1/projects/{project_id}/pages/{page_id}/regions/{created_region['id']}",
        json={
            "text_area": {
                "x": 36,
                "y": 28,
                "width": 110,
                "height": 92,
            },
            "context_area": {
                "x": 12,
                "y": 10,
                "width": 188,
                "height": 154,
            },
        },
    )

    assert split_update_response.status_code == 200
    split_updated_region = split_update_response.json()["region"]
    assert split_updated_region["bounding_box"]["x"] == 36
    assert split_updated_region["text_area"]["x"] == 36
    assert split_updated_region["context_area"]["x"] == 12
    assert split_updated_region["panel_area"]["x"] == 12
    assert split_updated_region["shape"]["points"][1]["x"] == 146


def test_reset_page_regions_clears_regions_and_pending_region_jobs(client: TestClient) -> None:
    project_id = create_project(client)
    page_payload = upload_single_page(client, project_id)
    page_id = page_payload["id"]

    create_region(client, project_id, page_id)
    create_region(client, project_id, page_id)

    job_response = client.post(
        f"/api/v1/projects/{project_id}/pages/{page_id}/jobs",
        json={"type": "detect_regions"},
    )
    assert job_response.status_code == 201

    reset_response = client.post(
        f"/api/v1/projects/{project_id}/pages/{page_id}/regions/reset"
    )

    assert reset_response.status_code == 200
    assert reset_response.json()["regions"] == []

    regions_response = client.get(f"/api/v1/projects/{project_id}/pages/{page_id}/regions")
    jobs_response = client.get(f"/api/v1/projects/{project_id}/pages/{page_id}/jobs")
    detail_response = client.get(f"/api/v1/projects/{project_id}")

    assert regions_response.status_code == 200
    assert jobs_response.status_code == 200
    assert detail_response.status_code == 200
    assert regions_response.json()["regions"] == []
    assert jobs_response.json()["jobs"] == []
    assert detail_response.json()["pages"][0]["status"] == "uploaded"


def test_page_regions_can_override_reading_order_manually(client: TestClient) -> None:
    project_id = create_project(client)
    page_payload = upload_single_page(client, project_id)
    page_id = page_payload["id"]

    first_region = create_region(client, project_id, page_id)
    second_region = create_region(client, project_id, page_id)

    reorder_response = client.patch(
        f"/api/v1/projects/{project_id}/pages/{page_id}/regions/{second_region['id']}",
        json={
            "global_reading_order": 1,
        },
    )

    assert reorder_response.status_code == 200
    reordered_region = reorder_response.json()["region"]
    assert reordered_region["id"] == second_region["id"]
    assert reordered_region["global_reading_order"] == 1

    list_response = client.get(f"/api/v1/projects/{project_id}/pages/{page_id}/regions")
    assert list_response.status_code == 200
    listed_regions = list_response.json()["regions"]
    assert [region["id"] for region in listed_regions] == [second_region["id"], first_region["id"]]
    assert [region["global_reading_order"] for region in listed_regions] == [1, 2]


def test_page_mask_revisions_can_be_created_listed_and_updated(client: TestClient) -> None:
    project_id = create_project(client)
    page_payload = upload_single_page(client, project_id)
    page_id = page_payload["id"]
    region = create_region(client, project_id, page_id)

    create_response = client.post(
        f"/api/v1/projects/{project_id}/pages/{page_id}/mask-revisions",
        json={
            "region_id": region["id"],
            "shape": region["shape"],
        },
    )

    assert create_response.status_code == 201
    created_mask_revision = create_response.json()["mask_revision"]
    assert created_mask_revision["region_id"] == region["id"]
    assert created_mask_revision["version"] == 1
    assert created_mask_revision["is_active"] is True
    assert created_mask_revision["approved"] is False

    list_response = client.get(
        f"/api/v1/projects/{project_id}/pages/{page_id}/mask-revisions"
    )
    assert list_response.status_code == 200
    listed_mask_revisions = list_response.json()["mask_revisions"]
    assert len(listed_mask_revisions) == 1
    assert listed_mask_revisions[0]["id"] == created_mask_revision["id"]

    update_response = client.patch(
        f"/api/v1/projects/{project_id}/pages/{page_id}/mask-revisions/{created_mask_revision['id']}",
        json={"approved": True},
    )
    assert update_response.status_code == 200
    updated_mask_revision = update_response.json()["mask_revision"]
    assert updated_mask_revision["approved"] is True
    assert updated_mask_revision["shape"]["points"][1]["x"] == region["shape"]["points"][1]["x"]

    detail_response = client.get(f"/api/v1/projects/{project_id}")
    assert detail_response.status_code == 200
    detail_page = detail_response.json()["pages"][0]
    assert detail_page["status"] == "cleanup_ready"
    assert detail_page["active_cleaned_asset_path"] is None


def test_page_jobs_can_be_queued_and_listed(client: TestClient) -> None:
    project_id = create_project(client)
    page_payload = upload_single_page(client, project_id)
    page_id = page_payload["id"]

    create_response = client.post(
        f"/api/v1/projects/{project_id}/pages/{page_id}/jobs",
        json={"type": "detect_regions"},
    )

    assert create_response.status_code == 201
    job = create_response.json()["job"]
    assert job["type"] == "detect_regions"
    assert job["status"] == "queued"
    assert job["page_id"] == page_id
    assert job["payload"]["job_id"] == job["id"]
    assert job["payload"]["page_id"] == page_id
    assert job["result"] is None

    list_response = client.get(f"/api/v1/projects/{project_id}/pages/{page_id}/jobs")
    assert list_response.status_code == 200
    jobs = list_response.json()["jobs"]
    assert len(jobs) == 1
    assert jobs[0]["id"] == job["id"]


def test_page_jobs_reuse_pending_job_of_same_type(client: TestClient) -> None:
    project_id = create_project(client)
    page_payload = upload_single_page(client, project_id)
    page_id = page_payload["id"]

    first_response = client.post(
        f"/api/v1/projects/{project_id}/pages/{page_id}/jobs",
        json={"type": "detect_regions"},
    )
    second_response = client.post(
        f"/api/v1/projects/{project_id}/pages/{page_id}/jobs",
        json={"type": "detect_regions"},
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 201
    assert second_response.json()["job"]["id"] == first_response.json()["job"]["id"]

    list_response = client.get(f"/api/v1/projects/{project_id}/pages/{page_id}/jobs")
    assert list_response.status_code == 200
    assert len(list_response.json()["jobs"]) == 1


def test_run_ocr_job_requires_candidate_regions(client: TestClient) -> None:
    project_id = create_project(client)
    page_payload = upload_single_page(client, project_id)
    page_id = page_payload["id"]

    response = client.post(
        f"/api/v1/projects/{project_id}/pages/{page_id}/jobs",
        json={"type": "run_ocr"},
    )

    assert response.status_code == 422
    payload = response.json()
    assert payload["error_code"] == "INVALID_JOB_REQUEST"


def test_run_ocr_job_can_be_queued_with_candidate_regions(client: TestClient) -> None:
    project_id = create_project(client)
    page_payload = upload_single_page(client, project_id)
    page_id = page_payload["id"]
    region = create_region(client, project_id, page_id)

    response = client.post(
        f"/api/v1/projects/{project_id}/pages/{page_id}/jobs",
        json={"type": "run_ocr"},
    )

    assert response.status_code == 201
    job = response.json()["job"]
    assert job["type"] == "run_ocr"
    assert job["payload"]["page_id"] == page_id
    assert job["payload"]["region_ids"] == [region["id"]]
    assert job["payload"]["source_language"] == "ja-JP"


def test_generate_cleanup_job_requires_approved_active_mask_revision(client: TestClient) -> None:
    project_id = create_project(client)
    page_payload = upload_single_page(client, project_id)
    page_id = page_payload["id"]
    region = create_region(client, project_id, page_id)

    mask_response = client.post(
        f"/api/v1/projects/{project_id}/pages/{page_id}/mask-revisions",
        json={
            "region_id": region["id"],
            "shape": region["shape"],
        },
    )
    assert mask_response.status_code == 201

    cleanup_response = client.post(
        f"/api/v1/projects/{project_id}/pages/{page_id}/jobs",
        json={"type": "generate_cleanup"},
    )

    assert cleanup_response.status_code == 422
    payload = cleanup_response.json()
    assert payload["error_code"] == "INVALID_JOB_REQUEST"


def test_generate_cleanup_job_can_be_queued_with_approved_active_mask_revision(
    client: TestClient,
) -> None:
    project_id = create_project(client)
    page_payload = upload_single_page(client, project_id)
    page_id = page_payload["id"]
    region = create_region(client, project_id, page_id)

    mask_response = client.post(
        f"/api/v1/projects/{project_id}/pages/{page_id}/mask-revisions",
        json={
            "region_id": region["id"],
            "shape": region["shape"],
        },
    )
    assert mask_response.status_code == 201
    mask_revision = mask_response.json()["mask_revision"]

    approve_response = client.patch(
        f"/api/v1/projects/{project_id}/pages/{page_id}/mask-revisions/{mask_revision['id']}",
        json={"approved": True},
    )
    assert approve_response.status_code == 200

    cleanup_response = client.post(
        f"/api/v1/projects/{project_id}/pages/{page_id}/jobs",
        json={"type": "generate_cleanup"},
    )

    assert cleanup_response.status_code == 201
    job = cleanup_response.json()["job"]
    assert job["type"] == "generate_cleanup"
    assert job["payload"]["page_id"] == page_id
    assert job["payload"]["source_asset_id"]
    assert job["payload"]["region_ids"] == [region["id"]]
    assert job["payload"]["mask_revision_ids"] == [mask_revision["id"]]


def test_manual_text_flow_persists_dialogues_translations_assignments_and_placements(
    client: TestClient,
) -> None:
    project_id = create_project(client)
    page_payload = upload_single_page(client, project_id)
    page_id = page_payload["id"]
    region = create_region(client, project_id, page_id)

    create_dialogue_response = client.post(
        f"/api/v1/projects/{project_id}/pages/{page_id}/dialogues",
        json={
            "page_id": page_id,
            "content": "Original line",
            "source_language": "ja-JP",
            "reading_order": 1,
        },
    )
    assert create_dialogue_response.status_code == 201
    dialogue = create_dialogue_response.json()["dialogue"]
    assert dialogue["source"] == "manual"

    update_dialogue_response = client.put(
        f"/api/v1/projects/{project_id}/pages/{page_id}/dialogues/{dialogue['id']}",
        json={
            "page_id": page_id,
            "content": "Original line updated",
            "source_language": "ja-JP",
            "reading_order": 1,
        },
    )
    assert update_dialogue_response.status_code == 200
    assert update_dialogue_response.json()["dialogue"]["content"] == "Original line updated"

    translation_response = client.put(
        f"/api/v1/projects/{project_id}/pages/{page_id}/translations",
        json={
            "dialogue_id": dialogue["id"],
            "target_language": "pt-BR",
            "text_direction": "ltr",
            "content": "Linha traduzida",
            "status": "approved",
        },
    )
    assert translation_response.status_code == 200
    translation = translation_response.json()["translation"]
    assert translation["provider"] == "manual"
    assert translation["edited_by_user"] is True

    assignment_response = client.put(
        f"/api/v1/projects/{project_id}/pages/{page_id}/assignments",
        json={
            "dialogue_id": dialogue["id"],
            "region_id": region["id"],
            "origin": "manual",
            "approved": True,
        },
    )
    assert assignment_response.status_code == 200
    assignment = assignment_response.json()["assignment"]
    assert assignment["region_id"] == region["id"]

    placement_response = client.put(
        f"/api/v1/projects/{project_id}/pages/{page_id}/placements",
        json={
            "assignment_id": assignment["id"],
            "text_box": region["bounding_box"],
            "style": {
                "font_family": "Komika",
                "font_fallbacks": ["Arial"],
                "font_size": 24,
                "leading": 28,
                "tracking": 0,
                "alignment": "center",
                "direction": "ltr",
                "rotation": 0,
                "fill": "#000000",
            },
        },
    )
    assert placement_response.status_code == 200
    placement = placement_response.json()["placement"]
    assert placement["assignment_id"] == assignment["id"]
    assert placement["layout_metrics"]["mode"] == "manual"

    dialogues_response = client.get(f"/api/v1/projects/{project_id}/pages/{page_id}/dialogues")
    translations_response = client.get(
        f"/api/v1/projects/{project_id}/pages/{page_id}/translations"
    )
    assignments_response = client.get(
        f"/api/v1/projects/{project_id}/pages/{page_id}/assignments"
    )
    placements_response = client.get(
        f"/api/v1/projects/{project_id}/pages/{page_id}/placements"
    )

    assert dialogues_response.status_code == 200
    assert translations_response.status_code == 200
    assert assignments_response.status_code == 200
    assert placements_response.status_code == 200
    assert len(dialogues_response.json()["dialogues"]) == 1
    assert len(translations_response.json()["translations"]) == 1
    assert len(assignments_response.json()["assignments"]) == 1
    assert len(placements_response.json()["placements"]) == 1

    detail_response = client.get(f"/api/v1/projects/{project_id}")
    assert detail_response.status_code == 200
    detail_page = detail_response.json()["pages"][0]
    assert detail_page["status"] == "typeset_ready"


def test_delete_page_region_removes_related_masks_assignments_and_placements(
    client: TestClient,
) -> None:
    project_id = create_project(client)
    page_payload = upload_single_page(client, project_id)
    page_id = page_payload["id"]
    region = create_region(client, project_id, page_id)

    mask_response = client.post(
        f"/api/v1/projects/{project_id}/pages/{page_id}/mask-revisions",
        json={
            "region_id": region["id"],
            "shape": region["shape"],
        },
    )
    assert mask_response.status_code == 201

    dialogue_response = client.post(
        f"/api/v1/projects/{project_id}/pages/{page_id}/dialogues",
        json={
            "page_id": page_id,
            "content": "Manual line",
            "source_language": "ja-JP",
            "reading_order": 1,
        },
    )
    assert dialogue_response.status_code == 201
    dialogue = dialogue_response.json()["dialogue"]

    translation_response = client.put(
        f"/api/v1/projects/{project_id}/pages/{page_id}/translations",
        json={
            "dialogue_id": dialogue["id"],
            "target_language": "pt-BR",
            "text_direction": "ltr",
            "content": "Linha manual",
            "status": "approved",
        },
    )
    assert translation_response.status_code == 200

    assignment_response = client.put(
        f"/api/v1/projects/{project_id}/pages/{page_id}/assignments",
        json={
            "dialogue_id": dialogue["id"],
            "region_id": region["id"],
            "origin": "manual",
            "approved": True,
        },
    )
    assert assignment_response.status_code == 200
    assignment = assignment_response.json()["assignment"]

    placement_response = client.put(
        f"/api/v1/projects/{project_id}/pages/{page_id}/placements",
        json={
            "assignment_id": assignment["id"],
            "text_box": region["bounding_box"],
            "style": {
                "font_family": "Komika",
                "font_fallbacks": ["Arial"],
                "font_size": 24,
                "leading": 28,
                "tracking": 0,
                "alignment": "center",
                "direction": "ltr",
                "rotation": 0,
                "fill": "#000000",
            },
        },
    )
    assert placement_response.status_code == 200

    delete_response = client.delete(
        f"/api/v1/projects/{project_id}/pages/{page_id}/regions/{region['id']}"
    )

    assert delete_response.status_code == 200
    assert delete_response.json()["regions"] == []

    mask_revisions_response = client.get(
        f"/api/v1/projects/{project_id}/pages/{page_id}/mask-revisions"
    )
    dialogues_response = client.get(f"/api/v1/projects/{project_id}/pages/{page_id}/dialogues")
    translations_response = client.get(
        f"/api/v1/projects/{project_id}/pages/{page_id}/translations"
    )
    assignments_response = client.get(
        f"/api/v1/projects/{project_id}/pages/{page_id}/assignments"
    )
    placements_response = client.get(
        f"/api/v1/projects/{project_id}/pages/{page_id}/placements"
    )
    detail_response = client.get(f"/api/v1/projects/{project_id}")

    assert mask_revisions_response.status_code == 200
    assert dialogues_response.status_code == 200
    assert translations_response.status_code == 200
    assert assignments_response.status_code == 200
    assert placements_response.status_code == 200
    assert detail_response.status_code == 200
    assert mask_revisions_response.json()["mask_revisions"] == []
    assert len(dialogues_response.json()["dialogues"]) == 1
    assert len(translations_response.json()["translations"]) == 1
    assert assignments_response.json()["assignments"] == []
    assert placements_response.json()["placements"] == []
    assert detail_response.json()["pages"][0]["status"] == "text_ready"


def test_generate_translation_job_can_be_queued_for_existing_dialogues(client: TestClient) -> None:
    project_id = create_project(client)
    page_payload = upload_single_page(client, project_id)
    page_id = page_payload["id"]

    dialogue_response = client.post(
        f"/api/v1/projects/{project_id}/pages/{page_id}/dialogues",
        json={
            "page_id": page_id,
            "content": "Original line",
            "source_language": "ja-JP",
            "reading_order": 1,
        },
    )
    assert dialogue_response.status_code == 201
    dialogue = dialogue_response.json()["dialogue"]

    response = client.post(
        f"/api/v1/projects/{project_id}/pages/{page_id}/jobs",
        json={"type": "generate_translation"},
    )

    assert response.status_code == 201
    job = response.json()["job"]
    assert job["type"] == "generate_translation"
    assert job["payload"]["project_id"] == project_id
    assert job["payload"]["dialogue_ids"] == [dialogue["id"]]
    assert job["payload"]["target_language"] == "pt-BR"


def test_match_dialogue_job_can_be_queued_for_unassigned_dialogues(client: TestClient) -> None:
    project_id = create_project(client)
    page_payload = upload_single_page(client, project_id)
    page_id = page_payload["id"]
    region = create_region(client, project_id, page_id)

    dialogue_response = client.post(
        f"/api/v1/projects/{project_id}/pages/{page_id}/dialogues",
        json={
            "page_id": page_id,
            "content": "Original line",
            "source_language": "ja-JP",
            "reading_order": 1,
        },
    )
    assert dialogue_response.status_code == 201
    dialogue = dialogue_response.json()["dialogue"]

    response = client.post(
        f"/api/v1/projects/{project_id}/pages/{page_id}/jobs",
        json={"type": "match_dialogue"},
    )

    assert response.status_code == 201
    job = response.json()["job"]
    assert job["type"] == "match_dialogue"
    assert job["payload"]["dialogue_ids"] == [dialogue["id"]]
    assert job["payload"]["region_ids"] == [region["id"]]


def test_page_jobs_reject_unsupported_job_type(client: TestClient) -> None:
    project_id = create_project(client)
    page_payload = upload_single_page(client, project_id)
    page_id = page_payload["id"]

    response = client.post(
        f"/api/v1/projects/{project_id}/pages/{page_id}/jobs",
        json={"type": "generate_typesetting"},
    )

    assert response.status_code == 422
    payload = response.json()
    assert payload["error_code"] == "INVALID_REQUEST"


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

    job_response = client.post(
        f"/api/v1/projects/{project_id}/pages/{page_id}/jobs",
        json={"type": "detect_regions"},
    )
    assert job_response.status_code == 201

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

        jobs_response = restarted_client.get(
            f"/api/v1/projects/{project_id}/pages/{page_id}/jobs"
        )
        assert jobs_response.status_code == 200
        assert len(jobs_response.json()["jobs"]) == 1
