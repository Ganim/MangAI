from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from mangai_api.config import get_settings
from mangai_api.error_handlers import register_error_handlers
from mangai_api.repositories import LocalProjectStore
from mangai_api.routers import build_api_router


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        default_response_class=JSONResponse,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_allowed_origins),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.state.project_store = LocalProjectStore(
        data_dir=settings.data_dir,
        api_prefix=settings.api_prefix,
    )
    register_error_handlers(app)
    app.include_router(build_api_router(), prefix=settings.api_prefix)
    return app


app = create_app()
