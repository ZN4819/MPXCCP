from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from mpxccp.domain.scoring_rules import build_default_indicators, map_indicator_to_units
from mpxccp.models.scoring import ManagementScore, ScoreDetail, ScoreSummary, ScoringIndicator
from mpxccp.models.shared import QuantitativeAssessment
from mpxccp.models.technical_application import (
    AccessControlIntegrityDetail,
    ApplicationUserAuthDetail,
    BusinessActionNonRepudiationDetail,
    DataStorageConfidentialityDetail,
    DataStorageIntegrityDetail,
    DataTransportConfidentialityDetail,
    DataTransportIntegrityDetail,
)
from mpxccp.models.technical_device import (
    DeviceAccessIntegrityDetail,
    DeviceAuthDetail,
    DeviceExecutableIntegrityDetail,
    DeviceLogIntegrityDetail,
    DeviceRemoteManagementDetail,
)
from mpxccp.models.technical_network import (
    NetworkAuthDetail,
    NetworkBoundaryIntegrityDetail,
    NetworkConfidentialityDetail,
    NetworkIntegrityDetail,
)
from mpxccp.models.technical_physical import (
    PhysicalAccessIntegrityDetail,
    PhysicalAuthDetail,
    PhysicalVideoIntegrityDetail,
)

TECHNICAL_DETAIL_MODELS: dict[str, type] = {
    "物理访问身份鉴别": PhysicalAuthDetail,
    "门禁记录完整性": PhysicalAccessIntegrityDetail,
    "视频记录完整性": PhysicalVideoIntegrityDetail,
    "通信实体身份鉴别": NetworkAuthDetail,
    "通信过程数据完整性": NetworkIntegrityDetail,
    "通信过程数据机密性": NetworkConfidentialityDetail,
    "网络边界访问控制完整性": NetworkBoundaryIntegrityDetail,
    "设备登录身份鉴别": DeviceAuthDetail,
    "远程管理通道": DeviceRemoteManagementDetail,
    "设备访问控制完整性": DeviceAccessIntegrityDetail,
    "设备日志完整性": DeviceLogIntegrityDetail,
    "可执行程序完整性": DeviceExecutableIntegrityDetail,
    "应用用户身份鉴别": ApplicationUserAuthDetail,
    "应用访问控制完整性": AccessControlIntegrityDetail,
    "重要数据传输机密性": DataTransportConfidentialityDetail,
    "重要数据存储机密性": DataStorageConfidentialityDetail,
    "重要数据传输完整性": DataTransportIntegrityDetail,
    "重要数据存储完整性": DataStorageIntegrityDetail,
    "关键业务行为不可否认性": BusinessActionNonRepudiationDetail,
}


class ScoringRepository:
    def ensure_indicators(self, session: Session) -> None:
        for indicator in build_default_indicators():
            model = session.scalar(
                select(ScoringIndicator).where(
                    ScoringIndicator.indicator_no == indicator.no,
                )
            )
            values = {
                "name": indicator.name,
                "layer": indicator.layer,
                "weight": indicator.weight,
                "always_not_applicable": indicator.always_not_applicable,
                "unit_types": list(map_indicator_to_units(indicator.no)),
                "sort_order": indicator.no,
            }
            if model is None:
                session.add(ScoringIndicator(indicator_no=indicator.no, **values))
            else:
                for field, value in values.items():
                    setattr(model, field, value)
        session.flush()

    def list_indicators(self, session: Session) -> list[ScoringIndicator]:
        return list(
            session.scalars(
                select(ScoringIndicator).order_by(ScoringIndicator.indicator_no)
            )
        )

    def get_management_score(
        self,
        session: Session,
        project_id: int,
        indicator_no: int,
    ) -> ManagementScore | None:
        return session.scalar(
            select(ManagementScore).where(
                ManagementScore.project_id == project_id,
                ManagementScore.indicator_no == indicator_no,
            )
        )

    def list_management_scores(
        self,
        session: Session,
        project_id: int,
    ) -> list[ManagementScore]:
        return list(
            session.scalars(
                select(ManagementScore)
                .where(ManagementScore.project_id == project_id)
                .order_by(ManagementScore.indicator_no)
            )
        )

    def upsert_management_score(
        self,
        session: Session,
        *,
        project_id: int,
        indicator_no: int,
        layer: str,
        compliance_status: str,
        score: float | None,
    ) -> ManagementScore:
        model = self.get_management_score(session, project_id, indicator_no)
        if model is None:
            model = ManagementScore(
                project_id=project_id,
                indicator_no=indicator_no,
                layer=layer,
                sort_order=indicator_no,
            )
            session.add(model)
        model.compliance_status = compliance_status
        model.score = score
        session.flush()
        return model

    def list_unit_details(self, session: Session, project_id: int, unit_type: str) -> list[Any]:
        model = TECHNICAL_DETAIL_MODELS.get(unit_type)
        if model is None:
            return []
        return list(
            session.scalars(
                select(model)
                .where(model.project_id == project_id)
                .order_by(model.sort_order, model.id)
            )
        )

    def get_quant(
        self,
        session: Session,
        project_id: int,
        unit_type: str,
        related_id: int,
    ) -> QuantitativeAssessment | None:
        return session.scalar(
            select(QuantitativeAssessment).where(
                QuantitativeAssessment.project_id == project_id,
                QuantitativeAssessment.unit_type == unit_type,
                QuantitativeAssessment.related_id == related_id,
            )
        )

    def ensure_empty_quant(
        self,
        session: Session,
        *,
        project_id: int,
        unit_type: str,
        related_id: int,
    ) -> QuantitativeAssessment:
        model = self.get_quant(session, project_id, unit_type, related_id)
        if model is None:
            model = QuantitativeAssessment(
                project_id=project_id,
                unit_type=unit_type,
                related_id=related_id,
            )
            session.add(model)
            session.flush()
        return model

    def get_summary(self, session: Session, project_id: int) -> ScoreSummary | None:
        return session.scalar(
            select(ScoreSummary).where(ScoreSummary.project_id == project_id)
        )

    def list_summary_details(self, session: Session, summary_id: int) -> list[ScoreDetail]:
        return list(
            session.scalars(
                select(ScoreDetail)
                .where(ScoreDetail.summary_id == summary_id)
                .order_by(ScoreDetail.indicator_no, ScoreDetail.sort_order, ScoreDetail.id)
            )
        )

    def mark_dirty(self, session: Session, project_id: int) -> ScoreSummary:
        summary = self.get_summary(session, project_id)
        if summary is None:
            summary = ScoreSummary(project_id=project_id, dirty=True)
            session.add(summary)
        summary.dirty = True
        session.flush()
        return summary

    def replace_summary(
        self,
        session: Session,
        *,
        project_id: int,
        summary_values: dict[str, Any],
        detail_values: Iterable[dict[str, Any]],
    ) -> ScoreSummary:
        summary = self.get_summary(session, project_id)
        if summary is None:
            summary = ScoreSummary(project_id=project_id)
            session.add(summary)
            session.flush()
        for field, value in summary_values.items():
            setattr(summary, field, value)
        summary.dirty = False
        session.flush()
        session.execute(delete(ScoreDetail).where(ScoreDetail.summary_id == summary.id))
        for sort_order, values in enumerate(detail_values):
            session.add(
                ScoreDetail(
                    project_id=project_id,
                    summary_id=summary.id,
                    sort_order=sort_order,
                    **values,
                )
            )
        session.flush()
        return summary
