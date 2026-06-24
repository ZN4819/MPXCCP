from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import Engine

from mpxccp.domain.enums import MeasureUnit
from mpxccp.domain.quant_rules import calculate_object_score, normalize_quant_values
from mpxccp.models.shared import QuantitativeAssessment
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
from mpxccp.repositories.application_repo import ApplicationRepository
from mpxccp.repositories.session import readonly_session_scope, session_scope
from mpxccp.repositories.shared_repo import SharedRepository
from mpxccp.services.result import ServiceResult


@dataclass(frozen=True)
class ApplicationSubsystemRecord:
    id: int
    project_id: int
    basic_subsystem_id: int | None
    name: str
    description: str
    sort_order: int


@dataclass(frozen=True)
class ApplicationObjectRecord:
    id: int
    project_id: int
    application_subsystem_id: int
    kind: str
    name: str
    sort_order: int
    role: str = ""
    scope: str = ""
    policy_description: str = ""
    data_type: str = ""
    related_channel_id: int | None = None
    description: str = ""
    extra_data: dict[str, Any] | None = None


@dataclass(frozen=True)
class ApplicationUnitRecord:
    id: int
    project_id: int
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
    application_user_id: int | None = None
    access_control_object_id: int | None = None
    important_data_id: int | None = None
    business_action_id: int | None = None
    network_channel_id: int | None = None
    auth_methods: str = ""
    certificate_usage: str = ""
    access_control_policy: str = ""
    integrity_method: str = ""
    encryption_method: str = ""
    storage_location: str = ""
    signature_method: str = ""
    timestamp_method: str = ""
    quant: dict[str, str | float] | None = None
    products: list[dict[str, str]] | None = None
    extra_data: dict[str, Any] | None = None


@dataclass(frozen=True)
class UserDetails:
    user: ApplicationObjectRecord
    auth: ApplicationUnitRecord

    def all_detail_ids(self) -> tuple[int]:
        return (self.auth.id,)


@dataclass(frozen=True)
class AccessControlDetails:
    access_control: ApplicationObjectRecord
    integrity: ApplicationUnitRecord

    def all_detail_ids(self) -> tuple[int]:
        return (self.integrity.id,)


@dataclass(frozen=True)
class ImportantDataDetails:
    data: ApplicationObjectRecord
    transport_confidentiality: ApplicationUnitRecord
    storage_confidentiality: ApplicationUnitRecord
    transport_integrity: ApplicationUnitRecord
    storage_integrity: ApplicationUnitRecord

    def all_detail_ids(self) -> tuple[int, int, int, int]:
        return (
            self.transport_confidentiality.id,
            self.storage_confidentiality.id,
            self.transport_integrity.id,
            self.storage_integrity.id,
        )


@dataclass(frozen=True)
class BusinessActionDetails:
    action: ApplicationObjectRecord
    non_repudiation: ApplicationUnitRecord

    def all_detail_ids(self) -> tuple[int]:
        return (self.non_repudiation.id,)


@dataclass(frozen=True)
class AssociationReference:
    unit_type: str
    related_id: int


