from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from mpxccp.models.technical_device import (
    DeviceAccessIntegrityDetail,
    DeviceAuthDetail,
    DeviceExecutableIntegrityDetail,
    DeviceLogIntegrityDetail,
    DeviceObject,
    DeviceRemoteManagementDetail,
)


class DeviceRepository:
    def list_objects(self, session: Session, project_id: int) -> list[DeviceObject]:
        return list(
            session.scalars(
                select(DeviceObject)
                .where(DeviceObject.project_id == project_id)
                .order_by(DeviceObject.sort_order, DeviceObject.id)
            )
        )

    def get_object(self, session: Session, object_id: int) -> DeviceObject | None:
        return session.get(DeviceObject, object_id)

    def create_object(self, session: Session, project_id: int, name: str) -> DeviceObject:
        obj = DeviceObject(
            project_id=project_id,
            name=name,
            sort_order=self._next_sort_order(session, project_id),
        )
        session.add(obj)
        session.flush()
        session.add_all(
            [
                DeviceAuthDetail(
                    project_id=project_id,
                    device_object_id=obj.id,
                    sort_order=0,
                ),
                DeviceRemoteManagementDetail(
                    project_id=project_id,
                    device_object_id=obj.id,
                    sort_order=1,
                ),
                DeviceAccessIntegrityDetail(
                    project_id=project_id,
                    device_object_id=obj.id,
                    sort_order=2,
                ),
                DeviceLogIntegrityDetail(
                    project_id=project_id,
                    device_object_id=obj.id,
                    sort_order=3,
                ),
                DeviceExecutableIntegrityDetail(
                    project_id=project_id,
                    device_object_id=obj.id,
                    sort_order=4,
                ),
            ]
        )
        session.flush()
        return obj

    def load_auth_detail(self, session: Session, object_id: int) -> DeviceAuthDetail | None:
        return session.scalar(
            select(DeviceAuthDetail).where(DeviceAuthDetail.device_object_id == object_id)
        )

    def load_remote_management_detail(
        self,
        session: Session,
        object_id: int,
    ) -> DeviceRemoteManagementDetail | None:
        return session.scalar(
            select(DeviceRemoteManagementDetail).where(
                DeviceRemoteManagementDetail.device_object_id == object_id
            )
        )

    def load_access_integrity_detail(
        self,
        session: Session,
        object_id: int,
    ) -> DeviceAccessIntegrityDetail | None:
        return session.scalar(
            select(DeviceAccessIntegrityDetail).where(
                DeviceAccessIntegrityDetail.device_object_id == object_id
            )
        )

    def load_log_integrity_detail(
        self,
        session: Session,
        object_id: int,
    ) -> DeviceLogIntegrityDetail | None:
        return session.scalar(
            select(DeviceLogIntegrityDetail).where(
                DeviceLogIntegrityDetail.device_object_id == object_id
            )
        )

    def load_executable_integrity_detail(
        self,
        session: Session,
        object_id: int,
    ) -> DeviceExecutableIntegrityDetail | None:
        return session.scalar(
            select(DeviceExecutableIntegrityDetail).where(
                DeviceExecutableIntegrityDetail.device_object_id == object_id
            )
        )

    def _next_sort_order(self, session: Session, project_id: int) -> int:
        current_max = session.scalar(
            select(func.max(DeviceObject.sort_order)).where(DeviceObject.project_id == project_id)
        )
        return int(current_max or 0) + 1
