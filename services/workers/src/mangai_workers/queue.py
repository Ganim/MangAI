from __future__ import annotations

import base64
import json
from datetime import UTC, datetime
from pathlib import Path
from time import sleep
from typing import Any
from uuid import uuid4

import cv2
import numpy as np

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
        source_language=str(project.get("source_language") or "ja-JP"),
        reading_profile=str(project.get("reading_profile") or ""),
        asset_path=source_asset_path,
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
    source_language: str,
    reading_profile: str | None,
    asset_path: Path,
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
                "panel_area": context_area,
                "balloon_group_id": None,
                "balloon_group_area": context_area,
                "panel_order": None,
                "balloon_group_order": None,
                "order_in_balloon_group": None,
                "order_in_panel": None,
                "global_reading_order": None,
                "shape": _polygon_shape(text_area),
                "created_at": timestamp,
                "updated_at": timestamp,
            }
        )
    return _apply_region_reading_metadata(
        regions,
        source_language=source_language,
        reading_profile=reading_profile,
        asset_path=asset_path,
    )


def _apply_region_reading_metadata(
    regions: list[dict[str, Any]],
    *,
    source_language: str,
    reading_profile: str | None = None,
    asset_path: Path | None = None,
    panel_boxes: list[dict[str, float]] | None = None,
) -> list[dict[str, Any]]:
    if len(regions) == 0:
        return regions
    resolved_reading_profile = _resolve_reading_profile(reading_profile, source_language)
    detected_panel_boxes = panel_boxes
    if detected_panel_boxes is None and asset_path is not None:
        detected_panel_boxes = _detect_panel_boxes_from_asset(asset_path)
    if not detected_panel_boxes:
        detected_panel_boxes = [_merge_region_areas(regions)]

    ordered_panels = _sort_panel_boxes_for_reading(
        detected_panel_boxes,
        reading_profile=resolved_reading_profile,
    )
    panel_region_groups: list[tuple[dict[str, float], list[dict[str, Any]]]] = [
        (panel_box, [])
        for panel_box in ordered_panels
    ]
    for region in regions:
        assigned_index = _assign_region_to_panel(region, ordered_panels)
        panel_region_groups[assigned_index][1].append(region)

    annotated_regions: list[dict[str, Any]] = []
    global_order = 1
    panel_order = 1
    balloon_group_order = 1
    for panel_box, panel_regions in panel_region_groups:
        if len(panel_regions) == 0:
            continue
        balloon_groups = _group_panel_regions_into_balloon_groups(
            panel_regions,
            reading_profile=resolved_reading_profile,
        )
        ordered_balloon_groups = _sort_balloon_groups_for_reading(
            balloon_groups,
            reading_profile=resolved_reading_profile,
        )
        order_in_panel = 1
        for balloon_group in ordered_balloon_groups:
            ordered_regions = _sort_regions_within_balloon_group(
                balloon_group["regions"],
                reading_profile=resolved_reading_profile,
            )
            for order_in_group, region in enumerate(ordered_regions, start=1):
                next_region = dict(region)
                next_region["panel_area"] = panel_box
                next_region["balloon_group_id"] = balloon_group["id"]
                next_region["balloon_group_area"] = balloon_group["area"]
                next_region["panel_order"] = panel_order
                next_region["balloon_group_order"] = balloon_group_order
                next_region["order_in_balloon_group"] = order_in_group
                next_region["order_in_panel"] = order_in_panel
                next_region["global_reading_order"] = global_order
                annotated_regions.append(next_region)
                global_order += 1
                order_in_panel += 1
            balloon_group_order += 1
        panel_order += 1
    return annotated_regions


def _detect_panel_boxes_from_asset(asset_path: Path) -> list[dict[str, float]]:
    try:
        asset_bytes = asset_path.read_bytes()
    except OSError:
        return []
    if len(asset_bytes) == 0:
        return []

    image = cv2.imdecode(np.frombuffer(asset_bytes, dtype=np.uint8), cv2.IMREAD_GRAYSCALE)
    if image is None or image.size == 0:
        return []
    return _detect_panel_boxes_from_grayscale(image)