OBJECT_CONFIG = {
    "user": {
        "model": ApplicationUser,
        "fields": ("name", "role"),
        "extra_fields": ("login_method", "interview_record", "user_type"),
        "missing_warning": "application_user_not_found",
    },
    "access_control": {
        "model": AccessControlObject,
        "fields": ("name", "scope", "policy_description"),
        "extra_fields": ("interview_record",),
        "missing_warning": "access_control_not_found",
    },
    "important_data": {
        "model": ImportantData,
        "fields": ("name", "data_type", "related_channel_id"),
        "extra_fields": ("data_location", "business_description", "interview_record"),
        "missing_warning": "important_data_not_found",
    },
    "business_action": {
        "model": BusinessAction,
        "fields": ("name", "description"),
        "extra_fields": ("responsibility_subject", "interview_record"),
        "missing_warning": "business_action_not_found",
    },
}
UNIT_CONFIG = {
    "user_auth": {
        "object_kind": "user",
        "unit_type": MeasureUnit.APP_USER_AUTH.value,
        "detail_model": ApplicationUserAuthDetail,
        "fk_field": "application_user_id",
        "specific_fields": ("auth_methods", "certificate_usage"),
    },
    "access_integrity": {
        "object_kind": "access_control",
        "unit_type": MeasureUnit.APP_ACCESS_INTEGRITY.value,
        "detail_model": AccessControlIntegrityDetail,
        "fk_field": "access_control_object_id",
        "specific_fields": ("access_control_policy", "integrity_method"),
    },
    "transport_confidentiality": {
        "object_kind": "important_data",
        "unit_type": MeasureUnit.DATA_TRANSPORT_CONFIDENTIALITY.value,
        "detail_model": DataTransportConfidentialityDetail,
        "fk_field": "important_data_id",
        "specific_fields": ("network_channel_id", "encryption_method"),
    },
    "storage_confidentiality": {
        "object_kind": "important_data",
        "unit_type": MeasureUnit.DATA_STORAGE_CONFIDENTIALITY.value,
        "detail_model": DataStorageConfidentialityDetail,
        "fk_field": "important_data_id",
        "specific_fields": ("storage_location", "encryption_method"),
    },
    "transport_integrity": {
        "object_kind": "important_data",
        "unit_type": MeasureUnit.DATA_TRANSPORT_INTEGRITY.value,
        "detail_model": DataTransportIntegrityDetail,
        "fk_field": "important_data_id",
        "specific_fields": ("network_channel_id", "integrity_method"),
    },
    "storage_integrity": {
        "object_kind": "important_data",
        "unit_type": MeasureUnit.DATA_STORAGE_INTEGRITY.value,
        "detail_model": DataStorageIntegrityDetail,
        "fk_field": "important_data_id",
        "specific_fields": ("storage_location", "integrity_method"),
    },
    "non_repudiation": {
        "object_kind": "business_action",
        "unit_type": MeasureUnit.BUSINESS_ACTION_NON_REPUDIATION.value,
        "detail_model": BusinessActionNonRepudiationDetail,
        "fk_field": "business_action_id",
        "specific_fields": ("signature_method", "timestamp_method", "certificate_usage"),
    },
}
OBJECT_UNITS = {
    "user": ("user_auth",),
    "access_control": ("access_integrity",),
    "important_data": (
        "transport_confidentiality",
        "storage_confidentiality",
        "transport_integrity",
        "storage_integrity",
    ),
    "business_action": ("non_repudiation",),
}
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
    "implementation_status",
    "mechanism_description",
    "image_path",
    "key_management",
    "auth_data",
    "product_used",
    "product_level",
    "mitigation_available",
    "mitigation_note",
    "mitigated_level",
    "other_info",
)


