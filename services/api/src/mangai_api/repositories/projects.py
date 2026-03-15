from __future__ import annotations

import json
import mimetypes
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from threading import Lock
from uuid import UUID, uuid4

from mangai_api.constants import (
    MAX_UPLOAD_FILE_SIZE_BYTES,
    SCHEMA_VERSION,
    SUPPORTED_UPLOAD_MIME_TYPES,
)
from mangai_api.domain_errors import (
    ProjectNotFoundError,
    ProjectPageNotFoundError,
    UploadValidationError,
)
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


def _utcnow() -> datetime:
    return datetime.now(UTC)


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
            ),
            None,
        )
        if asset is None:
            raise ProjectPageNotFoundError(str(project_id), str(page_id))

        asset_path = self._assets_dir / asset.storage_key
        if not asset_path.exists():
            raise ProjectPageNotFoundError(str(project_id), str(page_id))
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
                    width=upload.width,
                    height=upload.height,
                    status="uploaded",
                    original_asset_path=self._build_original_asset_path(project_id, page_id),
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

    def _require_project(self, state: StoredProjectState, project_id: UUID) -> ProjectSummary:
        project = next((candidate for candidate in state.projects if candidate.id == project_id), None)
        if project is None:
            raise ProjectNotFoundError(str(project_id))
        return project

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
        temp_file.replace(self._state_file)