def _detect_panel_boxes_from_grayscale(grayscale_image: np.ndarray) -> list[dict[str, float]]:
    height, width = grayscale_image.shape[:2]
    if width < 180 or height < 180:
        return []

    threshold_value, threshold_image = cv2.threshold(
        grayscale_image,
        0,
        255,
        cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU,
    )
    if threshold_value <= 0:
        return []
    dark_mask = threshold_image > 0
    dark_mask = cv2.morphologyEx(
        dark_mask.astype(np.uint8),
        cv2.MORPH_CLOSE,
        np.ones((3, 3), dtype=np.uint8),
    ).astype(bool)
    return _split_panel_rect_recursively(
        dark_mask,
        _bounding_box(0, 0, width, height),
        depth=0,
    )


def _split_panel_rect_recursively(
    dark_mask: np.ndarray,
    rect: dict[str, float],
    *,
    depth: int,
) -> list[dict[str, float]]:
    if depth >= 4 or rect["width"] < 180 or rect["height"] < 180:
        return [rect]

    horizontal_candidate = _find_panel_split_candidate(
        dark_mask,
        rect,
        axis="horizontal",
    )
    vertical_candidate = _find_panel_split_candidate(
        dark_mask,
        rect,
        axis="vertical",
    )

    best_candidate = None
    if horizontal_candidate is not None and vertical_candidate is not None:
        best_candidate = (
            horizontal_candidate
            if horizontal_candidate["score"] >= vertical_candidate["score"]
            else vertical_candidate
        )
    else:
        best_candidate = horizontal_candidate or vertical_candidate

    if best_candidate is None:
        return [rect]

    child_rects = _split_rect_by_candidate(rect, best_candidate)
    if child_rects is None:
        return [rect]

    leaf_rects: list[dict[str, float]] = []
    for child_rect in child_rects:
        leaf_rects.extend(
            _split_panel_rect_recursively(
                dark_mask,
                child_rect,
                depth=depth + 1,
            )
        )
    return leaf_rects


def _find_panel_split_candidate(
    dark_mask: np.ndarray,
    rect: dict[str, float],
    *,
    axis: str,
) -> dict[str, float] | None:
    x1 = int(round(rect["x"]))
    y1 = int(round(rect["y"]))
    x2 = x1 + int(round(rect["width"]))
    y2 = y1 + int(round(rect["height"]))
    crop = dark_mask[y1:y2, x1:x2]
    if crop.size == 0:
        return None

    coverage = (
        crop.mean(axis=1).astype(np.float32)
        if axis == "horizontal"
        else crop.mean(axis=0).astype(np.float32)
    )
    if coverage.size == 0:
        return None
    smoothed = np.convolve(coverage, np.ones(5, dtype=np.float32) / 5, mode="same")
    extent = crop.shape[0] if axis == "vertical" else crop.shape[1]
    length = smoothed.shape[0]
    margin = max(24, int(length * 0.08))
    threshold = 0.52

    best_candidate: dict[str, float] | None = None
    run_start: int | None = None
    for index in range(margin, max(length - margin, margin)):
        if smoothed[index] >= threshold:
            if run_start is None:
                run_start = index
            continue
        if run_start is None:
            continue
        candidate = _finalize_panel_split_candidate(
            run_start=run_start,
            run_end=index,
            smoothed=smoothed,
            rect=rect,
            axis=axis,
            extent=extent,
        )
        if candidate is not None and (
            best_candidate is None or candidate["score"] > best_candidate["score"]
        ):
            best_candidate = candidate
        run_start = None

    if run_start is not None:
        candidate = _finalize_panel_split_candidate(
            run_start=run_start,
            run_end=length - margin,
            smoothed=smoothed,
            rect=rect,
            axis=axis,
            extent=extent,
        )
        if candidate is not None and (
            best_candidate is None or candidate["score"] > best_candidate["score"]
        ):
            best_candidate = candidate

    return best_candidate


