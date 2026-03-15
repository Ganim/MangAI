from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from time import sleep
from typing import Any
from uuid import uuid4

from mangai_workers.config import WorkerSettings
from mangai_workers.runner import WorkerExecutionError, run_job


POLLABLE_JOB_STATUSES = {"queued"}
PENDING_JOB_STATUSES = {"queued", "running"}


def process_next_job(settings: WorkerSettings) -> dict[str, Any] | None:
    state_path = settings.data_dir / "state.json"
    if not state_path.exists():
        return None

    state = _load_state(state_path)
    jobs = state.setdefault("jobs", [])
    job = next((candidate for candidate in jobs if candidate.get("status") in POLLABLE_JOB_STATUSES), None)
    if job is None:
        return None

    running_timestamp = _utcnow_iso()
    job["status"] = "running"
    job["updated_at"] = running_timestamp
    _save_state(state_path, state)

    try:
        result = _execute_job(settings=settings, state=state, job=job)
    except Exception as exc:  # noqa: BLE001 - worker must persist failures
        job["status"] = "failed"
        job["updated_at"] = _utcnow_iso()
        job["error_code"] = "WORKER_EXECUTION_ERROR"
        job["error_message"] = str(exc)
        _save_state(state_path, state)
        return dict(job)

    job["status"] = "succeeded"
    job["updated_at"] = _utcnow_iso()
    job["result"] = result
    job["error_code"] = None
    job["error_message"] = None
    _save_state(state_path, state)
    return dict(job)


def run_worker_loop(settings: WorkerSettings) -> None:
    while True:
        processed_job = process_next_job(settings)
        if processed_job is None:
            sleep(settings.poll_interval_seconds)
            continue

        if processed_job["status"] != "succeeded":
            print(f"Worker job {processed_job['id']} failed: {processed_job['error_message']}")
        else:
            print(f"Worker job {processed_job['id']} succeeded.")


def has_pending_jobs(settings: WorkerSettings) -> bool:
    state_path = settings.data_dir / "state.json"
    if not state_path.exists():
        return False
    state = _load_state(state_path)
    return any(job.get("status") in PENDING_JOB_STATUSES for job in state.get("jobs", []))


def _execute_job(settings: WorkerSettings, state: dict[str, Any], job: dict[str, Any]) -> dict[str, Any]:
    job_type = str(job["type"])
    payload = _require_dict(job.get("payload"), "job payload")
    result = run_job(job_type, payload)

    if job_type == "detect_regions":
        _apply_detect_regions_result(
            settings=settings,
            state=state,
            job=job,
            result=result,
        )
        return result

    raise WorkerExecutionError(f"Unsupported job type '{job_type}'.")


def _apply_detect_regions_result(
    settings: WorkerSettings,
    state: dict[str, Any],
    job: dict[str, Any],
    result: dict[str, Any],
) -> None:
    project_id = str(job["project_id"])
    page_id = str(job["page_id"])
    payload = _require_dict(job.get("payload"), "job payload")
    asset_id = str(payload["asset_id"])

    page = _find_by_id(state.get("pages", []), page_id, "page")
    _find_by_id(state.get("assets", []), asset_id, "asset")

    width = int(page.get("width") or 1000)
    height = int(page.get("height") or 1400)
    timestamp = _utcnow_iso()
    detected_regions = _build_detected_regions(page_id=page_id, width=width, height=height, timestamp=timestamp)

    preserved_regions = [
        region
        for region in state.get("regions", [])
        if not (region.get("page_id") == page_id and region.get("origin") == "detected")
    ]
    state["regions"] = [*preserved_regions, *detected_regions]

    page["status"] = "analyzed"
    page["updated_at"] = timestamp

    overlay_asset = _build_overlay_asset(
        project_id=project_id,
        page_id=page_id,
        overlay_asset_id=str(result["overlay_asset_id"]),
        regions=detected_regions,
        settings=settings,
        timestamp=timestamp,
    )
    preserved_assets = [
        asset
        for asset in state.get("assets", [])
        if asset.get("id") != overlay_asset["id"]
    ]
    state["assets"] = [*preserved_assets, overlay_asset]
    result["regions_created"] = len(detected_regions)


