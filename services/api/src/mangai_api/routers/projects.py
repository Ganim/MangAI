from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, File, Request, UploadFile, status
from fastapi.responses import FileResponse

from mangai_api.domain_errors import UploadValidationError
from mangai_api.models.job import CreatePageJobRequest, JobResponse, ListJobsResponse
from mangai_api.models.mask import (
    CreateMaskRevisionRequest,
    ListMaskRevisionsResponse,
    MaskRevisionResponse,
    UpdateMaskRevisionRequest,
)
from mangai_api.models.project import (
    CreateProjectRequest,
    CreateProjectResponse,
    ListProjectsResponse,
    ProjectDetailResponse,
    RegisterProjectPagesRequest,
    RegisterProjectPagesResponse,
)
from mangai_api.models.region import (
    CreateRegionRequest,
    ListRegionsResponse,
    RegionResponse,
    UpdateRegionRequest,
)
from mangai_api.models.text import (
    AssignmentResponse,
    DialogueResponse,
    ListAssignmentsResponse,
    ListDialoguesResponse,
    ListPlacementsResponse,
    ListTranslationsResponse,
    ManualDialogueRequest,
    PlacementResponse,
    TranslationResponse,
    UpsertAssignmentRequest,
    UpsertPlacementRequest,
    UpsertTranslationRequest,
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


@router.get(
    "/{project_id}/pages/{page_id}/jobs",
    response_model=ListJobsResponse,
    summary="List page jobs",
)
def list_page_jobs(
    project_id: UUID,
    page_id: UUID,
    store: LocalProjectStore = Depends(get_project_store),
) -> ListJobsResponse:
    return ListJobsResponse(jobs=tuple(store.list_page_jobs(project_id=project_id, page_id=page_id)))


@router.get(
    "/{project_id}/pages/{page_id}/regions",
    response_model=ListRegionsResponse,
    summary="List page regions",
)
def list_page_regions(
    project_id: UUID,
    page_id: UUID,
    store: LocalProjectStore = Depends(get_project_store),
) -> ListRegionsResponse:
    return ListRegionsResponse(
        regions=tuple(store.list_page_regions(project_id=project_id, page_id=page_id))
    )


@router.get(
    "/{project_id}/pages/{page_id}/mask-revisions",
    response_model=ListMaskRevisionsResponse,
    summary="List page mask revisions",
)
def list_page_mask_revisions(
    project_id: UUID,
    page_id: UUID,
    store: LocalProjectStore = Depends(get_project_store),
) -> ListMaskRevisionsResponse:
    return ListMaskRevisionsResponse(
        mask_revisions=tuple(
            store.list_page_mask_revisions(project_id=project_id, page_id=page_id)
        )
    )


@router.get(
    "/{project_id}/pages/{page_id}/dialogues",
    response_model=ListDialoguesResponse,
    summary="List page dialogues",
)
def list_page_dialogues(
    project_id: UUID,
    page_id: UUID,
    store: LocalProjectStore = Depends(get_project_store),
) -> ListDialoguesResponse:
    return ListDialoguesResponse(
        dialogues=tuple(store.list_page_dialogues(project_id=project_id, page_id=page_id))
    )


@router.get(
    "/{project_id}/pages/{page_id}/translations",
    response_model=ListTranslationsResponse,
    summary="List page translations",
)
def list_page_translations(
    project_id: UUID,
    page_id: UUID,
    store: LocalProjectStore = Depends(get_project_store),
) -> ListTranslationsResponse:
    return ListTranslationsResponse(
        translations=tuple(store.list_page_translations(project_id=project_id, page_id=page_id))
    )


@router.get(
    "/{project_id}/pages/{page_id}/assignments",
    response_model=ListAssignmentsResponse,
    summary="List page assignments",
)
def list_page_assignments(
    project_id: UUID,
    page_id: UUID,
    store: LocalProjectStore = Depends(get_project_store),
) -> ListAssignmentsResponse:
    return ListAssignmentsResponse(
        assignments=tuple(store.list_page_assignments(project_id=project_id, page_id=page_id))
    )


@router.get(
    "/{project_id}/pages/{page_id}/placements",
    response_model=ListPlacementsResponse,
    summary="List page text placements",
)
def list_page_placements(
    project_id: UUID,
    page_id: UUID,
    store: LocalProjectStore = Depends(get_project_store),
) -> ListPlacementsResponse:
    return ListPlacementsResponse(
        placements=tuple(store.list_page_placements(project_id=project_id, page_id=page_id))
    )


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


@router.post(
    "/{project_id}/pages/{page_id}/regions",
    response_model=RegionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create page region",
)
def create_page_region(
    project_id: UUID,
    page_id: UUID,
    payload: CreateRegionRequest,
    store: LocalProjectStore = Depends(get_project_store),
) -> RegionResponse:
    region = store.create_page_region(project_id=project_id, page_id=page_id, payload=payload)
    return RegionResponse(region=region)


@router.post(
    "/{project_id}/pages/{page_id}/mask-revisions",
    response_model=MaskRevisionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create page mask revision",
)
def create_page_mask_revision(
    project_id: UUID,
    page_id: UUID,
    payload: CreateMaskRevisionRequest,
    store: LocalProjectStore = Depends(get_project_store),
) -> MaskRevisionResponse:
    mask_revision = store.create_mask_revision(
        project_id=project_id,
        page_id=page_id,
        payload=payload,
    )
    return MaskRevisionResponse(mask_revision=mask_revision)


@router.post(
    "/{project_id}/pages/{page_id}/dialogues",
    response_model=DialogueResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create manual page dialogue",
)
def create_page_dialogue(
    project_id: UUID,
    page_id: UUID,
    payload: ManualDialogueRequest,
    store: LocalProjectStore = Depends(get_project_store),
) -> DialogueResponse:
    dialogue = store.create_manual_dialogue(
        project_id=project_id,
        page_id=page_id,
        payload=payload,
    )
    return DialogueResponse(dialogue=dialogue)


@router.post(
    "/{project_id}/pages/{page_id}/jobs",
    response_model=JobResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Queue page job",
)
def create_page_job(
    project_id: UUID,
    page_id: UUID,
    payload: CreatePageJobRequest,
    store: LocalProjectStore = Depends(get_project_store),
) -> JobResponse:
    job = store.enqueue_page_job(project_id=project_id, page_id=page_id, job_type=payload.type)
    return JobResponse(job=job)


@router.patch(
    "/{project_id}/pages/{page_id}/regions/{region_id}",
    response_model=RegionResponse,
    summary="Update page region",
)
def update_page_region(
    project_id: UUID,
    page_id: UUID,
    region_id: UUID,
    payload: UpdateRegionRequest,
    store: LocalProjectStore = Depends(get_project_store),
) -> RegionResponse:
    region = store.update_page_region(
        project_id=project_id,
        page_id=page_id,
        region_id=region_id,
        payload=payload,
    )
    return RegionResponse(region=region)


@router.delete(
    "/{project_id}/pages/{page_id}/regions/{region_id}",
    response_model=ListRegionsResponse,
    summary="Delete a page region",
)
def delete_page_region(
    project_id: UUID,
    page_id: UUID,
    region_id: UUID,
    store: LocalProjectStore = Depends(get_project_store),
) -> ListRegionsResponse:
    regions = store.delete_page_region(
        project_id=project_id,
        page_id=page_id,
        region_id=region_id,
    )
    return ListRegionsResponse(regions=tuple(regions))


@router.post(
    "/{project_id}/pages/{page_id}/regions/reset",
    response_model=ListRegionsResponse,
    summary="Reset page regions",
)
def reset_page_regions(
    project_id: UUID,
    page_id: UUID,
    store: LocalProjectStore = Depends(get_project_store),
) -> ListRegionsResponse:
    regions = store.reset_page_regions(project_id=project_id, page_id=page_id)
    return ListRegionsResponse(regions=tuple(regions))


@router.patch(
    "/{project_id}/pages/{page_id}/mask-revisions/{mask_revision_id}",
    response_model=MaskRevisionResponse,
    summary="Update page mask revision",
)
def update_page_mask_revision(
    project_id: UUID,
    page_id: UUID,
    mask_revision_id: UUID,
    payload: UpdateMaskRevisionRequest,
    store: LocalProjectStore = Depends(get_project_store),
) -> MaskRevisionResponse:
    mask_revision = store.update_mask_revision(
        project_id=project_id,
        page_id=page_id,
        mask_revision_id=mask_revision_id,
        payload=payload,
    )
    return MaskRevisionResponse(mask_revision=mask_revision)


@router.put(
    "/{project_id}/pages/{page_id}/dialogues/{dialogue_id}",
    response_model=DialogueResponse,
    summary="Update manual page dialogue",
)
def update_page_dialogue(
    project_id: UUID,
    page_id: UUID,
    dialogue_id: UUID,
    payload: ManualDialogueRequest,
    store: LocalProjectStore = Depends(get_project_store),
) -> DialogueResponse:
    dialogue = store.update_manual_dialogue(
        project_id=project_id,
        page_id=page_id,
        dialogue_id=dialogue_id,
        payload=payload,
    )
    return DialogueResponse(dialogue=dialogue)


@router.put(
    "/{project_id}/pages/{page_id}/translations",
    response_model=TranslationResponse,
    summary="Upsert page translation",
)
def upsert_page_translation(
    project_id: UUID,
    page_id: UUID,
    payload: UpsertTranslationRequest,
    store: LocalProjectStore = Depends(get_project_store),
) -> TranslationResponse:
    translation = store.upsert_translation(
        project_id=project_id,
        page_id=page_id,
        payload=payload,
    )
    return TranslationResponse(translation=translation)


@router.put(
    "/{project_id}/pages/{page_id}/assignments",
    response_model=AssignmentResponse,
    summary="Upsert page dialogue assignment",
)
def upsert_page_assignment(
    project_id: UUID,
    page_id: UUID,
    payload: UpsertAssignmentRequest,
    store: LocalProjectStore = Depends(get_project_store),
) -> AssignmentResponse:
    assignment = store.upsert_assignment(
        project_id=project_id,
        page_id=page_id,
        payload=payload,
    )
    return AssignmentResponse(assignment=assignment)


@router.put(
    "/{project_id}/pages/{page_id}/placements",
    response_model=PlacementResponse,
    summary="Upsert page text placement",
)
def upsert_page_placement(
    project_id: UUID,
    page_id: UUID,
    payload: UpsertPlacementRequest,
    store: LocalProjectStore = Depends(get_project_store),
) -> PlacementResponse:
    placement = store.upsert_placement(
        project_id=project_id,
        page_id=page_id,
        payload=payload,
    )
    return PlacementResponse(placement=placement)


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


@router.get(
    "/{project_id}/assets/{asset_id}",
    summary="Get a stored project asset",
)
def get_project_asset(
    project_id: UUID,
    asset_id: UUID,
    store: LocalProjectStore = Depends(get_project_store),
) -> FileResponse:
    asset_path, mime_type = store.get_project_asset_file(project_id=project_id, asset_id=asset_id)
    return FileResponse(asset_path, media_type=mime_type)
