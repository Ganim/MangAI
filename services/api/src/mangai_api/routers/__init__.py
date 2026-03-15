from fastapi import APIRouter

from mangai_api.routers.health import router as health_router
from mangai_api.routers.projects import router as projects_router
from mangai_api.routers.system import router as system_router


def build_api_router() -> APIRouter:
    router = APIRouter()
    router.include_router(health_router)
    router.include_router(system_router)
    router.include_router(projects_router)
    return router

