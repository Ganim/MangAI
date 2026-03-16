import json

from mangai_workers.config import WorkerSettings
from mangai_workers.queue import has_pending_jobs, process_next_job


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
    overlay_asset = next(asset for asset in state["assets"] if asset["kind"] == "overlay")
    overlay_path = data_dir / "assets" / overlay_asset["storage_key"]
    assert overlay_path.exists()
    overlay_payload = json.loads(overlay_path.read_text(encoding="utf-8"))
    assert overlay_payload["regions_created"] in {2, 3}
    assert len(overlay_payload["regions"]) == overlay_payload["regions_created"]


def test_process_next_job_returns_none_without_queued_jobs(tmp_path) -> None:
    data_dir = tmp_path / "worker-data"
    seed_state(data_dir, job_status="succeeded")
    settings = WorkerSettings(data_dir=data_dir, poll_interval_seconds=0.01)

    assert has_pending_jobs(settings) is False
    assert process_next_job(settings) is None
