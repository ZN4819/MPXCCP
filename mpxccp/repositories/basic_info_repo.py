from __future__ import annotations

import json
from collections.abc import Iterable
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from mpxccp.models.basic_info import BasicInfo, CryptoApplicationInfo, Subsystem, SystemInfo
from mpxccp.models.project import Project
from mpxccp.models.technical_application import ApplicationSubsystem
from mpxccp.models.technical_network import NetworkSubsystem


class BasicInfoRepository:
    def get_project(self, session: Session, project_id: int) -> Project | None:
        return session.get(Project, project_id)

    def create_project(
        self,
        session: Session,
        *,
        flow_no: str,
        system_name: str,
        client_name: str = "",
        assessment_org: str = "",
        extra_data: dict[str, object] | None = None,
    ) -> Project:
        project = Project(
            flow_no=flow_no,
            system_name=system_name,
            client_name=client_name,
            assessment_org=assessment_org,
            extra_data=extra_data,
        )
        session.add(project)
        session.flush()
        return project

    def upsert_basic_info(
        self,
        session: Session,
        project: Project,
        *,
        flow_no: str,
        system_name: str,
        client_name: str = "",
        assessment_org: str = "",
        contact_name: str = "",
        contact_phone: str = "",
        interview_time: str = "",
        notes: str = "",
    ) -> BasicInfo:
        project.flow_no = flow_no
        project.system_name = system_name
        project.client_name = client_name
        project.assessment_org = assessment_org

        basic_info = self.get_basic_info(session, project.id)
        if basic_info is None:
            basic_info = BasicInfo(project_id=project.id)
            session.add(basic_info)

        basic_info.flow_no = flow_no
        basic_info.system_name = system_name
        basic_info.client_name = client_name
        basic_info.assessment_org = assessment_org
        basic_info.contact_name = contact_name
        basic_info.contact_phone = contact_phone
        basic_info.assessment_date = interview_time
        basic_info.notes = notes
        return basic_info

    def get_basic_info(self, session: Session, project_id: int) -> BasicInfo | None:
        return session.scalar(select(BasicInfo).where(BasicInfo.project_id == project_id))

    def get_system_info(self, session: Session, project_id: int) -> SystemInfo | None:
        return session.scalar(select(SystemInfo).where(SystemInfo.project_id == project_id))

    def get_crypto_application_info(
        self,
        session: Session,
        project_id: int,
    ) -> CryptoApplicationInfo | None:
        return session.scalar(
            select(CryptoApplicationInfo).where(CryptoApplicationInfo.project_id == project_id)
        )

    def upsert_system_info(
        self,
        session: Session,
        project_id: int,
        values: dict[str, object],
    ) -> SystemInfo:
        system_info = self.get_system_info(session, project_id)
        if system_info is None:
            system_info = SystemInfo(project_id=project_id)
            session.add(system_info)

        stored = dict(values)
        system_info.extra_data = stored
        for field in (
            "system_name",
            "security_level",
            "deployment_mode",
            "network_environment",
            "business_description",
        ):
            if field in values:
                setattr(system_info, field, str(values[field]))
        return system_info

    def upsert_crypto_application_info(
        self,
        session: Session,
        project_id: int,
        values: dict[str, object],
    ) -> CryptoApplicationInfo:
        info = self.get_crypto_application_info(session, project_id)
        if info is None:
            info = CryptoApplicationInfo(project_id=project_id)
            session.add(info)

        for field in (
            "application_scope",
            "algorithm_description",
            "key_management_description",
            "product_description",
        ):
            if field in values:
                setattr(info, field, str(values[field]))
        info.notes = json.dumps(dict(values), ensure_ascii=False, sort_keys=True)
        return info

    def list_subsystems(self, session: Session, project_id: int) -> list[dict[str, object]]:
        subsystems = session.scalars(
            select(Subsystem)
            .where(Subsystem.project_id == project_id, Subsystem.is_enabled.is_(True))
            .order_by(Subsystem.sort_order.asc(), Subsystem.id.asc())
        ).all()
        return [self._subsystem_row(subsystem) for subsystem in subsystems]

    def sync_subsystems(
        self,
        session: Session,
        project_id: int,
        names: Iterable[str],
    ) -> dict[str, object]:
        ordered_names = self._normalize_names(names)
        existing = {
            subsystem.name: subsystem
            for subsystem in session.scalars(
                select(Subsystem).where(Subsystem.project_id == project_id)
            ).all()
        }

        active_by_name: dict[str, Subsystem] = {}
        for sort_order, name in enumerate(ordered_names):
            subsystem = existing.get(name)
            if subsystem is None:
                subsystem = Subsystem(project_id=project_id, name=name)
                session.add(subsystem)
                existing[name] = subsystem
            subsystem.sort_order = sort_order
            subsystem.is_enabled = True
            active_by_name[name] = subsystem

        disabled: list[str] = []
        for name, subsystem in existing.items():
            if name not in active_by_name and subsystem.is_enabled:
                subsystem.is_enabled = False
                disabled.append(name)

        session.flush()
        network_created = self._sync_network_subsystems(session, project_id, active_by_name)
        application_created = self._sync_application_subsystems(session, project_id, active_by_name)
        rows = [self._subsystem_row(active_by_name[name]) for name in ordered_names]

        return {
            "subsystems": ordered_names,
            "subsystem_rows": rows,
            "disabled": disabled,
            "disabled_policy": "soft_disable_basic_subsystem",
            "network_created": network_created,
            "application_created": application_created,
        }

    def _sync_network_subsystems(
        self,
        session: Session,
        project_id: int,
        active_by_name: dict[str, Subsystem],
    ) -> list[str]:
        existing = {
            subsystem.name: subsystem
            for subsystem in session.scalars(
                select(NetworkSubsystem).where(NetworkSubsystem.project_id == project_id)
            ).all()
        }
        created: list[str] = []
        for name, subsystem in active_by_name.items():
            network = existing.get(name)
            if network is None:
                network = NetworkSubsystem(
                    project_id=project_id,
                    name=name,
                    description=subsystem.description,
                )
                session.add(network)
                created.append(name)
            network.basic_subsystem_id = subsystem.id
            network.name = name
            network.sort_order = subsystem.sort_order
        return created

    def _sync_application_subsystems(
        self,
        session: Session,
        project_id: int,
        active_by_name: dict[str, Subsystem],
    ) -> list[str]:
        existing = {
            subsystem.name: subsystem
            for subsystem in session.scalars(
                select(ApplicationSubsystem).where(ApplicationSubsystem.project_id == project_id)
            ).all()
        }
        created: list[str] = []
        for name, subsystem in active_by_name.items():
            application = existing.get(name)
            if application is None:
                application = ApplicationSubsystem(
                    project_id=project_id,
                    name=name,
                    description=subsystem.description,
                )
                session.add(application)
                created.append(name)
            application.basic_subsystem_id = subsystem.id
            application.name = name
            application.sort_order = subsystem.sort_order
        return created

    def _normalize_names(self, names: Iterable[str]) -> list[str]:
        normalized: list[str] = []
        seen: set[str] = set()
        for raw_name in names:
            name = str(raw_name).strip()
            if not name or name in seen:
                continue
            normalized.append(name)
            seen.add(name)
        return normalized

    def _subsystem_row(self, subsystem: Subsystem) -> dict[str, Any]:
        return {
            "id": subsystem.id,
            "project_id": subsystem.project_id,
            "name": subsystem.name,
            "description": subsystem.description,
            "sort_order": subsystem.sort_order,
            "is_enabled": subsystem.is_enabled,
        }