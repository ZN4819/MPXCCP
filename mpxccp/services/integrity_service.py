from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from sqlalchemy import Engine, select

import mpxccp.models as models
from mpxccp.domain.association_rules import ASSOCIATION_RULES
from mpxccp.repositories.session import readonly_session_scope


@dataclass(frozen=True)
class DetailReference:
    unit_type: str
    detail_model: type
    parent_model: type
    parent_id_field: str


@dataclass
class ProjectScope:
    detail_references: dict[str, set[int]] = field(default_factory=dict)
    quant_references: dict[str, set[int]] = field(default_factory=dict)
    evidence_references: dict[str, set[int]] = field(default_factory=dict)
    product_references: dict[str, set[int]] = field(default_factory=dict)
    compatible_product_references: dict[str, set[int]] = field(default_factory=dict)


@dataclass(frozen=True)
class IntegrityIssue:
    kind: str
    record_type: str
    record_id: int | None
    unit_type: str
    related_id: int | None
    message: str


@dataclass
class IntegrityReport:
    project_id: int
    items: list[IntegrityIssue] = field(default_factory=list)


DETAIL_REFERENCES: tuple[DetailReference, ...] = (
    DetailReference(
        "物理访问身份鉴别",
        models.PhysicalAuthDetail,
        models.PhysicalObject,
        "physical_object_id",
    ),
    DetailReference(
        "门禁记录完整性",
        models.PhysicalAccessIntegrityDetail,
        models.PhysicalObject,
        "physical_object_id",
    ),
    DetailReference(
        "视频记录完整性",
        models.PhysicalVideoIntegrityDetail,
        models.PhysicalObject,
        "physical_object_id",
    ),
    DetailReference(
        "设备登录身份鉴别",
        models.DeviceAuthDetail,
        models.DeviceObject,
        "device_object_id",
    ),
    DetailReference(
        "远程管理通道",
        models.DeviceRemoteManagementDetail,
        models.DeviceObject,
        "device_object_id",
    ),
    DetailReference(
        "设备访问控制完整性",
        models.DeviceAccessIntegrityDetail,
        models.DeviceObject,
        "device_object_id",
    ),
    DetailReference(
        "设备日志完整性",
        models.DeviceLogIntegrityDetail,
        models.DeviceObject,
        "device_object_id",
    ),
    DetailReference(
        "可执行程序完整性",
        models.DeviceExecutableIntegrityDetail,
        models.DeviceObject,
        "device_object_id",
    ),
    DetailReference(
        "通信实体身份鉴别",
        models.NetworkAuthDetail,
        models.NetworkChannel,
        "network_channel_id",
    ),
    DetailReference(
        "通信过程数据完整性",
        models.NetworkIntegrityDetail,
        models.NetworkChannel,
        "network_channel_id",
    ),
    DetailReference(
        "通信过程数据机密性",
        models.NetworkConfidentialityDetail,
        models.NetworkChannel,
        "network_channel_id",
    ),
    DetailReference(
        "网络边界访问控制完整性",
        models.NetworkBoundaryIntegrityDetail,
        models.NetworkChannel,
        "network_channel_id",
    ),
    DetailReference(
        "应用用户身份鉴别",
        models.ApplicationUserAuthDetail,
        models.ApplicationUser,
        "application_user_id",
    ),
    DetailReference(
        "应用访问控制完整性",
        models.AccessControlIntegrityDetail,
        models.AccessControlObject,
        "access_control_object_id",
    ),
    DetailReference(
        "重要数据传输机密性",
        models.DataTransportConfidentialityDetail,
        models.ImportantData,
        "important_data_id",
    ),
    DetailReference(
        "重要数据存储机密性",
        models.DataStorageConfidentialityDetail,
        models.ImportantData,
        "important_data_id",
    ),
    DetailReference(
        "重要数据传输完整性",
        models.DataTransportIntegrityDetail,
        models.ImportantData,
        "important_data_id",
    ),
    DetailReference(
        "重要数据存储完整性",
        models.DataStorageIntegrityDetail,
        models.ImportantData,
        "important_data_id",
    ),
    DetailReference(
        "关键业务行为不可否认性",
        models.BusinessActionNonRepudiationDetail,
        models.BusinessAction,
        "business_action_id",
    ),
)
DETAIL_BY_UNIT = {item.unit_type: item for item in DETAIL_REFERENCES}


