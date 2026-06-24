from __future__ import annotations

from collections.abc import Iterable

from sqlalchemy import Engine

from mpxccp.repositories.project_repo import ProjectRepository
from mpxccp.repositories.session import readonly_session_scope, session_scope
from mpxccp.services.result import ServiceResult


class ProjectService:
    def __init__(
        self,
        engine: Engine,
        project_repo: ProjectRepository | None = None,
    ) -> None:
        self.engine = engine
        self.project_repo = project_repo or ProjectRepository()

    def new_project_state(self) -> ServiceResult:
        return ServiceResult(
            success=True,
            message="new project is pending required basic information",
            payload={"requires": ["flow_no", "system_name"]},
        )

    def list_openable(self) -> list[dict[str, object]]:
        with readonly_session_scope(self.engine) as session:
            return self.project_repo.list_openable(session)

    def open_project(self, project_id: int) -> ServiceResult:
        with readonly_session_scope(self.engine) as session:
            project = self.project_repo.get_openable(session, project_id)
            if project is None:
                return ServiceResult(
                    success=False,
                    message="project not found or deleted",
                    project_id=project_id,
                    warnings=["project_not_openable"],
                )
            return ServiceResult(
                success=True,
                message="project opened",
                project_id=project.id,
                payload={"project": self.project_repo.project_row(project)},
            )

    def soft_delete(
        self,
        project_id: int,
        *,
        deleted_by: str = "",
        reason: str = "",
    ) -> ServiceResult:
        with session_scope(self.engine) as session:
            project = self.project_repo.get(session, project_id)
            if project is None:
                return ServiceResult(
                    success=False,
                    message="project not found",
                    project_id=project_id,
                    warnings=["project_not_found"],
                )
            project.is_deleted = True
            project.status = "deleted"
            self.project_repo.ensure_deleted_record(
                session,
                project,
                deleted_by=deleted_by,
                reason=reason,
            )
            return ServiceResult(
                success=True,
                message="project soft deleted",
                project_id=project.id,
            )

    def restore(self, project_ids: Iterable[int]) -> ServiceResult:
        ids = list(dict.fromkeys(project_ids))
        with session_scope(self.engine) as session:
            restored = self.project_repo.restore(session, ids)
            return ServiceResult(
                success=True,
                message="projects restored",
                payload={"restored": restored},
            )

    def hard_delete(self, project_id: int) -> ServiceResult:
        with session_scope(self.engine) as session:
            deleted = self.project_repo.hard_delete(session, project_id)
            if not deleted:
                return ServiceResult(
                    success=False,
                    message="project not found",
                    project_id=project_id,
                    warnings=["project_not_found"],
                )
            return ServiceResult(
                success=True,
                message="project hard deleted",
                project_id=project_id,
            )
