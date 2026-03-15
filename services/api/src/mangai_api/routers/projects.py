from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Request, status

from mangai_api.models.project import (
    CreateProjectRequest,
    CreateProjectResponse,
    ListProjectsResponse,
    RegisterProjectPagesRequest,
    RegisterProjectPagesResponse,
)
from mangai_api.repositories.projects import InMemoryProjectStore


router = APIRouter(prefix="/projects", tags=["projects"])


def get_project_store(request: Request) -> InMemoryProjectStore:
    return request.app.state.project_store


@router.get(
    "",
    response_model=ListProjectsResponse,
    summary="List projects",
)
def list_projects(
    store: InMemoryProjectStore = Depends(get_project_store),
) -> ListProjectsResponse:
    return ListProjectsResponse(projects=tuple(store.list_projects()))


@router.post(
    "",
    response_model=CreateProjectResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a project",
)
def create_project(
    payload: CreateProjectRequest,
    store: InMemoryProjectStore = Depends(get_project_store),
) -> CreateProjectResponse:
    return CreateProjectResponse(project=store.create_project(payload))


@router.post(
    "/{project_id}/pages",
    response_model=RegisterProjectPagesResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register uploaded project pages",
)
def register_project_pages(
    project_id: UUID,
    payload: RegisterProjectPagesRequest,
    store: InMemoryProjectStore = Depends(get_project_store),
) -> RegisterProjectPagesResponse:
    project, pages = store.register_project_pages(project_id=project_id, payload=payload)
    return RegisterProjectPagesResponse(project=project, pages=tuple(pages))
