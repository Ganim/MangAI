from uuid import NAMESPACE_URL, uuid5

import pytest

from mangai_workers.models import DetectRegionsJobPayload, OcrJobPayload
from mangai_workers.runner import WorkerExecutionError, run_detect_regions_job, run_job, run_ocr_job


def test_detect_regions_runner_returns_deterministic_overlay_id() -> None:
    payload = DetectRegionsJobPayload.from_dict(
        {
            "job_id": "11111111-1111-4111-8111-111111111111",
            "page_id": "22222222-2222-4222-8222-222222222222",
            "asset_id": "33333333-3333-4333-8333-333333333333",
        }
    )

    result = run_detect_regions_job(payload)

    assert result.page_id == payload.page_id
    assert result.regions_created == 2
    assert result.overlay_asset_id == uuid5(NAMESPACE_URL, f"{payload.asset_id}:overlay")


def test_run_job_dispatches_detect_regions_payload() -> None:
    result = run_job(
        "detect_regions",
        {
            "job_id": "11111111-1111-4111-8111-111111111111",
            "page_id": "22222222-2222-4222-8222-222222222222",
            "asset_id": "33333333-3333-4333-8333-333333333333",
        },
    )

    assert result["page_id"] == "22222222-2222-4222-8222-222222222222"
    assert result["regions_created"] == 2


def test_run_ocr_job_returns_deterministic_preview_id() -> None:
    payload = OcrJobPayload.from_dict(
        {
            "job_id": "11111111-1111-4111-8111-111111111111",
            "page_id": "22222222-2222-4222-8222-222222222222",
            "asset_id": "33333333-3333-4333-8333-333333333333",
            "region_ids": ["44444444-4444-4444-8444-444444444444"],
            "source_language": "ja-JP",
        }
    )

    result = run_ocr_job(payload)

    assert result.page_id == payload.page_id
    assert result.dialogue_ids == ()
    assert result.preview_asset_id == uuid5(NAMESPACE_URL, f"{payload.asset_id}:ocr-preview")


def test_run_job_dispatches_ocr_payload() -> None:
    result = run_job(
        "run_ocr",
        {
            "job_id": "11111111-1111-4111-8111-111111111111",
            "page_id": "22222222-2222-4222-8222-222222222222",
            "asset_id": "33333333-3333-4333-8333-333333333333",
            "region_ids": ["44444444-4444-4444-8444-444444444444"],
            "source_language": "ja-JP",
        },
    )

    assert result["page_id"] == "22222222-2222-4222-8222-222222222222"
    assert result["dialogue_ids"] == []


def test_run_job_rejects_unknown_type() -> None:
    with pytest.raises(WorkerExecutionError):
        run_job("export_project", {})