def _finalize_panel_split_candidate(
    *,
    run_start: int,
    run_end: int,
    smoothed: np.ndarray,
    rect: dict[str, float],
    axis: str,
    extent: int,
) -> dict[str, float] | None:
    band_width = run_end - run_start
    if band_width < 2:
        return None

    split_start = run_start + 1
    split_end = run_end - 1
    before_size = split_start
    after_size = len(smoothed) - split_end
    minimum_child_size = max(120, int(len(smoothed) * 0.18))
    if before_size < minimum_child_size or after_size < minimum_child_size:
        return None

    mean_coverage = float(smoothed[run_start:run_end].mean())
    score = mean_coverage * band_width * max(extent, 1)
    return {
        "axis": axis,
        "start": float(split_start),
        "end": float(split_end),
        "score": score,
    }


def _split_rect_by_candidate(
    rect: dict[str, float],
    candidate: dict[str, float],
) -> tuple[dict[str, float], dict[str, float]] | None:
    if candidate["axis"] == "horizontal":
        top_height = candidate["start"]
        bottom_y = rect["y"] + candidate["end"]
        bottom_height = rect["height"] - candidate["end"]
        if top_height <= 0 or bottom_height <= 0:
            return None
        return (
            _bounding_box(rect["x"], rect["y"], rect["width"], top_height),
            _bounding_box(rect["x"], bottom_y, rect["width"], bottom_height),
        )

    left_width = candidate["start"]
    right_x = rect["x"] + candidate["end"]
    right_width = rect["width"] - candidate["end"]
    if left_width <= 0 or right_width <= 0:
        return None
    return (
        _bounding_box(rect["x"], rect["y"], left_width, rect["height"]),
        _bounding_box(right_x, rect["y"], right_width, rect["height"]),
    )


def _sort_panel_boxes_for_reading(
    panel_boxes: list[dict[str, float]],
    *,
    reading_profile: str,
) -> list[dict[str, float]]:
    reading_direction = _get_inline_reading_direction(reading_profile)
    ordered_by_y = sorted(panel_boxes, key=lambda panel: panel["y"])
    rows: list[list[dict[str, float]]] = []
    for panel_box in ordered_by_y:
        target_row = next(
            (
                row
                for row in rows
                if _panel_box_belongs_to_row(panel_box, row)
            ),
            None,
        )
        if target_row is None:
            rows.append([panel_box])
            continue
        target_row.append(panel_box)

    ordered_panels: list[dict[str, float]] = []
    for row in rows:
        ordered_panels.extend(
            sorted(
                row,
                key=lambda panel: panel["x"],
                reverse=reading_direction == "rtl",
            )
        )
    return ordered_panels


def _panel_box_belongs_to_row(
    panel_box: dict[str, float],
    row: list[dict[str, float]],
) -> bool:
    row_bounds = _merge_bounding_boxes(row[0], row[-1] if len(row) > 1 else row[0])
    for candidate in row[1:-1]:
        row_bounds = _merge_bounding_boxes(row_bounds, candidate)
    overlap = _axis_overlap(
        panel_box["y"],
        panel_box["y"] + panel_box["height"],
        row_bounds["y"],
        row_bounds["y"] + row_bounds["height"],
    )
    min_height = min(panel_box["height"], row_bounds["height"])
    if overlap >= min_height * 0.18:
        return True
    panel_center_y = panel_box["y"] + panel_box["height"] / 2
    row_center_y = row_bounds["y"] + row_bounds["height"] / 2
    return abs(panel_center_y - row_center_y) <= min_height * 0.35


