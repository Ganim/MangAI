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
from mangai_workers.ocr import OcrCandidateRegion, extract_ocr_lines_from_asset
from mangai_workers.runner import WorkerExecutionError, run_job
from mangai_workers.translation import TranslationCandidate, translate_dialogues


PENDING_JOB_STATUSES = {"queued", "running"}
STATE_REPLACE_ATTEMPTS = 8
STATE_REPLACE_DELAY_SECONDS = 0.05


def process_next_job(settings: WorkerSettings) -> dict[str, Any] | None:
    state_path = settings.data_dir / "state.json"
    if not state_path.exists():
        return None

    state = _load_state(state_path)
    jobs = state.setdefault("jobs", [])
    current_timestamp = datetime.now(UTC)
    job = next(
        (
            candidate
            for candidate in jobs
            if _is_job_pollable(
                candidate,
                current_timestamp=current_timestamp,
                stalled_after_seconds=settings.stalled_job_timeout_seconds,
            )
        ),
        None,
    )
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

    if job_type == "run_ocr":
        _apply_run_ocr_result(
            settings=settings,
            state=state,
            job=job,
            result=result,
        )
        return result

    if job_type == "generate_translation":
        _apply_generate_translation_result(
            settings=settings,
            state=state,
            job=job,
            result=result,
        )
        return result

    if job_type == "match_dialogue":
        _apply_match_dialogue_result(
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

    project = _find_by_id(state.get("projects", []), project_id, "project")
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
        source_language=str(project.get("source_language") or "ja-JP"),
        settings=settings,
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


def _apply_run_ocr_result(
    settings: WorkerSettings,
    state: dict[str, Any],
    job: dict[str, Any],
    result: dict[str, Any],
) -> None:
    project_id = str(job["project_id"])
    page_id = str(job["page_id"])
    payload = _require_dict(job.get("payload"), "job payload")
    asset_id = str(payload["asset_id"])
    region_ids = _require_string_list(payload.get("region_ids"), "region_ids")
    source_language = str(payload.get("source_language") or "ja-JP")

    project = _find_by_id(state.get("projects", []), project_id, "project")
    page = _find_by_id(state.get("pages", []), page_id, "page")
    asset = _find_by_id(state.get("assets", []), asset_id, "asset")
    source_asset_path = settings.data_dir / "assets" / str(asset["storage_key"])

    region_lookup = {
        str(region.get("id")): region
        for region in state.get("regions", [])
        if str(region.get("page_id")) == page_id
    }
    candidate_regions = [
        _build_ocr_candidate_region(region_lookup, region_id)
        for region_id in region_ids
    ]

    extracted_lines = extract_ocr_lines_from_asset(
        asset_path=source_asset_path,
        source_language=source_language,
        regions=candidate_regions,
        settings=settings,
    )

    replaced_dialogues = [
        dialogue
        for dialogue in state.get("dialogues", [])
        if str(dialogue.get("page_id")) == page_id
        and str(dialogue.get("source")) == "ocr"
        and str(dialogue.get("source_region_id") or "") in set(region_ids)
    ]
    replaced_dialogue_ids = {str(dialogue.get("id")) for dialogue in replaced_dialogues}
    replaced_assignment_ids = {
        str(assignment.get("id"))
        for assignment in state.get("assignments", [])
        if str(assignment.get("dialogue_id")) in replaced_dialogue_ids
    }

    state["dialogues"] = [
        dialogue
        for dialogue in state.get("dialogues", [])
        if str(dialogue.get("id")) not in replaced_dialogue_ids
    ]
    state["translations"] = [
        translation
        for translation in state.get("translations", [])
        if str(translation.get("dialogue_id")) not in replaced_dialogue_ids
    ]
    state["assignments"] = [
        assignment
        for assignment in state.get("assignments", [])
        if str(assignment.get("id")) not in replaced_assignment_ids
        and str(assignment.get("dialogue_id")) not in replaced_dialogue_ids
    ]
    state["placements"] = [
        placement
        for placement in state.get("placements", [])
        if str(placement.get("assignment_id")) not in replaced_assignment_ids
    ]

    timestamp = _utcnow_iso()
    next_reading_order = (
        max(
            (
                int(dialogue.get("reading_order") or 0)
                for dialogue in state.get("dialogues", [])
                if str(dialogue.get("page_id")) == page_id
            ),
            default=0,
        )
        + 1
    )
    new_dialogues: list[dict[str, Any]] = []
    for offset, line in enumerate(extracted_lines):
        new_dialogues.append(
            {
                "id": str(uuid4()),
                "page_id": page_id,
                "source": "ocr",
                "source_language": source_language,
                "content": line.text,
                "reading_order": next_reading_order + offset,
                "status": "draft",
                "source_region_id": line.region_id,
                "created_at": timestamp,
                "updated_at": timestamp,
            }
        )

    preview_asset = _build_ocr_preview_asset(
        project_id=project_id,
        page_id=page_id,
        preview_asset_id=str(result["preview_asset_id"]),
        source_language=source_language,
        extracted_lines=extracted_lines,
        settings=settings,
        timestamp=timestamp,
    )

    state["dialogues"] = [*state.get("dialogues", []), *new_dialogues]
    preserved_assets = [
        candidate_asset
        for candidate_asset in state.get("assets", [])
        if candidate_asset.get("id") != preview_asset["id"]
    ]
    state["assets"] = [*preserved_assets, preview_asset]

    page["status"] = _max_page_status(page.get("status"), "text_ready")
    page["updated_at"] = timestamp
    project["updated_at"] = timestamp
    result["dialogue_ids"] = [dialogue["id"] for dialogue in new_dialogues]


def _apply_generate_translation_result(
    settings: WorkerSettings,
    state: dict[str, Any],
    job: dict[str, Any],
    result: dict[str, Any],
) -> None:
    project_id = str(job["project_id"])
    page_id = str(job["page_id"])
    payload = _require_dict(job.get("payload"), "job payload")
    dialogue_ids = _require_string_list(payload.get("dialogue_ids"), "dialogue_ids")
    target_language = str(payload.get("target_language") or "pt-BR")

    project = _find_by_id(state.get("projects", []), project_id, "project")
    page = _find_by_id(state.get("pages", []), page_id, "page")
    dialogue_lookup = {
        str(dialogue.get("id")): dialogue
        for dialogue in state.get("dialogues", [])
        if str(dialogue.get("page_id")) == page_id
    }
    translation_candidates = [
        TranslationCandidate(
            dialogue_id=dialogue_id,
            content=str(dialogue_lookup[dialogue_id].get("content") or ""),
            reading_order=int(dialogue_lookup[dialogue_id].get("reading_order") or 0),
        )
        for dialogue_id in dialogue_ids
        if dialogue_id in dialogue_lookup
    ]
    if len(translation_candidates) == 0:
        raise WorkerExecutionError("Could not find any dialogue candidates for automatic translation.")

    translated_outputs = translate_dialogues(
        source_language=str(payload.get("source_language") or "ja-JP"),
        target_language=target_language,
        dialogues=translation_candidates,
        settings=settings,
    )

    timestamp = _utcnow_iso()
    next_translations = list(state.get("translations", []))
    translation_ids: list[str] = []
    target_direction = str(project.get("target_text_direction") or "ltr")

    for translated_output in translated_outputs:
        existing_translation = next(
            (
                candidate
                for candidate in next_translations
                if str(candidate.get("dialogue_id")) == translated_output.dialogue_id
                and str(candidate.get("target_language")) == target_language
            ),
            None,
        )
        if (
            existing_translation is not None
            and bool(existing_translation.get("edited_by_user"))
            and str(existing_translation.get("content") or "").strip() != ""
        ):
            translation_ids.append(str(existing_translation["id"]))
            continue

        if existing_translation is None:
            translation_record = {
                "id": str(uuid4()),
                "dialogue_id": translated_output.dialogue_id,
                "target_language": target_language,
                "text_direction": target_direction,
                "provider": "worker_fallback",
                "content": translated_output.content,
                "status": "draft",
                "edited_by_user": False,
                "created_at": timestamp,
                "updated_at": timestamp,
            }
            next_translations.append(translation_record)
            translation_ids.append(translation_record["id"])
            continue

        existing_translation.update(
            {
                "text_direction": target_direction,
                "provider": "worker_fallback",
                "content": translated_output.content,
                "status": "draft",
                "edited_by_user": False,
                "updated_at": timestamp,
            }
        )
        translation_ids.append(str(existing_translation["id"]))

    state["translations"] = next_translations
    page["status"] = _max_page_status(page.get("status"), "text_ready")
    page["updated_at"] = timestamp
    project["updated_at"] = timestamp
    result["translation_ids"] = translation_ids


def _apply_match_dialogue_result(
    state: dict[str, Any],
    job: dict[str, Any],
    result: dict[str, Any],
) -> None:
    project_id = str(job["project_id"])
    page_id = str(job["page_id"])
    payload = _require_dict(job.get("payload"), "job payload")
    dialogue_ids = _require_string_list(payload.get("dialogue_ids"), "dialogue_ids")
    region_ids = _require_string_list(payload.get("region_ids"), "region_ids")

    project = _find_by_id(state.get("projects", []), project_id, "project")
    page = _find_by_id(state.get("pages", []), page_id, "page")
    dialogue_lookup = {
        str(dialogue.get("id")): dialogue
        for dialogue in state.get("dialogues", [])
        if str(dialogue.get("page_id")) == page_id
    }
    region_lookup = {
        str(region.get("id")): region
        for region in state.get("regions", [])
        if str(region.get("page_id")) == page_id
    }
    ordered_regions = [region_lookup[region_id] for region_id in region_ids if region_id in region_lookup]
    if len(ordered_regions) == 0:
        raise WorkerExecutionError("Could not find any candidate regions for automatic matching.")

    ordered_dialogues = sorted(
        [dialogue_lookup[dialogue_id] for dialogue_id in dialogue_ids if dialogue_id in dialogue_lookup],
        key=lambda dialogue: (int(dialogue.get("reading_order") or 0), str(dialogue.get("id"))),
    )
    if len(ordered_dialogues) == 0:
        raise WorkerExecutionError("Could not find any candidate dialogues for automatic matching.")

    timestamp = _utcnow_iso()
    occupied_region_ids = {
        str(assignment.get("region_id"))
        for assignment in state.get("assignments", [])
        if str(assignment.get("page_id")) == page_id and bool(assignment.get("approved"))
    }
    available_region_ids = [
        str(region.get("id"))
        for region in ordered_regions
        if str(region.get("id")) not in occupied_region_ids
    ]
    next_assignments = list(state.get("assignments", []))
    next_placements = list(state.get("placements", []))
    assignment_ids: list[str] = []
    placement_ids: list[str] = []

    for dialogue in ordered_dialogues:
        preferred_region_id = str(dialogue.get("source_region_id") or "")
        matched_region_id = None
        if preferred_region_id in available_region_ids:
            matched_region_id = preferred_region_id
        elif len(available_region_ids) > 0:
            matched_region_id = available_region_ids[0]

        if matched_region_id is None:
            continue

        available_region_ids = [
            region_id for region_id in available_region_ids if region_id != matched_region_id
        ]
        region = region_lookup[matched_region_id]
        existing_assignment = next(
            (
                candidate
                for candidate in next_assignments
                if str(candidate.get("page_id")) == page_id
                and str(candidate.get("dialogue_id")) == str(dialogue.get("id"))
            ),
            None,
        )
        assignment_confidence = 0.92 if preferred_region_id == matched_region_id else 0.61
        if existing_assignment is None:
            assignment_record = {
                "id": str(uuid4()),
                "page_id": page_id,
                "dialogue_id": str(dialogue["id"]),
                "region_id": matched_region_id,
                "origin": "automatic",
                "confidence": assignment_confidence,
                "approved": True,
                "created_at": timestamp,
                "updated_at": timestamp,
            }
            next_assignments.append(assignment_record)
        else:
            existing_assignment.update(
                {
                    "region_id": matched_region_id,
                    "origin": "automatic",
                    "confidence": assignment_confidence,
                    "approved": True,
                    "updated_at": timestamp,
                }
            )
            assignment_record = existing_assignment

        assignment_ids.append(str(assignment_record["id"]))
        existing_placement = next(
            (
                candidate
                for candidate in next_placements
                if str(candidate.get("assignment_id")) == str(assignment_record["id"])
                and bool(candidate.get("is_active"))
            ),
            None,
        )
        if existing_placement is None:
            placement_area = _require_dict(
                region.get("context_area") or region.get("bounding_box"),
                "region context_area",
            )
            default_style = _build_default_text_style(
                region=placement_area,
                target_language=str(project.get("target_language") or "pt-BR"),
                text_direction=str(project.get("target_text_direction") or "ltr"),
            )
            placement_record = {
                "id": str(uuid4()),
                "assignment_id": str(assignment_record["id"]),
                "is_active": True,
                "text_box": placement_area,
                "style": default_style,
                "layout_metrics": {
                    "mode": "automatic",
                    "source": "match_dialogue",
                    "font_size": default_style["font_size"],
                },
                "created_at": timestamp,
                "updated_at": timestamp,
            }
            next_placements.append(placement_record)
        else:
            placement_record = existing_placement

        placement_ids.append(str(placement_record["id"]))

    if len(assignment_ids) == 0:
        raise WorkerExecutionError("Automatic matching could not assign any dialogue to the available regions.")

    state["assignments"] = next_assignments
    state["placements"] = next_placements
    page["status"] = _max_page_status(page.get("status"), "typeset_ready")
    page["updated_at"] = timestamp
    project["updated_at"] = timestamp
    result["assignment_ids"] = assignment_ids
    result["placement_ids"] = placement_ids


def _build_detected_regions(
    *,
    page_id: str,
    detected_candidates: list[Any],
    timestamp: str,
) -> list[dict[str, Any]]:
    regions: list[dict[str, Any]] = []
    for candidate in detected_candidates:
        text_area = _bounding_box(
            candidate.bounding_box["x"],
            candidate.bounding_box["y"],
            candidate.bounding_box["width"],
            candidate.bounding_box["height"],
        )
        context_source = candidate.context_area or candidate.bounding_box
        context_area = _bounding_box(
            context_source["x"],
            context_source["y"],
            context_source["width"],
            context_source["height"],
        )
        regions.append(
            {
                "id": str(uuid4()),
                "page_id": page_id,
                "type": candidate.type,
                "origin": "detected",
                "state": "draft",
                "confidence": candidate.confidence,
                "cleanup_strategy": candidate.cleanup_strategy,
                "cleanup_confidence": candidate.cleanup_confidence,
                "bounding_box": text_area,
                "text_area": text_area,
                "context_area": context_area,
                "shape": _polygon_shape(text_area),
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
                "cleanup_strategy": region.get("cleanup_strategy"),
                "cleanup_confidence": region.get("cleanup_confidence"),
                "bounding_box": region["bounding_box"],
                "text_area": region.get("text_area") or region["bounding_box"],
                "context_area": region.get("context_area") or region["bounding_box"],
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


def _build_ocr_candidate_region(
    region_lookup: dict[str, dict[str, Any]],
    region_id: str,
) -> OcrCandidateRegion:
    region = region_lookup.get(region_id)
    if region is None:
        raise WorkerExecutionError(f"Could not find OCR region '{region_id}'.")
    bounding_box = _require_dict(
        region.get("text_area") or region.get("bounding_box"),
        "region text_area",
    )
    return OcrCandidateRegion(
        id=region_id,
        type=str(region.get("type") or "unknown"),
        confidence=(
            float(region["confidence"])
            if region.get("confidence") is not None
            else None
        ),
        x=float(bounding_box.get("x") or 0),
        y=float(bounding_box.get("y") or 0),
        width=float(bounding_box.get("width") or 1),
        height=float(bounding_box.get("height") or 1),
    )


def _build_ocr_preview_asset(
    *,
    project_id: str,
    page_id: str,
    preview_asset_id: str,
    source_language: str,
    extracted_lines: list[Any],
    settings: WorkerSettings,
    timestamp: str,
) -> dict[str, Any]:
    storage_key = str(Path(project_id) / f"{preview_asset_id}.json")
    asset_path = settings.data_dir / "assets" / storage_key
    asset_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "page_id": page_id,
        "source_language": source_language,
        "dialogues_created": len(extracted_lines),
        "lines": [
            {
                "region_id": line.region_id,
                "text": line.text,
                "confidence": line.confidence,
            }
            for line in extracted_lines
        ],
    }
    serialized = json.dumps(payload, indent=2).encode("utf-8")
    asset_path.write_bytes(serialized)
    return {
        "id": preview_asset_id,
        "project_id": project_id,
        "page_id": page_id,
        "kind": "ocr_preview",
        "file_name": f"{page_id}-ocr-preview.json",
        "storage_key": storage_key,
        "mime_type": "application/json",
        "size_bytes": len(serialized),
        "created_at": timestamp,
        "updated_at": timestamp,
    }


def _build_default_text_style(
    *,
    region: dict[str, Any],
    target_language: str,
    text_direction: str,
) -> dict[str, Any]:
    region_height = max(float(region.get("height") or 1), 1)
    font_size = max(18, round(region_height * 0.22))
    leading = max(font_size + 4, round(font_size * 1.2))
    font_family = "CC Meanwhile" if target_language.startswith("pt") else "Komika Axis"
    return {
        "font_family": font_family,
        "font_fallbacks": ["Arial", "sans-serif"],
        "font_size": font_size,
        "leading": leading,
        "tracking": 0,
        "alignment": "center",
        "direction": text_direction,
        "rotation": 0,
        "fill": "#111111",
    }


def _max_page_status(current_status: Any, next_status: str) -> str:
    ordered_statuses = {
        "uploaded": 0,
        "analyzed": 1,
        "cleanup_ready": 2,
        "cleaned": 3,
        "text_ready": 4,
        "typeset_ready": 5,
        "export_ready": 6,
        "error": 7,
    }
    current_value = str(current_status or "uploaded")
    if ordered_statuses.get(current_value, 0) > ordered_statuses[next_status]:
        return current_value
    return next_status


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
    _replace_file_with_retry(temp_path, state_path)


def _replace_file_with_retry(
    source_path: Path,
    target_path: Path,
    *,
    attempts: int = STATE_REPLACE_ATTEMPTS,
    delay_seconds: float = STATE_REPLACE_DELAY_SECONDS,
) -> None:
    for attempt in range(attempts):
        try:
            source_path.replace(target_path)
            return
        except PermissionError:
            if attempt == attempts - 1:
                raise
            sleep(delay_seconds)


def _utcnow_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _is_job_pollable(
    job: dict[str, Any],
    *,
    current_timestamp: datetime,
    stalled_after_seconds: float,
) -> bool:
    status = str(job.get("status") or "")
    if status == "queued":
        return True
    if status != "running":
        return False

    updated_at = job.get("updated_at")
    if not isinstance(updated_at, str):
        return False

    try:
        normalized_updated_at = updated_at.replace("Z", "+00:00")
        updated_at_timestamp = datetime.fromisoformat(normalized_updated_at)
    except ValueError:
        return False

    return (current_timestamp - updated_at_timestamp).total_seconds() >= stalled_after_seconds
