from __future__ import annotations

import json
from collections.abc import Iterable
from typing import Any

from sqlalchemy import Engine
from sqlalchemy.orm import Session

from mpxccp.models.basic_info import BasicInfo, CryptoApplicationInfo, SystemInfo
from mpxccp.models.project import Project
from mpxccp.repositories.basic_info_repo import BasicInfoRepository
from mpxccp.repositories.session import readonly_session_scope, session_scope
from mpxccp.services.result import ServiceResult

EXTRA_BASIC_INFO_KEYS = ("assessor_name", "assessor_phone", "interview_time")


class ProjectNotFoundError(ValueError):
    def __init__(self, project_id: int) -> None:
        super().__init__(f"project not found: {project_id}")
        self.project_id = project_id


def as_mapping(value: object) -> dict[str, object]:
    if isinstance(value, dict):
        return dict(value)
    return {}


class BasicInfoService:
    def __init__(
        self,
        engine: Engine,
        basic_info_repo: BasicInfoRepository | None = None,
    ) -> None:
        self.engine = engine
        self.basic_info_repo = basic_info_repo or BasicInfoRepository()

    def save_basic_info(
        self,
        *,
        flow_no: str,
        system_name: str,
        project_id: int | None = None,
        client_name: str = "",
        assessment_org: str = "",
        contact_name: str = "",
        contact_phone: str = "",
        assessor_name: str = "",
        assessor_phone: str = "",
        interview_time: str = "",
        notes: str = "",
        silent: bool = True,
    ) -> ServiceResult:
        values = self._clean_basic_values(
            flow_no=flow_no,
            system_name=system_name,
            client_name=client_name,
            assessment_org=assessment_org,
            contact_name=contact_name,
            contact_phone=contact_phone,
            assessor_name=assessor_name,
            assessor_phone=assessor_phone,
            interview_time=interview_time,
            notes=notes,
        )
        warnings = self._required_warnings(values)
        if warnings:
            return ServiceResult(
                success=False,
                message="required basic information is missing",
                warnings=warnings,
                project_id=project_id,
            )

        try:
            with session_scope(self.engine) as session:
                project, created = self._save_basic_info_in_session(
                    session,
                    project_id=project_id,
                    values=values,
                )
                message = "" if silent else "basic information saved"
                return ServiceResult(
                    success=True,
                    message=message,
                    project_id=project.id,
                    payload={"created": created},
                )
        except ProjectNotFoundError as exc:
            return ServiceResult(
                success=False,
                message="project not found",
                warnings=["project_not_found"],
                project_id=exc.project_id,
            )

    def save_full_basic_info(
        self,
        *,
        flow_no: str,
        system_name: str,
        project_id: int | None = None,
        client_name: str = "",
        assessment_org: str = "",
        contact_name: str = "",
        contact_phone: str = "",
        assessor_name: str = "",
        assessor_phone: str = "",
        interview_time: str = "",
        notes: str = "",
        system_info: dict[str, object] | None = None,
        crypto_application_info: dict[str, object] | None = None,
        subsystems: Iterable[str] | None = None,
        silent: bool = True,
    ) -> ServiceResult:
        values = self._clean_basic_values(
            flow_no=flow_no,
            system_name=system_name,
            client_name=client_name,
            assessment_org=assessment_org,
            contact_name=contact_name,
            contact_phone=contact_phone,
            assessor_name=assessor_name,
            assessor_phone=assessor_phone,
            interview_time=interview_time,
            notes=notes,
        )
        warnings = self._required_warnings(values)
        if warnings:
            return ServiceResult(
                success=False,
                message="required basic information is missing",
                warnings=warnings,
                project_id=project_id,
            )

        try:
            with session_scope(self.engine) as session:
                project, created = self._save_basic_info_in_session(
                    session,
                    project_id=project_id,
                    values=values,
                )
                payload: dict[str, object] = {"created": created}
                if system_info is not None:
                    self.basic_info_repo.upsert_system_info(session, project.id, system_info)
                    payload["system_info_saved"] = True
                if crypto_application_info is not None:
                    self.basic_info_repo.upsert_crypto_application_info(
                        session,
                        project.id,
                        crypto_application_info,
                    )
                    payload["crypto_application_info_saved"] = True
                if subsystems is not None:
                    payload.update(
                        self.basic_info_repo.sync_subsystems(session, project.id, subsystems)
                    )

                message = "" if silent else "full basic information saved"
                return ServiceResult(
                    success=True,
                    message=message,
                    project_id=project.id,
                    payload=payload,
                )
        except ProjectNotFoundError as exc:
            return ServiceResult(
                success=False,
                message="project not found",
                warnings=["project_not_found"],
                project_id=exc.project_id,
            )

    def load_basic_info(self, project_id: int) -> ServiceResult:
        with readonly_session_scope(self.engine) as session:
            project = self.basic_info_repo.get_project(session, project_id)
            basic_info = self.basic_info_repo.get_basic_info(session, project_id)
            if project is None or basic_info is None:
                return ServiceResult(
                    success=False,
                    message="basic information not found",
                    project_id=project_id,
                    warnings=["basic_info_not_found"],
                )

            return ServiceResult(
                success=True,
                message="basic information loaded",
                project_id=project_id,
                payload=self._basic_payload(project, basic_info),
            )

    def load_full_basic_info(self, project_id: int) -> ServiceResult:
        with readonly_session_scope(self.engine) as session:
            project = self.basic_info_repo.get_project(session, project_id)
            basic_info = self.basic_info_repo.get_basic_info(session, project_id)
            if project is None or basic_info is None:
                return ServiceResult(
                    success=False,
                    message="basic information not found",
                    project_id=project_id,
                    warnings=["basic_info_not_found"],
                )

            system_info = self.basic_info_repo.get_system_info(session, project_id)
            crypto_info = self.basic_info_repo.get_crypto_application_info(session, project_id)
            subsystem_rows = self.basic_info_repo.list_subsystems(session, project_id)
            return ServiceResult(
                success=True,
                message="full basic information loaded",
                project_id=project_id,
                payload={
                    "basic_info": self._basic_payload(project, basic_info),
                    "system_info": self._system_info_payload(system_info),
                    "crypto_application_info": self._crypto_application_info_payload(
                        crypto_info
                    ),
                    "subsystems": [str(item["name"]) for item in subsystem_rows],
                    "subsystem_rows": subsystem_rows,
                },
            )

    def sync_subsystems(self, project_id: int, names: Iterable[str]) -> ServiceResult:
        with session_scope(self.engine) as session:
            project = self.basic_info_repo.get_project(session, project_id)
            if project is None:
                return ServiceResult(
                    success=False,
                    message="project not found",
                    project_id=project_id,
                    warnings=["project_not_found"],
                )
            payload = self.basic_info_repo.sync_subsystems(session, project_id, names)
            return ServiceResult(
                success=True,
                message="subsystems synchronized",
                project_id=project_id,
                payload=payload,
            )

    def list_subsystems(self, project_id: int) -> list[str]:
        return [str(item["name"]) for item in self.list_subsystem_rows(project_id)]

    def list_subsystem_rows(self, project_id: int) -> list[dict[str, object]]:
        with readonly_session_scope(self.engine) as session:
            return self.basic_info_repo.list_subsystems(session, project_id)

    def _save_basic_info_in_session(
        self,
        session: Session,
        *,
        project_id: int | None,
        values: dict[str, str],
    ) -> tuple[Project, bool]:
        created = False
        if project_id is None:
            project = self.basic_info_repo.create_project(
                session,
                flow_no=values["flow_no"],
                system_name=values["system_name"],
                client_name=values["client_name"],
                assessment_org=values["assessment_org"],
                extra_data=self._extra_data_from_values(values),
            )
            created = True
        else:
            project = self.basic_info_repo.get_project(session, project_id)
            if project is None:
                raise ProjectNotFoundError(project_id)
            project.extra_data = self._merge_extra_data(project.extra_data, values)

        self.basic_info_repo.upsert_basic_info(
            session,
            project,
            flow_no=values["flow_no"],
            system_name=values["system_name"],
            client_name=values["client_name"],
            assessment_org=values["assessment_org"],
            contact_name=values["contact_name"],
            contact_phone=values["contact_phone"],
            interview_time=values["interview_time"],
            notes=values["notes"],
        )
        return project, created

    def _basic_payload(self, project: Project, basic_info: BasicInfo) -> dict[str, object]:
        extra = as_mapping(project.extra_data)
        return {
            "project_id": project.id,
            "flow_no": basic_info.flow_no,
            "system_name": basic_info.system_name,
            "client_name": basic_info.client_name,
            "assessment_org": basic_info.assessment_org,
            "contact_name": basic_info.contact_name,
            "contact_phone": basic_info.contact_phone,
            "assessor_name": str(extra.get("assessor_name", "")),
            "assessor_phone": str(extra.get("assessor_phone", "")),
            "interview_time": str(extra.get("interview_time", basic_info.assessment_date)),
            "notes": basic_info.notes,
        }

    def _system_info_payload(self, system_info: SystemInfo | None) -> dict[str, object]:
        if system_info is None:
            return {}
        payload = as_mapping(system_info.extra_data)
        if payload:
            return payload
        return self._non_empty_payload(
            {
                "business_description": system_info.business_description,
                "security_level": system_info.security_level,
            }
        )

    def _crypto_application_info_payload(
        self,
        crypto_info: CryptoApplicationInfo | None,
    ) -> dict[str, object]:
        if crypto_info is None:
            return {}
        if crypto_info.notes:
            try:
                payload = json.loads(crypto_info.notes)
            except json.JSONDecodeError:
                payload = None
            if isinstance(payload, dict):
                return payload
        return self._non_empty_payload(
            {
                "application_scope": crypto_info.application_scope,
                "algorithm_description": crypto_info.algorithm_description,
                "key_management_description": crypto_info.key_management_description,
                "product_description": crypto_info.product_description,
                "notes": crypto_info.notes,
            }
        )

    def _non_empty_payload(self, values: dict[str, object]) -> dict[str, object]:
        return {key: value for key, value in values.items() if value not in (None, "")}

    def _clean_basic_values(self, **values: object) -> dict[str, str]:
        return {key: "" if value is None else str(value).strip() for key, value in values.items()}

    def _required_warnings(self, values: dict[str, str]) -> list[str]:
        warnings: list[str] = []
        if not values["flow_no"]:
            warnings.append("flow_no")
        if not values["system_name"]:
            warnings.append("system_name")
        return warnings

    def _extra_data_from_values(self, values: dict[str, str]) -> dict[str, object]:
        return {key: values[key] for key in EXTRA_BASIC_INFO_KEYS}

    def _merge_extra_data(
        self,
        current: dict[str, Any] | None,
        values: dict[str, str],
    ) -> dict[str, object]:
        extra = as_mapping(current)
        extra.update(self._extra_data_from_values(values))
        return extra
