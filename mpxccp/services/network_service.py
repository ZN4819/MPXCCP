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
from mpxccp.models.technical_network import (
    NetworkAuthDetail,
    NetworkBoundaryIntegrityDetail,
    NetworkChannel,
    NetworkConfidentialityDetail,
    NetworkIntegrityDetail,
    NetworkSubsystem,
)
from mpxccp.repositories.network_repo import NetworkRepository
from mpxccp.repositories.session import readonly_session_scope, session_scope
from mpxccp.repositories.shared_repo import SharedRepository
from mpxccp.services.result import ServiceResult


@dataclass(frozen=True)
class NetworkSubsystemRecord:
    id: int
    project_id: int
    basic_subsystem_id: int | None
    name: str
    description: str
    sort_order: int


@dataclass(frozen=True)
class NetworkChannelRecord:
    id: int
    project_id: int
    network_subsystem_id: int
    name: str
    source: str
    target: str
    protocol: str
    network_environment: str
    client_type: str
    server_type: str
    interview_record: str
    description: str
    sort_order: int
    extra_data: dict[str, Any] | None = None


@dataclass(frozen=True)
class NetworkUnitRecord:
    id: int
    project_id: int
    network_channel_id: int
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
    certificate_usage: str = ""
    integrity_method: str = ""
    encryption_method: str = ""
    boundary_device: str = ""
    boundary_product_level: str = ""
    quant: dict[str, str | float] | None = None
    products: list[dict[str, str]] | None = None
    extra_data: dict[str, Any] | None = None


@dataclass(frozen=True)
class NetworkDetails:
    channel: NetworkChannelRecord
    auth: NetworkUnitRecord
    integrity: NetworkUnitRecord
    confidentiality: NetworkUnitRecord
    boundary: NetworkUnitRecord

    def all_detail_ids(self) -> tuple[int, int, int, int]:
        return (
            self.auth.id,
            self.integrity.id,
            self.confidentiality.id,
            self.boundary.id,
        )


@dataclass(frozen=True)
class AssociationReference:
    unit_type: str
    related_id: int


UNIT_CONFIG = {
    "auth": {
        "unit_type": MeasureUnit.NETWORK_AUTH.value,
        "specific_fields": ("auth_methods", "certificate_usage"),
        "product_write": True,
        "model": NetworkAuthDetail,
    },
    "integrity": {
        "unit_type": MeasureUnit.NETWORK_INTEGRITY.value,
        "specific_fields": ("integrity_method", "certificate_usage"),
        "product_write": True,
        "model": NetworkIntegrityDetail,
    },
    "confidentiality": {
        "unit_type": MeasureUnit.NETWORK_CONFIDENTIALITY.value,
        "specific_fields": ("encryption_method", "certificate_usage"),
        "product_write": True,
        "model": NetworkConfidentialityDetail,
    },
    "boundary": {
        "unit_type": MeasureUnit.NETWORK_BOUNDARY_INTEGRITY.value,
        "specific_fields": ("boundary_device", "boundary_product_level", "integrity_method"),
        "product_write": False,
        "model": NetworkBoundaryIntegrityDetail,
    },
}
CHANNEL_FIELDS = ("name", "source", "target", "protocol")
CHANNEL_EXTRA_FIELDS = (
    "network_environment",
    "client_type",
    "server_type",
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
    "certificate_algorithm",
    "certificate_source",
    "certificate_start_date",
    "certificate_end_date",
    "certificate_other_info",
    "implementation_status",
    "technical_compliance",
    "product_used",
    "product_level",
    "mitigation_available",
    "mitigation_note",
    "mitigated_level",
    "other_info",
)
NetworkDetailModel = (
    NetworkAuthDetail
    | NetworkIntegrityDetail
    | NetworkConfidentialityDetail
    | NetworkBoundaryIntegrityDetail
)


