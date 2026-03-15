from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import Field, field_validator, model_validator

from mangai_api.constants import SCHEMA_VERSION, SUPPORTED_TEXT_DIRECTIONS
from mangai_api.i18n import (
    infer_text_direction,
    normalize_project_source_language,
    normalize_project_target_language,
)
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
    def validate_language_tag(cls, value: str, info) -> str:
        if info.field_name == "source_language":
            return normalize_project_source_language(value)
        return normalize_project_target_language(value)

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


class ProjectPage(APIModel):
    id: UUID
    project_id: UUID
    index: int = Field(ge=1)
    file_name: str
    mime_type: str
    size_bytes: int = Field(ge=1)
    width: int | None = Field(default=None, ge=1)
    height: int | None = Field(default=None, ge=1)
    status: Literal["uploaded"]
    original_asset_path: str = Field(min_length=1)
    created_at: datetime
    updated_at: datetime


class ProjectDetailResponse(APIModel):
    project: ProjectSummary
    pages: tuple[ProjectPage, ...]


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


class StoredProjectAsset(APIModel):
    id: UUID
    project_id: UUID
    page_id: UUID
    kind: Literal["original"]
    file_name: str
    storage_key: str
    mime_type: str
    size_bytes: int = Field(ge=1)
    created_at: datetime
    updated_at: datetime


class StoredProjectState(APIModel):
    projects: tuple[ProjectSummary, ...] = ()
    pages: tuple[ProjectPage, ...] = ()
    assets: tuple[StoredProjectAsset, ...] = ()


class PageUploadDraft(ProjectPage):
    pass


class RegisterUploadedProjectPage(APIModel):
    id: UUID
    project_id: UUID
    index: int = Field(ge=1)
    file_name: str
    mime_type: str
    size_bytes: int = Field(ge=1)
    width: int | None = Field(default=None, ge=1)
    height: int | None = Field(default=None, ge=1)
    status: Literal["uploaded"]
    original_asset_path: str = Field(min_length=1)
    created_at: datetime
    updated_at: datetime


class RegisterProjectPagesResponse(APIModel):
    project: ProjectSummary
    pages: tuple[RegisterUploadedProjectPage, ...]


class CreateProjectResponse(APIModel):
    project: ProjectSummary