def _build_detected_regions(
    *,
    page_id: str,
    width: int,
    height: int,
    timestamp: str,
) -> list[dict[str, Any]]:
    candidate_boxes = (
        {
            "type": "speech_balloon",
            "confidence": 0.94,
            "bounding_box": _bounding_box(width * 0.12, height * 0.1, width * 0.34, height * 0.17),
        },
        {
            "type": "speech_balloon",
            "confidence": 0.88,
            "bounding_box": _bounding_box(width * 0.56, height * 0.46, width * 0.26, height * 0.15),
        },
    )

    regions: list[dict[str, Any]] = []
    for candidate in candidate_boxes:
        bounding_box = candidate["bounding_box"]
        regions.append(
            {
                "id": str(uuid4()),
                "page_id": page_id,
                "type": candidate["type"],
                "origin": "detected",
                "state": "draft",
                "confidence": candidate["confidence"],
                "bounding_box": bounding_box,
                "shape": _polygon_shape(bounding_box),
                "created_at": timestamp,
                "updated_at": timestamp,
            }
        )
    return regions


def _build_overlay_asset(
    *,
    project_id: str,
    page_id: str,
    overlay_asset_id: str,
    regions: list[dict[str, Any]],
    settings: WorkerSettings,
    timestamp: str,
) -> dict[str, Any]:
    storage_key = str(Path(project_id) / f"{overlay_asset_id}.json")
    asset_path = settings.data_dir / "assets" / storage_key
    asset_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "page_id": page_id,
        "region_ids": [region["id"] for region in regions],
        "regions_created": len(regions),
    }
    serialized = json.dumps(payload, indent=2).encode("utf-8")
    asset_path.write_bytes(serialized)
    return {
        "id": overlay_asset_id,
        "project_id": project_id,
        "page_id": page_id,
        "kind": "overlay",
        "file_name": f"{page_id}-overlay.json",
        "storage_key": storage_key,
        "mime_type": "application/json",
        "size_bytes": len(serialized),
        "created_at": timestamp,
        "updated_at": timestamp,
    }


def _bounding_box(x: float, y: float, width: float, height: float) -> dict[str, float]:
    return {
        "x": round(max(x, 0), 2),
        "y": round(max(y, 0), 2),
        "width": round(max(width, 1), 2),
        "height": round(max(height, 1), 2),
    }


def _polygon_shape(bounding_box: dict[str, float]) -> dict[str, Any]:
    x = bounding_box["x"]
    y = bounding_box["y"]
    width = bounding_box["width"]
    height = bounding_box["height"]
    return {
        "type": "polygon",
        "points": [
            {"x": x, "y": y},
            {"x": x + width, "y": y},
            {"x": x + width, "y": y + height},
            {"x": x, "y": y + height},
        ],
    }


def _find_by_id(items: list[dict[str, Any]], identifier: str, label: str) -> dict[str, Any]:
    item = next((candidate for candidate in items if str(candidate.get("id")) == identifier), None)
    if item is None:
        raise WorkerExecutionError(f"Could not find {label} '{identifier}'.")
    return item


def _require_dict(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise WorkerExecutionError(f"Expected {label} to be an object.")
    return value


def _load_state(state_path: Path) -> dict[str, Any]:
    raw_text = state_path.read_text(encoding="utf-8").strip()
    if raw_text == "":
        return {}
    return json.loads(raw_text)


def _save_state(state_path: Path, state: dict[str, Any]) -> None:
    state_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = state_path.with_suffix(".tmp")
    temp_path.write_text(json.dumps(state, indent=2), encoding="utf-8")
    temp_path.replace(state_path)


def _utcnow_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")
