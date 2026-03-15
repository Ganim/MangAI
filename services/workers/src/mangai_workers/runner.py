from __future__ import annotations

from typing import Callable
from uuid import NAMESPACE_URL, uuid5

from mangai_workers.models import DetectRegionsJobPayload, DetectRegionsJobResult


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


def run_job(job_type: str, payload: dict[str, str]) -> dict[str, str | int]:
    handler = JOB_HANDLERS.get(job_type)
    if handler is None:
        raise WorkerExecutionError(f"Unsupported job type '{job_type}'.")
    return handler(payload)


def _handle_detect_regions(payload: dict[str, str]) -> dict[str, str | int]:
    parsed_payload = DetectRegionsJobPayload.from_dict(payload)
    return run_detect_regions_job(parsed_payload).to_dict()


JOB_HANDLERS: dict[str, Callable[[dict[str, str]], dict[str, str | int]]] = {
    "detect_regions": _handle_detect_regions,
}
