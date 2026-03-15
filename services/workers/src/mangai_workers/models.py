from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class DetectRegionsJobPayload:
    job_id: UUID
    page_id: UUID
    asset_id: UUID

    @classmethod
    def from_dict(cls, payload: dict[str, str]) -> "DetectRegionsJobPayload":
        return cls(
            job_id=UUID(payload["job_id"]),
            page_id=UUID(payload["page_id"]),
            asset_id=UUID(payload["asset_id"]),
        )


@dataclass(frozen=True)
class DetectRegionsJobResult:
    page_id: UUID
    regions_created: int
    overlay_asset_id: UUID

    def to_dict(self) -> dict[str, str | int]:
        return {
            "page_id": str(self.page_id),
            "regions_created": self.regions_created,
            "overlay_asset_id": str(self.overlay_asset_id),
        }
