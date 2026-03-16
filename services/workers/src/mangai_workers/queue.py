from __future__ import annotations

import base64
import json
from datetime import UTC, datetime
from pathlib import Path
from time import sleep
from typing import Any
from uuid import uuid4

from mangai_workers.config import WorkerSettings
from mangai_workers.detection import detect_regions_from_asset
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

    if job_type == "generate_cleanup":
        _apply_generate_cleanup_result(
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
    asset = _find_by_id(state.get("assets", []), asset_id, "asset")

    width = int(page.get("width") or 1000)
    height = int(page.get("height") or 1400)
    timestamp = _utcnow_iso()
    source_asset_path = settings.data_dir / "assets" / str(asset["storage_key"])
    detected_candidates = detect_regions_from_asset(
        asset_path=source_asset_path,
        page_width=width,
        page_height=height,
    )
    detected_regions = _build_detected_regions(
        page_id=page_id,
        detected_candidates=detected_candidates,
        timestamp=timestamp,
    )

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


def _apply_generate_cleanup_result(
    settings: WorkerSettings,
    state: dict[str, Any],
    job: dict[str, Any],
    result: dict[str, Any],
) -> None:
    project_id = str(job["project_id"])
    page_id = str(job["page_id"])
    payload = _require_dict(job.get("payload"), "job payload")
    source_asset_id = str(payload["source_asset_id"])
    mask_revision_ids = _require_string_list(payload.get("mask_revision_ids"), "mask_revision_ids")

    page = _find_by_id(state.get("pages", []), page_id, "page")
    source_asset = _find_by_id(state.get("assets", []), source_asset_id, "asset")
    approved_masks = _get_mask_revisions(state, page_id, mask_revision_ids)
    if len(approved_masks) == 0:
        raise WorkerExecutionError("Cleanup jobs require at least one approved active mask revision.")

    cleaned_asset = _build_cleaned_asset(
        project_id=project_id,
        page_id=page_id,
        cleaned_asset_id=str(result["cleaned_asset_id"]),
        source_asset=source_asset,
        approved_masks=approved_masks,
        settings=settings,
        page_width=int(page.get("width") or 1000),
        page_height=int(page.get("height") or 1400),
    )

    timestamp = _utcnow_iso()
    page["status"] = "cleaned"
    page["active_cleaned_asset_path"] = f"/api/v1/projects/{project_id}/assets/{cleaned_asset['id']}"
    page["updated_at"] = timestamp

    preserved_assets = [
        asset
        for asset in state.get("assets", [])
        if asset.get("id") != cleaned_asset["id"]
    ]
    state["assets"] = [*preserved_assets, cleaned_asset]
    result["variant_asset_ids"] = []


def _build_detected_regions(
    *,
    page_id: str,
    detected_candidates: list[Any],
    timestamp: str,
) -> list[dict[str, Any]]:
    regions: list[dict[str, Any]] = []
    for candidate in detected_candidates:
        bounding_box = _bounding_box(
            candidate.bounding_box["x"],
            candidate.bounding_box["y"],
            candidate.bounding_box["width"],
            candidate.bounding_box["height"],
        )
        regions.append(
            {
                "id": str(uuid4()),
                "page_id": page_id,
                "type": candidate.type,
                "origin": "detected",
                "state": "draft",
                "confidence": candidate.confidence,
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
        "regions": [
            {
                "id": region["id"],
                "type": region["type"],
                "confidence": region["confidence"],
                "bounding_box": region["bounding_box"],
            }
            for region in regions
        ],
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


def _build_cleaned_asset(
    *,
    project_id: str,
    page_id: str,
    cleaned_asset_id: str,
    source_asset: dict[str, Any],
    approved_masks: list[dict[str, Any]],
    settings: WorkerSettings,
    page_width: int,
    page_height: int,
) -> dict[str, Any]:
    storage_key = str(Path(project_id) / f"{cleaned_asset_id}.svg")
    asset_path = settings.data_dir / "assets" / storage_key
    asset_path.parent.mkdir(parents=True, exist_ok=True)

    source_asset_path = settings.data_dir / "assets" / str(source_asset["storage_key"])
    if not source_asset_path.exists():
        raise WorkerExecutionError(f"Could not find source asset '{source_asset['id']}'.")

    source_bytes = source_asset_path.read_bytes()
    svg_markup = _render_cleanup_svg(
        source_bytes=source_bytes,
        source_mime_type=str(source_asset["mime_type"]),
        approved_masks=approved_masks,
        page_width=page_width,
        page_height=page_height,
    )
    serialized = svg_markup.encode("utf-8")
    asset_path.write_bytes(serialized)
    timestamp = _utcnow_iso()
    return {
        "id": cleaned_asset_id,
        "project_id": project_id,
        "page_id": page_id,
        "kind": "cleaned",
        "file_name": f"{page_id}-cleaned.svg",
        "storage_key": storage_key,
        "mime_type": "image/svg+xml",
        "size_bytes": len(serialized),
        "created_at": timestamp,
        "updated_at": timestamp,
    }


def _render_cleanup_svg(
    *,
    source_bytes: bytes,
    source_mime_type: str,
    approved_masks: list[dict[str, Any]],
    page_width: int,
    page_height: int,
) -> str:
    encoded_source = base64.b64encode(source_bytes).decode("ascii")
    polygons_markup = "\n".join(
        f'<polygon fill="#f8f7f1" points="{_serialize_polygon_points(mask["shape"]["points"])}" />'
        for mask in approved_masks
    )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{page_width}" height="{page_height}" '
        f'viewBox="0 0 {page_width} {page_height}">'
        f'<image href="data:{source_mime_type};base64,{encoded_source}" '
        f'width="{page_width}" height="{page_height}" preserveAspectRatio="none" />'
        f'<g opacity="1">{polygons_markup}</g>'
        "</svg>"
    )


def _serialize_polygon_points(points: list[dict[str, Any]]) -> str:
    return " ".join(f'{point["x"]},{point["y"]}' for point in points)


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


def _get_mask_revisions(
    state: dict[str, Any],
    page_id: str,
    mask_revision_ids: list[str],
) -> list[dict[str, Any]]:
    page_region_ids = {
        str(region.get("id"))
        for region in state.get("regions", [])
        if str(region.get("page_id")) == page_id
    }
    mask_revision_lookup = {
        str(mask_revision.get("id")): mask_revision
        for mask_revision in state.get("mask_revisions", [])
        if str(mask_revision.get("region_id")) in page_region_ids
    }
    matched_mask_revisions = []
    for mask_revision_id in mask_revision_ids:
        mask_revision = mask_revision_lookup.get(mask_revision_id)
        if mask_revision is None:
            raise WorkerExecutionError(f"Could not find mask revision '{mask_revision_id}'.")
        if not mask_revision.get("is_active") or not mask_revision.get("approved"):
            raise WorkerExecutionError(
                f"Mask revision '{mask_revision_id}' is not approved and active."
            )
        matched_mask_revisions.append(mask_revision)
    return matched_mask_revisions


def _require_dict(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise WorkerExecutionError(f"Expected {label} to be an object.")
    return value


def _require_string_list(value: Any, label: str) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise WorkerExecutionError(f"Expected {label} to be an array of strings.")
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
