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


@dataclass(frozen=True)
class CleanupJobPayload:
    job_id: UUID
    page_id: UUID
    source_asset_id: UUID
    region_ids: tuple[UUID, ...]
    mask_revision_ids: tuple[UUID, ...]

    @classmethod
    def from_dict(cls, payload: dict[str, str | list[str]]) -> "CleanupJobPayload":
        return cls(
            job_id=UUID(str(payload["job_id"])),
            page_id=UUID(str(payload["page_id"])),
            source_asset_id=UUID(str(payload["source_asset_id"])),
            region_ids=tuple(UUID(str(value)) for value in payload["region_ids"]),
            mask_revision_ids=tuple(UUID(str(value)) for value in payload["mask_revision_ids"]),
        )


@dataclass(frozen=True)
class CleanupJobResult:
    page_id: UUID
    cleaned_asset_id: UUID
    variant_asset_ids: tuple[UUID, ...]

    def to_dict(self) -> dict[str, str | list[str]]:
        return {
            "page_id": str(self.page_id),
            "cleaned_asset_id": str(self.cleaned_asset_id),
            "variant_asset_ids": [str(value) for value in self.variant_asset_ids],
        }
