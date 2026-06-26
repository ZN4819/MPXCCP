from __future__ import annotations

from pathlib import Path

from sqlalchemy import func, select

import mpxccp.models as models
from mpxccp.repositories.session import create_engine_for_path, init_database, session_scope
from mpxccp.services.basic_info_service import BasicInfoService
from mpxccp.services.integrity_service import IntegrityService


def _engine(tmp_path: Path):
    engine = create_engine_for_path(tmp_path / "task16-integrity.sqlite3")
    init_database(engine)
    return engine


def _project(engine, flow_no: str = "INT-001", system_name: str = "完整性系统") -> int:
    result = BasicInfoService(engine).save_basic_info(
        flow_no=flow_no,
        system_name=system_name,
        client_name="Client",
        assessment_org="Org",
    )
    assert result.success
    assert result.project_id is not None
    return result.project_id


def _physical_object_with_detail(engine, project_id: int) -> tuple[int, int]:
    with session_scope(engine) as session:
        obj = models.PhysicalObject(project_id=project_id, name="机房")
        session.add(obj)
        session.flush()
        detail = models.PhysicalAuthDetail(
            project_id=project_id,
            physical_object_id=obj.id,
            requirement="身份鉴别",
        )
        session.add(detail)
        session.flush()
        return obj.id, detail.id


def _physical_object_without_detail(engine, project_id: int) -> int:
    with session_scope(engine) as session:
        obj = models.PhysicalObject(project_id=project_id, name="备用机房")
        session.add(obj)
        session.flush()
        return obj.id


def _device_object_without_detail(engine, project_id: int) -> int:
    with session_scope(engine) as session:
        obj = models.DeviceObject(project_id=project_id, name="服务器")
        session.add(obj)
        session.flush()
        return obj.id


def _network_channel_without_detail(engine, project_id: int) -> int:
    with session_scope(engine) as session:
        subsystem = models.NetworkSubsystem(project_id=project_id, name="网络子系统")
        session.add(subsystem)
        session.flush()
        channel = models.NetworkChannel(
            project_id=project_id,
            network_subsystem_id=subsystem.id,
            name="通信信道",
        )
        session.add(channel)
        session.flush()
        return channel.id


def _application_business_action_without_detail(engine, project_id: int) -> int:
    with session_scope(engine) as session:
        subsystem = models.ApplicationSubsystem(project_id=project_id, name="应用子系统")
        session.add(subsystem)
        session.flush()
        action = models.BusinessAction(
            project_id=project_id,
            application_subsystem_id=subsystem.id,
            name="交易确认",
        )
        session.add(action)
        session.flush()
        return action.id


def _shared_count(engine, model: type, project_id: int) -> int:
    with session_scope(engine) as session:
        return session.scalar(
            select(func.count()).select_from(model).where(model.project_id == project_id)
        )


def test_integrity_report_detects_orphan_quant_without_modifying_data(tmp_path):
    engine = _engine(tmp_path)
    project_id = _project(engine)
    with session_scope(engine) as session:
        orphan = models.QuantitativeAssessment(
            project_id=project_id,
            unit_type="物理访问身份鉴别",
            related_id=999,
            d_value="√",
        )
        session.add(orphan)
        session.flush()
        orphan_id = orphan.id

    report = IntegrityService(engine).check_project(project_id)

    assert any(item.kind == "orphan_quant" for item in report.items)
    with session_scope(engine) as session:
        assert session.get(models.QuantitativeAssessment, orphan_id) is not None
    assert _shared_count(engine, models.QuantitativeAssessment, project_id) == 1


def test_integrity_report_accepts_detail_and_compatible_outer_product_references(tmp_path):
    engine = _engine(tmp_path)
    project_id = _project(engine)
    object_id, detail_id = _physical_object_with_detail(engine, project_id)
    with session_scope(engine) as session:
        session.add_all(
            [
                models.QuantitativeAssessment(
                    project_id=project_id,
                    unit_type="物理访问身份鉴别",
                    related_id=detail_id,
                ),
                models.EvidenceImage(
                    project_id=project_id,
                    unit_type="物理访问身份鉴别",
                    related_id=detail_id,
                    file_name="1. 物理身份鉴别.png",
                    original_name="source.png",
                    checksum="abc",
                ),
                models.CryptoProduct(
                    project_id=project_id,
                    unit_type="物理访问身份鉴别",
                    related_id=detail_id,
                    product_name="详情产品",
                ),
                models.CryptoProduct(
                    project_id=project_id,
                    unit_type="物理访问身份鉴别",
                    related_id=object_id,
                    product_name="历史外层产品",
                ),
            ]
        )

    report = IntegrityService(engine).check_project(project_id)

    assert report.items == []


