from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import Field, field_validator

from mangai_api.models.common import APIModel


JobType = Literal[
    "detect_regions",
    "generate_cleanup",
    "run_ocr",
    "generate_translation",
    "match_dialogue",
    "generate_typesetting",
    "export_project",
]

JobStatus = Literal["queued", "running", "succeeded", "failed", "canceled"]


class JobRecord(APIModel):
    id: UUID
    project_id: UUID
    page_id: UUID | None = None
    type: JobType
    status: JobStatus
    payload: dict[str, Any]
    result: dict[str, Any] | None = None
    error_code: str | None = None
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime


class CreatePageJobRequest(APIModel):
    type: JobType

    @field_validator("type")
    @classmethod
    def validate_supported_type(cls, value: JobType) -> JobType:
        if value not in {"detect_regions", "generate_cleanup", "run_ocr", "generate_translation", "match_dialogue"}:
            raise ValueError(
                "Only detect_regions, generate_cleanup, run_ocr, generate_translation, and match_dialogue jobs are currently supported."
            )
        return value


class JobResponse(APIModel):
    job: JobRecord


class ListJobsResponse(APIModel):
    jobs: tuple[JobRecord, ...]
