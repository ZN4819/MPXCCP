from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import Engine

from mpxccp.domain.enums import MeasureUnit
from mpxccp.domain.quant_rules import (
    QuantRuleResult,
    apply_quant_auto_rule,
    calculate_object_score,
    normalize_quant_values,
)
from mpxccp.models.shared import QuantitativeAssessment
from mpxccp.models.technical_device import (
    DeviceAccessIntegrityDetail,
    DeviceAuthDetail,
    DeviceExecutableIntegrityDetail,
    DeviceLogIntegrityDetail,
    DeviceObject,
    DeviceRemoteManagementDetail,
)
from mpxccp.repositories.device_repo import DeviceRepository
from mpxccp.repositories.session import readonly_session_scope, session_scope
from mpxccp.repositories.shared_repo import SharedRepository
from mpxccp.services.result import ServiceResult


@dataclass(frozen=True)
class DeviceObjectRecord:
    id: int
    project_id: int
    name: str
    device_type: str
    location: str
    management_address: str
    interview_record: str
    description: str
    sort_order: int


@dataclass(frozen=True)
class DeviceUnitRecord:
    id: int
    project_id: int
    device_object_id: int
    unit_key: str
    unit_type: str
    requirement: str
    implementation: str
    evaluation_result: str
    crypto_usage: str
    algorithm: str
    product_compliance: str
    compliance_status: str
    risk_level: str
    risk_analysis: str
    remediation: str
    auth_methods: str = ""
    login_channel: str = ""
    remote_protocol: str = ""
    certificate_usage: str = ""
    channel_protection: str = ""
    access_control_policy: str = ""
    integrity_method: str = ""
    log_source: str = ""
    executable_scope: str = ""
    quant: dict[str, str | float] | None = None
    products: list[dict[str, str]] | None = None
    extra_data: dict[str, Any] | None = None


@dataclass(frozen=True)
class DeviceDetails:
    object: DeviceObjectRecord
    auth: DeviceUnitRecord
    remote_management: DeviceUnitRecord
    access_integrity: DeviceUnitRecord
    log_integrity: DeviceUnitRecord
    executable_integrity: DeviceUnitRecord

    def all_detail_ids(self) -> tuple[int, int, int, int, int]:
        return (
            self.auth.id,
            self.remote_management.id,
            self.access_integrity.id,
            self.log_integrity.id,
            self.executable_integrity.id,
        )


UNIT_CONFIG = {
    "auth": {
        "unit_type": MeasureUnit.DEVICE_AUTH.value,
        "specific_fields": ("auth_methods", "login_channel"),
    },
    "remote_management": {
        "unit_type": MeasureUnit.DEVICE_REMOTE.value,
        "specific_fields": ("remote_protocol", "certificate_usage", "channel_protection"),
    },
    "access_integrity": {
        "unit_type": MeasureUnit.DEVICE_ACCESS_INTEGRITY.value,
        "specific_fields": ("access_control_policy", "integrity_method"),
    },
    "log_integrity": {
        "unit_type": MeasureUnit.DEVICE_LOG_INTEGRITY.value,
        "specific_fields": ("log_source", "integrity_method"),
    },
    "executable_integrity": {
        "unit_type": MeasureUnit.DEVICE_EXECUTABLE_INTEGRITY.value,
        "specific_fields": ("executable_scope", "integrity_method"),
    },
}
OBJECT_FIELDS = (
    "name",
    "device_type",
    "location",
    "management_address",
    "interview_record",
    "description",
)
COMMON_DETAIL_FIELDS = (
    "requirement",
    "implementation",
    "evaluation_result",
    "crypto_usage",
    "algorithm",
    "product_compliance",
    "compliance_status",
    "risk_level",
    "risk_analysis",
    "remediation",
)
EXTRA_DETAIL_FIELDS = (
    "certificate_start_date",
    "certificate_end_date",
    "remote_position",
    "centralized_management",
    "certificate_algorithm",
    "certificate_source",
    "confidentiality_algorithm",
    "integrity_algorithm",
    "other_info",
    "product_used",
    "product_level",
    "implementation_status",
    "mitigation_available",
    "mitigation_note",
    "mitigated_level",
)
DeviceDetailModel = (
    DeviceAuthDetail
    | DeviceRemoteManagementDetail
    | DeviceAccessIntegrityDetail
    | DeviceLogIntegrityDetail
    | DeviceExecutableIntegrityDetail
)


