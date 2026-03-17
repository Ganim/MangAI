from __future__ import annotations

import json
import mimetypes
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from threading import Lock
from time import sleep
from uuid import UUID, uuid4

from mangai_api.constants import (
    MAX_UPLOAD_FILE_SIZE_BYTES,
    SCHEMA_VERSION,
    SUPPORTED_UPLOAD_MIME_TYPES,
)
from mangai_api.domain_errors import (
    JobValidationError,
    MaskRevisionNotFoundError,
    ProjectNotFoundError,
    ProjectPageNotFoundError,
    RegionNotFoundError,
    UploadValidationError,
)
from mangai_api.image_metadata import infer_image_dimensions
from mangai_api.models.project import (
    CreateProjectRequest,
    ProjectDetailResponse,
    ProjectPage,
    ProjectSummary,
    RegisterProjectPagesRequest,
    RegisterUploadedProjectPage,
    StoredProjectAsset,
    StoredProjectState,
)
from mangai_api.models.job import JobRecord
from mangai_api.models.mask import (
    CreateMaskRevisionRequest,
    MaskRevisionRecord,
    UpdateMaskRevisionRequest,
)
from mangai_api.models.region import (
    BoundingBox,
    CreateRegionRequest,
    PolygonPoint,
    PolygonShape,
    RegionRecord,
    UpdateRegionRequest,
)
from mangai_api.models.text import (
    AssignmentRecord,
    DialogueRecord,
    ManualDialogueRequest,
    TextPlacementRecord,
    TextStyle,
    TranslationRecord,
    UpsertAssignmentRequest,
    UpsertPlacementRequest,
    UpsertTranslationRequest,
)


def _utcnow() -> datetime:
    return datetime.now(UTC)


SYSTEM_ACTOR_ID = UUID("00000000-0000-4000-8000-000000000000")
PENDING_JOB_STATUSES = {"queued", "running"}
STATE_REPLACE_ATTEMPTS = 8
STATE_REPLACE_DELAY_SECONDS = 0.05


@dataclass(frozen=True)
class UploadedPageFile:
    file_name: str
    mime_type: str
    size_bytes: int
    content: bytes
    width: int | None = None
    height: int | None = None


