from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from mangai_api.constants import SCHEMA_VERSION
from mangai_api.domain_errors import ProjectNotFoundError
from mangai_api.models.project import (
    CreateProjectRequest,
    PageUploadDraft,
    ProjectSummary,
    RegisterProjectPagesRequest,
)


def _utcnow() -> datetime:
    return datetime.now(UTC)


class InMemoryProjectStore:
    def __init__(self) -> None:
        self._projects: dict[UUID, ProjectSummary] = {}
        self._pages_by_project: dict[UUID, list[PageUploadDraft]] = {}

    def list_projects(self) -> list[ProjectSummary]:
        projects = sorted(
            self._projects.values(),
            key=lambda project: project.created_at,
            reverse=True,
        )
        return [project.model_copy(deep=True) for project in projects]

    def create_project(self, payload: CreateProjectRequest) -> ProjectSummary:
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
        self._projects[project.id] = project
        self._pages_by_project[project.id] = []
        return project.model_copy(deep=True)

    def register_project_pages(
        self,
        project_id: UUID,
        payload: RegisterProjectPagesRequest,
    ) -> tuple[ProjectSummary, list[PageUploadDraft]]:
        project = self._projects.get(project_id)
        if project is None:
            raise ProjectNotFoundError(str(project_id))

        existing_pages = self._pages_by_project.setdefault(project_id, [])
        now = _utcnow()
        next_index = len(existing_pages) + 1
        created_pages: list[PageUploadDraft] = []

        for offset, page in enumerate(payload.pages):
            created_page = PageUploadDraft(
                id=uuid4(),
                project_id=project_id,
                index=next_index + offset,
                file_name=page.file_name,
                mime_type=page.mime_type,
                size_bytes=page.size_bytes,
                width=page.width,
                height=page.height,
                status="uploaded",
                created_at=now,
                updated_at=now,
            )
            existing_pages.append(created_page)
            created_pages.append(created_page)

        updated_project = project.model_copy(
            update={
                "page_count": len(existing_pages),
                "updated_at": now,
            }
        )
        self._projects[project_id] = updated_project

        return updated_project.model_copy(deep=True), [
            page.model_copy(deep=True) for page in created_pages
        ]