class DeviceService:
    def __init__(
        self,
        engine: Engine,
        *,
        device_repo: DeviceRepository | None = None,
        shared_repo: SharedRepository | None = None,
    ) -> None:
        self.engine = engine
        self.device_repo = device_repo or DeviceRepository()
        self.shared_repo = shared_repo or SharedRepository()

    def create_object(self, project_id: int, name: str) -> DeviceObjectRecord:
        cleaned_name = self._text(name) or "未命名设备对象"
        with session_scope(self.engine) as session:
            obj = self.device_repo.create_object(session, project_id, cleaned_name)
            return self._object_record(obj)

    def list_objects(self, project_id: int) -> list[DeviceObjectRecord]:
        with readonly_session_scope(self.engine) as session:
            return [
                self._object_record(obj)
                for obj in self.device_repo.list_objects(session, project_id)
            ]

    def load_detail(self, object_id: int) -> DeviceDetails:
        return self.load_details(object_id)

    def load_details(self, object_id: int) -> DeviceDetails:
        with readonly_session_scope(self.engine) as session:
            obj = self.device_repo.get_object(session, object_id)
            if obj is None:
                raise ValueError(f"device object not found: {object_id}")
            auth, remote, access, log, executable = self._load_required_details(
                session,
                object_id,
            )
            return DeviceDetails(
                object=self._object_record(obj),
                auth=self._unit_record(session, obj, "auth", auth),
                remote_management=self._unit_record(session, obj, "remote_management", remote),
                access_integrity=self._unit_record(session, obj, "access_integrity", access),
                log_integrity=self._unit_record(session, obj, "log_integrity", log),
                executable_integrity=self._unit_record(
                    session,
                    obj,
                    "executable_integrity",
                    executable,
                ),
            )

    def save_detail(
        self,
        object_id: int,
        payload: dict[str, Any],
        silent: bool = True,
    ) -> ServiceResult:
        with session_scope(self.engine) as session:
            obj = self.device_repo.get_object(session, object_id)
            if obj is None:
                return ServiceResult(
                    success=False,
                    message="device object not found",
                    warnings=["device_object_not_found"],
                )
            for field, value in self._mapping(payload.get("object")).items():
                if field in OBJECT_FIELDS:
                    setattr(obj, field, self._text(value))

            details = dict(
                zip(UNIT_CONFIG, self._load_required_details(session, object_id), strict=True)
            )
            units = self._mapping(payload.get("units"))
            for unit_key, detail_payload in units.items():
                if unit_key not in details:
                    continue
                detail_values = self._mapping(detail_payload)
                detail = details[unit_key]
                self._apply_detail_values(unit_key, detail, detail_values)
                unit_type = UNIT_CONFIG[unit_key]["unit_type"]
                if "quant" in detail_values:
                    self._save_quant(
                        session,
                        project_id=obj.project_id,
                        unit_type=unit_type,
                        related_id=detail.id,
                        values=self._mapping(detail_values["quant"]),
                    )
                if "products" in detail_values:
                    self._save_products(
                        session,
                        project_id=obj.project_id,
                        unit_type=unit_type,
                        related_id=obj.id,
                        products=detail_values["products"],
                    )

            message = "" if silent else "device detail saved"
            return ServiceResult(
                success=True,
                message=message,
                project_id=obj.project_id,
                payload={"object_id": obj.id, "object_name": obj.name},
            )

    def delete_object(self, object_id: int) -> ServiceResult:
        with session_scope(self.engine) as session:
            obj = self.device_repo.get_object(session, object_id)
            if obj is None:
                return ServiceResult(
                    success=False,
                    message="device object not found",
                    warnings=["device_object_not_found"],
                )
            details = self._load_existing_details(session, object_id)
            warnings = [
                f"missing_device_detail:{unit_key}"
                for unit_key, detail in details.items()
                if detail is None
            ]
            for unit_key, detail in details.items():
                unit_type = UNIT_CONFIG[unit_key]["unit_type"]
                if detail is not None:
                    self.shared_repo.delete_quant_for_related(
                        session,
                        obj.project_id,
                        unit_type,
                        detail.id,
                    )
                    self.shared_repo.delete_evidence_for_related(
                        session,
                        obj.project_id,
                        unit_type,
                        detail.id,
                    )
                    if self._detail_product_reference_is_ambiguous(session, obj, detail.id):
                        warnings.append(f"ambiguous_device_detail_product:{unit_key}")
                    else:
                        self.shared_repo.delete_products_for_related(
                            session,
                            obj.project_id,
                            unit_type,
                            detail.id,
                        )
                    session.delete(detail)
                self.shared_repo.delete_products_for_related(
                    session,
                    obj.project_id,
                    unit_type,
                    obj.id,
                )
            session.flush()
            session.delete(obj)
            return ServiceResult(
                success=True,
                message="device object deleted",
                warnings=warnings,
                project_id=obj.project_id,
                payload={"object_id": object_id},
            )

    def apply_product_level_quant_rule(
        self,
        unit_name: str,
        product_level: str,
    ) -> QuantRuleResult:
        if unit_name not in {config["unit_type"] for config in UNIT_CONFIG.values()}:
            raise ValueError(f"unknown device measure unit: {unit_name}")
        return apply_quant_auto_rule(product_level=product_level)

    def _detail_product_reference_is_ambiguous(
        self,
        session,
        obj: DeviceObject,
        detail_id: int,
    ) -> bool:
        if detail_id == obj.id:
            return False
        candidate = session.get(DeviceObject, detail_id)
        return candidate is not None and candidate.project_id == obj.project_id

    def _load_required_details(self, session, object_id: int):
        auth = self.device_repo.load_auth_detail(session, object_id)
        remote = self.device_repo.load_remote_management_detail(session, object_id)
        access = self.device_repo.load_access_integrity_detail(session, object_id)
        log = self.device_repo.load_log_integrity_detail(session, object_id)
        executable = self.device_repo.load_executable_integrity_detail(session, object_id)
        if any(detail is None for detail in (auth, remote, access, log, executable)):
            raise ValueError(f"device details are incomplete: {object_id}")
        return auth, remote, access, log, executable

    def _load_existing_details(self, session, object_id: int) -> dict[str, Any]:
        return {
            "auth": self.device_repo.load_auth_detail(session, object_id),
            "remote_management": self.device_repo.load_remote_management_detail(
                session,
                object_id,
            ),
            "access_integrity": self.device_repo.load_access_integrity_detail(
                session,
                object_id,
            ),
            "log_integrity": self.device_repo.load_log_integrity_detail(session, object_id),
            "executable_integrity": self.device_repo.load_executable_integrity_detail(
                session,
                object_id,
            ),
        }

    def _apply_detail_values(
        self,
        unit_key: str,
        detail: DeviceDetailModel,
        values: dict[str, Any],
    ) -> None:
        fields = set(COMMON_DETAIL_FIELDS)
        fields.update(UNIT_CONFIG[unit_key]["specific_fields"])
        for field, value in values.items():
            if field in fields:
                setattr(detail, field, self._text(value))
        extra = self._mapping(getattr(detail, "extra_data", None))
        for field in EXTRA_DETAIL_FIELDS:
            if field not in values:
                continue
            value = values[field]
            extra[field] = value if isinstance(value, bool) else self._text(value)
        if extra:
            detail.extra_data = extra

    def _save_quant(
        self,
        session,
        *,
        project_id: int,
        unit_type: str,
        related_id: int,
        values: dict[str, Any],
    ) -> None:
        normalized = normalize_quant_values(
            d=values.get("d", ""),
            a=values.get("a", ""),
            k=values.get("k", ""),
            ra=values.get("ra", 1),
            rk=values.get("rk", 1),
        )
        score = calculate_object_score(
            d=normalized.d,
            a=normalized.a,
            k=normalized.k,
            ra=normalized.ra,
            rk=normalized.rk,
        )
        record = self.shared_repo.get_quant(session, project_id, unit_type, related_id)
        if record is None:
            record = QuantitativeAssessment(
                project_id=project_id,
                unit_type=unit_type,
                related_id=related_id,
            )
            session.add(record)
            session.flush()
        record.d_value = normalized.d
        record.a_value = normalized.a
        record.k_value = normalized.k
        record.ra_value = str(float(normalized.ra))
        record.rk_value = str(float(normalized.rk))
        record.score = score

    def _save_products(
        self,
        session,
        *,
        project_id: int,
        unit_type: str,
        related_id: int,
        products: Any,
    ) -> None:
        self.shared_repo.delete_products_for_related(session, project_id, unit_type, related_id)
        if not isinstance(products, list):
            return
        created = []
        for sort_order, item in enumerate(products):
            values = self._mapping(item)
            name = self._text(values.get("product_name", values.get("name", "")))
            if not name:
                continue
            created.append(
                self.shared_repo.add_product(
                    session,
                    project_id=project_id,
                    unit_type=unit_type,
                    related_id=related_id,
                    product_name=name,
                    product_model=self._text(values.get("product_model", values.get("model", ""))),
                    certificate_no=self._text(values.get("certificate_no", "")),
                    product_level=self._text(values.get("product_level", values.get("level", ""))),
                    vendor=self._text(values.get("vendor", "")),
                    usage=self._text(values.get("usage", "")),
                    sort_order=sort_order,
                )
            )
        for product in created:
            self.shared_repo.sync_same_certificate(session, product)

    def _object_record(self, obj: DeviceObject) -> DeviceObjectRecord:
        return DeviceObjectRecord(
            id=obj.id,
            project_id=obj.project_id,
            name=obj.name,
            device_type=obj.device_type,
            location=obj.location,
            management_address=obj.management_address,
            interview_record=obj.interview_record,
            description=obj.description,
            sort_order=obj.sort_order,
        )

    def _unit_record(
        self,
        session,
        obj: DeviceObject,
        unit_key: str,
        detail: DeviceDetailModel,
    ) -> DeviceUnitRecord:
        unit_type = UNIT_CONFIG[unit_key]["unit_type"]
        quant = self.shared_repo.get_quant(session, obj.project_id, unit_type, detail.id)
        return DeviceUnitRecord(
            id=detail.id,
            project_id=detail.project_id,
            device_object_id=detail.device_object_id,
            unit_key=unit_key,
            unit_type=unit_type,
            requirement=detail.requirement,
            implementation=detail.implementation,
            evaluation_result=detail.evaluation_result,
            crypto_usage=detail.crypto_usage,
            algorithm=detail.algorithm,
            product_compliance=detail.product_compliance or "",
            compliance_status=detail.compliance_status or "",
            risk_level=detail.risk_level or "",
            risk_analysis=detail.risk_analysis,
            remediation=detail.remediation,
            auth_methods=getattr(detail, "auth_methods", ""),
            login_channel=getattr(detail, "login_channel", ""),
            remote_protocol=getattr(detail, "remote_protocol", ""),
            certificate_usage=getattr(detail, "certificate_usage", ""),
            channel_protection=getattr(detail, "channel_protection", ""),
            access_control_policy=getattr(detail, "access_control_policy", ""),
            integrity_method=getattr(detail, "integrity_method", ""),
            log_source=getattr(detail, "log_source", ""),
            executable_scope=getattr(detail, "executable_scope", ""),
            quant=self._quant_payload(quant),
            products=[
                {
                    "name": product.product_name,
                    "vendor": product.vendor,
                    "certificate_no": product.certificate_no,
                    "level": product.product_level or "",
                    "usage": product.usage,
                }
                for product in self.shared_repo.load_products(
                    session,
                    obj.project_id,
                    unit_type,
                    obj.id,
                )
            ],
            extra_data=self._mapping(getattr(detail, "extra_data", None)),
        )

    def _quant_payload(self, quant: QuantitativeAssessment | None) -> dict[str, str | float]:
        if quant is None:
            return {"d": "", "a": "", "k": "", "ra": 1.0, "rk": 1.0}
        normalized = normalize_quant_values(
            d=quant.d_value,
            a=quant.a_value,
            k=quant.k_value,
            ra=quant.ra_value,
            rk=quant.rk_value,
        )
        return {
            "d": normalized.d,
            "a": normalized.a,
            "k": normalized.k,
            "ra": normalized.ra,
            "rk": normalized.rk,
        }

    def _mapping(self, value: Any) -> dict[str, Any]:
        return dict(value) if isinstance(value, dict) else {}

    def _text(self, value: Any) -> str:
        return "" if value is None else str(value).strip()