class IntegrityService:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def resolve_project_scope(self, project_id: int) -> ProjectScope:
        with readonly_session_scope(self.engine) as session:
            return self._resolve_project_scope_in_session(session, project_id)

    def check_project(self, project_id: int) -> IntegrityReport:
        with readonly_session_scope(self.engine) as session:
            if session.get(models.Project, project_id) is None:
                return IntegrityReport(
                    project_id=project_id,
                    items=[
                        IntegrityIssue(
                            kind="project_missing",
                            record_type="project",
                            record_id=project_id,
                            unit_type="",
                            related_id=None,
                            message="项目不存在。",
                        )
                    ],
                )
            scope = self._resolve_project_scope_in_session(session, project_id)
            report = IntegrityReport(project_id=project_id)
            for model, record_type in (
                (models.QuantitativeAssessment, "quant"),
                (models.EvidenceImage, "evidence"),
                (models.CryptoProduct, "product"),
            ):
                for record in session.scalars(
                    select(model).where(model.project_id == project_id).order_by(model.id)
                ):
                    issue = self._check_record(session, scope, project_id, record, record_type)
                    if issue is not None:
                        report.items.append(issue)
            return report

    def _resolve_project_scope_in_session(self, session, project_id: int) -> ProjectScope:
        scope = ProjectScope(
            detail_references={unit: set() for unit in ASSOCIATION_RULES},
            quant_references=defaultdict(set),
            evidence_references=defaultdict(set),
            product_references=defaultdict(set),
            compatible_product_references={unit: set() for unit in ASSOCIATION_RULES},
        )
        for reference in DETAIL_REFERENCES:
            details = session.scalars(
                select(reference.detail_model).where(
                    reference.detail_model.project_id == project_id
                )
            ).all()
            detail_ids = {detail.id for detail in details}
            parent_ids = {
                parent_id
                for detail in details
                if (parent_id := getattr(detail, reference.parent_id_field, None)) is not None
            }
            parent_ids.update(
                session.execute(
                    select(reference.parent_model.id).where(
                        reference.parent_model.project_id == project_id
                    )
                ).scalars()
            )
            scope.detail_references[reference.unit_type] = detail_ids
            scope.compatible_product_references[reference.unit_type] = detail_ids | parent_ids

        for model, target in (
            (models.QuantitativeAssessment, scope.quant_references),
            (models.EvidenceImage, scope.evidence_references),
            (models.CryptoProduct, scope.product_references),
        ):
            for record in session.scalars(select(model).where(model.project_id == project_id)):
                target[record.unit_type].add(record.related_id)
        return self._plain_scope(scope)

    def _check_record(
        self,
        session,
        scope: ProjectScope,
        project_id: int,
        record,
        record_type: str,
    ) -> IntegrityIssue | None:
        unit_type = record.unit_type or ""
        related_id = record.related_id
        if not unit_type or related_id is None or related_id <= 0:
            return self._issue("empty_association", record_type, record, "关联信息为空。")
        if unit_type not in DETAIL_BY_UNIT:
            return self._issue("unknown_unit_type", record_type, record, "未知测评单元。")

        valid_ids = (
            scope.compatible_product_references[unit_type]
            if record_type == "product"
            else scope.detail_references[unit_type]
        )
        if related_id in valid_ids:
            return None

        if self._belongs_to_other_project(session, project_id, unit_type, related_id, record_type):
            return self._issue(
                f"cross_project_{record_type}",
                record_type,
                record,
                "关联记录属于其他项目。",
            )
        return self._issue(
            f"orphan_{record_type}",
            record_type,
            record,
            "关联记录不在当前项目范围内。",
        )

    def _belongs_to_other_project(
        self,
        session,
        project_id: int,
        unit_type: str,
        related_id: int,
        record_type: str,
    ) -> bool:
        reference = DETAIL_BY_UNIT[unit_type]
        models_to_check = [reference.detail_model]
        if record_type == "product":
            models_to_check.append(reference.parent_model)
        for model in models_to_check:
            found_project_id = session.execute(
                select(model.project_id).where(model.id == related_id)
            ).scalar_one_or_none()
            if found_project_id is not None and found_project_id != project_id:
                return True
        return False

    def _issue(
        self,
        kind: str,
        record_type: str,
        record,
        message: str,
    ) -> IntegrityIssue:
        return IntegrityIssue(
            kind=kind,
            record_type=record_type,
            record_id=record.id,
            unit_type=record.unit_type or "",
            related_id=record.related_id,
            message=message,
        )

    def _plain_scope(self, scope: ProjectScope) -> ProjectScope:
        return ProjectScope(
            detail_references={key: set(value) for key, value in scope.detail_references.items()},
            quant_references={key: set(value) for key, value in scope.quant_references.items()},
            evidence_references={
                key: set(value) for key, value in scope.evidence_references.items()
            },
            product_references={key: set(value) for key, value in scope.product_references.items()},
            compatible_product_references={
                key: set(value) for key, value in scope.compatible_product_references.items()
            },
        )
