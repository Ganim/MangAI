from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import Field, field_validator, model_validator

from mangai_api.constants import SCHEMA_VERSION, SUPPORTED_TEXT_DIRECTIONS
from mangai_api.i18n import infer_text_direction, normalize_language_tag
from mangai_api.models.common import APIModel


ProjectStatus = Literal["draft", "active", "archived"]
TextDirection = Literal["ltr", "rtl", "ttb"]


class CreateProjectRequest(APIModel):
    name: str = Field(min_length=1, max_length=200)
    source_language: str
    target_language: str
    target_text_direction: TextDirection | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Project name cannot be empty.")
        return stripped

    @field_validator("source_language", "target_language")
    @classmethod
    def validate_language_tag(cls, value: str) -> str:
        return normalize_language_tag(value)

    @model_validator(mode="after")
    def apply_direction_default(self) -> "CreateProjectRequest":
        if self.target_text_direction is None:
            object.__setattr__(
                self,
                "target_text_direction",
                infer_text_direction(self.target_language),
            )
        if self.target_text_direction not in SUPPORTED_TEXT_DIRECTIONS:
            raise ValueError("Unsupported target text direction.")
        return self


class ProjectSummary(APIModel):
    id: UUID
    schema_version: Literal[SCHEMA_VERSION]
    name: str
    status: ProjectStatus
    source_language: str
    target_language: str
    target_text_direction: TextDirection
    page_count: int = Field(ge=0)
    created_at: datetime
    updated_at: datetime


class ListProjectsResponse(APIModel):
    projects: tuple[ProjectSummary, ...]


class RegisterProjectPageRequest(APIModel):
    file_name: str = Field(min_length=1, max_length=255)
    mime_type: str = Field(min_length=1, max_length=100)
    size_bytes: int = Field(ge=1)
    width: int | None = Field(default=None, ge=1)
    height: int | None = Field(default=None, ge=1)

    @field_validator("file_name", "mime_type")
    @classmethod
    def validate_non_empty_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Value cannot be empty.")
        return stripped


class RegisterProjectPagesRequest(APIModel):
    pages: tuple[RegisterProjectPageRequest, ...] = Field(min_length=1)


class PageUploadDraft(APIModel):
    id: UUID
    project_id: UUID
    index: int = Field(ge=1)
    file_name: str
    mime_type: str
    size_bytes: int = Field(ge=1)
    width: int | None = Field(default=None, ge=1)
    height: int | None = Field(default=None, ge=1)
    status: Literal["uploaded"]
    created_at: datetime
    updated_at: datetime


class RegisterProjectPagesResponse(APIModel):
    project: ProjectSummary
    pages: tuple[PageUploadDraft, ...]


class CreateProjectResponse(APIModel):
    project: ProjectSummary