class NetworkService:
    def __init__(
        self,
        engine: Engine,
        *,
        network_repo: NetworkRepository | None = None,
        shared_repo: SharedRepository | None = None,
    ) -> None:
        self.engine = engine
        self.network_repo = network_repo or NetworkRepository()
        self.shared_repo = shared_repo or SharedRepository()

    def sync_from_basic_subsystems(self, project_id: int) -> list[NetworkSubsystemRecord]:
        with session_scope(self.engine) as session:
            return [
                self._subsystem_record(subsystem)
                for subsystem in self.network_repo.sync_from_basic_subsystems(
                    session,
                    project_id,
                )
            ]

    def list_subsystems(self, project_id: int) -> list[NetworkSubsystemRecord]:
        with readonly_session_scope(self.engine) as session:
            return [
                self._subsystem_record(subsystem)
                for subsystem in self.network_repo.list_subsystems(session, project_id)
            ]

    def list_channels(self, network_subsystem_id: int) -> list[NetworkChannelRecord]:
        with readonly_session_scope(self.engine) as session:
            return [
                self._channel_record(channel)
                for channel in self.network_repo.list_channels(session, network_subsystem_id)
            ]

    def channel_count(self, network_subsystem_id: int) -> int:
        return len(self.list_channels(network_subsystem_id))

    def create_channel(
        self,
        network_subsystem_id: int,
        name: str,
    ) -> NetworkChannelRecord:
        cleaned_name = self._text(name) or "未命名通信信道"
        with session_scope(self.engine) as session:
            channel = self.network_repo.create_channel(
                session,
                network_subsystem_id,
                cleaned_name,
            )
            return self._channel_record(channel)

    def load_detail(self, channel_id: int) -> NetworkDetails:
        return self.load_details(channel_id)

    def load_details(self, channel_id: int) -> NetworkDetails:
        with readonly_session_scope(self.engine) as session:
            channel = self.network_repo.get_channel(session, channel_id)
            if channel is None:
                raise ValueError(f"network channel not found: {channel_id}")
            auth, integrity, confidentiality, boundary = self._load_required_details(
                session,
                channel_id,
            )
            return NetworkDetails(
                channel=self._channel_record(channel),
                auth=self._unit_record(session, channel, "auth", auth),
                integrity=self._unit_record(session, channel, "integrity", integrity),
                confidentiality=self._unit_record(
                    session,
                    channel,
                    "confidentiality",
                    confidentiality,
                ),
                boundary=self._unit_record(session, channel, "boundary", boundary),
            )

    def save_channel_detail(
        self,
        channel_id: int,
        payload: dict[str, Any],
        silent: bool = True,
    ) -> ServiceResult:
        with session_scope(self.engine) as session:
            channel = self.network_repo.get_channel(session, channel_id)
            if channel is None:
                return ServiceResult(
                    success=False,
                    message="network channel not found",
                    warnings=["network_channel_not_found"],
                )

            self._apply_channel_values(channel, self._mapping(payload.get("channel")))

            details = dict(
                zip(UNIT_CONFIG, self._load_required_details(session, channel_id), strict=True)
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
                        project_id=channel.project_id,
                        unit_type=unit_type,
                        related_id=detail.id,
                        values=self._mapping(detail_values["quant"]),
                    )
                if UNIT_CONFIG[unit_key]["product_write"] and "products" in detail_values:
                    self._save_products(
                        session,
                        project_id=channel.project_id,
                        unit_type=unit_type,
                        related_id=channel.id,
                        products=detail_values["products"],
                    )

            message = "" if silent else "network channel detail saved"
            return ServiceResult(
                success=True,
                message=message,
                project_id=channel.project_id,
                payload={"channel_id": channel.id, "channel_name": channel.name},
            )

    def delete_channel(self, channel_id: int) -> ServiceResult:
        with session_scope(self.engine) as session:
            channel = self.network_repo.get_channel(session, channel_id)
            if channel is None:
                return ServiceResult(
                    success=False,
                    message="network channel not found",
                    warnings=["network_channel_not_found"],
                )
            details = self._load_existing_details(session, channel_id)
            warnings = [
                f"missing_network_detail:{unit_key}"
                for unit_key, detail in details.items()
                if detail is None
            ]
            for unit_key, detail in details.items():
                unit_type = UNIT_CONFIG[unit_key]["unit_type"]
                if detail is not None:
                    self.shared_repo.delete_quant_for_related(
                        session,
                        channel.project_id,
                        unit_type,
                        detail.id,
                    )
                    self.shared_repo.delete_evidence_for_related(
                        session,
                        channel.project_id,
                        unit_type,
                        detail.id,
                    )
                    if self._detail_product_reference_is_ambiguous(
                        session,
                        channel,
                        detail.id,
                    ):
                        warnings.append(f"ambiguous_network_detail_product:{unit_key}")
                    else:
                        self.shared_repo.delete_products_for_related(
                            session,
                            channel.project_id,
                            unit_type,
                            detail.id,
                        )
                    session.delete(detail)
                if self._channel_product_reference_is_ambiguous(session, channel, unit_key):
                    warnings.append(f"ambiguous_network_channel_product:{unit_key}")
                else:
                    self.shared_repo.delete_products_for_related(
                        session,
                        channel.project_id,
                        unit_type,
                        channel.id,
                    )
            session.flush()
            session.delete(channel)
            return ServiceResult(
                success=True,
                message="network channel deleted",
                warnings=warnings,
                project_id=channel.project_id,
                payload={"channel_id": channel_id},
            )

    def evidence_ref_for_boundary(self, boundary_detail_id: int) -> AssociationReference:
        return AssociationReference(
            unit_type=MeasureUnit.NETWORK_BOUNDARY_INTEGRITY.value,
            related_id=boundary_detail_id,
        )

    def apply_product_level_quant_rule(
        self,
        unit_name: str,
        product_level: str,
    ) -> QuantRuleResult:
        if unit_name not in {config["unit_type"] for config in UNIT_CONFIG.values()}:
            raise ValueError(f"unknown network measure unit: {unit_name}")
        return apply_quant_auto_rule(product_level=product_level)

    def _load_required_details(self, session, channel_id: int):
        auth = self.network_repo.load_auth_detail(session, channel_id)
        integrity = self.network_repo.load_integrity_detail(session, channel_id)
        confidentiality = self.network_repo.load_confidentiality_detail(session, channel_id)
        boundary = self.network_repo.load_boundary_detail(session, channel_id)
        if any(detail is None for detail in (auth, integrity, confidentiality, boundary)):
            raise ValueError(f"network details are incomplete: {channel_id}")
        return auth, integrity, confidentiality, boundary

    def _load_existing_details(self, session, channel_id: int) -> dict[str, Any]:
        return {
            "auth": self.network_repo.load_auth_detail(session, channel_id),
            "integrity": self.network_repo.load_integrity_detail(session, channel_id),
            "confidentiality": self.network_repo.load_confidentiality_detail(
                session,
                channel_id,
            ),
            "boundary": self.network_repo.load_boundary_detail(session, channel_id),
        }

    def _detail_product_reference_is_ambiguous(
        self,
        session,
        channel: NetworkChannel,
        detail_id: int,
    ) -> bool:
        if detail_id == channel.id:
            return False
        candidate = session.get(NetworkChannel, detail_id)
        return candidate is not None and candidate.project_id == channel.project_id

    def _channel_product_reference_is_ambiguous(
        self,
        session,
        channel: NetworkChannel,
        unit_key: str,
    ) -> bool:
        detail_model = UNIT_CONFIG[unit_key]["model"]
        candidate = session.get(detail_model, channel.id)
        return (
            candidate is not None
            and candidate.project_id == channel.project_id
            and candidate.network_channel_id != channel.id
        )

    def _apply_channel_values(self, channel: NetworkChannel, values: dict[str, Any]) -> None:
        for field, value in values.items():
            if field in CHANNEL_FIELDS:
                setattr(channel, field, self._text(value))
        extra = self._mapping(channel.extra_data)
        for field in CHANNEL_EXTRA_FIELDS:
            if field in values:
                extra[field] = self._text(values[field])
        if extra:
            channel.extra_data = extra

    def _apply_detail_values(
        self,
        unit_key: str,
        detail: NetworkDetailModel,
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

    def _subsystem_record(self, subsystem: NetworkSubsystem) -> NetworkSubsystemRecord:
        return NetworkSubsystemRecord(
            id=subsystem.id,
            project_id=subsystem.project_id,
            basic_subsystem_id=subsystem.basic_subsystem_id,
            name=subsystem.name,
            description=subsystem.description,
            sort_order=subsystem.sort_order,
        )

    def _channel_record(self, channel: NetworkChannel) -> NetworkChannelRecord:
        extra = self._mapping(channel.extra_data)
        return NetworkChannelRecord(
            id=channel.id,
            project_id=channel.project_id,
            network_subsystem_id=channel.network_subsystem_id,
            name=channel.name,
            source=channel.source,
            target=channel.target,
            protocol=channel.protocol,
            network_environment=self._text(extra.get("network_environment", "")),
            client_type=self._text(extra.get("client_type", "")),
            server_type=self._text(extra.get("server_type", "")),
            interview_record=self._text(extra.get("interview_record", "")),
            description=self._text(extra.get("description", "")),
            sort_order=channel.sort_order,
            extra_data=extra,
        )

    def _unit_record(
        self,
        session,
        channel: NetworkChannel,
        unit_key: str,
        detail: NetworkDetailModel,
    ) -> NetworkUnitRecord:
        unit_type = UNIT_CONFIG[unit_key]["unit_type"]
        quant = self.shared_repo.get_quant(session, channel.project_id, unit_type, detail.id)
        products = []
        if UNIT_CONFIG[unit_key]["product_write"]:
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
                    channel.project_id,
                    unit_type,
                    channel.id,
                )
            ]
        return NetworkUnitRecord(
            id=detail.id,
            project_id=detail.project_id,
            network_channel_id=detail.network_channel_id,
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
            certificate_usage=getattr(detail, "certificate_usage", ""),
            integrity_method=getattr(detail, "integrity_method", ""),
            encryption_method=getattr(detail, "encryption_method", ""),
            boundary_device=getattr(detail, "boundary_device", ""),
            boundary_product_level=getattr(detail, "boundary_product_level", "") or "",
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

    def _mapping(self, value: Any) -> dict[str, Any]:
        return dict(value) if isinstance(value, dict) else {}

    def _text(self, value: Any) -> str:
        return "" if value is None else str(value).strip()
