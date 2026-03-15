from fastapi import APIRouter

from mangai_api.config import get_settings
from mangai_api.constants import SCHEMA_VERSION, SUPPORTED_TEXT_DIRECTIONS, SUPPORTED_UI_LOCALES
from mangai_api.models.common import MetaResponse


router = APIRouter(prefix="/system", tags=["system"])


@router.get("/meta", response_model=MetaResponse, summary="System metadata")
def get_meta() -> MetaResponse:
    settings = get_settings()
    return MetaResponse(
        app_name=settings.app_name,
        schema_version=SCHEMA_VERSION,
        environment=settings.environment,
        supported_ui_locales=SUPPORTED_UI_LOCALES,
        supported_text_directions=SUPPORTED_TEXT_DIRECTIONS,
    )

