from __future__ import annotations

from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

import mpxccp.models as models
from mpxccp.models.project import DeletedProject, Project

SHARED_SCOPE_MODELS: tuple[type, ...] = (
    models.QuantitativeAssessment,
    models.EvidenceImage,
    models.CryptoProduct,
)

TECHNICAL_DETAIL_MODELS: tuple[type, ...] = (
    models.PhysicalAuthDetail,
    models.PhysicalAccessIntegrityDetail,
    models.PhysicalVideoIntegrityDetail,
    models.DeviceAuthDetail,
    models.DeviceRemoteManagementDetail,
    models.DeviceAccessIntegrityDetail,
    models.DeviceLogIntegrityDetail,
    models.DeviceExecutableIntegrityDetail,
    models.NetworkAuthDetail,
    models.NetworkIntegrityDetail,
    models.NetworkConfidentialityDetail,
    models.NetworkBoundaryIntegrityDetail,
    models.ApplicationUserAuthDetail,
    models.AccessControlIntegrityDetail,
    models.DataTransportConfidentialityDetail,
    models.DataStorageConfidentialityDetail,
    models.DataTransportIntegrityDetail,
    models.DataStorageIntegrityDetail,
    models.BusinessActionNonRepudiationDetail,
)

TECHNICAL_OBJECT_MODELS: tuple[type, ...] = (
    models.PhysicalObject,
    models.DeviceObject,
    models.ApplicationUser,
    models.AccessControlObject,
    models.ImportantData,
    models.BusinessAction,
    models.NetworkChannel,
    models.NetworkSubsystem,
    models.ApplicationSubsystem,
)

BASIC_INFO_MODELS: tuple[type, ...] = (
    models.BasicInfo,
    models.SystemInfo,
    models.CryptoApplicationInfo,
    models.Subsystem,
)

SCORING_MODELS: tuple[type, ...] = (
    models.ScoreDetail,
    models.ScoreSummary,
    models.ManagementScore,
)

RECYCLE_BIN_MODELS: tuple[type, ...] = (models.DeletedProject,)


class ProjectRepository:
    def list_openable(self, session: Session) -> list[dict[str, object]]:
        projects = session.scalars(
            select(Project)
            .where(Project.is_deleted.is_(False))
            .order_by(Project.created_at.desc(), Project.id.desc())
        ).all()
        return [self._project_row(project) for project in projects]

    def get(self, session: Session, project_id: int) -> Project | None:
        return session.get(Project, project_id)

    def get_openable(self, session: Session, project_id: int) -> Project | None:
        project = self.get(session, project_id)
        if project is None or project.is_deleted:
            return None
        return project

    def ensure_deleted_record(
        self,
        session: Session,
        project: Project,
        *,
        deleted_by: str = "",
        reason: str = "",
    ) -> DeletedProject:
        record = session.scalar(
            select(DeletedProject).where(DeletedProject.project_id == project.id)
        )
        if record is None:
            record = DeletedProject(
                project_id=project.id,
                flow_no=project.flow_no,
                system_name=project.system_name,
                deleted_by=deleted_by,
                reason=reason,
                project_snapshot=self._project_row(project),
            )
            session.add(record)
            return record

        record.flow_no = project.flow_no
        record.system_name = project.system_name
        if deleted_by:
            record.deleted_by = deleted_by
        if reason:
            record.reason = reason
        record.project_snapshot = self._project_row(project)
        return record

    def restore(self, session: Session, project_ids: list[int]) -> list[int]:
        if not project_ids:
            return []

        projects = session.scalars(select(Project).where(Project.id.in_(project_ids))).all()
        restored: list[int] = []
        for project in projects:
            project.is_deleted = False
            project.status = "active"
            restored.append(project.id)
        session.execute(delete(DeletedProject).where(DeletedProject.project_id.in_(project_ids)))
        return restored

    def hard_delete(self, session: Session, project_id: int) -> bool:
        project = session.get(Project, project_id)
        if project is None:
            return False

        # DEL-003: delete only database rows scoped to the target project.
        # Evidence image files on disk are intentionally outside this sequence.
        for delete_step in (
            SHARED_SCOPE_MODELS,
            TECHNICAL_DETAIL_MODELS,
            TECHNICAL_OBJECT_MODELS,
            BASIC_INFO_MODELS,
            SCORING_MODELS,
            RECYCLE_BIN_MODELS,
        ):
            for model in delete_step:
                self._delete_project_rows(session, model, project_id)

        session.execute(delete(Project).where(Project.id == project_id))
        return True

    def project_row(self, project: Project) -> dict[str, Any]:
        return self._project_row(project)

    def _delete_project_rows(self, session: Session, model: type, project_id: int) -> None:
        session.execute(delete(model).where(model.project_id == project_id))

    def _project_row(self, project: Project) -> dict[str, Any]:
        return {
            "id": project.id,
            "flow_no": project.flow_no,
            "system_name": project.system_name,
            "client_name": project.client_name,
            "assessment_org": project.assessment_org,
            "status": project.status,
            "is_deleted": project.is_deleted,
            "created_at": project.created_at.isoformat(),
            "updated_at": project.updated_at.isoformat(),
        }