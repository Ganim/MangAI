import json
from pathlib import Path

from mangai_workers.config import WorkerSettings
import mangai_workers.queue as worker_queue
from mangai_workers.queue import (
    _apply_region_reading_metadata,
    has_pending_jobs,
    process_next_job,
)


def seed_state(data_dir, *, job_status: str = "queued") -> str:
    project_id = "11111111-1111-4111-8111-111111111111"
    page_id = "22222222-2222-4222-8222-222222222222"
    asset_id = "33333333-3333-4333-8333-333333333333"
    job_id = "44444444-4444-4444-8444-444444444444"
    timestamp = "2026-03-15T00:00:00Z"

    state = {
        "projects": [
            {
                "id": project_id,
                "schema_version": 1,
                "name": "Worker Test",
                "status": "draft",
                "source_language": "ja-JP",
                "target_language": "pt-BR",
                "target_text_direction": "ltr",
                "page_count": 1,
                "created_at": timestamp,
                "updated_at": timestamp,
            }
        ],
        "pages": [
            {
                "id": page_id,
                "project_id": project_id,
                "index": 1,
                "file_name": "001.png",
                "mime_type": "image/png",
                "size_bytes": 2048,
                "width": 1600,
                "height": 2400,
                "status": "uploaded",
                "original_asset_path": f"/api/v1/projects/{project_id}/pages/{page_id}/original",
                "active_cleaned_asset_path": None,
                "created_at": timestamp,
                "updated_at": timestamp,
            }
        ],
        "assets": [
            {
                "id": asset_id,
                "project_id": project_id,
                "page_id": page_id,
                "kind": "original",
                "file_name": "001.png",
                "storage_key": f"{project_id}/{asset_id}.png",
                "mime_type": "image/png",
                "size_bytes": 2048,
                "created_at": timestamp,
                "updated_at": timestamp,
            }
        ],
        "regions": [],
        "mask_revisions": [],
        "dialogues": [],
        "translations": [],
        "assignments": [],
        "placements": [],
        "jobs": [
            {
                "id": job_id,
                "project_id": project_id,
                "page_id": page_id,
                "type": "detect_regions",
                "status": job_status,
                "payload": {
                    "job_id": job_id,
                    "page_id": page_id,
                    "asset_id": asset_id,
                },
                "result": None,
                "error_code": None,
                "error_message": None,
                "created_at": timestamp,
                "updated_at": timestamp,
            }
        ],
    }

    data_dir.mkdir(parents=True, exist_ok=True)
    asset_path = data_dir / "assets" / f"{project_id}/{asset_id}.png"
    asset_path.parent.mkdir(parents=True, exist_ok=True)
    asset_path.write_bytes(b"worker-test-page" * 32)
    (data_dir / "state.json").write_text(json.dumps(state, indent=2), encoding="utf-8")
    return page_id


