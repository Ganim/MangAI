from fastapi import FastAPI
from fastapi.responses import JSONResponse

from mangai_api.config import get_settings
from mangai_api.error_handlers import register_error_handlers
from mangai_api.routers import build_api_router


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        default_response_class=JSONResponse,
    )
    register_error_handlers(app)
    app.include_router(build_api_router(), prefix=settings.api_prefix)
    return app


app = create_app()
