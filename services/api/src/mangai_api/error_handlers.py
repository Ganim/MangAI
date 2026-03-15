from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from mangai_api.domain_errors import ProjectNotFoundError
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