def seed_cleanup_state(data_dir) -> tuple[str, str]:
    project_id = "11111111-1111-4111-8111-111111111111"
    page_id = "22222222-2222-4222-8222-222222222222"
    asset_id = "33333333-3333-4333-8333-333333333333"
    region_id = "55555555-5555-4555-8555-555555555555"
    mask_revision_id = "66666666-6666-4666-8666-666666666666"
    job_id = "77777777-7777-4777-8777-777777777777"
    timestamp = "2026-03-15T00:00:00Z"

    state = {
        "projects": [
            {
                "id": project_id,
                "schema_version": 1,
                "name": "Cleanup Worker Test",
                "status": "draft",
                "source_language": "ja-JP",
                "target_language": "pt-BR",
                "target_text_direction": "ltr",
                "page_count": 1,
                "created_at": timestamp,
                "updated_at": timestamp,
            }
        ],
        "pages": [
            {
                "id": page_id,
                "project_id": project_id,
                "index": 1,
                "file_name": "001.png",
                "mime_type": "image/png",
                "size_bytes": 2048,
                "width": 1600,
                "height": 2400,
                "status": "cleanup_ready",
                "original_asset_path": f"/api/v1/projects/{project_id}/pages/{page_id}/original",
                "active_cleaned_asset_path": None,
                "created_at": timestamp,
                "updated_at": timestamp,
            }
        ],
        "assets": [
            {
                "id": asset_id,
                "project_id": project_id,
                "page_id": page_id,
                "kind": "original",
                "file_name": "001.png",
                "storage_key": f"{project_id}/{asset_id}.png",
                "mime_type": "image/png",
                "size_bytes": 2048,
                "created_at": timestamp,
                "updated_at": timestamp,
            }
        ],
        "regions": [
            {
                "id": region_id,
                "page_id": page_id,
                "type": "speech_balloon",
                "origin": "user_created",
                "state": "approved",
                "confidence": None,
                "bounding_box": {
                    "x": 200,
                    "y": 180,
                    "width": 420,
                    "height": 260,
                },
                "shape": {
                    "type": "polygon",
                    "points": [
                        {"x": 200, "y": 180},
                        {"x": 620, "y": 180},
                        {"x": 620, "y": 440},
                        {"x": 200, "y": 440},
                    ],
                },
                "created_at": timestamp,
                "updated_at": timestamp,
            }
        ],
        "mask_revisions": [
            {
                "id": mask_revision_id,
                "region_id": region_id,
                "version": 1,
                "is_active": True,
                "approved": True,
                "shape": {
                    "type": "polygon",
                    "points": [
                        {"x": 210, "y": 190},
                        {"x": 610, "y": 190},
                        {"x": 610, "y": 430},
                        {"x": 210, "y": 430},
                    ],
                },
                "created_by": "00000000-0000-4000-8000-000000000000",
                "created_at": timestamp,
                "updated_at": timestamp,
            }
        ],
        "dialogues": [],
        "translations": [],
        "assignments": [],
        "placements": [],
        "jobs": [
            {
                "id": job_id,
                "project_id": project_id,
                "page_id": page_id,
                "type": "generate_cleanup",
                "status": "queued",
                "payload": {
                    "job_id": job_id,
                    "page_id": page_id,
                    "source_asset_id": asset_id,
                    "region_ids": [region_id],
                    "mask_revision_ids": [mask_revision_id],
                },
                "result": None,
                "error_code": None,
                "error_message": None,
                "created_at": timestamp,
                "updated_at": timestamp,
            }
        ],
    }

    data_dir.mkdir(parents=True, exist_ok=True)
    asset_path = data_dir / "assets" / f"{project_id}/{asset_id}.png"
    asset_path.parent.mkdir(parents=True, exist_ok=True)
    asset_path.write_bytes(b"cleanup-worker-page" * 32)
    (data_dir / "state.json").write_text(json.dumps(state, indent=2), encoding="utf-8")
    return page_id, project_id


