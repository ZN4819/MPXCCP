from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import Engine

from mpxccp.domain.enums import MeasureUnit
from mpxccp.domain.quant_rules import calculate_object_score, normalize_quant_values
from mpxccp.models.shared import QuantitativeAssessment
from mpxccp.models.technical_physical import (
    PhysicalAccessIntegrityDetail,
    PhysicalAuthDetail,
    PhysicalObject,
    PhysicalVideoIntegrityDetail,
)
from mpxccp.repositories.physical_repo import PhysicalRepository
from mpxccp.repositories.session import readonly_session_scope, session_scope
from mpxccp.repositories.shared_repo import SharedRepository
from mpxccp.services.result import ServiceResult


@dataclass(frozen=True)
class PhysicalObjectRecord:
    id: int
    project_id: int
    name: str
    location: str
    access_control_system: str
    video_system: str
    interview_record: str
    sort_order: int


@dataclass(frozen=True)
class PhysicalUnitRecord:
    id: int
    project_id: int
    physical_object_id: int
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
    access_control_device: str = ""
    record_source: str = ""
    integrity_method: str = ""
    video_record_source: str = ""
    quant: dict[str, str | float] | None = None
    products: list[dict[str, str]] | None = None
    extra_data: dict[str, Any] | None = None


@dataclass(frozen=True)
class PhysicalDetails:
    object: PhysicalObjectRecord
    auth: PhysicalUnitRecord
    access_integrity: PhysicalUnitRecord
    video_integrity: PhysicalUnitRecord

    def detail_ids(self) -> tuple[int, int, int]:
        return (self.auth.id, self.access_integrity.id, self.video_integrity.id)


UNIT_CONFIG = {
    "auth": {
        "unit_type": MeasureUnit.PHYSICAL_AUTH.value,
        "specific_fields": ("auth_methods", "access_control_device"),
    },
    "access_integrity": {
        "unit_type": MeasureUnit.PHYSICAL_ACCESS_INTEGRITY.value,
        "specific_fields": ("record_source", "integrity_method"),
    },
    "video_integrity": {
        "unit_type": MeasureUnit.PHYSICAL_VIDEO_INTEGRITY.value,
        "specific_fields": ("video_record_source", "integrity_method"),
    },
}
OBJECT_FIELDS = (
    "name",
    "location",
    "access_control_system",
    "video_system",
    "interview_record",
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
    "guarded",
    "registered",
    "accompanied",
    "realtime_monitoring",
    "mitigation_available",
    "mitigation_note",
    "mitigated_level",
)


class PhysicalService:
    def __init__(
        self,
        engine: Engine,
        *,
        physical_repo: PhysicalRepository | None = None,
        shared_repo: SharedRepository | None = None,
    ) -> None:
        self.engine = engine
        self.physical_repo = physical_repo or PhysicalRepository()
        self.shared_repo = shared_repo or SharedRepository()

    def create_object(self, project_id: int, name: str) -> PhysicalObjectRecord:
        cleaned_name = self._text(name) or "未命名物理对象"
        with session_scope(self.engine) as session:
            obj = self.physical_repo.create_object(session, project_id, cleaned_name)
            return self._object_record(obj)

    def list_objects(self, project_id: int) -> list[PhysicalObjectRecord]:
        with readonly_session_scope(self.engine) as session:
            return [
                self._object_record(obj)
                for obj in self.physical_repo.list_objects(session, project_id)
            ]

    def load_detail(self, object_id: int) -> PhysicalDetails:
        return self.load_details(object_id)

    def load_details(self, object_id: int) -> PhysicalDetails:
        with readonly_session_scope(self.engine) as session:
            obj = self.physical_repo.get_object(session, object_id)
            if obj is None:
                raise ValueError(f"physical object not found: {object_id}")
            auth, access, video = self._load_required_details(session, object_id)
            return PhysicalDetails(
                object=self._object_record(obj),
                auth=self._unit_record(session, obj, "auth", auth),
                access_integrity=self._unit_record(session, obj, "access_integrity", access),
                video_integrity=self._unit_record(session, obj, "video_integrity", video),
            )

    def save_detail(
        self,
        object_id: int,
        payload: dict[str, Any],
        silent: bool = True,
    ) -> ServiceResult:
        with session_scope(self.engine) as session:
            obj = self.physical_repo.get_object(session, object_id)
            if obj is None:
                return ServiceResult(
                    success=False,
                    message="physical object not found",
                    warnings=["physical_object_not_found"],
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

            message = "" if silent else "physical detail saved"
            return ServiceResult(
                success=True,
                message=message,
                project_id=obj.project_id,
                payload={"object_id": obj.id, "object_name": obj.name},
            )

    def delete_object(self, object_id: int) -> ServiceResult:
        with session_scope(self.engine) as session:
            obj = self.physical_repo.get_object(session, object_id)
            if obj is None:
                return ServiceResult(
                    success=False,
                    message="physical object not found",
                    warnings=["physical_object_not_found"],
                )
            details = self._load_existing_details(session, object_id)
            warnings = [
                f"missing_physical_detail:{unit_key}"
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
                message="physical object deleted",
                warnings=warnings,
                project_id=obj.project_id,
                payload={"object_id": object_id},
            )

    def _load_required_details(self, session, object_id: int):
        auth = self.physical_repo.load_auth_detail(session, object_id)
        access = self.physical_repo.load_access_integrity_detail(session, object_id)
        video = self.physical_repo.load_video_integrity_detail(session, object_id)
        if auth is None or access is None or video is None:
            raise ValueError(f"physical details are incomplete: {object_id}")
        return auth, access, video

    def _load_existing_details(self, session, object_id: int) -> dict[str, Any]:
        return {
            "auth": self.physical_repo.load_auth_detail(session, object_id),
            "access_integrity": self.physical_repo.load_access_integrity_detail(
                session,
                object_id,
            ),
            "video_integrity": self.physical_repo.load_video_integrity_detail(
                session,
                object_id,
            ),
        }

    def _apply_detail_values(
        self,
        unit_key: str,
        detail: PhysicalAuthDetail | PhysicalAccessIntegrityDetail | PhysicalVideoIntegrityDetail,
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

    def _object_record(self, obj: PhysicalObject) -> PhysicalObjectRecord:
        return PhysicalObjectRecord(
            id=obj.id,
            project_id=obj.project_id,
            name=obj.name,
            location=obj.location,
            access_control_system=obj.access_control_system,
            video_system=obj.video_system,
            interview_record=obj.interview_record,
            sort_order=obj.sort_order,
        )

    def _unit_record(
        self,
        session,
        obj: PhysicalObject,
        unit_key: str,
        detail: PhysicalAuthDetail | PhysicalAccessIntegrityDetail | PhysicalVideoIntegrityDetail,
    ) -> PhysicalUnitRecord:
        unit_type = UNIT_CONFIG[unit_key]["unit_type"]
        quant = self.shared_repo.get_quant(session, obj.project_id, unit_type, detail.id)
        return PhysicalUnitRecord(
            id=detail.id,
            project_id=detail.project_id,
            physical_object_id=detail.physical_object_id,
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
            access_control_device=getattr(detail, "access_control_device", ""),
            record_source=getattr(detail, "record_source", ""),
            integrity_method=getattr(detail, "integrity_method", ""),
            video_record_source=getattr(detail, "video_record_source", ""),
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
