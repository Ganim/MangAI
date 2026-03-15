from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, File, Request, UploadFile, status
from fastapi.responses import FileResponse

from mangai_api.domain_errors import UploadValidationError
from mangai_api.models.project import (
    CreateProjectRequest,
    CreateProjectResponse,
    ListProjectsResponse,
    ProjectDetailResponse,
    RegisterProjectPagesRequest,
    RegisterProjectPagesResponse,
)
from mangai_api.repositories.projects import LocalProjectStore, UploadedPageFile


router = APIRouter(prefix="/projects", tags=["projects"])


def get_project_store(request: Request) -> LocalProjectStore:
    return request.app.state.project_store


@router.get(
    "",
    response_model=ListProjectsResponse,
    summary="List projects",
)
def list_projects(
    store: LocalProjectStore = Depends(get_project_store),
) -> ListProjectsResponse:
    return ListProjectsResponse(projects=tuple(store.list_projects()))


@router.get(
    "/{project_id}",
    response_model=ProjectDetailResponse,
    summary="Get project detail",
)
def get_project_detail(
    project_id: UUID,
    store: LocalProjectStore = Depends(get_project_store),
) -> ProjectDetailResponse:
    return store.get_project_detail(project_id)


@router.post(
    "",
    response_model=CreateProjectResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a project",
)
def create_project(
    payload: CreateProjectRequest,
    store: LocalProjectStore = Depends(get_project_store),
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
    store: LocalProjectStore = Depends(get_project_store),
) -> RegisterProjectPagesResponse:
    project, pages = store.register_project_pages(project_id=project_id, payload=payload)
    return RegisterProjectPagesResponse(project=project, pages=tuple(pages))


@router.post(
    "/{project_id}/pages/upload",
    response_model=RegisterProjectPagesResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload original project pages",
)
async def upload_project_pages(
    project_id: UUID,
    files: list[UploadFile] = File(...),
    store: LocalProjectStore = Depends(get_project_store),
) -> RegisterProjectPagesResponse:
    if len(files) == 0:
        raise UploadValidationError("At least one file must be uploaded.")

    uploads: list[UploadedPageFile] = []
    for file in files:
        content = await file.read()
        uploads.append(
            UploadedPageFile(
                file_name=file.filename or "page-upload",
                mime_type=file.content_type or "",
                size_bytes=len(content),
                content=content,
            )
        )

    project, pages = store.upload_project_pages(project_id=project_id, uploads=uploads)
    return RegisterProjectPagesResponse(project=project, pages=tuple(pages))


@router.get(
    "/{project_id}/pages/{page_id}/original",
    summary="Get original uploaded page asset",
)
def get_original_page_asset(
    project_id: UUID,
    page_id: UUID,
    store: LocalProjectStore = Depends(get_project_store),
) -> FileResponse:
    asset_path, mime_type = store.get_original_asset_file(project_id=project_id, page_id=page_id)
    return FileResponse(asset_path, media_type=mime_type)
