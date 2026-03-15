from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class APIModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ErrorResponse(APIModel):
    error_code: str = Field(description="Stable machine-readable error code.")
    message: str = Field(description="Developer-readable fallback message.")


class HealthResponse(APIModel):
    status: Literal["ok"]
    service: str
    version: str


class MetaResponse(APIModel):
    app_name: str
    schema_version: int
    environment: str
    supported_ui_locales: tuple[str, ...]
    supported_text_directions: tuple[str, ...]

