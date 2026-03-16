from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import Field, model_validator

from mangai_api.models.common import APIModel
from mangai_api.models.region import PolygonShape


class MaskRevisionRecord(APIModel):
    id: UUID
    region_id: UUID
    version: int = Field(ge=1)
    is_active: bool
    approved: bool
    shape: PolygonShape
    created_by: UUID
    created_at: datetime
    updated_at: datetime


class CreateMaskRevisionRequest(APIModel):
    region_id: UUID
    shape: PolygonShape


class UpdateMaskRevisionRequest(APIModel):
    approved: bool | None = None
    is_active: bool | None = None
    shape: PolygonShape | None = None

    @model_validator(mode="after")
    def validate_has_one_field(self) -> "UpdateMaskRevisionRequest":
        if self.approved is None and self.is_active is None and self.shape is None:
            raise ValueError("At least one mask revision field must be updated.")
        return self


class MaskRevisionResponse(APIModel):
    mask_revision: MaskRevisionRecord


class ListMaskRevisionsResponse(APIModel):
    mask_revisions: tuple[MaskRevisionRecord, ...]
