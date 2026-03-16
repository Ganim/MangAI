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


@dataclass(frozen=True)
class OcrJobPayload:
    job_id: UUID
    page_id: UUID
    asset_id: UUID
    region_ids: tuple[UUID, ...]
    source_language: str

    @classmethod
    def from_dict(cls, payload: dict[str, str | list[str]]) -> "OcrJobPayload":
        return cls(
            job_id=UUID(str(payload["job_id"])),
            page_id=UUID(str(payload["page_id"])),
            asset_id=UUID(str(payload["asset_id"])),
            region_ids=tuple(UUID(str(value)) for value in payload["region_ids"]),
            source_language=str(payload["source_language"]),
        )


@dataclass(frozen=True)
class OcrJobResult:
    page_id: UUID
    dialogue_ids: tuple[UUID, ...]
    preview_asset_id: UUID

    def to_dict(self) -> dict[str, str | list[str]]:
        return {
            "page_id": str(self.page_id),
            "dialogue_ids": [str(value) for value in self.dialogue_ids],
            "preview_asset_id": str(self.preview_asset_id),
        }


@dataclass(frozen=True)
class TranslationJobPayload:
    job_id: UUID
    project_id: UUID
    dialogue_ids: tuple[UUID, ...]
    source_language: str
    target_language: str

    @classmethod
    def from_dict(cls, payload: dict[str, str | list[str]]) -> "TranslationJobPayload":
        return cls(
            job_id=UUID(str(payload["job_id"])),
            project_id=UUID(str(payload["project_id"])),
            dialogue_ids=tuple(UUID(str(value)) for value in payload["dialogue_ids"]),
            source_language=str(payload["source_language"]),
            target_language=str(payload["target_language"]),
        )


@dataclass(frozen=True)
class TranslationJobResult:
    project_id: UUID
    translation_ids: tuple[UUID, ...]

    def to_dict(self) -> dict[str, str | list[str]]:
        return {
            "project_id": str(self.project_id),
            "translation_ids": [str(value) for value in self.translation_ids],
        }


@dataclass(frozen=True)
class MatchingJobPayload:
    job_id: UUID
    page_id: UUID
    dialogue_ids: tuple[UUID, ...]
    region_ids: tuple[UUID, ...]

    @classmethod
    def from_dict(cls, payload: dict[str, str | list[str]]) -> "MatchingJobPayload":
        return cls(
            job_id=UUID(str(payload["job_id"])),
            page_id=UUID(str(payload["page_id"])),
            dialogue_ids=tuple(UUID(str(value)) for value in payload["dialogue_ids"]),
            region_ids=tuple(UUID(str(value)) for value in payload["region_ids"]),
        )


@dataclass(frozen=True)
class MatchingJobResult:
    page_id: UUID
    assignment_ids: tuple[UUID, ...]
    placement_ids: tuple[UUID, ...]

    def to_dict(self) -> dict[str, str | list[str]]:
        return {
            "page_id": str(self.page_id),
            "assignment_ids": [str(value) for value in self.assignment_ids],
            "placement_ids": [str(value) for value in self.placement_ids],
        }
