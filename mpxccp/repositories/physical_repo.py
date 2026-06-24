from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from mpxccp.models.technical_physical import (
    PhysicalAccessIntegrityDetail,
    PhysicalAuthDetail,
    PhysicalObject,
    PhysicalVideoIntegrityDetail,
)


class PhysicalRepository:
    def list_objects(self, session: Session, project_id: int) -> list[PhysicalObject]:
        return list(
            session.scalars(
                select(PhysicalObject)
                .where(PhysicalObject.project_id == project_id)
                .order_by(PhysicalObject.sort_order, PhysicalObject.id)
            )
        )

    def get_object(self, session: Session, object_id: int) -> PhysicalObject | None:
        return session.get(PhysicalObject, object_id)

    def create_object(self, session: Session, project_id: int, name: str) -> PhysicalObject:
        obj = PhysicalObject(
            project_id=project_id,
            name=name,
            sort_order=self._next_sort_order(session, project_id),
        )
        session.add(obj)
        session.flush()
        session.add_all(
            [
                PhysicalAuthDetail(
                    project_id=project_id,
                    physical_object_id=obj.id,
                    sort_order=0,
                ),
                PhysicalAccessIntegrityDetail(
                    project_id=project_id,
                    physical_object_id=obj.id,
                    sort_order=1,
                ),
                PhysicalVideoIntegrityDetail(
                    project_id=project_id,
                    physical_object_id=obj.id,
                    sort_order=2,
                ),
            ]
        )
        session.flush()
        return obj

    def load_auth_detail(
        self,
        session: Session,
        object_id: int,
    ) -> PhysicalAuthDetail | None:
        return session.scalar(
            select(PhysicalAuthDetail).where(PhysicalAuthDetail.physical_object_id == object_id)
        )

    def load_access_integrity_detail(
        self,
        session: Session,
        object_id: int,
    ) -> PhysicalAccessIntegrityDetail | None:
        return session.scalar(
            select(PhysicalAccessIntegrityDetail).where(
                PhysicalAccessIntegrityDetail.physical_object_id == object_id
            )
        )

    def load_video_integrity_detail(
        self,
        session: Session,
        object_id: int,
    ) -> PhysicalVideoIntegrityDetail | None:
        return session.scalar(
            select(PhysicalVideoIntegrityDetail).where(
                PhysicalVideoIntegrityDetail.physical_object_id == object_id
            )
        )

    def _next_sort_order(self, session: Session, project_id: int) -> int:
        current_max = session.scalar(
            select(func.max(PhysicalObject.sort_order)).where(
                PhysicalObject.project_id == project_id
            )
        )
        return int(current_max or 0) + 1
