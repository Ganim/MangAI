from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from mangai_api.domain_errors import (
    JobValidationError,
    MaskRevisionNotFoundError,
    ProjectNotFoundError,
    ProjectPageNotFoundError,
    RegionNotFoundError,
    UploadValidationError,
)
from mangai_api.i18n import LocaleValidationError
from mangai_api.models.common import ErrorResponse


def register_error_handlers(app) -> None:
    @app.exception_handler(LocaleValidationError)
    async def handle_locale_error(_: Request, exc: LocaleValidationError) -> JSONResponse:
        payload = ErrorResponse(
            error_code="INVALID_LOCALE_OR_LANGUAGE",
            message=str(exc),
        )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content=payload.model_dump(),
        )

    @app.exception_handler(ProjectNotFoundError)
    async def handle_project_not_found(_: Request, exc: ProjectNotFoundError) -> JSONResponse:
        payload = ErrorResponse(
            error_code="PROJECT_NOT_FOUND",
            message=str(exc),
        )
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=payload.model_dump(),
        )

    @app.exception_handler(ProjectPageNotFoundError)
    async def handle_page_not_found(_: Request, exc: ProjectPageNotFoundError) -> JSONResponse:
        payload = ErrorResponse(
            error_code="PAGE_NOT_FOUND",
            message=str(exc),
        )
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=payload.model_dump(),
        )

    @app.exception_handler(RegionNotFoundError)
    async def handle_region_not_found(_: Request, exc: RegionNotFoundError) -> JSONResponse:
        payload = ErrorResponse(
            error_code="REGION_NOT_FOUND",
            message=str(exc),
        )
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=payload.model_dump(),
        )

    @app.exception_handler(MaskRevisionNotFoundError)
    async def handle_mask_revision_not_found(
        _: Request,
        exc: MaskRevisionNotFoundError,
    ) -> JSONResponse:
        payload = ErrorResponse(
            error_code="MASK_REVISION_NOT_FOUND",
            message=str(exc),
        )
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=payload.model_dump(),
        )

    @app.exception_handler(JobValidationError)
    async def handle_job_validation(_: Request, exc: JobValidationError) -> JSONResponse:
        payload = ErrorResponse(
            error_code="INVALID_JOB_REQUEST",
            message=str(exc),
        )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content=payload.model_dump(),
        )

    @app.exception_handler(UploadValidationError)
    async def handle_upload_validation(_: Request, exc: UploadValidationError) -> JSONResponse:
        payload = ErrorResponse(
            error_code="INVALID_UPLOAD",
            message=str(exc),
        )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content=payload.model_dump(),
        )

    @app.exception_handler(RequestValidationError)
    async def handle_request_validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        payload = ErrorResponse(
            error_code="INVALID_REQUEST",
            message=str(exc),
        )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content=payload.model_dump(),
        )
