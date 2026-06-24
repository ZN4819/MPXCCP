from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from mpxccp.models.basic_info import Subsystem
from mpxccp.models.technical_application import (
    AccessControlIntegrityDetail,
    AccessControlObject,
    ApplicationSubsystem,
    ApplicationUser,
    ApplicationUserAuthDetail,
    BusinessAction,
    BusinessActionNonRepudiationDetail,
    DataStorageConfidentialityDetail,
    DataStorageIntegrityDetail,
    DataTransportConfidentialityDetail,
    DataTransportIntegrityDetail,
    ImportantData,
)


class ApplicationRepository:
    def list_subsystems(self, session: Session, project_id: int) -> list[ApplicationSubsystem]:
        return list(
            session.scalars(
                select(ApplicationSubsystem)
                .where(ApplicationSubsystem.project_id == project_id)
                .order_by(ApplicationSubsystem.sort_order, ApplicationSubsystem.id)
            )
        )

    def get_subsystem(self, session: Session, subsystem_id: int) -> ApplicationSubsystem | None:
        return session.get(ApplicationSubsystem, subsystem_id)

    def sync_from_basic_subsystems(
        self,
        session: Session,
        project_id: int,
    ) -> list[ApplicationSubsystem]:
        basic_subsystems = list(
            session.scalars(
                select(Subsystem)
                .where(
                    Subsystem.project_id == project_id,
                    Subsystem.is_enabled.is_(True),
                )
                .order_by(Subsystem.sort_order, Subsystem.id)
            )
        )
        by_basic_id = {
            item.basic_subsystem_id: item
            for item in session.scalars(
                select(ApplicationSubsystem).where(
                    ApplicationSubsystem.project_id == project_id
                )
            )
            if item.basic_subsystem_id is not None
        }
        by_name = {
            item.name: item
            for item in session.scalars(
                select(ApplicationSubsystem).where(
                    ApplicationSubsystem.project_id == project_id
                )
            )
        }
        synced: list[ApplicationSubsystem] = []
        for basic in basic_subsystems:
            application = by_basic_id.get(basic.id) or by_name.get(basic.name)
            if application is None:
                application = ApplicationSubsystem(
                    project_id=project_id,
                    name=basic.name,
                    description=basic.description,
                )
                session.add(application)
            application.basic_subsystem_id = basic.id
            application.name = basic.name
            application.sort_order = basic.sort_order
            synced.append(application)
        session.flush()
        return synced

    def list_users(self, session: Session, subsystem_id: int) -> list[ApplicationUser]:
        return list(
            session.scalars(
                select(ApplicationUser)
                .where(ApplicationUser.application_subsystem_id == subsystem_id)
                .order_by(ApplicationUser.sort_order, ApplicationUser.id)
            )
        )

    def list_access_controls(
        self,
        session: Session,
        subsystem_id: int,
    ) -> list[AccessControlObject]:
        return list(
            session.scalars(
                select(AccessControlObject)
                .where(AccessControlObject.application_subsystem_id == subsystem_id)
                .order_by(AccessControlObject.sort_order, AccessControlObject.id)
            )
        )

    def list_important_data(self, session: Session, subsystem_id: int) -> list[ImportantData]:
        return list(
            session.scalars(
                select(ImportantData)
                .where(ImportantData.application_subsystem_id == subsystem_id)
                .order_by(ImportantData.sort_order, ImportantData.id)
            )
        )

    def list_business_actions(self, session: Session, subsystem_id: int) -> list[BusinessAction]:
        return list(
            session.scalars(
                select(BusinessAction)
                .where(BusinessAction.application_subsystem_id == subsystem_id)
                .order_by(BusinessAction.sort_order, BusinessAction.id)
            )
        )

    def get_user(self, session: Session, object_id: int) -> ApplicationUser | None:
        return session.get(ApplicationUser, object_id)

    def get_access_control(self, session: Session, object_id: int) -> AccessControlObject | None:
        return session.get(AccessControlObject, object_id)

    def get_important_data(self, session: Session, object_id: int) -> ImportantData | None:
        return session.get(ImportantData, object_id)

    def get_business_action(self, session: Session, object_id: int) -> BusinessAction | None:
        return session.get(BusinessAction, object_id)

    def create_user(
        self,
        session: Session,
        subsystem_id: int,
        name: str,
    ) -> ApplicationUser:
        subsystem = self._require_subsystem(session, subsystem_id)
        user = ApplicationUser(
            project_id=subsystem.project_id,
            application_subsystem_id=subsystem.id,
            name=name,
            sort_order=self._next_sort_order(session, ApplicationUser, subsystem.id),
        )
        session.add(user)
        session.flush()
        session.add(
            ApplicationUserAuthDetail(
                project_id=subsystem.project_id,
                application_user_id=user.id,
                sort_order=0,
            )
        )
        session.flush()
        return user

    def create_access_control(
        self,
        session: Session,
        subsystem_id: int,
        name: str,
    ) -> AccessControlObject:
        subsystem = self._require_subsystem(session, subsystem_id)
        obj = AccessControlObject(
            project_id=subsystem.project_id,
            application_subsystem_id=subsystem.id,
            name=name,
            sort_order=self._next_sort_order(session, AccessControlObject, subsystem.id),
        )
        session.add(obj)
        session.flush()
        session.add(
            AccessControlIntegrityDetail(
                project_id=subsystem.project_id,
                access_control_object_id=obj.id,
                sort_order=0,
            )
        )
        session.flush()
        return obj

    def create_important_data(
        self,
        session: Session,
        subsystem_id: int,
        name: str,
        data_type: str,
    ) -> ImportantData:
        subsystem = self._require_subsystem(session, subsystem_id)
        data = ImportantData(
            project_id=subsystem.project_id,
            application_subsystem_id=subsystem.id,
            name=name,
            data_type=data_type,
            sort_order=self._next_sort_order(session, ImportantData, subsystem.id),
        )
        session.add(data)
        session.flush()
        session.add_all(
            [
                DataTransportConfidentialityDetail(
                    project_id=subsystem.project_id,
                    important_data_id=data.id,
                    sort_order=0,
                ),
                DataStorageConfidentialityDetail(
                    project_id=subsystem.project_id,
                    important_data_id=data.id,
                    sort_order=1,
                ),
                DataTransportIntegrityDetail(
                    project_id=subsystem.project_id,
                    important_data_id=data.id,
                    sort_order=2,
                ),
                DataStorageIntegrityDetail(
                    project_id=subsystem.project_id,
                    important_data_id=data.id,
                    sort_order=3,
                ),
            ]
        )
        session.flush()
        return data

    def create_business_action(
        self,
        session: Session,
        subsystem_id: int,
        name: str,
    ) -> BusinessAction:
        subsystem = self._require_subsystem(session, subsystem_id)
        action = BusinessAction(
            project_id=subsystem.project_id,
            application_subsystem_id=subsystem.id,
            name=name,
            sort_order=self._next_sort_order(session, BusinessAction, subsystem.id),
        )
        session.add(action)
        session.flush()
        session.add(
            BusinessActionNonRepudiationDetail(
                project_id=subsystem.project_id,
                business_action_id=action.id,
                sort_order=0,
            )
        )
        session.flush()
        return action

    def load_user_auth_detail(
        self,
        session: Session,
        object_id: int,
    ) -> ApplicationUserAuthDetail | None:
        return session.scalar(
            select(ApplicationUserAuthDetail).where(
                ApplicationUserAuthDetail.application_user_id == object_id
            )
        )

    def load_access_integrity_detail(
        self,
        session: Session,
        object_id: int,
    ) -> AccessControlIntegrityDetail | None:
        return session.scalar(
            select(AccessControlIntegrityDetail).where(
                AccessControlIntegrityDetail.access_control_object_id == object_id
            )
        )

    def load_transport_confidentiality_detail(
        self,
        session: Session,
        object_id: int,
    ) -> DataTransportConfidentialityDetail | None:
        return session.scalar(
            select(DataTransportConfidentialityDetail).where(
                DataTransportConfidentialityDetail.important_data_id == object_id
            )
        )

    def load_storage_confidentiality_detail(
        self,
        session: Session,
        object_id: int,
    ) -> DataStorageConfidentialityDetail | None:
        return session.scalar(
            select(DataStorageConfidentialityDetail).where(
                DataStorageConfidentialityDetail.important_data_id == object_id
            )
        )

    def load_transport_integrity_detail(
        self,
        session: Session,
        object_id: int,
    ) -> DataTransportIntegrityDetail | None:
        return session.scalar(
            select(DataTransportIntegrityDetail).where(
                DataTransportIntegrityDetail.important_data_id == object_id
            )
        )

    def load_storage_integrity_detail(
        self,
        session: Session,
        object_id: int,
    ) -> DataStorageIntegrityDetail | None:
        return session.scalar(
            select(DataStorageIntegrityDetail).where(
                DataStorageIntegrityDetail.important_data_id == object_id
            )
        )

    def load_non_repudiation_detail(
        self,
        session: Session,
        object_id: int,
    ) -> BusinessActionNonRepudiationDetail | None:
        return session.scalar(
            select(BusinessActionNonRepudiationDetail).where(
                BusinessActionNonRepudiationDetail.business_action_id == object_id
            )
        )

    def _require_subsystem(self, session: Session, subsystem_id: int) -> ApplicationSubsystem:
        subsystem = self.get_subsystem(session, subsystem_id)
        if subsystem is None:
            raise ValueError(f"application subsystem not found: {subsystem_id}")
        return subsystem

    def _next_sort_order(
        self,
        session: Session,
        model,
        subsystem_id: int,
    ) -> int:
        current_max = session.scalar(
            select(func.max(model.sort_order)).where(
                model.application_subsystem_id == subsystem_id
            )
        )
        return int(current_max or 0) + 1