def seed_ocr_state(data_dir) -> tuple[str, str]:
    project_id = "11111111-1111-4111-8111-111111111111"
    page_id = "22222222-2222-4222-8222-222222222222"
    asset_id = "33333333-3333-4333-8333-333333333333"
    region_ids = [
        "55555555-5555-4555-8555-555555555555",
        "66666666-6666-4666-8666-666666666666",
    ]
    job_id = "77777777-7777-4777-8777-777777777777"
    timestamp = "2026-03-15T00:00:00Z"

    state = {
        "projects": [
            {
                "id": project_id,
                "schema_version": 1,
                "name": "OCR Worker Test",
                "status": "draft",
                "source_language": "ja-JP",
                "target_language": "pt-BR",
                "target_text_direction": "ltr",
                "page_count": 1,
                "created_at": timestamp,
                "updated_at": timestamp,
            }
        ],
        "pages": [
            {
                "id": page_id,
                "project_id": project_id,
                "index": 1,
                "file_name": "001.png",
                "mime_type": "image/png",
                "size_bytes": 2048,
                "width": 1600,
                "height": 2400,
                "status": "analyzed",
                "original_asset_path": f"/api/v1/projects/{project_id}/pages/{page_id}/original",
                "active_cleaned_asset_path": None,
                "created_at": timestamp,
                "updated_at": timestamp,
            }
        ],
        "assets": [
            {
                "id": asset_id,
                "project_id": project_id,
                "page_id": page_id,
                "kind": "original",
                "file_name": "001.png",
                "storage_key": f"{project_id}/{asset_id}.png",
                "mime_type": "image/png",
                "size_bytes": 2048,
                "created_at": timestamp,
                "updated_at": timestamp,
            }
        ],
        "regions": [
            {
                "id": region_ids[0],
                "page_id": page_id,
                "type": "speech_balloon",
                "origin": "detected",
                "state": "approved",
                "confidence": 0.91,
                "bounding_box": {"x": 180, "y": 140, "width": 360, "height": 210},
                "shape": {
                    "type": "polygon",
                    "points": [
                        {"x": 180, "y": 140},
                        {"x": 540, "y": 140},
                        {"x": 540, "y": 350},
                        {"x": 180, "y": 350},
                    ],
                },
                "created_at": timestamp,
                "updated_at": timestamp,
            },
            {
                "id": region_ids[1],
                "page_id": page_id,
                "type": "speech_balloon",
                "origin": "detected",
                "state": "approved",
                "confidence": 0.87,
                "bounding_box": {"x": 640, "y": 320, "width": 340, "height": 220},
                "shape": {
                    "type": "polygon",
                    "points": [
                        {"x": 640, "y": 320},
                        {"x": 980, "y": 320},
                        {"x": 980, "y": 540},
                        {"x": 640, "y": 540},
                    ],
                },
                "created_at": timestamp,
                "updated_at": timestamp,
            },
        ],
        "mask_revisions": [],
        "dialogues": [],
        "translations": [],
        "assignments": [],
        "placements": [],
        "jobs": [
            {
                "id": job_id,
                "project_id": project_id,
                "page_id": page_id,
                "type": "run_ocr",
                "status": "queued",
                "payload": {
                    "job_id": job_id,
                    "page_id": page_id,
                    "asset_id": asset_id,
                    "region_ids": region_ids,
                    "source_language": "ja-JP",
                },
                "result": None,
                "error_code": None,
                "error_message": None,
                "created_at": timestamp,
                "updated_at": timestamp,
            }
        ],
    }

    data_dir.mkdir(parents=True, exist_ok=True)
    asset_path = data_dir / "assets" / f"{project_id}/{asset_id}.png"
    asset_path.parent.mkdir(parents=True, exist_ok=True)
    asset_path.write_bytes(b"ocr-worker-page" * 32)
    (data_dir / "state.json").write_text(json.dumps(state, indent=2), encoding="utf-8")
    return page_id, project_id


