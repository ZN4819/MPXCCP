from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import Engine, func, select

import mpxccp.models as models
from mpxccp.domain.constants import MANAGEMENT_FULL_SCORE, TECHNICAL_FULL_SCORE
from mpxccp.domain.enums import SecurityLayer
from mpxccp.domain.quant_rules import calculate_object_score
from mpxccp.domain.scoring_rules import (
    calculate_total_score,
    calculate_weighted_layer_score,
    classify_compliance,
)
from mpxccp.models.scoring import ScoreDetail, ScoreSummary, ScoringIndicator
from mpxccp.models.shared import QuantitativeAssessment
from mpxccp.repositories.scoring_repo import ScoringRepository
from mpxccp.repositories.session import readonly_session_scope, session_scope

TECHNICAL_LAYERS = (
    SecurityLayer.PHYSICAL.value,
    SecurityLayer.NETWORK.value,
    SecurityLayer.DEVICE.value,
    SecurityLayer.APPLICATION.value,
)
MANAGEMENT_LAYERS = (
    SecurityLayer.MANAGEMENT_SYSTEM.value,
    SecurityLayer.PERSONNEL.value,
    SecurityLayer.CONSTRUCTION.value,
    SecurityLayer.EMERGENCY.value,
)
COMPLIANCE_SCORE = {
    "符合": 1.0,
    "部分符合": 0.5,
    "不符合": 0.0,
    "不适用": None,
    "": None,
}


@dataclass(frozen=True)
class IndicatorRecord:
    no: int
    name: str
    layer: str
    weight: float
    always_not_applicable: bool
    unit_types: tuple[str, ...] = ()


@dataclass
class ScoreObjectRecord:
    unit_type: str
    related_id: int
    object_name: str
    d: str
    a: str
    k: str
    ra: float
    rk: float
    score: float | None


@dataclass
class ScoreDetailRecord:
    indicator_no: int
    indicator_name: str
    layer: str
    unit_type: str
    score: float | None
    compliance_status: str
    indicator_weight: float
    effective_object_count: int
    allocated_score: float | None = None
    earned_score: float | None = None
    lost_score: float | None = None
    not_applicable: bool = False
    object_rows: list[ScoreObjectRecord] = field(default_factory=list)


@dataclass(frozen=True)
class LayerScoreRecord:
    name: str
    score: float | None
    actual_weight: float
    allocated_score: float | None
    earned_score: float | None
    lost_score: float | None


@dataclass
class ScoreSummaryRecord:
    project_id: int
    technical_score: float | None = None
    management_score: float | None = None
    total_score: float = 0.0
    total_allocated_score: float = 100.0
    total_earned_score: float = 0.0
    total_lost_score: float = 100.0
    compliant_count: int = 0
    partial_count: int = 0
    non_compliant_count: int = 0
    not_applicable_count: int = 0
    dirty: bool = False
    layer_scores: list[LayerScoreRecord] = field(default_factory=list)
    details: list[ScoreDetailRecord] = field(default_factory=list)


