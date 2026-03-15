from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, status

from mangai_api.constants import SCHEMA_VERSION
from mangai_api.models.project import CreateProjectRequest, CreateProjectResponse, ProjectSummary


router = APIRouter(prefix="/projects", tags=["projects"])


@router.post(
    "",
    response_model=CreateProjectResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a project",
)
def create_project(payload: CreateProjectRequest) -> CreateProjectResponse:
    project = ProjectSummary(
        id=uuid4(),
        schema_version=SCHEMA_VERSION,
        name=payload.name,
        status="draft",
        source_language=payload.source_language,
        target_language=payload.target_language,
        target_text_direction=payload.target_text_direction,
    )
    return CreateProjectResponse(project=project)