def seed_translation_state(data_dir) -> tuple[str, str]:
    project_id = "11111111-1111-4111-8111-111111111111"
    page_id = "22222222-2222-4222-8222-222222222222"
    dialogue_ids = [
        "55555555-5555-4555-8555-555555555555",
        "66666666-6666-4666-8666-666666666666",
    ]
    job_id = "77777777-7777-4777-8777-777777777777"
    timestamp = "2026-03-15T00:00:00Z"

    state = {
        "projects": [
            {
                "id": project_id,
                "schema_version": 1,
                "name": "Translation Worker Test",
                "status": "draft",
                "source_language": "ja-JP",
                "target_language": "pt-BR",
                "target_text_direction": "ltr",
                "page_count": 1,
                "created_at": timestamp,
                "updated_at": timestamp,
            }
        ],
        "pages": [
            {
                "id": page_id,
                "project_id": project_id,
                "index": 1,
                "file_name": "001.png",
                "mime_type": "image/png",
                "size_bytes": 2048,
                "width": 1600,
                "height": 2400,
                "status": "text_ready",
                "original_asset_path": f"/api/v1/projects/{project_id}/pages/{page_id}/original",
                "active_cleaned_asset_path": None,
                "created_at": timestamp,
                "updated_at": timestamp,
            }
        ],
        "assets": [],
        "regions": [],
        "mask_revisions": [],
        "dialogues": [
            {
                "id": dialogue_ids[0],
                "page_id": page_id,
                "source": "ocr",
                "source_language": "ja-JP",
                "content": "テキスト 1",
                "reading_order": 1,
                "status": "draft",
                "source_region_id": None,
                "created_at": timestamp,
                "updated_at": timestamp,
            },
            {
                "id": dialogue_ids[1],
                "page_id": page_id,
                "source": "ocr",
                "source_language": "ja-JP",
                "content": "テキスト 2",
                "reading_order": 2,
                "status": "draft",
                "source_region_id": None,
                "created_at": timestamp,
                "updated_at": timestamp,
            },
        ],
        "translations": [],
        "assignments": [],
        "placements": [],
        "jobs": [
            {
                "id": job_id,
                "project_id": project_id,
                "page_id": page_id,
                "type": "generate_translation",
                "status": "queued",
                "payload": {
                    "job_id": job_id,
                    "project_id": project_id,
                    "dialogue_ids": dialogue_ids,
                    "source_language": "ja-JP",
                    "target_language": "pt-BR",
                },
                "result": None,
                "error_code": None,
                "error_message": None,
                "created_at": timestamp,
                "updated_at": timestamp,
            }
        ],
    }

    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "state.json").write_text(json.dumps(state, indent=2), encoding="utf-8")
    return page_id, project_id


def seed_matching_state(data_dir) -> tuple[str, str]:
    project_id = "11111111-1111-4111-8111-111111111111"
    page_id = "22222222-2222-4222-8222-222222222222"
    region_ids = [
        "33333333-3333-4333-8333-333333333333",
        "44444444-4444-4444-8444-444444444444",
    ]
    dialogue_ids = [
        "55555555-5555-4555-8555-555555555555",
        "66666666-6666-4666-8666-666666666666",
    ]
    job_id = "77777777-7777-4777-8777-777777777777"
    timestamp = "2026-03-15T00:00:00Z"

    state = {
        "projects": [
            {
                "id": project_id,
                "schema_version": 1,
                "name": "Matching Worker Test",
                "status": "draft",
                "source_language": "ja-JP",
                "target_language": "pt-BR",
                "target_text_direction": "ltr",
                "page_count": 1,
                "created_at": timestamp,
                "updated_at": timestamp,
            }
        ],
        "pages": [
            {
                "id": page_id,
                "project_id": project_id,
                "index": 1,
                "file_name": "001.png",
                "mime_type": "image/png",
                "size_bytes": 2048,
                "width": 1600,
                "height": 2400,
                "status": "text_ready",
                "original_asset_path": f"/api/v1/projects/{project_id}/pages/{page_id}/original",
                "active_cleaned_asset_path": None,
                "created_at": timestamp,
                "updated_at": timestamp,
            }
        ],
        "assets": [],
        "regions": [
            {
                "id": region_ids[0],
                "page_id": page_id,
                "type": "speech_balloon",
                "origin": "detected",
                "state": "approved",
                "confidence": 0.93,
                "bounding_box": {"x": 160, "y": 130, "width": 360, "height": 210},
                "shape": {
                    "type": "polygon",
                    "points": [
                        {"x": 160, "y": 130},
                        {"x": 520, "y": 130},
                        {"x": 520, "y": 340},
                        {"x": 160, "y": 340},
                    ],
                },
                "created_at": timestamp,
                "updated_at": timestamp,
            },
            {
                "id": region_ids[1],
                "page_id": page_id,
                "type": "speech_balloon",
                "origin": "detected",
                "state": "approved",
                "confidence": 0.89,
                "bounding_box": {"x": 610, "y": 310, "width": 350, "height": 230},
                "shape": {
                    "type": "polygon",
                    "points": [
                        {"x": 610, "y": 310},
                        {"x": 960, "y": 310},
                        {"x": 960, "y": 540},
                        {"x": 610, "y": 540},
                    ],
                },
                "created_at": timestamp,
                "updated_at": timestamp,
            },
        ],
        "mask_revisions": [],
        "dialogues": [
            {
                "id": dialogue_ids[0],
                "page_id": page_id,
                "source": "ocr",
                "source_language": "ja-JP",
                "content": "テキスト 1",
                "reading_order": 1,
                "status": "draft",
                "source_region_id": region_ids[0],
                "created_at": timestamp,
                "updated_at": timestamp,
            },
            {
                "id": dialogue_ids[1],
                "page_id": page_id,
                "source": "manual",
                "source_language": "ja-JP",
                "content": "テキスト 2",
                "reading_order": 2,
                "status": "draft",
                "source_region_id": None,
                "created_at": timestamp,
                "updated_at": timestamp,
            },
        ],
        "translations": [],
        "assignments": [],
        "placements": [],
        "jobs": [
            {
                "id": job_id,
                "project_id": project_id,
                "page_id": page_id,
                "type": "match_dialogue",
                "status": "queued",
                "payload": {
                    "job_id": job_id,
                    "page_id": page_id,
                    "dialogue_ids": dialogue_ids,
                    "region_ids": region_ids,
                },
                "result": None,
                "error_code": None,
                "error_message": None,
                "created_at": timestamp,
                "updated_at": timestamp,
            }
        ],
    }

    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "state.json").write_text(json.dumps(state, indent=2), encoding="utf-8")
    return page_id, project_id


