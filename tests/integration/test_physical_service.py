from __future__ import annotations

from pathlib import Path

from sqlalchemy import select

import mpxccp.models as models
from mpxccp.domain.constants import CHECK, CROSS
from mpxccp.domain.enums import MeasureUnit
from mpxccp.repositories.session import create_engine_for_path, init_database, session_scope
from mpxccp.services.basic_info_service import BasicInfoService
from mpxccp.services.physical_service import PhysicalService
from mpxccp.services.product_service import ProductService
from mpxccp.services.quant_service import QuantService


def _engine(tmp_path: Path):
    engine = create_engine_for_path(tmp_path / "physical.sqlite3")
    init_database(engine)
    return engine


def _project_id(engine, flow_no: str = "PHY-001") -> int:
    result = BasicInfoService(engine).save_basic_info(
        flow_no=flow_no,
        system_name=f"物理测试系统-{flow_no}",
        client_name="委托方",
        assessment_org="测评机构",
    )
    assert result.success
    assert result.project_id is not None
    return result.project_id


def test_create_physical_object_creates_three_details(tmp_path):
    engine = _engine(tmp_path)
    project_id = _project_id(engine)

    obj = PhysicalService(engine).create_object(project_id, "机房A")
    details = PhysicalService(engine).load_details(obj.id)

    assert obj.project_id == project_id
    assert obj.name == "机房A"
    assert details.auth is not None
    assert details.access_integrity is not None
    assert details.video_integrity is not None
    assert details.auth.physical_object_id == obj.id
    assert details.access_integrity.physical_object_id == obj.id
    assert details.video_integrity.physical_object_id == obj.id


def test_save_physical_detail_persists_object_units_quant_products_and_risk(tmp_path):
    engine = _engine(tmp_path)
    project_id = _project_id(engine)
    service = PhysicalService(engine)
    obj = service.create_object(project_id, "机房A")

    result = service.save_detail(
        obj.id,
        {
            "object": {
                "name": "主机房",
                "location": "一层东侧",
                "access_control_system": "门禁系统 V1",
                "video_system": "视频系统 V2",
                "interview_record": "已访谈值守人员",
            },
            "units": {
                "auth": {
                    "auth_methods": "指纹,口令",
                    "crypto_usage": "已使用",
                    "algorithm": "SM4",
                    "compliance_status": "符合",
                    "product_compliance": "符合",
                    "risk_level": "高风险",
                    "risk_analysis": "存在身份鉴别风险",
                    "remediation": "完善值守和登记制度",
                    "quant": {"d": CHECK, "a": CHECK, "k": CHECK, "ra": 1, "rk": 1},
                    "products": [
                        {
                            "name": "门禁密码模块",
                            "vendor": "厂商A",
                            "certificate_no": "CERT-PHY-1",
                            "level": "二级",
                            "usage": "身份鉴别",
                        }
                    ],
                },
                "access_integrity": {
                    "implementation": "门禁记录完整",
                    "algorithm": "SM3",
                    "risk_level": "低风险",
                    "risk_analysis": "门禁记录可校验",
                    "remediation": "持续留存记录",
                    "quant": {"d": CHECK, "a": CHECK, "k": CHECK, "ra": 1, "rk": 1},
                },
                "video_integrity": {
                    "implementation": "视频记录完整",
                    "algorithm": "SM3",
                    "risk_level": "无风险",
                    "risk_analysis": "",
                    "remediation": "",
                    "quant": {"d": CROSS, "a": "/", "k": "/", "ra": 1, "rk": 1},
                },
            },
        },
        silent=True,
    )

    reloaded = service.load_details(obj.id)
    quant = QuantService(engine, project_id=project_id)
    products = ProductService(engine).load_products(
        project_id,
        MeasureUnit.PHYSICAL_AUTH.value,
        obj.id,
    )

    assert result.success is True
    assert reloaded.object.name == "主机房"
    assert reloaded.object.location == "一层东侧"
    assert reloaded.auth.auth_methods == "指纹,口令"
    assert reloaded.auth.risk_level == "高风险"
    assert reloaded.access_integrity.implementation == "门禁记录完整"
    assert quant.load(MeasureUnit.PHYSICAL_AUTH.value, reloaded.auth.id).score == 1.0
    video_quant = quant.load(
        MeasureUnit.PHYSICAL_VIDEO_INTEGRITY.value,
        reloaded.video_integrity.id,
    )
    assert video_quant.d == CROSS
    assert [item.product_name for item in products] == ["门禁密码模块"]


def test_physical_auth_detail_persists_extra_identity_and_mitigation_fields(tmp_path):
    engine = _engine(tmp_path)
    project_id = _project_id(engine)
    service = PhysicalService(engine)
    obj = service.create_object(project_id, "机房A")

    service.save_detail(
        obj.id,
        {
            "units": {
                "auth": {
                    "auth_methods": "指纹,其他:虹膜",
                    "crypto_usage": "已使用",
                    "guarded": "是",
                    "registered": "是",
                    "accompanied": "否",
                    "realtime_monitoring": "是",
                    "mitigation_available": True,
                    "mitigation_note": "已增加双人值守和实时监控",
                    "mitigated_level": "低风险",
                }
            }
        },
        silent=True,
    )

    auth = service.load_details(obj.id).auth

    assert auth.auth_methods == "指纹,其他:虹膜"
    assert auth.extra_data["guarded"] == "是"
    assert auth.extra_data["registered"] == "是"
    assert auth.extra_data["accompanied"] == "否"
    assert auth.extra_data["realtime_monitoring"] == "是"
    assert auth.extra_data["mitigation_available"] is True
    assert auth.extra_data["mitigation_note"] == "已增加双人值守和实时监控"
    assert auth.extra_data["mitigated_level"] == "低风险"