def test_integrity_report_detects_cross_project_and_unknown_unit_references(tmp_path):
    engine = _engine(tmp_path)
    first_id = _project(engine, "INT-A", "A系统")
    second_id = _project(engine, "INT-B", "B系统")
    _, second_detail_id = _physical_object_with_detail(engine, second_id)
    with session_scope(engine) as session:
        session.add_all(
            [
                models.EvidenceImage(
                    project_id=first_id,
                    unit_type="物理访问身份鉴别",
                    related_id=second_detail_id,
                    file_name="cross.png",
                    original_name="cross.png",
                    checksum="cross",
                ),
                models.CryptoProduct(
                    project_id=first_id,
                    unit_type="未知测评单元",
                    related_id=1,
                    product_name="未知产品",
                ),
                models.CryptoProduct(
                    project_id=first_id,
                    unit_type="物理访问身份鉴别",
                    related_id=999,
                    product_name="孤儿产品",
                ),
            ]
        )

    report = IntegrityService(engine).check_project(first_id)
    kinds = {item.kind for item in report.items}

    assert {"cross_project_evidence", "unknown_unit_type", "orphan_product"} <= kinds
    assert _shared_count(engine, models.EvidenceImage, first_id) == 1
    assert _shared_count(engine, models.CryptoProduct, first_id) == 2


def test_integrity_report_detects_orphan_evidence_and_empty_association(tmp_path):
    engine = _engine(tmp_path)
    project_id = _project(engine)
    with session_scope(engine) as session:
        session.add_all(
            [
                models.EvidenceImage(
                    project_id=project_id,
                    unit_type="设备登录身份鉴别",
                    related_id=404,
                    file_name="missing.png",
                    original_name="missing.png",
                    checksum="missing",
                ),
                models.CryptoProduct(
                    project_id=project_id,
                    unit_type="",
                    related_id=0,
                    product_name="空关联产品",
                ),
            ]
        )

    report = IntegrityService(engine).check_project(project_id)
    kinds = {item.kind for item in report.items}

    assert {"orphan_evidence", "empty_association"} <= kinds
    assert _shared_count(engine, models.EvidenceImage, project_id) == 1
    assert _shared_count(engine, models.CryptoProduct, project_id) == 1


def test_integrity_report_accepts_outer_products_across_technical_domains(tmp_path):
    engine = _engine(tmp_path)
    project_id = _project(engine)
    device_id = _device_object_without_detail(engine, project_id)
    channel_id = _network_channel_without_detail(engine, project_id)
    action_id = _application_business_action_without_detail(engine, project_id)
    with session_scope(engine) as session:
        session.add_all(
            [
                models.CryptoProduct(
                    project_id=project_id,
                    unit_type="设备登录身份鉴别",
                    related_id=device_id,
                    product_name="设备外层产品",
                ),
                models.CryptoProduct(
                    project_id=project_id,
                    unit_type="通信实体身份鉴别",
                    related_id=channel_id,
                    product_name="网络外层产品",
                ),
                models.CryptoProduct(
                    project_id=project_id,
                    unit_type="关键业务行为不可否认性",
                    related_id=action_id,
                    product_name="应用外层产品",
                ),
            ]
        )

    report = IntegrityService(engine).check_project(project_id)

    assert report.items == []


def test_integrity_report_rejects_quant_and_evidence_pointing_to_outer_object(tmp_path):
    engine = _engine(tmp_path)
    project_id = _project(engine)
    _, detail_id = _physical_object_with_detail(engine, project_id)
    object_id = _physical_object_without_detail(engine, project_id)
    assert object_id != detail_id
    with session_scope(engine) as session:
        session.add_all(
            [
                models.QuantitativeAssessment(
                    project_id=project_id,
                    unit_type="物理访问身份鉴别",
                    related_id=object_id,
                ),
                models.EvidenceImage(
                    project_id=project_id,
                    unit_type="物理访问身份鉴别",
                    related_id=object_id,
                    file_name="outer.png",
                    original_name="outer.png",
                    checksum="outer",
                ),
            ]
        )

    report = IntegrityService(engine).check_project(project_id)
    kinds = {item.kind for item in report.items}

    assert {"orphan_quant", "orphan_evidence"} <= kinds


def test_resolve_project_scope_groups_detail_and_shared_references(tmp_path):
    engine = _engine(tmp_path)
    project_id = _project(engine)
    object_id, detail_id = _physical_object_with_detail(engine, project_id)
    with session_scope(engine) as session:
        session.add_all(
            [
                models.QuantitativeAssessment(
                    project_id=project_id,
                    unit_type="物理访问身份鉴别",
                    related_id=detail_id,
                ),
                models.CryptoProduct(
                    project_id=project_id,
                    unit_type="物理访问身份鉴别",
                    related_id=object_id,
                    product_name="历史外层产品",
                ),
            ]
        )

    scope = IntegrityService(engine).resolve_project_scope(project_id)

    assert detail_id in scope.detail_references["物理访问身份鉴别"]
    assert object_id in scope.compatible_product_references["物理访问身份鉴别"]
    assert detail_id in scope.quant_references["物理访问身份鉴别"]
    assert object_id in scope.product_references["物理访问身份鉴别"]
