from __future__ import annotations

from pathlib import Path

from mpxccp.domain.constants import CHECK
from mpxccp.domain.enums import MeasureUnit, SecurityLayer
from mpxccp.repositories.session import create_engine_for_path, init_database
from mpxccp.services.basic_info_service import BasicInfoService
from mpxccp.services.physical_service import PhysicalService
from mpxccp.services.quant_service import QuantService
from mpxccp.services.scoring_service import ScoringService


def _engine(tmp_path: Path):
    engine = create_engine_for_path(tmp_path / "scoring.sqlite3")
    init_database(engine)
    return engine


def _project_id(engine) -> int:
    result = BasicInfoService(engine).save_basic_info(
        flow_no="SCORE-001",
        system_name="评分测试系统",
        client_name="委托方",
        assessment_org="测评机构",
    )
    assert result.success
    assert result.project_id is not None
    return result.project_id


def test_scoring_initializes_41_indicators(tmp_path):
    engine = _engine(tmp_path)
    service = ScoringService(engine)

    service.ensure_indicators()
    indicators = service.list_indicators()

    assert len(indicators) == 41
    assert [item.no for item in indicators] == list(range(1, 42))
    assert {8, 12, 17}.issubset(
        {item.no for item in indicators if item.always_not_applicable}
    )


def test_scoring_refresh_creates_missing_empty_quant_record(tmp_path):
    engine = _engine(tmp_path)
    project_id = _project_id(engine)
    physical = PhysicalService(engine)
    obj = physical.create_object(project_id, "主机房")
    detail_id = physical.load_details(obj.id).auth.id
    quant = QuantService(engine, project_id=project_id)

    assert quant.load(MeasureUnit.PHYSICAL_AUTH.value, detail_id).record_id is None

    ScoringService(engine).refresh_technical_domain(project_id, SecurityLayer.PHYSICAL.value)

    created = quant.load(MeasureUnit.PHYSICAL_AUTH.value, detail_id)
    assert created.record_id is not None
    assert created.d == ""
    assert created.score is None


def test_scoring_persists_summary_and_indicator_details(tmp_path):
    engine = _engine(tmp_path)
    project_id = _project_id(engine)
    physical = PhysicalService(engine)
    obj = physical.create_object(project_id, "主机房")
    detail_id = physical.load_details(obj.id).auth.id
    quant = QuantService(engine, project_id=project_id)
    quant.save(
        MeasureUnit.PHYSICAL_AUTH.value,
        detail_id,
        d=CHECK,
        a=CHECK,
        k=CHECK,
        ra=1,
        rk=1,
    )

    service = ScoringService(engine)
    service.save_management_score(project_id, 23, "符合")
    service.save_management_score(project_id, 24, "部分符合")
    service.save_management_score(project_id, 25, "不符合")
    service.save_management_score(project_id, 26, "不适用")
    summary = service.refresh_technical_domain(project_id, SecurityLayer.PHYSICAL.value)

    detail_by_no = {detail.indicator_no: detail for detail in summary.details}
    assert summary.project_id == project_id
    assert summary.total_allocated_score == 100.0
    assert summary.total_earned_score == summary.total_score
    assert summary.total_lost_score == round(100.0 - summary.total_score, 2)
    assert summary.compliant_count >= 1
    assert summary.partial_count >= 1
    assert summary.non_compliant_count >= 1
    assert detail_by_no[1].score == 1.0
    assert detail_by_no[1].effective_object_count == 1
    assert detail_by_no[8].not_applicable is True
    assert detail_by_no[23].score == 1.0
    assert detail_by_no[24].score == 0.5
    assert detail_by_no[25].score == 0.0
    assert detail_by_no[26].not_applicable is True


def test_mark_dirty_is_persisted_until_recalculation(tmp_path):
    engine = _engine(tmp_path)
    project_id = _project_id(engine)
    service = ScoringService(engine)

    service.mark_dirty(project_id)
    dirty = service.load_summary(project_id)

    assert dirty is not None
    assert dirty.dirty is True

    recalculated = service.calculate_and_persist_summary(project_id)

    assert recalculated.dirty is False