class ScoringService:
    def __init__(
        self,
        engine: Engine,
        *,
        scoring_repo: ScoringRepository | None = None,
    ) -> None:
        self.engine = engine
        self.scoring_repo = scoring_repo or ScoringRepository()

    def ensure_indicators(self) -> None:
        with session_scope(self.engine) as session:
            self.scoring_repo.ensure_indicators(session)

    def list_indicators(self) -> list[IndicatorRecord]:
        with readonly_session_scope(self.engine) as session:
            return [
                self._indicator_record(indicator)
                for indicator in self.scoring_repo.list_indicators(session)
            ]

    def count_indicators(self) -> int:
        with readonly_session_scope(self.engine) as session:
            return session.scalar(select(func.count()).select_from(models.ScoringIndicator)) or 0

    def refresh_technical_domain(self, project_id: int, layer: str) -> ScoreSummaryRecord:
        with session_scope(self.engine) as session:
            self.scoring_repo.ensure_indicators(session)
            indicators = [
                indicator
                for indicator in self.scoring_repo.list_indicators(session)
                if indicator.layer == layer and indicator.indicator_no <= 22
            ]
            for indicator in indicators:
                for unit_type in indicator.unit_types or []:
                    for detail in self.scoring_repo.list_unit_details(
                        session,
                        project_id,
                        unit_type,
                    ):
                        self.scoring_repo.ensure_empty_quant(
                            session,
                            project_id=project_id,
                            unit_type=unit_type,
                            related_id=detail.id,
                        )
        return self.calculate_and_persist_summary(project_id)

    def refresh_all_technical_domains(self, project_id: int) -> ScoreSummaryRecord:
        with session_scope(self.engine) as session:
            self.scoring_repo.ensure_indicators(session)
            indicators = [
                indicator
                for indicator in self.scoring_repo.list_indicators(session)
                if indicator.indicator_no <= 22
            ]
            for indicator in indicators:
                for unit_type in indicator.unit_types or []:
                    for detail in self.scoring_repo.list_unit_details(
                        session,
                        project_id,
                        unit_type,
                    ):
                        self.scoring_repo.ensure_empty_quant(
                            session,
                            project_id=project_id,
                            unit_type=unit_type,
                            related_id=detail.id,
                        )
        return self.calculate_and_persist_summary(project_id)

    def save_management_score(
        self,
        project_id: int,
        indicator_no: int,
        compliance: str,
    ) -> ScoreSummaryRecord:
        with session_scope(self.engine) as session:
            self.scoring_repo.ensure_indicators(session)
            indicator = next(
                item
                for item in self.scoring_repo.list_indicators(session)
                if item.indicator_no == indicator_no
            )
            status = compliance if compliance in COMPLIANCE_SCORE else ""
            self.scoring_repo.upsert_management_score(
                session,
                project_id=project_id,
                indicator_no=indicator_no,
                layer=indicator.layer,
                compliance_status=status,
                score=COMPLIANCE_SCORE[status],
            )
        return self.calculate_and_persist_summary(project_id)

    def calculate_and_persist_summary(self, project_id: int) -> ScoreSummaryRecord:
        with session_scope(self.engine) as session:
            return self.calculate_and_persist_summary_in_session(session, project_id)

    def calculate_and_persist_summary_in_session(
        self,
        session,
        project_id: int,
    ) -> ScoreSummaryRecord:
        self.scoring_repo.ensure_indicators(session)
        indicators = self.scoring_repo.list_indicators(session)
        management = {
            item.indicator_no: item
            for item in self.scoring_repo.list_management_scores(session, project_id)
        }
        details = [
            self._calculate_indicator_detail(session, project_id, indicator, management)
            for indicator in indicators
        ]
        technical_score = self._category_score(details, TECHNICAL_LAYERS)
        management_score = self._category_score(details, MANAGEMENT_LAYERS)
        layer_scores = self._allocate_scores(details)
        counts = self._compliance_counts(details)
        total_score = calculate_total_score(technical_score, management_score)
        self.scoring_repo.replace_summary(
            session,
            project_id=project_id,
            summary_values={
                "technical_score": technical_score,
                "management_score": management_score,
                "total_score": total_score,
                "total_allocated_score": 100.0,
                "total_earned_score": total_score,
                "total_lost_score": round(100.0 - total_score, 2),
                "compliant_count": counts["符合"],
                "partial_count": counts["部分符合"],
                "non_compliant_count": counts["不符合"],
                "not_applicable_count": counts["不适用"],
                "layer_scores": {
                    item.name: {
                        "score": item.score,
                        "actual_weight": item.actual_weight,
                        "allocated_score": item.allocated_score,
                        "earned_score": item.earned_score,
                        "lost_score": item.lost_score,
                    }
                    for item in layer_scores
                },
            },
            detail_values=[self._detail_values(detail) for detail in details],
        )
        return ScoreSummaryRecord(
            project_id=project_id,
            technical_score=technical_score,
            management_score=management_score,
            total_score=total_score,
            total_allocated_score=100.0,
            total_earned_score=total_score,
            total_lost_score=round(100.0 - total_score, 2),
            compliant_count=counts["符合"],
            partial_count=counts["部分符合"],
            non_compliant_count=counts["不符合"],
            not_applicable_count=counts["不适用"],
            dirty=False,
            layer_scores=layer_scores,
            details=details,
        )

    def load_summary(self, project_id: int) -> ScoreSummaryRecord | None:
        with readonly_session_scope(self.engine) as session:
            summary = self.scoring_repo.get_summary(session, project_id)
            if summary is None:
                return None
            return self._summary_record(session, summary)

    def mark_dirty(self, project_id: int) -> ScoreSummaryRecord:
        with session_scope(self.engine) as session:
            summary = self.scoring_repo.mark_dirty(session, project_id)
            return self._summary_record(session, summary)

    def _calculate_indicator_detail(
        self,
        session,
        project_id: int,
        indicator: ScoringIndicator,
        management: dict[int, Any],
    ) -> ScoreDetailRecord:
        unit_types = tuple(indicator.unit_types or ())
        if indicator.always_not_applicable:
            return self._not_applicable_detail(indicator, unit_types)
        if indicator.indicator_no <= 22:
            return self._technical_detail(session, project_id, indicator, unit_types)
        model = management.get(indicator.indicator_no)
        score = model.score if model is not None else None
        status = classify_compliance(score)
        return ScoreDetailRecord(
            indicator_no=indicator.indicator_no,
            indicator_name=indicator.name,
            layer=indicator.layer,
            unit_type="管理域评分",
            score=score,
            compliance_status=status,
            indicator_weight=indicator.weight,
            effective_object_count=0 if score is None else 1,
            not_applicable=score is None,
        )

    def _technical_detail(
        self,
        session,
        project_id: int,
        indicator: ScoringIndicator,
        unit_types: tuple[str, ...],
    ) -> ScoreDetailRecord:
        if not unit_types:
            return self._not_applicable_detail(indicator, unit_types)
        has_detail = False
        has_quant = False
        object_scores: list[float] = []
        object_rows: list[ScoreObjectRecord] = []
        for unit_type in unit_types:
            for detail in self.scoring_repo.list_unit_details(session, project_id, unit_type):
                has_detail = True
                quant = self.scoring_repo.get_quant(session, project_id, unit_type, detail.id)
                if quant is None:
                    continue
                has_quant = True
                score = self._object_score(quant)
                object_rows.append(
                    ScoreObjectRecord(
                        unit_type=unit_type,
                        related_id=detail.id,
                        object_name=self._object_name(session, unit_type, detail),
                        d=quant.d_value or "",
                        a=quant.a_value or "",
                        k=quant.k_value or "",
                        ra=self._float_or_default(quant.ra_value),
                        rk=self._float_or_default(quant.rk_value),
                        score=score,
                    )
                )
                if score is not None:
                    object_scores.append(score)
        if not has_detail:
            return self._not_applicable_detail(indicator, unit_types)
        if object_scores:
            score = sum(object_scores) / len(object_scores)
            return ScoreDetailRecord(
                indicator_no=indicator.indicator_no,
                indicator_name=indicator.name,
                layer=indicator.layer,
                unit_type="、".join(unit_types),
                score=score,
                compliance_status=classify_compliance(score),
                indicator_weight=indicator.weight,
                effective_object_count=len(object_scores),
                object_rows=object_rows,
            )
        if has_quant:
            detail = self._not_applicable_detail(indicator, unit_types)
            detail.object_rows = object_rows
            return detail
        return ScoreDetailRecord(
            indicator_no=indicator.indicator_no,
            indicator_name=indicator.name,
            layer=indicator.layer,
            unit_type="、".join(unit_types),
            score=0.0,
            compliance_status="不符合",
            indicator_weight=indicator.weight,
            effective_object_count=0,
            not_applicable=False,
        )

    def _not_applicable_detail(
        self,
        indicator: ScoringIndicator,
        unit_types: tuple[str, ...],
    ) -> ScoreDetailRecord:
        return ScoreDetailRecord(
            indicator_no=indicator.indicator_no,
            indicator_name=indicator.name,
            layer=indicator.layer,
            unit_type="、".join(unit_types),
            score=None,
            compliance_status="不适用",
            indicator_weight=indicator.weight,
            effective_object_count=0,
            not_applicable=True,
        )

    def _object_score(self, quant: QuantitativeAssessment) -> float | None:
        return calculate_object_score(
            d=quant.d_value,
            a=quant.a_value,
            k=quant.k_value,
            ra=quant.ra_value,
            rk=quant.rk_value,
        )

    def _object_name(self, session, unit_type: str, detail: Any) -> str:
        object_ref = {
            "物理访问身份鉴别": (models.PhysicalObject, "physical_object_id"),
            "门禁记录完整性": (models.PhysicalObject, "physical_object_id"),
            "视频记录完整性": (models.PhysicalObject, "physical_object_id"),
            "设备登录身份鉴别": (models.DeviceObject, "device_object_id"),
            "远程管理通道": (models.DeviceObject, "device_object_id"),
            "设备访问控制完整性": (models.DeviceObject, "device_object_id"),
            "设备日志完整性": (models.DeviceObject, "device_object_id"),
            "可执行程序完整性": (models.DeviceObject, "device_object_id"),
            "通信实体身份鉴别": (models.NetworkChannel, "network_channel_id"),
            "通信过程数据完整性": (models.NetworkChannel, "network_channel_id"),
            "通信过程数据机密性": (models.NetworkChannel, "network_channel_id"),
            "网络边界访问控制完整性": (models.NetworkChannel, "network_channel_id"),
            "应用用户身份鉴别": (models.ApplicationUser, "application_user_id"),
            "应用访问控制完整性": (models.AccessControlObject, "access_control_object_id"),
            "重要数据传输机密性": (models.ImportantData, "important_data_id"),
            "重要数据存储机密性": (models.ImportantData, "important_data_id"),
            "重要数据传输完整性": (models.ImportantData, "important_data_id"),
            "重要数据存储完整性": (models.ImportantData, "important_data_id"),
            "关键业务行为不可否认性": (models.BusinessAction, "business_action_id"),
        }.get(unit_type)
        if object_ref is None:
            return f"详情 {detail.id}"
        model, field_name = object_ref
        parent_id = getattr(detail, field_name, None)
        parent = session.get(model, parent_id) if parent_id is not None else None
        name = getattr(parent, "name", "") if parent is not None else ""
        return str(name or f"详情 {detail.id}")

    def _category_score(
        self,
        details: list[ScoreDetailRecord],
        layer_names: tuple[str, ...],
    ) -> float | None:
        layer_scores = [
            self._layer_score(details, layer_name)
            for layer_name in layer_names
        ]
        return calculate_weighted_layer_score(
            [(score, 1.0) for score in layer_scores]
        )

    def _layer_score(
        self,
        details: list[ScoreDetailRecord],
        layer_name: str,
    ) -> float | None:
        return calculate_weighted_layer_score(
            [
                (detail.score, detail.indicator_weight)
                for detail in details
                if detail.layer == layer_name
            ]
        )

    def _allocate_scores(self, details: list[ScoreDetailRecord]) -> list[LayerScoreRecord]:
        layer_records: list[LayerScoreRecord] = []
        for layer_group, full_score in (
            (TECHNICAL_LAYERS, TECHNICAL_FULL_SCORE),
            (MANAGEMENT_LAYERS, MANAGEMENT_FULL_SCORE),
        ):
            valid_layers = [
                layer_name
                for layer_name in layer_group
                if self._layer_score(details, layer_name) is not None
            ]
            layer_weight = 1.0 / len(valid_layers) if valid_layers else 0.0
            for layer_name in layer_group:
                layer_score = self._layer_score(details, layer_name)
                valid_details = [
                    detail
                    for detail in details
                    if detail.layer == layer_name and detail.score is not None
                ]
                if layer_score is None or not valid_details:
                    layer_records.append(
                        LayerScoreRecord(layer_name, None, 0.0, None, None, None)
                    )
                    continue
                layer_allocated = round(full_score * layer_weight, 2)
                weight_sum = sum(detail.indicator_weight for detail in valid_details)
                for detail in valid_details:
                    allocated = layer_allocated * detail.indicator_weight / weight_sum
                    earned = allocated * (detail.score or 0.0)
                    detail.allocated_score = round(allocated, 2)
                    detail.earned_score = round(earned, 2)
                    detail.lost_score = round(allocated - earned, 2)
                layer_earned = sum(detail.earned_score or 0.0 for detail in valid_details)
                layer_records.append(
                    LayerScoreRecord(
                        name=layer_name,
                        score=layer_score,
                        actual_weight=round(layer_weight, 4),
                        allocated_score=layer_allocated,
                        earned_score=round(layer_earned, 2),
                        lost_score=round(layer_allocated - layer_earned, 2),
                    )
                )
        return layer_records

    def _compliance_counts(self, details: list[ScoreDetailRecord]) -> dict[str, int]:
        counts = {"符合": 0, "部分符合": 0, "不符合": 0, "不适用": 0}
        for detail in details:
            counts[detail.compliance_status] += 1
        return counts

    def _detail_values(self, detail: ScoreDetailRecord) -> dict[str, Any]:
        return {
            "indicator_no": detail.indicator_no,
            "indicator_name": detail.indicator_name,
            "layer": detail.layer,
            "unit_type": detail.unit_type,
            "related_id": None,
            "score": self._round_or_none(detail.score),
            "indicator_weight": detail.indicator_weight,
            "effective_object_count": detail.effective_object_count,
            "allocated_score": detail.allocated_score,
            "earned_score": detail.earned_score,
            "lost_score": detail.lost_score,
            "compliance_status": detail.compliance_status,
            "risk_level": "",
            "not_applicable": detail.not_applicable,
            "notes": "",
        }

    def _summary_record(self, session, summary: ScoreSummary) -> ScoreSummaryRecord:
        layer_payload = summary.layer_scores or {}
        details = [
            self._score_detail_record(detail)
            for detail in self.scoring_repo.list_summary_details(session, summary.id)
        ]
        return ScoreSummaryRecord(
            project_id=summary.project_id,
            technical_score=summary.technical_score,
            management_score=summary.management_score,
            total_score=summary.total_score,
            total_allocated_score=summary.total_allocated_score,
            total_earned_score=summary.total_earned_score,
            total_lost_score=summary.total_lost_score,
            compliant_count=summary.compliant_count,
            partial_count=summary.partial_count,
            non_compliant_count=summary.non_compliant_count,
            not_applicable_count=summary.not_applicable_count,
            dirty=summary.dirty,
            layer_scores=[
                LayerScoreRecord(
                    name=name,
                    score=values.get("score"),
                    actual_weight=values.get("actual_weight", 0.0),
                    allocated_score=values.get("allocated_score"),
                    earned_score=values.get("earned_score"),
                    lost_score=values.get("lost_score"),
                )
                for name, values in layer_payload.items()
            ],
            details=details,
        )

    def _score_detail_record(self, detail: ScoreDetail) -> ScoreDetailRecord:
        return ScoreDetailRecord(
            indicator_no=detail.indicator_no,
            indicator_name=detail.indicator_name,
            layer=detail.layer,
            unit_type=detail.unit_type,
            score=detail.score,
            compliance_status=detail.compliance_status or "不适用",
            indicator_weight=detail.indicator_weight,
            effective_object_count=detail.effective_object_count,
            allocated_score=detail.allocated_score,
            earned_score=detail.earned_score,
            lost_score=detail.lost_score,
            not_applicable=detail.not_applicable,
        )

    def _indicator_record(self, indicator: ScoringIndicator) -> IndicatorRecord:
        return IndicatorRecord(
            no=indicator.indicator_no,
            name=indicator.name,
            layer=indicator.layer,
            weight=indicator.weight,
            always_not_applicable=indicator.always_not_applicable,
            unit_types=tuple(indicator.unit_types or ()),
        )

    def _round_or_none(self, value: float | None) -> float | None:
        return None if value is None else round(value, 4)

    def _float_or_default(self, value: Any, default: float = 1.0) -> float:
        if value in (None, ""):
            return default
        return float(value)
