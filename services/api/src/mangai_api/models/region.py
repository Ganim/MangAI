from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import Field, model_validator

from mangai_api.models.common import APIModel


RegionType = Literal["speech_balloon", "narration_box", "free_text", "sfx", "unknown"]
RegionOrigin = Literal["detected", "user_created", "user_split", "user_merged"]
RegionState = Literal["draft", "reviewed", "approved", "rejected"]
CleanupStrategy = Literal["solid_fill", "background_reconstruction"]


class BoundingBox(APIModel):
    x: float = Field(ge=0)
    y: float = Field(ge=0)
    width: float = Field(ge=0)
    height: float = Field(ge=0)


class PolygonPoint(APIModel):
    x: float = Field(ge=0)
    y: float = Field(ge=0)


class PolygonShape(APIModel):
    type: Literal["polygon"]
    points: tuple[PolygonPoint, ...] = Field(min_length=4)


class RegionRecord(APIModel):
    id: UUID
    page_id: UUID
    type: RegionType
    origin: RegionOrigin
    state: RegionState
    confidence: float | None = Field(default=None, ge=0, le=1)
    cleanup_strategy: CleanupStrategy | None = None
    cleanup_confidence: float | None = Field(default=None, ge=0, le=1)
    bounding_box: BoundingBox
    text_area: BoundingBox | None = None
    context_area: BoundingBox | None = None
    shape: PolygonShape
    created_at: datetime
    updated_at: datetime

    @model_validator(mode="before")
    @classmethod
    def populate_area_defaults(cls, value: object) -> object:
        if not isinstance(value, dict):
            return value

        next_value = dict(value)
        bounding_box = next_value.get("bounding_box")
        if next_value.get("text_area") is None:
            next_value["text_area"] = bounding_box
        if next_value.get("context_area") is None:
            next_value["context_area"] = bounding_box
        return next_value


class CreateRegionRequest(APIModel):
    type: RegionType
    bounding_box: BoundingBox


class UpdateRegionRequest(APIModel):
    type: RegionType | None = None
    state: RegionState | None = None
    bounding_box: BoundingBox | None = None
    text_area: BoundingBox | None = None
    context_area: BoundingBox | None = None

    @model_validator(mode="after")
    def validate_has_one_field(self) -> "UpdateRegionRequest":
        if (
            self.type is None
            and self.state is None
            and self.bounding_box is None
            and self.text_area is None
            and self.context_area is None
        ):
            raise ValueError("At least one region field must be updated.")
        return self


class RegionResponse(APIModel):
    region: RegionRecord


class ListRegionsResponse(APIModel):
    regions: tuple[RegionRecord, ...]
