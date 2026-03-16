from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import Field, field_validator

from mangai_api.i18n import normalize_project_source_language, normalize_project_target_language
from mangai_api.models.common import APIModel
from mangai_api.models.region import BoundingBox


DialogueSource = Literal["ocr", "manual", "imported_script"]
DialogueStatus = Literal["draft", "reviewed", "approved", "rejected"]
TranslationStatus = Literal["draft", "reviewed", "approved"]
AssignmentOrigin = Literal["automatic", "manual"]
TextDirection = Literal["ltr", "rtl", "ttb"]


class TextStyle(APIModel):
    font_family: str = Field(min_length=1, max_length=200)
    font_fallbacks: tuple[str, ...] = ()
    font_size: int = Field(ge=1)
    leading: int = Field(ge=1)
    tracking: float
    alignment: str = Field(min_length=1, max_length=20)
    direction: TextDirection
    rotation: float
    fill: str = Field(min_length=1, max_length=32)


class DialogueRecord(APIModel):
    id: UUID
    page_id: UUID
    source: DialogueSource
    source_language: str
    content: str
    reading_order: int = Field(ge=1)
    status: DialogueStatus
    source_region_id: UUID | None = None
    created_at: datetime
    updated_at: datetime


class TranslationRecord(APIModel):
    id: UUID
    dialogue_id: UUID
    target_language: str
    text_direction: TextDirection
    provider: str = Field(min_length=1, max_length=100)
    content: str
    status: TranslationStatus
    edited_by_user: bool
    created_at: datetime
    updated_at: datetime


class AssignmentRecord(APIModel):
    id: UUID
    page_id: UUID
    dialogue_id: UUID
    region_id: UUID
    origin: AssignmentOrigin
    confidence: float | None = Field(default=None, ge=0, le=1)
    approved: bool
    created_at: datetime
    updated_at: datetime


class TextPlacementRecord(APIModel):
    id: UUID
    assignment_id: UUID
    is_active: bool
    text_box: BoundingBox
    style: TextStyle
    layout_metrics: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class ManualDialogueRequest(APIModel):
    page_id: UUID
    content: str
    source_language: str
    reading_order: int = Field(ge=1)

    @field_validator("source_language")
    @classmethod
    def validate_source_language(cls, value: str) -> str:
        return normalize_project_source_language(value)


class UpsertTranslationRequest(APIModel):
    dialogue_id: UUID
    target_language: str
    text_direction: TextDirection
    content: str
    status: TranslationStatus

    @field_validator("target_language")
    @classmethod
    def validate_target_language(cls, value: str) -> str:
        return normalize_project_target_language(value)


class UpsertAssignmentRequest(APIModel):
    dialogue_id: UUID
    region_id: UUID
    origin: AssignmentOrigin
    approved: bool


class UpsertPlacementRequest(APIModel):
    assignment_id: UUID
    text_box: BoundingBox
    style: TextStyle


class DialogueResponse(APIModel):
    dialogue: DialogueRecord


class ListDialoguesResponse(APIModel):
    dialogues: tuple[DialogueRecord, ...]


class TranslationResponse(APIModel):
    translation: TranslationRecord


class ListTranslationsResponse(APIModel):
    translations: tuple[TranslationRecord, ...]


class AssignmentResponse(APIModel):
    assignment: AssignmentRecord


class ListAssignmentsResponse(APIModel):
    assignments: tuple[AssignmentRecord, ...]


class PlacementResponse(APIModel):
    placement: TextPlacementRecord


class ListPlacementsResponse(APIModel):
    placements: tuple[TextPlacementRecord, ...]
