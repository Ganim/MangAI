from __future__ import annotations

from typing import Callable
from uuid import NAMESPACE_URL, uuid5

from mangai_workers.models import (
    CleanupJobPayload,
    CleanupJobResult,
    DetectRegionsJobPayload,
    DetectRegionsJobResult,
    MatchingJobPayload,
    MatchingJobResult,
    OcrJobPayload,
    OcrJobResult,
    TranslationJobPayload,
    TranslationJobResult,
)


class WorkerExecutionError(Exception):
    pass


def run_detect_regions_job(payload: DetectRegionsJobPayload) -> DetectRegionsJobResult:
    overlay_asset_id = uuid5(NAMESPACE_URL, f"{payload.asset_id}:overlay")
    regions_created = 2
    return DetectRegionsJobResult(
        page_id=payload.page_id,
        regions_created=regions_created,
        overlay_asset_id=overlay_asset_id,
    )


def run_generate_cleanup_job(payload: CleanupJobPayload) -> CleanupJobResult:
    mask_revision_key = ",".join(sorted(str(mask_revision_id) for mask_revision_id in payload.mask_revision_ids))
    cleaned_asset_id = uuid5(
        NAMESPACE_URL,
        f"{payload.source_asset_id}:cleanup:{mask_revision_key}",
    )
    return CleanupJobResult(
        page_id=payload.page_id,
        cleaned_asset_id=cleaned_asset_id,
        variant_asset_ids=(),
    )


def run_ocr_job(payload: OcrJobPayload) -> OcrJobResult:
    preview_asset_id = uuid5(NAMESPACE_URL, f"{payload.asset_id}:ocr-preview")
    return OcrJobResult(
        page_id=payload.page_id,
        dialogue_ids=(),
        preview_asset_id=preview_asset_id,
    )


def run_generate_translation_job(payload: TranslationJobPayload) -> TranslationJobResult:
    return TranslationJobResult(
        project_id=payload.project_id,
        translation_ids=(),
    )


def run_match_dialogue_job(payload: MatchingJobPayload) -> MatchingJobResult:
    return MatchingJobResult(
        page_id=payload.page_id,
        assignment_ids=(),
        placement_ids=(),
    )


def run_job(
    job_type: str,
    payload: dict[str, str | list[str]],
) -> dict[str, str | int | list[str]]:
    handler = JOB_HANDLERS.get(job_type)
    if handler is None:
        raise WorkerExecutionError(f"Unsupported job type '{job_type}'.")
    return handler(payload)


def _handle_detect_regions(payload: dict[str, str | list[str]]) -> dict[str, str | int]:
    parsed_payload = DetectRegionsJobPayload.from_dict(payload)
    return run_detect_regions_job(parsed_payload).to_dict()


def _handle_generate_cleanup(payload: dict[str, str | list[str]]) -> dict[str, str | list[str]]:
    parsed_payload = CleanupJobPayload.from_dict(payload)
    return run_generate_cleanup_job(parsed_payload).to_dict()


def _handle_run_ocr(payload: dict[str, str | list[str]]) -> dict[str, str | list[str]]:
    parsed_payload = OcrJobPayload.from_dict(payload)
    return run_ocr_job(parsed_payload).to_dict()


def _handle_generate_translation(payload: dict[str, str | list[str]]) -> dict[str, str | list[str]]:
    parsed_payload = TranslationJobPayload.from_dict(payload)
    return run_generate_translation_job(parsed_payload).to_dict()


def _handle_match_dialogue(payload: dict[str, str | list[str]]) -> dict[str, str | list[str]]:
    parsed_payload = MatchingJobPayload.from_dict(payload)
    return run_match_dialogue_job(parsed_payload).to_dict()


JOB_HANDLERS: dict[str, Callable[[dict[str, str] | dict[str, str | list[str]]], dict[str, str | int | list[str]]]] = {
    "detect_regions": _handle_detect_regions,
    "generate_cleanup": _handle_generate_cleanup,
    "run_ocr": _handle_run_ocr,
    "generate_translation": _handle_generate_translation,
    "match_dialogue": _handle_match_dialogue,
}