def _assign_region_to_panel(
    region: dict[str, Any],
    panel_boxes: list[dict[str, float]],
) -> int:
    region_area = _get_region_area(region, "context_area")
    center_x = region_area["x"] + region_area["width"] / 2
    center_y = region_area["y"] + region_area["height"] / 2
    containing_index = next(
        (
            index
            for index, panel_box in enumerate(panel_boxes)
            if (
                panel_box["x"] <= center_x <= panel_box["x"] + panel_box["width"]
                and panel_box["y"] <= center_y <= panel_box["y"] + panel_box["height"]
            )
        ),
        None,
    )
    if containing_index is not None:
        return containing_index

    best_index = 0
    best_overlap = -1.0
    best_distance = float("inf")
    for index, panel_box in enumerate(panel_boxes):
        overlap_x = _axis_overlap(
            region_area["x"],
            region_area["x"] + region_area["width"],
            panel_box["x"],
            panel_box["x"] + panel_box["width"],
        )
        overlap_y = _axis_overlap(
            region_area["y"],
            region_area["y"] + region_area["height"],
            panel_box["y"],
            panel_box["y"] + panel_box["height"],
        )
        overlap_area = overlap_x * overlap_y
        panel_center_x = panel_box["x"] + panel_box["width"] / 2
        panel_center_y = panel_box["y"] + panel_box["height"] / 2
        center_distance = abs(panel_center_x - center_x) + abs(panel_center_y - center_y)
        if overlap_area > best_overlap or (
            overlap_area == best_overlap and center_distance < best_distance
        ):
            best_index = index
            best_overlap = overlap_area
            best_distance = center_distance
    return best_index


def _resolve_reading_profile(reading_profile: str | None, source_language: str) -> str:
    normalized_profile = str(reading_profile or "").strip().lower()
    if normalized_profile in {"manga", "manhwa"}:
        return normalized_profile
    normalized_language = source_language.split("-", 1)[0].lower()
    return "manhwa" if normalized_language == "ko" else "manga"


def _get_inline_reading_direction(reading_profile: str) -> str:
    return "rtl" if reading_profile == "manga" else "ltr"