def test_physical_product_save_syncs_same_certificate_records(tmp_path):
    engine = _engine(tmp_path)
    project_id = _project_id(engine)
    service = PhysicalService(engine)
    first = service.create_object(project_id, "机房A")
    second = service.create_object(project_id, "机房B")

    service.save_detail(
        first.id,
        {
            "units": {
                "auth": {
                    "products": [
                        {
                            "name": "旧产品",
                            "vendor": "旧厂商",
                            "certificate_no": "CERT-SYNC",
                            "level": "二级",
                            "usage": "身份鉴别",
                        }
                    ]
                }
            }
        },
        silent=True,
    )
    service.save_detail(
        second.id,
        {
            "units": {
                "auth": {
                    "products": [
                        {
                            "name": "新产品",
                            "vendor": "新厂商",
                            "certificate_no": "CERT-SYNC",
                            "level": "三级",
                            "usage": "门禁",
                        }
                    ]
                }
            }
        },
        silent=True,
    )

    products = ProductService(engine).load_products(
        project_id,
        MeasureUnit.PHYSICAL_AUTH.value,
        first.id,
    )

    assert products[0].product_name == "新产品"
    assert products[0].vendor == "新厂商"
    assert products[0].product_level == "三级"


def test_quant_exists_for_related_requires_project_scope(tmp_path):
    engine = _engine(tmp_path)
    project_id = _project_id(engine)
    obj = PhysicalService(engine).create_object(project_id, "机房A")
    detail = PhysicalService(engine).load_details(obj.id).auth
    QuantService(engine, project_id=project_id).save(
        MeasureUnit.PHYSICAL_AUTH.value,
        detail.id,
        d=CHECK,
        a=CHECK,
        k=CHECK,
        ra=1,
        rk=1,
    )

    try:
        QuantService(engine).exists_for_related(
            detail.id,
            unit_type=MeasureUnit.PHYSICAL_AUTH.value,
        )
    except ValueError as exc:
        assert "project_id is required" in str(exc)
    else:
        raise AssertionError("exists_for_related should require project_id")


def test_delete_physical_object_removes_quant_evidence_and_products_for_its_details_only(tmp_path):
    engine = _engine(tmp_path)
    project_id = _project_id(engine, "PHY-DEL-1")
    other_project_id = _project_id(engine, "PHY-DEL-2")
    service = PhysicalService(engine)
    target = service.create_object(project_id, "目标机房")
    other = service.create_object(other_project_id, "其他机房")
    target_details = service.load_details(target.id)
    other_details = service.load_details(other.id)

    QuantService(engine, project_id=project_id).save(
        MeasureUnit.PHYSICAL_AUTH.value,
        target_details.auth.id,
        d=CHECK,
        a=CHECK,
        k=CHECK,
        ra=1,
        rk=1,
    )
    QuantService(engine, project_id=other_project_id).save(
        MeasureUnit.PHYSICAL_AUTH.value,
        other_details.auth.id,
        d=CHECK,
        a=CHECK,
        k=CHECK,
        ra=1,
        rk=1,
    )
    ProductService(engine).save_products(
        project_id,
        MeasureUnit.PHYSICAL_AUTH.value,
        target.id,
        [{"name": "待删产品"}],
    )
    ProductService(engine).save_products(
        other_project_id,
        MeasureUnit.PHYSICAL_AUTH.value,
        other.id,
        [{"name": "保留产品"}],
    )
    with session_scope(engine) as session:
        session.add(
            models.EvidenceImage(
                project_id=project_id,
                unit_type=MeasureUnit.PHYSICAL_AUTH.value,
                related_id=target_details.auth.id,
                file_name="1. 物理身份鉴别.png",
                original_name="source.png",
                caption="",
                checksum="abc",
            )
        )

    result = service.delete_object(target.id)

    assert result.success is True
    assert QuantService(engine, project_id=project_id).exists_for_related(
        target_details.auth.id,
        unit_type=MeasureUnit.PHYSICAL_AUTH.value,
    ) is False
    assert QuantService(engine, project_id=other_project_id).exists_for_related(
        other_details.auth.id,
        unit_type=MeasureUnit.PHYSICAL_AUTH.value,
    ) is True
    assert ProductService(engine).load_products(
        project_id,
        MeasureUnit.PHYSICAL_AUTH.value,
        target.id,
    ) == []
    assert [item.product_name for item in ProductService(engine).load_products(
        other_project_id,
        MeasureUnit.PHYSICAL_AUTH.value,
        other.id,
    )] == ["保留产品"]
    with session_scope(engine) as session:
        assert session.get(models.PhysicalObject, target.id) is None
        assert session.get(models.PhysicalObject, other.id) is not None
        assert session.scalar(
            select(models.EvidenceImage).where(
                models.EvidenceImage.project_id == project_id,
                models.EvidenceImage.related_id == target_details.auth.id,
            )
        ) is None


def test_delete_physical_object_tolerates_missing_legacy_detail_rows(tmp_path):
    engine = _engine(tmp_path)
    project_id = _project_id(engine)
    service = PhysicalService(engine)
    obj = service.create_object(project_id, "旧库机房")
    details = service.load_details(obj.id)
    with session_scope(engine) as session:
        stale_detail = session.get(
            models.PhysicalAccessIntegrityDetail,
            details.access_integrity.id,
        )
        session.delete(stale_detail)

    result = service.delete_object(obj.id)

    assert result.success is True
    assert "missing_physical_detail:access_integrity" in result.warnings
    with session_scope(engine) as session:
        assert session.get(models.PhysicalObject, obj.id) is None