def test_process_next_job_generates_detected_regions_and_overlay(tmp_path) -> None:
    data_dir = tmp_path / "worker-data"
    page_id = seed_state(data_dir)
    settings = WorkerSettings(data_dir=data_dir, poll_interval_seconds=0.01)

    processed_job = process_next_job(settings)

    assert processed_job is not None
    assert processed_job["status"] == "succeeded"
    assert processed_job["result"]["page_id"] == page_id
    assert processed_job["result"]["regions_created"] in {2, 3}

    state = json.loads((data_dir / "state.json").read_text(encoding="utf-8"))
    assert state["pages"][0]["status"] == "analyzed"
    assert len(state["regions"]) in {2, 3}
    assert all(region["origin"] == "detected" for region in state["regions"])
    assert all(region["confidence"] is not None for region in state["regions"])
    assert all("text_area" in region for region in state["regions"])
    assert all("context_area" in region for region in state["regions"])
    assert all(region["panel_area"] for region in state["regions"])
    assert all(region["global_reading_order"] is None for region in state["regions"])
    overlay_asset = next(asset for asset in state["assets"] if asset["kind"] == "overlay")
    overlay_path = data_dir / "assets" / overlay_asset["storage_key"]
    assert overlay_path.exists()
    overlay_payload = json.loads(overlay_path.read_text(encoding="utf-8"))
    assert overlay_payload["regions_created"] in {2, 3}
    assert len(overlay_payload["regions"]) == overlay_payload["regions_created"]
    assert all("text_area" in region for region in overlay_payload["regions"])
    assert all("context_area" in region for region in overlay_payload["regions"])
    assert all("panel_area" in region for region in overlay_payload["regions"])