class ApplicationService:
    def __init__(
        self,
        engine: Engine,
        *,
        application_repo: ApplicationRepository | None = None,
        shared_repo: SharedRepository | None = None,
    ) -> None:
        self.engine = engine
        self.application_repo = application_repo or ApplicationRepository()
        self.shared_repo = shared_repo or SharedRepository()

    def sync_from_basic_subsystems(self, project_id: int) -> list[ApplicationSubsystemRecord]:
        with session_scope(self.engine) as session:
            return [
                self._subsystem_record(subsystem)
                for subsystem in self.application_repo.sync_from_basic_subsystems(
                    session,
                    project_id,
                )
            ]

    def list_subsystems(self, project_id: int) -> list[ApplicationSubsystemRecord]:
        with readonly_session_scope(self.engine) as session:
            return [
                self._subsystem_record(subsystem)
                for subsystem in self.application_repo.list_subsystems(session, project_id)
            ]

    def list_users(self, subsystem_id: int) -> list[ApplicationObjectRecord]:
        with readonly_session_scope(self.engine) as session:
            return [
                self._object_record("user", item)
                for item in self.application_repo.list_users(session, subsystem_id)
            ]

    def list_access_controls(self, subsystem_id: int) -> list[ApplicationObjectRecord]:
        with readonly_session_scope(self.engine) as session:
            return [
                self._object_record("access_control", item)
                for item in self.application_repo.list_access_controls(session, subsystem_id)
            ]

    def list_important_data(self, subsystem_id: int) -> list[ApplicationObjectRecord]:
        with readonly_session_scope(self.engine) as session:
            return [
                self._object_record("important_data", item)
                for item in self.application_repo.list_important_data(session, subsystem_id)
            ]

    def list_business_actions(self, subsystem_id: int) -> list[ApplicationObjectRecord]:
        with readonly_session_scope(self.engine) as session:
            return [
                self._object_record("business_action", item)
                for item in self.application_repo.list_business_actions(session, subsystem_id)
            ]

    def user_count(self, subsystem_id: int) -> int:
        return len(self.list_users(subsystem_id))

    def create_user(self, subsystem_id: int, name: str) -> ApplicationObjectRecord:
        with session_scope(self.engine) as session:
            user = self.application_repo.create_user(
                session,
                subsystem_id,
                self._text(name) or "未命名应用用户",
            )
            return self._object_record("user", user)

    def create_access_control(self, subsystem_id: int, name: str) -> ApplicationObjectRecord:
        with session_scope(self.engine) as session:
            obj = self.application_repo.create_access_control(
                session,
                subsystem_id,
                self._text(name) or "未命名访问控制信息",
            )
            return self._object_record("access_control", obj)

    def create_important_data(
        self,
        subsystem_id: int,
        name: str,
        data_type: str,
    ) -> ApplicationObjectRecord:
        with session_scope(self.engine) as session:
            data = self.application_repo.create_important_data(
                session,
                subsystem_id,
                self._text(name) or "未命名重要数据",
                self._text(data_type),
            )
            return self._object_record("important_data", data)

    def create_business_action(self, subsystem_id: int, name: str) -> ApplicationObjectRecord:
        with session_scope(self.engine) as session:
            action = self.application_repo.create_business_action(
                session,
                subsystem_id,
                self._text(name) or "未命名关键业务行为",
            )
            return self._object_record("business_action", action)

    def load_user_details(self, object_id: int) -> UserDetails:
        with readonly_session_scope(self.engine) as session:
            user = self.application_repo.get_user(session, object_id)
            if user is None:
                raise ValueError(f"application user not found: {object_id}")
            auth = self._load_required_detail(session, "user_auth", object_id)
            return UserDetails(
                user=self._object_record("user", user),
                auth=self._unit_record(session, user, "user_auth", auth),
            )

    def load_access_control_details(self, object_id: int) -> AccessControlDetails:
        with readonly_session_scope(self.engine) as session:
            obj = self.application_repo.get_access_control(session, object_id)
            if obj is None:
                raise ValueError(f"access control object not found: {object_id}")
            detail = self._load_required_detail(session, "access_integrity", object_id)
            return AccessControlDetails(
                access_control=self._object_record("access_control", obj),
                integrity=self._unit_record(session, obj, "access_integrity", detail),
            )

    def load_important_data_details(self, object_id: int) -> ImportantDataDetails:
        with readonly_session_scope(self.engine) as session:
            data = self.application_repo.get_important_data(session, object_id)
            if data is None:
                raise ValueError(f"important data not found: {object_id}")
            transport_conf = self._load_required_detail(
                session,
                "transport_confidentiality",
                object_id,
            )
            storage_conf = self._load_required_detail(
                session,
                "storage_confidentiality",
                object_id,
            )
            transport_integrity = self._load_required_detail(
                session,
                "transport_integrity",
                object_id,
            )
            storage_integrity = self._load_required_detail(
                session,
                "storage_integrity",
                object_id,
            )
            return ImportantDataDetails(
                data=self._object_record("important_data", data),
                transport_confidentiality=self._unit_record(
                    session,
                    data,
                    "transport_confidentiality",
                    transport_conf,
                ),
                storage_confidentiality=self._unit_record(
                    session,
                    data,
                    "storage_confidentiality",
                    storage_conf,
                ),
                transport_integrity=self._unit_record(
                    session,
                    data,
                    "transport_integrity",
                    transport_integrity,
                ),
                storage_integrity=self._unit_record(
                    session,
                    data,
                    "storage_integrity",
                    storage_integrity,
                ),
            )

    def load_business_action_details(self, object_id: int) -> BusinessActionDetails:
        with readonly_session_scope(self.engine) as session:
            action = self.application_repo.get_business_action(session, object_id)
            if action is None:
                raise ValueError(f"business action not found: {object_id}")
            detail = self._load_required_detail(session, "non_repudiation", object_id)
            return BusinessActionDetails(
                action=self._object_record("business_action", action),
                non_repudiation=self._unit_record(session, action, "non_repudiation", detail),
            )

    def save_user_detail(
        self,
        object_id: int,
        payload: dict[str, Any],
        silent: bool = True,
    ) -> ServiceResult:
        return self._save_object_detail("user", object_id, payload, silent=silent)

    def save_access_control_detail(
        self,
        object_id: int,
        payload: dict[str, Any],
        silent: bool = True,
    ) -> ServiceResult:
        return self._save_object_detail("access_control", object_id, payload, silent=silent)

    def save_important_data_detail(
        self,
        object_id: int,
        payload: dict[str, Any],
        silent: bool = True,
    ) -> ServiceResult:
        return self._save_object_detail("important_data", object_id, payload, silent=silent)

    def save_business_action_detail(
        self,
        object_id: int,
        payload: dict[str, Any],
        silent: bool = True,
    ) -> ServiceResult:
        return self._save_object_detail("business_action", object_id, payload, silent=silent)

    def delete_application_object(self, kind: str, object_id: int) -> ServiceResult:
        self._validate_kind(kind)
        with session_scope(self.engine) as session:
            target = self._get_object(session, kind, object_id)
            if target is None:
                return ServiceResult(
                    success=False,
                    message=f"{kind} not found",
                    warnings=[str(OBJECT_CONFIG[kind]["missing_warning"])],
                )
            details = self._load_existing_details(session, kind, object_id)
            warnings = [
                f"missing_application_detail:{unit_key}"
                for unit_key, detail in details.items()
                if detail is None
            ]
            for unit_key, detail in details.items():
                unit_type = UNIT_CONFIG[unit_key]["unit_type"]
                if detail is not None:
                    self.shared_repo.delete_quant_for_related(
                        session,
                        target.project_id,
                        unit_type,
                        detail.id,
                    )
                    self.shared_repo.delete_evidence_for_related(
                        session,
                        target.project_id,
                        unit_type,
                        detail.id,
                    )
                    if self._detail_product_reference_is_ambiguous(
                        session,
                        unit_key,
                        target,
                        detail.id,
                    ):
                        warnings.append(f"ambiguous_application_detail_product:{unit_key}")
                    else:
                        self.shared_repo.delete_products_for_related(
                            session,
                            target.project_id,
                            unit_type,
                            detail.id,
                        )
                    session.delete(detail)
                if self._object_product_reference_is_ambiguous(session, unit_key, target):
                    warnings.append(f"ambiguous_application_object_product:{unit_key}")
                else:
                    self.shared_repo.delete_products_for_related(
                        session,
                        target.project_id,
                        unit_type,
                        target.id,
                    )
            session.flush()
            session.delete(target)
            return ServiceResult(
                success=True,
                message=f"{kind} deleted",
                warnings=warnings,
                project_id=target.project_id,
                payload={"kind": kind, "object_id": object_id},
            )

    def evidence_ref_for_unit(self, unit_key: str, detail_id: int) -> AssociationReference:
        if unit_key not in UNIT_CONFIG:
            raise ValueError(f"unknown application unit: {unit_key}")
        return AssociationReference(
            unit_type=UNIT_CONFIG[unit_key]["unit_type"],
            related_id=detail_id,
        )

    def _save_object_detail(
        self,
        kind: str,
        object_id: int,
        payload: dict[str, Any],
        *,
        silent: bool,
    ) -> ServiceResult:
        self._validate_kind(kind)
        with session_scope(self.engine) as session:
            target = self._get_object(session, kind, object_id)
            if target is None:
                return ServiceResult(
                    success=False,
                    message=f"{kind} not found",
                    warnings=[str(OBJECT_CONFIG[kind]["missing_warning"])],
                )
            self._apply_object_values(kind, target, self._mapping(payload.get("object")))
            details = self._load_existing_details(session, kind, object_id)
            units = self._mapping(payload.get("units"))
            for unit_key, detail_payload in units.items():
                if unit_key not in details or details[unit_key] is None:
                    continue
                detail_values = self._mapping(detail_payload)
                detail = details[unit_key]
                self._apply_detail_values(unit_key, detail, detail_values)
                unit_type = UNIT_CONFIG[unit_key]["unit_type"]
                if "quant" in detail_values:
                    self._save_quant(
                        session,
                        project_id=target.project_id,
                        unit_type=unit_type,
                        related_id=detail.id,
                        values=self._mapping(detail_values["quant"]),
                    )
                if "products" in detail_values:
                    self._save_products(
                        session,
                        project_id=target.project_id,
                        unit_type=unit_type,
                        related_id=target.id,
                        products=detail_values["products"],
                    )
            message = "" if silent else f"{kind} detail saved"
            return ServiceResult(
                success=True,
                message=message,
                project_id=target.project_id,
                payload={"kind": kind, "object_id": target.id, "object_name": target.name},
            )

    def _load_required_detail(self, session, unit_key: str, object_id: int):
        detail = self._load_detail(session, unit_key, object_id)
        if detail is None:
            raise ValueError(f"application detail is missing: {unit_key}:{object_id}")
        return detail

    def _load_existing_details(self, session, kind: str, object_id: int) -> dict[str, Any]:
        return {
            unit_key: self._load_detail(session, unit_key, object_id)
            for unit_key in OBJECT_UNITS[kind]
        }

    def _load_detail(self, session, unit_key: str, object_id: int):
        loaders = {
            "user_auth": self.application_repo.load_user_auth_detail,
            "access_integrity": self.application_repo.load_access_integrity_detail,
            "transport_confidentiality": (
                self.application_repo.load_transport_confidentiality_detail
            ),
            "storage_confidentiality": (
                self.application_repo.load_storage_confidentiality_detail
            ),
            "transport_integrity": self.application_repo.load_transport_integrity_detail,
            "storage_integrity": self.application_repo.load_storage_integrity_detail,
            "non_repudiation": self.application_repo.load_non_repudiation_detail,
        }
        return loaders[unit_key](session, object_id)

    def _get_object(self, session, kind: str, object_id: int):
        getters = {
            "user": self.application_repo.get_user,
            "access_control": self.application_repo.get_access_control,
            "important_data": self.application_repo.get_important_data,
            "business_action": self.application_repo.get_business_action,
        }
        return getters[kind](session, object_id)

    def _apply_object_values(self, kind: str, target, values: dict[str, Any]) -> None:
        config = OBJECT_CONFIG[kind]
        for field in config["fields"]:
            if field not in values:
                continue
            if field == "related_channel_id":
                target.related_channel_id = self._int_or_none(values[field])
            else:
                setattr(target, field, self._text(values[field]))
        extra = self._mapping(target.extra_data)
        for field in config["extra_fields"]:
            if field in values:
                extra[field] = self._text(values[field])
        if extra:
            target.extra_data = extra

    def _apply_detail_values(self, unit_key: str, detail, values: dict[str, Any]) -> None:
        fields = set(COMMON_DETAIL_FIELDS)
        fields.update(UNIT_CONFIG[unit_key]["specific_fields"])
        for field, value in values.items():
            if field not in fields:
                continue
            if field == "network_channel_id":
                detail.network_channel_id = self._int_or_none(value)
            else:
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

    def _detail_product_reference_is_ambiguous(
        self,
        session,
        unit_key: str,
        target,
        detail_id: int,
    ) -> bool:
        if detail_id == target.id:
            return False
        object_kind = UNIT_CONFIG[unit_key]["object_kind"]
        object_model = OBJECT_CONFIG[object_kind]["model"]
        candidate = session.get(object_model, detail_id)
        return candidate is not None and candidate.project_id == target.project_id

    def _object_product_reference_is_ambiguous(self, session, unit_key: str, target) -> bool:
        detail_model = UNIT_CONFIG[unit_key]["detail_model"]
        fk_field = UNIT_CONFIG[unit_key]["fk_field"]
        candidate = session.get(detail_model, target.id)
        return (
            candidate is not None
            and candidate.project_id == target.project_id
            and getattr(candidate, fk_field) != target.id
        )

    def _subsystem_record(self, subsystem: ApplicationSubsystem) -> ApplicationSubsystemRecord:
        return ApplicationSubsystemRecord(
            id=subsystem.id,
            project_id=subsystem.project_id,
            basic_subsystem_id=subsystem.basic_subsystem_id,
            name=subsystem.name,
            description=subsystem.description,
            sort_order=subsystem.sort_order,
        )

    def _object_record(self, kind: str, target) -> ApplicationObjectRecord:
        extra = self._mapping(getattr(target, "extra_data", None))
        return ApplicationObjectRecord(
            id=target.id,
            project_id=target.project_id,
            application_subsystem_id=target.application_subsystem_id,
            kind=kind,
            name=target.name,
            sort_order=target.sort_order,
            role=getattr(target, "role", ""),
            scope=getattr(target, "scope", ""),
            policy_description=getattr(target, "policy_description", ""),
            data_type=getattr(target, "data_type", ""),
            related_channel_id=getattr(target, "related_channel_id", None),
            description=getattr(target, "description", ""),
            extra_data=extra,
        )

    def _unit_record(self, session, target, unit_key: str, detail) -> ApplicationUnitRecord:
        unit_type = UNIT_CONFIG[unit_key]["unit_type"]
        quant = self.shared_repo.get_quant(session, target.project_id, unit_type, detail.id)
        products = [
            {
                "name": product.product_name,
                "vendor": product.vendor,
                "certificate_no": product.certificate_no,
                "level": product.product_level or "",
                "usage": product.usage,
            }
            for product in self.shared_repo.load_products(
                session,
                target.project_id,
                unit_type,
                target.id,
            )
        ]
        return ApplicationUnitRecord(
            id=detail.id,
            project_id=detail.project_id,
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
            application_user_id=getattr(detail, "application_user_id", None),
            access_control_object_id=getattr(detail, "access_control_object_id", None),
            important_data_id=getattr(detail, "important_data_id", None),
            business_action_id=getattr(detail, "business_action_id", None),
            network_channel_id=getattr(detail, "network_channel_id", None),
            auth_methods=getattr(detail, "auth_methods", ""),
            certificate_usage=getattr(detail, "certificate_usage", ""),
            access_control_policy=getattr(detail, "access_control_policy", ""),
            integrity_method=getattr(detail, "integrity_method", ""),
            encryption_method=getattr(detail, "encryption_method", ""),
            storage_location=getattr(detail, "storage_location", ""),
            signature_method=getattr(detail, "signature_method", ""),
            timestamp_method=getattr(detail, "timestamp_method", ""),
            quant=self._quant_payload(quant),
            products=products,
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

    def _validate_kind(self, kind: str) -> None:
        if kind not in OBJECT_CONFIG:
            raise ValueError(f"unknown application object kind: {kind}")

    def _mapping(self, value: Any) -> dict[str, Any]:
        return dict(value) if isinstance(value, dict) else {}

    def _text(self, value: Any) -> str:
        return "" if value is None else str(value).strip()

    def _int_or_none(self, value: Any) -> int | None:
        if value in (None, ""):
            return None
        return int(value)