class LocalProjectStore:
    def __init__(self, data_dir: Path, api_prefix: str) -> None:
        self._data_dir = data_dir
        self._assets_dir = data_dir / "assets"
        self._state_file = data_dir / "state.json"
        self._api_prefix = api_prefix.rstrip("/")
        self._lock = Lock()
        self._ensure_storage_ready()

    def list_projects(self) -> list[ProjectSummary]:
        state = self._load_state()
        projects = sorted(state.projects, key=lambda project: project.created_at, reverse=True)
        return [project.model_copy(deep=True) for project in projects]

    def get_project_detail(self, project_id: UUID) -> ProjectDetailResponse:
        state = self._load_state()
        project = self._require_project(state, project_id)
        pages = self._get_pages_for_project(state, project_id)
        return ProjectDetailResponse(
            project=project.model_copy(deep=True),
            pages=tuple(page.model_copy(deep=True) for page in pages),
        )

    def list_page_jobs(self, project_id: UUID, page_id: UUID) -> list[JobRecord]:
        state = self._load_state()
        self._require_project(state, project_id)
        self._require_page(state, project_id, page_id)
        return [
            job.model_copy(deep=True)
            for job in sorted(
                [candidate for candidate in state.jobs if candidate.page_id == page_id],
                key=lambda candidate: candidate.created_at,
                reverse=True,
            )
        ]

    def enqueue_page_job(self, project_id: UUID, page_id: UUID, job_type: str) -> JobRecord:
        with self._lock:
            state = self._load_state_unlocked()
            project = self._require_project(state, project_id)
            self._require_page(state, project_id, page_id)
            existing_pending_job = next(
                (
                    candidate
                    for candidate in state.jobs
                    if candidate.page_id == page_id
                    and candidate.type == job_type
                    and candidate.status in PENDING_JOB_STATUSES
                ),
                None,
            )
            if existing_pending_job is not None:
                return existing_pending_job.model_copy(deep=True)
            original_asset = self._require_original_asset(state, project_id, page_id)
            job_id = uuid4()
            now = _utcnow()

            if job_type == "detect_regions":
                payload = {
                    "job_id": str(job_id),
                    "page_id": str(page_id),
                    "asset_id": str(original_asset.id),
                }
            elif job_type == "generate_cleanup":
                approved_mask_revisions = self._get_approved_active_mask_revisions_for_page(
                    state,
                    page_id,
                )
                if len(approved_mask_revisions) == 0:
                    raise JobValidationError(
                        "At least one approved active mask revision is required before cleanup."
                    )
                payload = {
                    "job_id": str(job_id),
                    "page_id": str(page_id),
                    "source_asset_id": str(original_asset.id),
                    "region_ids": [
                        str(mask_revision.region_id) for mask_revision in approved_mask_revisions
                    ],
                    "mask_revision_ids": [
                        str(mask_revision.id) for mask_revision in approved_mask_revisions
                    ],
                }
            elif job_type == "run_ocr":
                candidate_regions = self._get_ocr_candidate_regions_for_page(state, page_id)
                if len(candidate_regions) == 0:
                    raise JobValidationError(
                        "At least one OCR candidate region is required before OCR can run."
                    )
                payload = {
                    "job_id": str(job_id),
                    "page_id": str(page_id),
                    "asset_id": str(original_asset.id),
                    "region_ids": [str(region.id) for region in candidate_regions],
                    "source_language": project.source_language,
                }
            elif job_type == "generate_translation":
                locked_translation_dialogue_ids = {
                    translation.dialogue_id
                    for translation in state.translations
                    if translation.target_language == project.target_language
                    and translation.edited_by_user
                    and translation.content.strip() != ""
                }
                candidate_dialogues = [
                    dialogue
                    for dialogue in self._get_page_dialogues(state, page_id)
                    if dialogue.id not in locked_translation_dialogue_ids
                ]
                if len(candidate_dialogues) == 0:
                    raise JobValidationError(
                        "At least one page dialogue without a locked user translation is required before automatic translation can run."
                    )
                payload = {
                    "job_id": str(job_id),
                    "project_id": str(project_id),
                    "dialogue_ids": [str(dialogue.id) for dialogue in candidate_dialogues],
                    "source_language": project.source_language,
                    "target_language": project.target_language,
                }
            elif job_type == "match_dialogue":
                assigned_dialogue_ids = {
                    assignment.dialogue_id
                    for assignment in state.assignments
                    if assignment.page_id == page_id and assignment.approved
                }
                occupied_region_ids = {
                    assignment.region_id
                    for assignment in state.assignments
                    if assignment.page_id == page_id and assignment.approved
                }
                candidate_dialogues = [
                    dialogue
                    for dialogue in self._get_page_dialogues(state, page_id)
                    if dialogue.id not in assigned_dialogue_ids
                ]
                candidate_regions = [
                    region
                    for region in self._get_ocr_candidate_regions_for_page(state, page_id)
                    if region.id not in occupied_region_ids
                ]
                if len(candidate_dialogues) == 0:
                    raise JobValidationError(
                        "At least one page dialogue without an approved assignment is required before automatic matching can run."
                    )
                if len(candidate_regions) == 0:
                    raise JobValidationError(
                        "At least one candidate region is required before automatic matching can run."
                    )
                payload = {
                    "job_id": str(job_id),
                    "page_id": str(page_id),
                    "dialogue_ids": [str(dialogue.id) for dialogue in candidate_dialogues],
                    "region_ids": [str(region.id) for region in candidate_regions],
                }
            else:
                raise JobValidationError(
                    "Only detect_regions, generate_cleanup, run_ocr, generate_translation, and match_dialogue jobs are currently supported."
                )

            job = JobRecord(
                id=job_id,
                project_id=project_id,
                page_id=page_id,
                type=job_type,
                status="queued",
                payload=payload,
                result=None,
                error_code=None,
                error_message=None,
                created_at=now,
                updated_at=now,
            )
            next_state = state.model_copy(update={"jobs": (*state.jobs, job)})
            self._save_state_unlocked(next_state)
            return job.model_copy(deep=True)

    def list_page_regions(self, project_id: UUID, page_id: UUID) -> list[RegionRecord]:
        state = self._load_state()
        self._require_project(state, project_id)
        self._require_page(state, project_id, page_id)
        return [
            region.model_copy(deep=True)
            for region in self._sort_regions_by_reading_order(
                [candidate for candidate in state.regions if candidate.page_id == page_id]
            )
        ]

    def list_page_mask_revisions(
        self,
        project_id: UUID,
        page_id: UUID,
    ) -> list[MaskRevisionRecord]:
        state = self._load_state()
        self._require_project(state, project_id)
        self._require_page(state, project_id, page_id)
        page_region_ids = {
            region.id for region in state.regions if region.page_id == page_id
        }
        return [
            mask_revision.model_copy(deep=True)
            for mask_revision in sorted(
                [
                    candidate
                    for candidate in state.mask_revisions
                    if candidate.region_id in page_region_ids
                ],
                key=lambda candidate: (candidate.created_at, candidate.version),
            )
        ]

    def _sort_regions_by_reading_order(
        self,
        regions: list[RegionRecord] | tuple[RegionRecord, ...],
    ) -> list[RegionRecord]:
        return sorted(
            list(regions),
            key=lambda region: (
                region.global_reading_order if region.global_reading_order is not None else 9999,
                region.panel_order if region.panel_order is not None else 9999,
                region.balloon_group_order if region.balloon_group_order is not None else 9999,
                region.order_in_balloon_group
                if region.order_in_balloon_group is not None
                else 9999,
                region.order_in_panel if region.order_in_panel is not None else 9999,
                region.bounding_box.y,
                region.bounding_box.x,
                region.created_at,
            ),
        )

    def _reassign_page_region_reading_order(
        self,
        regions: tuple[RegionRecord, ...],
        *,
        page_id: UUID,
        target_region_id: UUID,
        target_position: int,
    ) -> tuple[RegionRecord, ...]:
        page_regions = [
            candidate
            for candidate in self._sort_regions_by_reading_order(regions)
            if candidate.page_id == page_id
        ]
        target_region = next(
            candidate for candidate in page_regions if candidate.id == target_region_id
        )
        page_regions = [
            candidate for candidate in page_regions if candidate.id != target_region_id
        ]
        insert_index = max(0, min(target_position - 1, len(page_regions)))
        page_regions.insert(insert_index, target_region)

        timestamp = _utcnow()
        reordered_by_id = {
            candidate.id: candidate.model_copy(
                update={
                    "global_reading_order": index,
                    "updated_at": timestamp,
                }
            )
            for index, candidate in enumerate(page_regions, start=1)
        }
        return tuple(
            reordered_by_id.get(candidate.id, candidate)
            for candidate in regions
        )

    def create_mask_revision(
        self,
        project_id: UUID,
        page_id: UUID,
        payload: CreateMaskRevisionRequest,
    ) -> MaskRevisionRecord:
        with self._lock:
            state = self._load_state_unlocked()
            self._require_project(state, project_id)
            page = self._require_page(state, project_id, page_id)
            region = self._require_region(state, page_id, payload.region_id)
            current_versions = [
                candidate.version
                for candidate in state.mask_revisions
                if candidate.region_id == region.id
            ]
            now = _utcnow()
            mask_revision = MaskRevisionRecord(
                id=uuid4(),
                region_id=region.id,
                version=(max(current_versions) + 1) if current_versions else 1,
                is_active=True,
                approved=False,
                shape=payload.shape,
                created_by=SYSTEM_ACTOR_ID,
                created_at=now,
                updated_at=now,
            )
            next_mask_revisions = tuple(
                candidate.model_copy(update={"is_active": False, "updated_at": now})
                if candidate.region_id == region.id and candidate.is_active
                else candidate
                for candidate in state.mask_revisions
            )
            next_mask_revisions = (*next_mask_revisions, mask_revision)
            next_pages = self._replace_page_after_mask_change(
                state=state,
                page=page,
                next_mask_revisions=next_mask_revisions,
            )
            next_state = state.model_copy(
                update={
                    "pages": next_pages,
                    "mask_revisions": next_mask_revisions,
                }
            )
            self._save_state_unlocked(next_state)
            return mask_revision.model_copy(deep=True)

    def update_mask_revision(
        self,
        project_id: UUID,
        page_id: UUID,
        mask_revision_id: UUID,
        payload: UpdateMaskRevisionRequest,
    ) -> MaskRevisionRecord:
        with self._lock:
            state = self._load_state_unlocked()
            self._require_project(state, project_id)
            page = self._require_page(state, project_id, page_id)
            mask_revision = self._require_mask_revision(state, page_id, mask_revision_id)
            now = _utcnow()

            updated_mask_revision = mask_revision.model_copy(
                update={
                    "approved": payload.approved if payload.approved is not None else mask_revision.approved,
                    "is_active": payload.is_active if payload.is_active is not None else mask_revision.is_active,
                    "shape": payload.shape or mask_revision.shape,
                    "updated_at": now,
                }
            )

            next_mask_revisions: list[MaskRevisionRecord] = []
            for candidate in state.mask_revisions:
                if candidate.id == mask_revision_id:
                    next_mask_revisions.append(updated_mask_revision)
                    continue

                if (
                    payload.is_active is True
                    and candidate.region_id == mask_revision.region_id
                    and candidate.is_active
                ):
                    next_mask_revisions.append(
                        candidate.model_copy(update={"is_active": False, "updated_at": now})
                    )
                    continue

                next_mask_revisions.append(candidate)

            next_pages = self._replace_page_after_mask_change(
                state=state,
                page=page,
                next_mask_revisions=tuple(next_mask_revisions),
            )
            next_state = state.model_copy(
                update={
                    "pages": next_pages,
                    "mask_revisions": tuple(next_mask_revisions),
                }
            )
            self._save_state_unlocked(next_state)
            return updated_mask_revision.model_copy(deep=True)

    def list_page_dialogues(self, project_id: UUID, page_id: UUID) -> list[DialogueRecord]:
        state = self._load_state()
        self._require_project(state, project_id)
        self._require_page(state, project_id, page_id)
        return [
            dialogue.model_copy(deep=True)
            for dialogue in sorted(
                [candidate for candidate in state.dialogues if candidate.page_id == page_id],
                key=lambda candidate: candidate.reading_order,
            )
        ]

    def create_manual_dialogue(
        self,
        project_id: UUID,
        page_id: UUID,
        payload: ManualDialogueRequest,
    ) -> DialogueRecord:
        with self._lock:
            state = self._load_state_unlocked()
            self._require_project(state, project_id)
            page = self._require_page(state, project_id, page_id)
            now = _utcnow()
            dialogue = DialogueRecord(
                id=uuid4(),
                page_id=page_id,
                source="manual",
                source_language=payload.source_language,
                content=payload.content,
                reading_order=payload.reading_order,
                status="draft",
                source_region_id=None,
                created_at=now,
                updated_at=now,
            )
            next_state = state.model_copy(
                update={
                    "pages": self._replace_page_status(state, page, "text_ready"),
                    "dialogues": (*state.dialogues, dialogue),
                }
            )
            self._save_state_unlocked(next_state)
            return dialogue.model_copy(deep=True)

    def update_manual_dialogue(
        self,
        project_id: UUID,
        page_id: UUID,
        dialogue_id: UUID,
        payload: ManualDialogueRequest,
    ) -> DialogueRecord:
        with self._lock:
            state = self._load_state_unlocked()
            self._require_project(state, project_id)
            page = self._require_page(state, project_id, page_id)
            dialogue = self._require_dialogue(state, page_id, dialogue_id)
            updated_dialogue = dialogue.model_copy(
                update={
                    "source_language": payload.source_language,
                    "content": payload.content,
                    "reading_order": payload.reading_order,
                    "updated_at": _utcnow(),
                }
            )
            next_dialogues = tuple(
                updated_dialogue if candidate.id == dialogue_id else candidate
                for candidate in state.dialogues
            )
            next_state = state.model_copy(
                update={
                    "pages": self._replace_page_status(state, page, "text_ready"),
                    "dialogues": next_dialogues,
                }
            )
            self._save_state_unlocked(next_state)
            return updated_dialogue.model_copy(deep=True)

    def list_page_translations(self, project_id: UUID, page_id: UUID) -> list[TranslationRecord]:
        state = self._load_state()
        self._require_project(state, project_id)
        self._require_page(state, project_id, page_id)
        dialogue_ids = {dialogue.id for dialogue in state.dialogues if dialogue.page_id == page_id}
        return [
            translation.model_copy(deep=True)
            for translation in sorted(
                [
                    candidate
                    for candidate in state.translations
                    if candidate.dialogue_id in dialogue_ids
                ],
                key=lambda candidate: candidate.created_at,
            )
        ]

    def upsert_translation(
        self,
        project_id: UUID,
        page_id: UUID,
        payload: UpsertTranslationRequest,
    ) -> TranslationRecord:
        with self._lock:
            state = self._load_state_unlocked()
            self._require_project(state, project_id)
            page = self._require_page(state, project_id, page_id)
            dialogue = self._require_dialogue(state, page_id, payload.dialogue_id)
            existing_translation = next(
                (
                    candidate
                    for candidate in state.translations
                    if candidate.dialogue_id == dialogue.id
                    and candidate.target_language == payload.target_language
                ),
                None,
            )
            now = _utcnow()
            if existing_translation is None:
                translation = TranslationRecord(
                    id=uuid4(),
                    dialogue_id=dialogue.id,
                    target_language=payload.target_language,
                    text_direction=payload.text_direction,
                    provider="manual",
                    content=payload.content,
                    status=payload.status,
                    edited_by_user=True,
                    created_at=now,
                    updated_at=now,
                )
                next_translations = (*state.translations, translation)
            else:
                translation = existing_translation.model_copy(
                    update={
                        "text_direction": payload.text_direction,
                        "provider": "manual",
                        "content": payload.content,
                        "status": payload.status,
                        "edited_by_user": True,
                        "updated_at": now,
                    }
                )
                next_translations = tuple(
                    translation if candidate.id == existing_translation.id else candidate
                    for candidate in state.translations
                )

            next_state = state.model_copy(
                update={
                    "pages": self._replace_page_status(state, page, "text_ready"),
                    "translations": next_translations,
                }
            )
            self._save_state_unlocked(next_state)
            return translation.model_copy(deep=True)

    def list_page_assignments(self, project_id: UUID, page_id: UUID) -> list[AssignmentRecord]:
        state = self._load_state()
        self._require_project(state, project_id)
        self._require_page(state, project_id, page_id)
        return [
            assignment.model_copy(deep=True)
            for assignment in sorted(
                [candidate for candidate in state.assignments if candidate.page_id == page_id],
                key=lambda candidate: candidate.created_at,
            )
        ]

    def upsert_assignment(
        self,
        project_id: UUID,
        page_id: UUID,
        payload: UpsertAssignmentRequest,
    ) -> AssignmentRecord:
        with self._lock:
            state = self._load_state_unlocked()
            self._require_project(state, project_id)
            page = self._require_page(state, project_id, page_id)
            dialogue = self._require_dialogue(state, page_id, payload.dialogue_id)
            region = self._require_region(state, page_id, payload.region_id)
            existing_assignment = next(
                (
                    candidate
                    for candidate in state.assignments
                    if candidate.page_id == page_id and candidate.dialogue_id == dialogue.id
                ),
                None,
            )
            now = _utcnow()
            if existing_assignment is None:
                assignment = AssignmentRecord(
                    id=uuid4(),
                    page_id=page_id,
                    dialogue_id=dialogue.id,
                    region_id=region.id,
                    origin=payload.origin,
                    confidence=None,
                    approved=payload.approved,
                    created_at=now,
                    updated_at=now,
                )
                next_assignments = (*state.assignments, assignment)
            else:
                assignment = existing_assignment.model_copy(
                    update={
                        "region_id": region.id,
                        "origin": payload.origin,
                        "approved": payload.approved,
                        "updated_at": now,
                    }
                )
                next_assignments = tuple(
                    assignment if candidate.id == existing_assignment.id else candidate
                    for candidate in state.assignments
                )

            next_state = state.model_copy(
                update={
                    "pages": self._replace_page_status(state, page, "text_ready"),
                    "assignments": next_assignments,
                }
            )
            self._save_state_unlocked(next_state)
            return assignment.model_copy(deep=True)

    def list_page_placements(self, project_id: UUID, page_id: UUID) -> list[TextPlacementRecord]:
        state = self._load_state()
        self._require_project(state, project_id)
        self._require_page(state, project_id, page_id)
        assignment_ids = {
            assignment.id for assignment in state.assignments if assignment.page_id == page_id
        }
        return [
            placement.model_copy(deep=True)
            for placement in sorted(
                [
                    candidate
                    for candidate in state.placements
                    if candidate.assignment_id in assignment_ids
                ],
                key=lambda candidate: candidate.created_at,
            )
        ]

    def upsert_placement(
        self,
        project_id: UUID,
        page_id: UUID,
        payload: UpsertPlacementRequest,
    ) -> TextPlacementRecord:
        with self._lock:
            state = self._load_state_unlocked()
            self._require_project(state, project_id)
            page = self._require_page(state, project_id, page_id)
            assignment = self._require_assignment(state, page_id, payload.assignment_id)
            existing_placement = next(
                (
                    candidate
                    for candidate in state.placements
                    if candidate.assignment_id == assignment.id and candidate.is_active
                ),
                None,
            )
            now = _utcnow()
            layout_metrics = {
                "mode": "manual",
                "font_size": payload.style.font_size,
            }
            if existing_placement is None:
                placement = TextPlacementRecord(
                    id=uuid4(),
                    assignment_id=assignment.id,
                    is_active=True,
                    text_box=payload.text_box,
                    style=payload.style,
                    layout_metrics=layout_metrics,
                    created_at=now,
                    updated_at=now,
                )
                next_placements = (*state.placements, placement)
            else:
                placement = existing_placement.model_copy(
                    update={
                        "text_box": payload.text_box,
                        "style": payload.style,
                        "layout_metrics": layout_metrics,
                        "updated_at": now,
                    }
                )
                next_placements = tuple(
                    placement if candidate.id == existing_placement.id else candidate
                    for candidate in state.placements
                )

            next_state = state.model_copy(
                update={
                    "pages": self._replace_page_status(state, page, "typeset_ready"),
                    "placements": next_placements,
                }
            )
            self._save_state_unlocked(next_state)
            return placement.model_copy(deep=True)

    def create_page_region(
        self,
        project_id: UUID,
        page_id: UUID,
        payload: CreateRegionRequest,
    ) -> RegionRecord:
        with self._lock:
            state = self._load_state_unlocked()
            self._require_project(state, project_id)
            self._require_page(state, project_id, page_id)
            now = _utcnow()
            region = RegionRecord(
                id=uuid4(),
                page_id=page_id,
                type=payload.type,
                origin="user_created",
                state="draft",
                confidence=None,
                bounding_box=payload.bounding_box,
                text_area=payload.bounding_box,
                context_area=payload.bounding_box,
                panel_area=payload.bounding_box,
                balloon_group_id=None,
                balloon_group_area=payload.bounding_box,
                panel_order=None,
                balloon_group_order=None,
                order_in_balloon_group=None,
                order_in_panel=None,
                global_reading_order=None,
                shape=self._polygon_shape_from_bounding_box(payload.bounding_box),
                created_at=now,
                updated_at=now,
            )
            next_state = state.model_copy(update={"regions": (*state.regions, region)})
            self._save_state_unlocked(next_state)
            return region.model_copy(deep=True)

    def update_page_region(
        self,
        project_id: UUID,
        page_id: UUID,
        region_id: UUID,
        payload: UpdateRegionRequest,
    ) -> RegionRecord:
        with self._lock:
            state = self._load_state_unlocked()
            self._require_project(state, project_id)
            self._require_page(state, project_id, page_id)
            region = self._require_region(state, page_id, region_id)
            if (
                payload.bounding_box is not None
                and payload.text_area is None
                and payload.context_area is None
            ):
                next_text_area = payload.bounding_box
                next_context_area = payload.bounding_box
            else:
                next_text_area = payload.text_area or region.text_area or region.bounding_box
                next_context_area = (
                    payload.context_area or region.context_area or region.bounding_box
                )
            next_bounding_box = payload.bounding_box or next_text_area
            next_panel_area = (
                next_context_area
                if (
                    region.panel_area is None
                    or region.panel_area == region.context_area
                    or region.panel_area == region.bounding_box
                )
                else region.panel_area
            )
            next_balloon_group_area = (
                next_context_area
                if (
                    region.balloon_group_area is None
                    or region.balloon_group_area == region.context_area
                    or region.balloon_group_area == region.bounding_box
                )
                else region.balloon_group_area
            )
            next_region = region.model_copy(
                update={
                    "type": payload.type or region.type,
                    "state": payload.state or region.state,
                    "bounding_box": next_bounding_box,
                    "text_area": next_text_area,
                    "context_area": next_context_area,
                    "panel_area": next_panel_area,
                    "balloon_group_area": next_balloon_group_area,
                    "global_reading_order": (
                        payload.global_reading_order
                        if payload.global_reading_order is not None
                        else region.global_reading_order
                    ),
                    "shape": self._polygon_shape_from_bounding_box(next_text_area),
                    "updated_at": _utcnow(),
                }
            )
            next_regions = tuple(
                next_region if candidate.id == region_id else candidate
                for candidate in state.regions
            )
            if payload.global_reading_order is not None:
                next_regions = self._reassign_page_region_reading_order(
                    next_regions,
                    page_id=page_id,
                    target_region_id=region_id,
                    target_position=payload.global_reading_order,
                )
            self._save_state_unlocked(state.model_copy(update={"regions": next_regions}))
            updated_region = next(
                candidate for candidate in next_regions if candidate.id == region_id
            )
            return updated_region.model_copy(deep=True)

    def delete_page_region(
        self,
        project_id: UUID,
        page_id: UUID,
        region_id: UUID,
    ) -> list[RegionRecord]:
        with self._lock:
            state = self._load_state_unlocked()
            self._require_project(state, project_id)
            self._require_page(state, project_id, page_id)
            self._require_region(state, page_id, region_id)
            next_state = self._remove_page_regions(
                state=state,
                page_id=page_id,
                region_ids={region_id},
            )
            self._save_state_unlocked(next_state)
            return [
                region.model_copy(deep=True)
                for region in sorted(
                    [candidate for candidate in next_state.regions if candidate.page_id == page_id],
                    key=lambda candidate: candidate.created_at,
                )
            ]

    def reset_page_regions(
        self,
        project_id: UUID,
        page_id: UUID,
    ) -> list[RegionRecord]:
        with self._lock:
            state = self._load_state_unlocked()
            self._require_project(state, project_id)
            self._require_page(state, project_id, page_id)
            region_ids = {
                candidate.id
                for candidate in state.regions
                if candidate.page_id == page_id
            }
            next_state = self._remove_page_regions(
                state=state,
                page_id=page_id,
                region_ids=region_ids,
            )
            self._save_state_unlocked(next_state)
            return [
                region.model_copy(deep=True)
                for region in sorted(
                    [candidate for candidate in next_state.regions if candidate.page_id == page_id],
                    key=lambda candidate: candidate.created_at,
                )
            ]

    def create_project(self, payload: CreateProjectRequest) -> ProjectSummary:
        with self._lock:
            state = self._load_state_unlocked()
            now = _utcnow()
            project = ProjectSummary(
                id=uuid4(),
                schema_version=SCHEMA_VERSION,
                name=payload.name,
                status="draft",
                source_language=payload.source_language,
                reading_profile=payload.reading_profile,
                target_language=payload.target_language,
                target_text_direction=payload.target_text_direction,
                page_count=0,
                created_at=now,
                updated_at=now,
            )
            next_state = state.model_copy(
                update={
                    "projects": (*state.projects, project),
                }
            )
            self._save_state_unlocked(next_state)
            return project.model_copy(deep=True)

    def register_project_pages(
        self,
        project_id: UUID,
        payload: RegisterProjectPagesRequest,
    ) -> tuple[ProjectSummary, list[RegisterUploadedProjectPage]]:
        uploads = [
            UploadedPageFile(
                file_name=page.file_name,
                mime_type=page.mime_type,
                size_bytes=page.size_bytes,
                content=b"",
                width=page.width,
                height=page.height,
            )
            for page in payload.pages
        ]
        return self._register_project_pages(project_id, uploads, persist_content=False)

    def upload_project_pages(
        self,
        project_id: UUID,
        uploads: list[UploadedPageFile],
    ) -> tuple[ProjectSummary, list[RegisterUploadedProjectPage]]:
        return self._register_project_pages(project_id, uploads, persist_content=True)

    def get_original_asset_file(
        self,
        project_id: UUID,
        page_id: UUID,
    ) -> tuple[Path, str]:
        state = self._load_state()
        self._require_project(state, project_id)
        page = next(
            (
                candidate
                for candidate in state.pages
                if candidate.project_id == project_id and candidate.id == page_id
            ),
            None,
        )
        if page is None:
            raise ProjectPageNotFoundError(str(project_id), str(page_id))

        asset = next(
            (
                candidate
                for candidate in state.assets
                if candidate.project_id == project_id and candidate.page_id == page_id
                and candidate.kind == "original"
            ),
            None,
        )
        if asset is None:
            raise ProjectPageNotFoundError(str(project_id), str(page_id))

        return self.get_project_asset_file(project_id=project_id, asset_id=asset.id)

    def get_project_asset_file(
        self,
        project_id: UUID,
        asset_id: UUID,
    ) -> tuple[Path, str]:
        state = self._load_state()
        self._require_project(state, project_id)
        asset = self._require_asset(state, project_id, asset_id)
        asset_path = self._assets_dir / asset.storage_key
        if not asset_path.exists():
            raise ProjectPageNotFoundError(str(project_id), str(asset.page_id))
        return asset_path, asset.mime_type

    def _register_project_pages(
        self,
        project_id: UUID,
        uploads: list[UploadedPageFile],
        *,
        persist_content: bool,
    ) -> tuple[ProjectSummary, list[RegisterUploadedProjectPage]]:
        with self._lock:
            state = self._load_state_unlocked()
            project = self._require_project(state, project_id)
            existing_pages = self._get_pages_for_project(state, project_id)
            next_index = len(existing_pages) + 1
            now = _utcnow()

            created_pages: list[RegisterUploadedProjectPage] = []
            created_assets: list[StoredProjectAsset] = []

            for offset, upload in enumerate(uploads):
                self._validate_upload(upload)
                inferred_width, inferred_height = infer_image_dimensions(upload.content, upload.mime_type)
                page_width = upload.width if upload.width is not None else inferred_width
                page_height = upload.height if upload.height is not None else inferred_height
                page_id = uuid4()
                asset_id = uuid4()
                storage_key = self._build_storage_key(project_id, asset_id, upload)
                if persist_content:
                    asset_path = self._assets_dir / storage_key
                    asset_path.parent.mkdir(parents=True, exist_ok=True)
                    asset_path.write_bytes(upload.content)

                page = RegisterUploadedProjectPage(
                    id=page_id,
                    project_id=project_id,
                    index=next_index + offset,
                    file_name=upload.file_name,
                    mime_type=upload.mime_type,
                    size_bytes=upload.size_bytes,
                    width=page_width,
                    height=page_height,
                    status="uploaded",
                    original_asset_path=self._build_original_asset_path(project_id, page_id),
                    active_cleaned_asset_path=None,
                    created_at=now,
                    updated_at=now,
                )
                asset = StoredProjectAsset(
                    id=asset_id,
                    project_id=project_id,
                    page_id=page_id,
                    kind="original",
                    file_name=upload.file_name,
                    storage_key=storage_key,
                    mime_type=upload.mime_type,
                    size_bytes=upload.size_bytes,
                    created_at=now,
                    updated_at=now,
                )
                created_pages.append(page)
                created_assets.append(asset)

            updated_project = project.model_copy(
                update={
                    "page_count": project.page_count + len(created_pages),
                    "updated_at": now,
                }
            )

            next_projects = tuple(
                updated_project if candidate.id == project_id else candidate
                for candidate in state.projects
            )
            next_state = state.model_copy(
                update={
                    "projects": next_projects,
                    "pages": (*state.pages, *created_pages),
                    "assets": (*state.assets, *created_assets),
                }
            )
            self._save_state_unlocked(next_state)

            return updated_project.model_copy(deep=True), [
                page.model_copy(deep=True) for page in created_pages
            ]

    def _validate_upload(self, upload: UploadedPageFile) -> None:
        if upload.mime_type not in SUPPORTED_UPLOAD_MIME_TYPES:
            raise UploadValidationError(
                "Unsupported upload type. Use JPEG, PNG, or WEBP files."
            )
        if upload.size_bytes < 1:
            raise UploadValidationError("Uploaded files must not be empty.")
        if upload.size_bytes > MAX_UPLOAD_FILE_SIZE_BYTES:
            raise UploadValidationError("Uploaded file exceeds the current 25 MB limit.")

    def _build_storage_key(
        self,
        project_id: UUID,
        asset_id: UUID,
        upload: UploadedPageFile,
    ) -> str:
        guessed_extension = mimetypes.guess_extension(upload.mime_type) or Path(upload.file_name).suffix
        extension = guessed_extension if guessed_extension else ".bin"
        return str(Path(str(project_id)) / f"{asset_id}{extension}")

    def _build_original_asset_path(self, project_id: UUID, page_id: UUID) -> str:
        return f"{self._api_prefix}/projects/{project_id}/pages/{page_id}/original"

    def _build_project_asset_path(self, project_id: UUID, asset_id: UUID) -> str:
        return f"{self._api_prefix}/projects/{project_id}/assets/{asset_id}"

    def _require_project(self, state: StoredProjectState, project_id: UUID) -> ProjectSummary:
        project = next((candidate for candidate in state.projects if candidate.id == project_id), None)
        if project is None:
            raise ProjectNotFoundError(str(project_id))
        return project

    def _require_page(
        self,
        state: StoredProjectState,
        project_id: UUID,
        page_id: UUID,
    ) -> ProjectPage:
        page = next(
            (
                candidate
                for candidate in state.pages
                if candidate.project_id == project_id and candidate.id == page_id
            ),
            None,
        )
        if page is None:
            raise ProjectPageNotFoundError(str(project_id), str(page_id))
        return page

    def _require_original_asset(
        self,
        state: StoredProjectState,
        project_id: UUID,
        page_id: UUID,
    ) -> StoredProjectAsset:
        asset = next(
            (
                candidate
                for candidate in state.assets
                if candidate.project_id == project_id
                and candidate.page_id == page_id
                and candidate.kind == "original"
            ),
            None,
        )
        if asset is None:
            raise ProjectPageNotFoundError(str(project_id), str(page_id))
        return asset

    def _require_region(
        self,
        state: StoredProjectState,
        page_id: UUID,
        region_id: UUID,
    ) -> RegionRecord:
        region = next(
            (
                candidate
                for candidate in state.regions
                if candidate.page_id == page_id and candidate.id == region_id
            ),
            None,
        )
        if region is None:
            raise RegionNotFoundError(str(page_id), str(region_id))
        return region

    def _require_mask_revision(
        self,
        state: StoredProjectState,
        page_id: UUID,
        mask_revision_id: UUID,
    ) -> MaskRevisionRecord:
        page_region_ids = {
            region.id for region in state.regions if region.page_id == page_id
        }
        mask_revision = next(
            (
                candidate
                for candidate in state.mask_revisions
                if candidate.id == mask_revision_id and candidate.region_id in page_region_ids
            ),
            None,
        )
        if mask_revision is None:
            raise MaskRevisionNotFoundError(str(page_id), str(mask_revision_id))
        return mask_revision

    def _require_dialogue(
        self,
        state: StoredProjectState,
        page_id: UUID,
        dialogue_id: UUID,
    ) -> DialogueRecord:
        dialogue = next(
            (
                candidate
                for candidate in state.dialogues
                if candidate.page_id == page_id and candidate.id == dialogue_id
            ),
            None,
        )
        if dialogue is None:
            raise ProjectPageNotFoundError(str(page_id), str(dialogue_id))
        return dialogue

    def _require_assignment(
        self,
        state: StoredProjectState,
        page_id: UUID,
        assignment_id: UUID,
    ) -> AssignmentRecord:
        assignment = next(
            (
                candidate
                for candidate in state.assignments
                if candidate.page_id == page_id and candidate.id == assignment_id
            ),
            None,
        )
        if assignment is None:
            raise ProjectPageNotFoundError(str(page_id), str(assignment_id))
        return assignment

    def _require_asset(
        self,
        state: StoredProjectState,
        project_id: UUID,
        asset_id: UUID,
    ) -> StoredProjectAsset:
        asset = next(
            (
                candidate
                for candidate in state.assets
                if candidate.project_id == project_id and candidate.id == asset_id
            ),
            None,
        )
        if asset is None:
            raise ProjectNotFoundError(str(project_id))
        return asset

    def _get_approved_active_mask_revisions_for_page(
        self,
        state: StoredProjectState,
        page_id: UUID,
    ) -> tuple[MaskRevisionRecord, ...]:
        page_region_ids = {
            region.id for region in state.regions if region.page_id == page_id
        }
        return tuple(
            candidate
            for candidate in state.mask_revisions
            if candidate.region_id in page_region_ids and candidate.is_active and candidate.approved
        )

    def _get_page_dialogues(
        self,
        state: StoredProjectState,
        page_id: UUID,
    ) -> list[DialogueRecord]:
        return sorted(
            [candidate for candidate in state.dialogues if candidate.page_id == page_id],
            key=lambda candidate: (candidate.reading_order, candidate.created_at),
        )

    def _get_ocr_candidate_regions_for_page(
        self,
        state: StoredProjectState,
        page_id: UUID,
    ) -> tuple[RegionRecord, ...]:
        supported_region_types = {"speech_balloon", "narration_box", "free_text", "unknown"}
        return tuple(
            self._sort_regions_by_reading_order(
                [
                    candidate
                    for candidate in state.regions
                    if candidate.page_id == page_id
                    and candidate.state != "rejected"
                    and candidate.type in supported_region_types
                ]
            )
        )

    def _replace_page_after_mask_change(
        self,
        *,
        state: StoredProjectState,
        page: ProjectPage,
        next_mask_revisions: tuple[MaskRevisionRecord, ...],
    ) -> tuple[ProjectPage, ...]:
        next_state = state.model_copy(update={"mask_revisions": next_mask_revisions})
        approved_active_mask_exists = len(
            self._get_approved_active_mask_revisions_for_page(next_state, page.id)
        ) > 0

        next_page = page.model_copy(
            update={
                "status": "cleanup_ready" if approved_active_mask_exists else "analyzed",
                "active_cleaned_asset_path": None,
                "updated_at": _utcnow(),
            }
        )
        return tuple(
            next_page if candidate.id == page.id else candidate
            for candidate in state.pages
        )

    def _replace_page_status(
        self,
        state: StoredProjectState,
        page: ProjectPage,
        next_status: str,
    ) -> tuple[ProjectPage, ...]:
        ordered_statuses = {
            "uploaded": 0,
            "analyzed": 1,
            "cleanup_ready": 2,
            "cleaned": 3,
            "text_ready": 4,
            "typeset_ready": 5,
            "export_ready": 6,
            "error": 7,
        }
        current_status = page.status
        effective_status = (
            current_status
            if ordered_statuses[current_status] > ordered_statuses[next_status]
            else next_status
        )
        updated_page = page.model_copy(
            update={
                "status": effective_status,
                "updated_at": _utcnow(),
            }
        )
        return tuple(
            updated_page if candidate.id == page.id else candidate
            for candidate in state.pages
        )

    def _remove_page_regions(
        self,
        *,
        state: StoredProjectState,
        page_id: UUID,
        region_ids: set[UUID],
    ) -> StoredProjectState:
        if len(region_ids) == 0:
            return state

        removed_dialogue_ids = {
            candidate.id
            for candidate in state.dialogues
            if candidate.page_id == page_id
            and candidate.source == "ocr"
            and candidate.source_region_id in region_ids
        }
        removed_assignment_ids = {
            candidate.id
            for candidate in state.assignments
            if candidate.page_id == page_id
            and (
                candidate.region_id in region_ids
                or candidate.dialogue_id in removed_dialogue_ids
            )
        }
        next_regions = tuple(
            candidate
            for candidate in state.regions
            if not (candidate.page_id == page_id and candidate.id in region_ids)
        )
        next_mask_revisions = tuple(
            candidate
            for candidate in state.mask_revisions
            if candidate.region_id not in region_ids
        )
        next_dialogues = tuple(
            candidate
            for candidate in state.dialogues
            if candidate.id not in removed_dialogue_ids
        )
        next_translations = tuple(
            candidate
            for candidate in state.translations
            if candidate.dialogue_id not in removed_dialogue_ids
        )
        next_assignments = tuple(
            candidate
            for candidate in state.assignments
            if candidate.id not in removed_assignment_ids
        )
        next_placements = tuple(
            candidate
            for candidate in state.placements
            if candidate.assignment_id not in removed_assignment_ids
        )
        next_jobs = tuple(
            candidate
            for candidate in state.jobs
            if not (
                candidate.page_id == page_id
                and candidate.status == "queued"
                and candidate.type in {
                    "detect_regions",
                    "generate_cleanup",
                    "run_ocr",
                    "match_dialogue",
                }
            )
        )
        next_pages = self._recalculate_page_after_region_change(
            state=state,
            page_id=page_id,
            next_regions=next_regions,
            next_mask_revisions=next_mask_revisions,
            next_dialogues=next_dialogues,
            next_translations=next_translations,
            next_assignments=next_assignments,
            next_placements=next_placements,
        )
        return state.model_copy(
            update={
                "pages": next_pages,
                "regions": next_regions,
                "mask_revisions": next_mask_revisions,
                "dialogues": next_dialogues,
                "translations": next_translations,
                "assignments": next_assignments,
                "placements": next_placements,
                "jobs": next_jobs,
            }
        )

    def _recalculate_page_after_region_change(
        self,
        *,
        state: StoredProjectState,
        page_id: UUID,
        next_regions: tuple[RegionRecord, ...],
        next_mask_revisions: tuple[MaskRevisionRecord, ...],
        next_dialogues: tuple[DialogueRecord, ...],
        next_translations: tuple[TranslationRecord, ...],
        next_assignments: tuple[AssignmentRecord, ...],
        next_placements: tuple[TextPlacementRecord, ...],
    ) -> tuple[ProjectPage, ...]:
        page = next(candidate for candidate in state.pages if candidate.id == page_id)
        region_ids = {candidate.id for candidate in next_regions if candidate.page_id == page_id}
        approved_active_mask_exists = any(
            candidate.region_id in region_ids and candidate.is_active and candidate.approved
            for candidate in next_mask_revisions
        )
        page_dialogue_ids = {
            candidate.id for candidate in next_dialogues if candidate.page_id == page_id
        }
        page_assignment_ids = {
            candidate.id for candidate in next_assignments if candidate.page_id == page_id
        }
        has_placements = any(
            candidate.assignment_id in page_assignment_ids for candidate in next_placements
        )
        has_text = (
            len(page_dialogue_ids) > 0
            or any(candidate.dialogue_id in page_dialogue_ids for candidate in next_translations)
            or len(page_assignment_ids) > 0
        )
        has_regions = len(region_ids) > 0

        if has_placements:
            next_status = "typeset_ready"
        elif has_text:
            next_status = "text_ready"
        elif approved_active_mask_exists:
            next_status = "cleanup_ready"
        elif has_regions:
            next_status = "analyzed"
        else:
            next_status = "uploaded"

        updated_page = page.model_copy(
            update={
                "status": next_status,
                "active_cleaned_asset_path": None,
                "updated_at": _utcnow(),
            }
        )
        return tuple(
            updated_page if candidate.id == page.id else candidate
            for candidate in state.pages
        )

    def _get_pages_for_project(
        self,
        state: StoredProjectState,
        project_id: UUID,
    ) -> list[ProjectPage]:
        return sorted(
            [page for page in state.pages if page.project_id == project_id],
            key=lambda page: page.index,
        )

    def _ensure_storage_ready(self) -> None:
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._assets_dir.mkdir(parents=True, exist_ok=True)
        if not self._state_file.exists():
            empty_state = StoredProjectState()
            self._state_file.write_text(
                empty_state.model_dump_json(indent=2),
                encoding="utf-8",
            )

    def _load_state(self) -> StoredProjectState:
        with self._lock:
            return self._load_state_unlocked()

    def _load_state_unlocked(self) -> StoredProjectState:
        if not self._state_file.exists():
            return StoredProjectState()
        raw_text = self._state_file.read_text(encoding="utf-8").strip()
        if raw_text == "":
            return StoredProjectState()
        return StoredProjectState.model_validate(json.loads(raw_text))

    def _save_state_unlocked(self, state: StoredProjectState) -> None:
        temp_file = self._state_file.with_suffix(".tmp")
        temp_file.write_text(state.model_dump_json(indent=2), encoding="utf-8")
        self._replace_state_file_with_retry(temp_file, self._state_file)

    def _replace_state_file_with_retry(
        self,
        source_path: Path,
        target_path: Path,
        *,
        attempts: int = STATE_REPLACE_ATTEMPTS,
        delay_seconds: float = STATE_REPLACE_DELAY_SECONDS,
    ) -> None:
        for attempt in range(attempts):
            try:
                source_path.replace(target_path)
                return
            except PermissionError:
                if attempt == attempts - 1:
                    raise
                sleep(delay_seconds)

    def _polygon_shape_from_bounding_box(self, bounding_box: BoundingBox) -> PolygonShape:
        x = bounding_box.x
        y = bounding_box.y
        width = bounding_box.width
        height = bounding_box.height
        return PolygonShape(
            type="polygon",
            points=(
                PolygonPoint(x=x, y=y),
                PolygonPoint(x=x + width, y=y),
                PolygonPoint(x=x + width, y=y + height),
                PolygonPoint(x=x, y=y + height),
            ),
        )