def test_apply_region_reading_metadata_uses_panel_boxes_for_manga_reading_order() -> None:
    annotated = _apply_region_reading_metadata(
        [
            {
                "id": "top-panel",
                "bounding_box": {"x": 420, "y": 420, "width": 420, "height": 110},
                "text_area": {"x": 420, "y": 420, "width": 420, "height": 110},
                "context_area": {"x": 390, "y": 390, "width": 520, "height": 180},
            },
            {
                "id": "bottom-left-panel",
                "bounding_box": {"x": 440, "y": 860, "width": 110, "height": 260},
                "text_area": {"x": 440, "y": 860, "width": 110, "height": 260},
                "context_area": {"x": 400, "y": 820, "width": 180, "height": 320},
            },
            {
                "id": "bottom-right-top",
                "bounding_box": {"x": 760, "y": 760, "width": 180, "height": 260},
                "text_area": {"x": 760, "y": 760, "width": 180, "height": 260},
                "context_area": {"x": 720, "y": 720, "width": 260, "height": 320},
            },
            {
                "id": "bottom-right-bottom",
                "bounding_box": {"x": 680, "y": 980, "width": 180, "height": 220},
                "text_area": {"x": 680, "y": 980, "width": 180, "height": 220},
                "context_area": {"x": 650, "y": 950, "width": 240, "height": 300},
            },
        ],
        source_language="ja-JP",
        panel_boxes=[
            {"x": 0, "y": 0, "width": 1000, "height": 600},
            {"x": 560, "y": 600, "width": 440, "height": 800},
            {"x": 0, "y": 600, "width": 560, "height": 800},
        ],
    )

    assert [region["id"] for region in annotated] == [
        "top-panel",
        "bottom-right-top",
        "bottom-right-bottom",
        "bottom-left-panel",
    ]
    assert [region["global_reading_order"] for region in annotated] == [1, 2, 3, 4]
    assert [region["panel_order"] for region in annotated] == [1, 2, 2, 3]
    assert [region["order_in_panel"] for region in annotated] == [1, 1, 2, 1]
    assert annotated[1]["panel_area"]["x"] == 560
    assert annotated[3]["panel_area"]["x"] == 0


def test_process_next_job_returns_none_without_queued_jobs(tmp_path) -> None:
    data_dir = tmp_path / "worker-data"
    seed_state(data_dir, job_status="succeeded")
    settings = WorkerSettings(data_dir=data_dir, poll_interval_seconds=0.01)

    assert has_pending_jobs(settings) is False
    assert process_next_job(settings) is None


def test_process_next_job_recovers_stalled_running_job(tmp_path) -> None:
    data_dir = tmp_path / "worker-data"
    page_id = seed_state(data_dir, job_status="running")
    settings = WorkerSettings(
        data_dir=data_dir,
        poll_interval_seconds=0.01,
        stalled_job_timeout_seconds=0,
    )

    processed_job = process_next_job(settings)

    assert processed_job is not None
    assert processed_job["status"] == "succeeded"
    assert processed_job["result"]["page_id"] == page_id


def test_process_next_job_generates_cleaned_asset_preview(tmp_path) -> None:
    data_dir = tmp_path / "worker-data"
    page_id, project_id = seed_cleanup_state(data_dir)
    settings = WorkerSettings(data_dir=data_dir, poll_interval_seconds=0.01)

    processed_job = process_next_job(settings)

    assert processed_job is not None
    assert processed_job["status"] == "succeeded"
    assert processed_job["type"] == "generate_cleanup"
    assert processed_job["result"]["page_id"] == page_id
    assert processed_job["result"]["variant_asset_ids"] == []

    state = json.loads((data_dir / "state.json").read_text(encoding="utf-8"))
    page = state["pages"][0]
    assert page["status"] == "cleaned"
    assert page["active_cleaned_asset_path"].startswith(
        f"/api/v1/projects/{project_id}/assets/"
    )

    cleaned_asset = next(asset for asset in state["assets"] if asset["kind"] == "cleaned")
    cleaned_asset_path = data_dir / "assets" / cleaned_asset["storage_key"]
    assert cleaned_asset_path.exists()
    svg_markup = cleaned_asset_path.read_text(encoding="utf-8")
    assert svg_markup.startswith("<svg")
    assert "data:image/png;base64," in svg_markup
    assert "<polygon" in svg_markup