def _group_regions_into_columns(regions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ordered_regions = sorted(
        regions,
        key=lambda region: (
            _get_region_area(region, "context_area")["x"],
            _get_region_area(region, "context_area")["y"],
        ),
    )
    columns: list[dict[str, Any]] = []
    for region in ordered_regions:
        area = _get_region_area(region, "context_area")
        target_column = next(
            (
                column
                for column in columns
                if _should_assign_region_to_column(area, column["bounds"])
            ),
            None,
        )
        if target_column is None:
            columns.append({"regions": [region], "bounds": dict(area)})
            continue

        target_column["regions"].append(region)
        target_column["bounds"] = _merge_bounding_boxes(target_column["bounds"], area)
    return columns


def _should_assign_region_to_column(
    region_area: dict[str, Any],
    column_area: dict[str, Any],
) -> bool:
    region_x1 = float(region_area["x"])
    region_x2 = region_x1 + float(region_area["width"])
    column_x1 = float(column_area["x"])
    column_x2 = column_x1 + float(column_area["width"])
    horizontal_overlap = _axis_overlap(region_x1, region_x2, column_x1, column_x2)
    horizontal_gap = _axis_gap(region_x1, region_x2, column_x1, column_x2)
    minimum_width = max(min(float(region_area["width"]), float(column_area["width"])), 1.0)
    return (
        horizontal_overlap >= minimum_width * 0.26
        or horizontal_gap <= max(54.0, minimum_width * 0.58)
    )


def _split_column_into_panel_groups(column_regions: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    if len(column_regions) <= 1:
        return [column_regions]

    ordered_regions = sorted(
        column_regions,
        key=lambda region: (
            _get_region_area(region, "context_area")["y"],
            _get_region_area(region, "context_area")["x"],
        ),
    )
    groups: list[list[dict[str, Any]]] = [[ordered_regions[0]]]
    for region in ordered_regions[1:]:
        current_area = _get_region_area(region, "context_area")
        previous_area = _get_region_area(groups[-1][-1], "context_area")
        vertical_gap = _axis_gap(
            float(previous_area["y"]),
            float(previous_area["y"]) + float(previous_area["height"]),
            float(current_area["y"]),
            float(current_area["y"]) + float(current_area["height"]),
        )
        if vertical_gap > max(96.0, min(float(previous_area["height"]), float(current_area["height"])) * 0.75):
            groups.append([region])
            continue
        groups[-1].append(region)
    return groups


def _group_panel_regions_into_balloon_groups(
    regions: list[dict[str, Any]],
    *,
    reading_profile: str,
) -> list[dict[str, Any]]:
    ordered_regions = _sort_regions_by_area_for_reading(
        regions,
        area_key="context_area",
        reading_profile=reading_profile,
    )
    balloon_groups: list[dict[str, Any]] = []
    for region in ordered_regions:
        region_area = _get_region_area(region, "context_area")
        matching_group_indexes = [
            index
            for index, candidate_group in enumerate(balloon_groups)
            if _should_assign_region_to_balloon_group(region_area, candidate_group["area"])
        ]
        if len(matching_group_indexes) == 0:
            balloon_groups.append(
                {
                    "id": str(uuid4()),
                    "area": dict(region_area),
                    "regions": [region],
                }
            )
            continue

        primary_group = balloon_groups[matching_group_indexes[0]]
        primary_group["regions"].append(region)
        primary_group["area"] = _merge_bounding_boxes(primary_group["area"], region_area)

        for index in reversed(matching_group_indexes[1:]):
            merged_group = balloon_groups.pop(index)
            primary_group["regions"].extend(merged_group["regions"])
            primary_group["area"] = _merge_bounding_boxes(primary_group["area"], merged_group["area"])

    return balloon_groups


def _sort_balloon_groups_for_reading(
    balloon_groups: list[dict[str, Any]],
    *,
    reading_profile: str,
) -> list[dict[str, Any]]:
    return sorted(
        balloon_groups,
        key=lambda balloon_group: _build_reading_sort_key(
            balloon_group["area"],
            reading_profile=reading_profile,
        ),
    )


def _sort_regions_within_balloon_group(
    regions: list[dict[str, Any]],
    *,
    reading_profile: str,
) -> list[dict[str, Any]]:
    return _sort_regions_by_area_for_reading(
        regions,
        area_key="text_area",
        reading_profile=reading_profile,
    )


def _sort_regions_by_area_for_reading(
    regions: list[dict[str, Any]],
    *,
    area_key: str,
    reading_profile: str,
) -> list[dict[str, Any]]:
    return sorted(
        regions,
        key=lambda region: _build_reading_sort_key(
            _get_region_area(region, area_key),
            reading_profile=reading_profile,
        ),
    )


def _build_reading_sort_key(
    bounding_box: dict[str, Any],
    *,
    reading_profile: str,
) -> tuple[float, float, float, float]:
    inline_direction = _get_inline_reading_direction(reading_profile)
    return (
        round(float(bounding_box["y"]) / 24),
        -float(bounding_box["x"]) if inline_direction == "rtl" else float(bounding_box["x"]),
        float(bounding_box["y"]),
        float(bounding_box["x"]),
    )


def _should_assign_region_to_balloon_group(
    region_area: dict[str, Any],
    group_area: dict[str, Any],
) -> bool:
    overlap_x = _axis_overlap(
        float(region_area["x"]),
        float(region_area["x"]) + float(region_area["width"]),
        float(group_area["x"]),
        float(group_area["x"]) + float(group_area["width"]),
    )
    overlap_y = _axis_overlap(
        float(region_area["y"]),
        float(region_area["y"]) + float(region_area["height"]),
        float(group_area["y"]),
        float(group_area["y"]) + float(group_area["height"]),
    )
    gap_x = _axis_gap(
        float(region_area["x"]),
        float(region_area["x"]) + float(region_area["width"]),
        float(group_area["x"]),
        float(group_area["x"]) + float(group_area["width"]),
    )
    gap_y = _axis_gap(
        float(region_area["y"]),
        float(region_area["y"]) + float(region_area["height"]),
        float(group_area["y"]),
        float(group_area["y"]) + float(group_area["height"]),
    )
    minimum_width = max(min(float(region_area["width"]), float(group_area["width"])), 1.0)
    minimum_height = max(min(float(region_area["height"]), float(group_area["height"])), 1.0)
    return (
        _boxes_intersect(
            _expand_bounding_box(region_area, padding_x=max(24.0, minimum_width * 0.18), padding_y=max(24.0, minimum_height * 0.18)),
            _expand_bounding_box(group_area, padding_x=max(24.0, minimum_width * 0.18), padding_y=max(24.0, minimum_height * 0.18)),
        )
        or (
            overlap_x >= minimum_width * 0.14
            and gap_y <= max(42.0, minimum_height * 0.45)
        )
        or (
            overlap_y >= minimum_height * 0.14
            and gap_x <= max(42.0, minimum_width * 0.45)
        )
    )


def _merge_region_areas(regions: list[dict[str, Any]]) -> dict[str, float]:
    merged = _get_region_area(regions[0], "context_area")
    for region in regions[1:]:
        merged = _merge_bounding_boxes(merged, _get_region_area(region, "context_area"))
    return merged


def _merge_bounding_boxes(
    left: dict[str, Any],
    right: dict[str, Any],
) -> dict[str, float]:
    x1 = min(float(left["x"]), float(right["x"]))
    y1 = min(float(left["y"]), float(right["y"]))
    x2 = max(float(left["x"]) + float(left["width"]), float(right["x"]) + float(right["width"]))
    y2 = max(float(left["y"]) + float(left["height"]), float(right["y"]) + float(right["height"]))
    return _bounding_box(x1, y1, x2 - x1, y2 - y1)


def _expand_bounding_box(
    bounding_box: dict[str, Any],
    *,
    padding_x: float,
    padding_y: float,
) -> dict[str, float]:
    return _bounding_box(
        float(bounding_box["x"]) - padding_x,
        float(bounding_box["y"]) - padding_y,
        float(bounding_box["width"]) + (padding_x * 2),
        float(bounding_box["height"]) + (padding_y * 2),
    )


def _boxes_intersect(left: dict[str, Any], right: dict[str, Any]) -> bool:
    return not (
        float(left["x"]) + float(left["width"]) < float(right["x"])
        or float(right["x"]) + float(right["width"]) < float(left["x"])
        or float(left["y"]) + float(left["height"]) < float(right["y"])
        or float(right["y"]) + float(right["height"]) < float(left["y"])
    )


def _get_region_area(region: dict[str, Any], key: str) -> dict[str, Any]:
    return _require_dict(region.get(key) or region.get("bounding_box"), key)


def _axis_gap(left_start: float, left_end: float, right_start: float, right_end: float) -> float:
    if left_end < right_start:
        return right_start - left_end
    if right_end < left_start:
        return left_start - right_end
    return 0.0


def _axis_overlap(left_start: float, left_end: float, right_start: float, right_end: float) -> float:
    return max(0.0, min(left_end, right_end) - max(left_start, right_start))


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
                "panel_area": region.get("panel_area") or region.get("context_area") or region["bounding_box"],
                "balloon_group_id": region.get("balloon_group_id"),
                "balloon_group_area": region.get("balloon_group_area") or region.get("context_area") or region["bounding_box"],
                "panel_order": region.get("panel_order"),
                "balloon_group_order": region.get("balloon_group_order"),
                "order_in_balloon_group": region.get("order_in_balloon_group"),
                "order_in_panel": region.get("order_in_panel"),
                "global_reading_order": region.get("global_reading_order"),
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
        panel_order=(
            int(region["panel_order"])
            if region.get("panel_order") is not None
            else None
        ),
        balloon_group_order=(
            int(region["balloon_group_order"])
            if region.get("balloon_group_order") is not None
            else None
        ),
        order_in_balloon_group=(
            int(region["order_in_balloon_group"])
            if region.get("order_in_balloon_group") is not None
            else None
        ),
        order_in_panel=(
            int(region["order_in_panel"])
            if region.get("order_in_panel") is not None
            else None
        ),
        global_reading_order=(
            int(region["global_reading_order"])
            if region.get("global_reading_order") is not None
            else None
        ),
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