def test_process_next_job_runs_ocr_and_persists_preview_dialogues(tmp_path) -> None:
    data_dir = tmp_path / "worker-data"
    page_id, _project_id = seed_ocr_state(data_dir)
    settings = WorkerSettings(data_dir=data_dir, poll_interval_seconds=0.01)

    processed_job = process_next_job(settings)

    assert processed_job is not None
    assert processed_job["status"] == "succeeded"
    assert processed_job["type"] == "run_ocr"
    assert processed_job["result"]["page_id"] == page_id
    assert len(processed_job["result"]["dialogue_ids"]) == 2

    state = json.loads((data_dir / "state.json").read_text(encoding="utf-8"))
    page = state["pages"][0]
    assert page["status"] == "text_ready"
    assert len(state["dialogues"]) == 2
    assert all(dialogue["source"] == "ocr" for dialogue in state["dialogues"])
    preview_asset = next(asset for asset in state["assets"] if asset["kind"] == "ocr_preview")
    preview_path = data_dir / "assets" / preview_asset["storage_key"]
    assert preview_path.exists()
    preview_payload = json.loads(preview_path.read_text(encoding="utf-8"))
    assert preview_payload["dialogues_created"] == 2
    assert preview_payload["source_language"] == "ja-JP"


def test_process_next_job_generates_translation_drafts(tmp_path) -> None:
    data_dir = tmp_path / "worker-data"
    page_id, _project_id = seed_translation_state(data_dir)
    settings = WorkerSettings(data_dir=data_dir, poll_interval_seconds=0.01)

    processed_job = process_next_job(settings)

    assert processed_job is not None
    assert processed_job["status"] == "succeeded"
    assert processed_job["type"] == "generate_translation"
    assert len(processed_job["result"]["translation_ids"]) == 2

    state = json.loads((data_dir / "state.json").read_text(encoding="utf-8"))
    page = state["pages"][0]
    assert page["id"] == page_id
    assert page["status"] == "text_ready"
    assert len(state["translations"]) == 2
    assert all(translation["provider"] == "worker_fallback" for translation in state["translations"])
    assert all(translation["target_language"] == "pt-BR" for translation in state["translations"])


def test_process_next_job_matches_dialogues_and_creates_placements(tmp_path) -> None:
    data_dir = tmp_path / "worker-data"
    page_id, _project_id = seed_matching_state(data_dir)
    settings = WorkerSettings(data_dir=data_dir, poll_interval_seconds=0.01)

    processed_job = process_next_job(settings)

    assert processed_job is not None
    assert processed_job["status"] == "succeeded"
    assert processed_job["type"] == "match_dialogue"
    assert processed_job["result"]["page_id"] == page_id
    assert len(processed_job["result"]["assignment_ids"]) == 2
    assert len(processed_job["result"]["placement_ids"]) == 2

    state = json.loads((data_dir / "state.json").read_text(encoding="utf-8"))
    page = state["pages"][0]
    assert page["status"] == "typeset_ready"
    assert len(state["assignments"]) == 2
    assert len(state["placements"]) == 2
    assert all(assignment["origin"] == "automatic" for assignment in state["assignments"])
    assert all(placement["layout_metrics"]["mode"] == "automatic" for placement in state["placements"])


def test_save_state_retries_replace_when_file_is_temporarily_locked(tmp_path, monkeypatch) -> None:
    state_path = tmp_path / "state.json"
    replace_calls = {"count": 0}
    original_replace = Path.replace

    def flaky_replace(self: Path, target: Path):
        replace_calls["count"] += 1
        if replace_calls["count"] == 1:
            raise PermissionError("locked")
        return original_replace(self, target)

    monkeypatch.setattr(worker_queue, "sleep", lambda _seconds: None)
    monkeypatch.setattr(Path, "replace", flaky_replace)

    worker_queue._save_state(state_path, {"jobs": []})

    assert replace_calls["count"] == 2
    assert json.loads(state_path.read_text(encoding="utf-8")) == {"jobs": []}
