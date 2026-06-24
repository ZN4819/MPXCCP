from __future__ import annotations

from pathlib import Path

from sqlalchemy import select

import mpxccp.models as models
from mpxccp.domain.constants import CHECK, CROSS
from mpxccp.domain.enums import MeasureUnit
from mpxccp.repositories.session import create_engine_for_path, init_database, session_scope
from mpxccp.services.basic_info_service import BasicInfoService
from mpxccp.services.device_service import DeviceService
from mpxccp.services.product_service import ProductService
from mpxccp.services.quant_service import QuantService


def _engine(tmp_path: Path):
    engine = create_engine_for_path(tmp_path / "device.sqlite3")
    init_database(engine)
    return engine


def _project_id(engine, flow_no: str = "DEV-001") -> int:
    result = BasicInfoService(engine).save_basic_info(
        flow_no=flow_no,
        system_name=f"设备测试系统-{flow_no}",
        client_name="委托方",
        assessment_org="测评机构",
    )
    assert result.success
    assert result.project_id is not None
    return result.project_id


def test_create_device_object_creates_five_details(tmp_path):
    engine = _engine(tmp_path)
    project_id = _project_id(engine)

    device = DeviceService(engine).create_object(project_id, "服务器A")
    details = DeviceService(engine).load_details(device.id)

    assert device.project_id == project_id
    assert device.name == "服务器A"
    assert len(details.all_detail_ids()) == 5
    assert details.auth.device_object_id == device.id
    assert details.remote_management.device_object_id == device.id
    assert details.access_integrity.device_object_id == device.id
    assert details.log_integrity.device_object_id == device.id
    assert details.executable_integrity.device_object_id == device.id


def test_save_device_detail_persists_units_quant_products_risk_and_dates(tmp_path):
    engine = _engine(tmp_path)
    project_id = _project_id(engine)
    service = DeviceService(engine)
    device = service.create_object(project_id, "服务器A")

    result = service.save_detail(
        device.id,
        {
            "object": {
                "name": "业务服务器",
                "device_type": "服务器",
                "location": "数据中心 A 区",
                "management_address": "10.0.0.8",
                "interview_record": "已访谈运维人员",
                "description": "承载核心业务",
            },
            "units": {
                "auth": {
                    "auth_methods": "口令,USBKey",
                    "login_channel": "本地控制台",
                    "algorithm": "SM3",
                    "risk_level": "中风险",
                    "risk_analysis": "口令策略需加强",
                    "remediation": "启用多因素鉴别",
                    "quant": {"d": CHECK, "a": CHECK, "k": CHECK, "ra": 1, "rk": 1},
                    "products": [
                        {
                            "name": "服务器密码模块",
                            "vendor": "厂商A",
                            "certificate_no": "CERT-DEV-1",
                            "level": "二级",
                            "usage": "身份鉴别",
                        }
                    ],
                },
                "remote_management": {
                    "remote_protocol": "SSH",
                    "certificate_usage": "使用运维证书",
                    "channel_protection": "专用通道",
                    "certificate_start_date": "2026-01-01",
                    "certificate_end_date": "2027-01-01",
                    "quant": {"d": CHECK, "a": CHECK, "k": CROSS, "ra": 1, "rk": 1.2},
                },
                "log_integrity": {
                    "log_source": "安全审计日志",
                    "integrity_method": "SM3 摘要",
                    "quant": {"d": CROSS, "a": "/", "k": "/", "ra": 1, "rk": 1},
                },
            },
        },
        silent=True,
    )

    reloaded = service.load_details(device.id)
    auth_quant = QuantService(engine, project_id=project_id).load(
        MeasureUnit.DEVICE_AUTH.value,
        reloaded.auth.id,
    )
    remote_quant = QuantService(engine, project_id=project_id).load(
        MeasureUnit.DEVICE_REMOTE.value,
        reloaded.remote_management.id,
    )
    products = ProductService(engine).load_products(
        project_id,
        MeasureUnit.DEVICE_AUTH.value,
        device.id,
    )

    assert result.success is True
    assert reloaded.object.name == "业务服务器"
    assert reloaded.object.management_address == "10.0.0.8"
    assert reloaded.auth.auth_methods == "口令,USBKey"
    assert reloaded.auth.risk_level == "中风险"
    assert reloaded.remote_management.extra_data["certificate_start_date"] == "2026-01-01"
    assert reloaded.remote_management.extra_data["certificate_end_date"] == "2027-01-01"
    assert auth_quant.score == 1.0
    assert (remote_quant.d, remote_quant.a, remote_quant.k, remote_quant.rk) == (
        CHECK,
        CHECK,
        CROSS,
        1.2,
    )
    assert [item.product_name for item in products] == ["服务器密码模块"]


def test_first_level_product_sets_k_fail_and_rk_1_2(tmp_path):
    engine = _engine(tmp_path)

    result = DeviceService(engine).apply_product_level_quant_rule("设备访问控制完整性", "一级")

    assert (result.d, result.a, result.k, result.rk) == (CHECK, CHECK, CROSS, 1.2)


def test_device_product_save_syncs_same_certificate_records(tmp_path):
    engine = _engine(tmp_path)
    project_id = _project_id(engine)
    service = DeviceService(engine)
    first = service.create_object(project_id, "服务器A")
    second = service.create_object(project_id, "服务器B")

    service.save_detail(
        first.id,
        {
            "units": {
                "auth": {
                    "products": [
                        {
                            "name": "旧产品",
                            "vendor": "旧厂商",
                            "certificate_no": "CERT-SYNC-DEV",
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
                            "certificate_no": "CERT-SYNC-DEV",
                            "level": "三级",
                            "usage": "登录鉴别",
                        }
                    ]
                }
            }
        },
        silent=True,
    )

    products = ProductService(engine).load_products(
        project_id,
        MeasureUnit.DEVICE_AUTH.value,
        first.id,
    )

    assert products[0].product_name == "新产品"
    assert products[0].vendor == "新厂商"
    assert products[0].product_level == "三级"


def test_delete_device_object_removes_quant_evidence_and_products_for_its_details_only(tmp_path):
    engine = _engine(tmp_path)
    project_id = _project_id(engine, "DEV-DEL-1")
    other_project_id = _project_id(engine, "DEV-DEL-2")
    service = DeviceService(engine)
    target = service.create_object(project_id, "目标服务器")
    other = service.create_object(other_project_id, "其他服务器")
    target_details = service.load_details(target.id)
    other_details = service.load_details(other.id)

    QuantService(engine, project_id=project_id).save(
        MeasureUnit.DEVICE_AUTH.value,
        target_details.auth.id,
        d=CHECK,
        a=CHECK,
        k=CHECK,
        ra=1,
        rk=1,
    )
    QuantService(engine, project_id=other_project_id).save(
        MeasureUnit.DEVICE_AUTH.value,
        other_details.auth.id,
        d=CHECK,
        a=CHECK,
        k=CHECK,
        ra=1,
        rk=1,
    )
    ProductService(engine).save_products(
        project_id,
        MeasureUnit.DEVICE_AUTH.value,
        target.id,
        [{"name": "待删产品"}],
    )
    ProductService(engine).save_products(
        other_project_id,
        MeasureUnit.DEVICE_AUTH.value,
        other.id,
        [{"name": "保留产品"}],
    )
    with session_scope(engine) as session:
        session.add(
            models.EvidenceImage(
                project_id=project_id,
                unit_type=MeasureUnit.DEVICE_AUTH.value,
                related_id=target_details.auth.id,
                file_name="1. 设备身份鉴别.png",
                original_name="source.png",
                caption="",
                checksum="abc",
            )
        )

    result = service.delete_object(target.id)

    assert result.success is True
    assert QuantService(engine, project_id=project_id).exists_for_related(
        target_details.auth.id,
        unit_type=MeasureUnit.DEVICE_AUTH.value,
    ) is False
    assert QuantService(engine, project_id=other_project_id).exists_for_related(
        other_details.auth.id,
        unit_type=MeasureUnit.DEVICE_AUTH.value,
    ) is True
    assert ProductService(engine).load_products(
        project_id,
        MeasureUnit.DEVICE_AUTH.value,
        target.id,
    ) == []
    assert [
        item.product_name
        for item in ProductService(engine).load_products(
            other_project_id,
            MeasureUnit.DEVICE_AUTH.value,
            other.id,
        )
    ] == ["保留产品"]
    with session_scope(engine) as session:
        assert session.get(models.DeviceObject, target.id) is None
        assert session.get(models.DeviceObject, other.id) is not None
        assert session.scalar(
            select(models.EvidenceImage).where(
                models.EvidenceImage.project_id == project_id,
                models.EvidenceImage.related_id == target_details.auth.id,
            )
        ) is None


def test_delete_device_object_removes_legacy_detail_related_products(tmp_path):
    engine = _engine(tmp_path)
    project_id = _project_id(engine)
    service = DeviceService(engine)
    target = service.create_object(project_id, "目标服务器")
    other = service.create_object(project_id, "其他服务器")
    with session_scope(engine) as session:
        target_auth = session.scalar(
            select(models.DeviceAuthDetail).where(
                models.DeviceAuthDetail.device_object_id == target.id
            )
        )
        target_auth.id = target.id + 1000
    target_details = service.load_details(target.id)

    ProductService(engine).save_products(
        project_id,
        MeasureUnit.DEVICE_AUTH.value,
        target_details.auth.id,
        [{"name": "旧详情关联产品"}],
    )
    ProductService(engine).save_products(
        project_id,
        MeasureUnit.DEVICE_AUTH.value,
        other.id,
        [{"name": "保留外层产品"}],
    )

    result = service.delete_object(target.id)

    assert result.success is True
    assert ProductService(engine).load_products(
        project_id,
        MeasureUnit.DEVICE_AUTH.value,
        target_details.auth.id,
    ) == []
    assert [
        item.product_name
        for item in ProductService(engine).load_products(
            project_id,
            MeasureUnit.DEVICE_AUTH.value,
            other.id,
        )
    ] == ["保留外层产品"]


def test_delete_device_object_does_not_delete_other_outer_product_when_detail_id_collides(
    tmp_path,
):
    engine = _engine(tmp_path)
    project_id = _project_id(engine)
    service = DeviceService(engine)
    target = service.create_object(project_id, "目标服务器")
    with session_scope(engine) as session:
        target_auth = session.scalar(
            select(models.DeviceAuthDetail).where(
                models.DeviceAuthDetail.device_object_id == target.id
            )
        )
        target_auth.id = target.id + 1000
    target_details = service.load_details(target.id)
    with session_scope(engine) as session:
        session.add(
            models.DeviceObject(
                id=target_details.auth.id,
                project_id=project_id,
                name="ID 碰撞服务器",
                sort_order=99,
            )
        )
    ProductService(engine).save_products(
        project_id,
        MeasureUnit.DEVICE_AUTH.value,
        target_details.auth.id,
        [{"name": "碰撞设备外层产品"}],
    )

    result = service.delete_object(target.id)

    assert result.success is True
    assert "ambiguous_device_detail_product:auth" in result.warnings
    assert [
        item.product_name
        for item in ProductService(engine).load_products(
            project_id,
            MeasureUnit.DEVICE_AUTH.value,
            target_details.auth.id,
        )
    ] == ["碰撞设备外层产品"]


def test_delete_device_object_tolerates_missing_legacy_detail_rows(tmp_path):
    engine = _engine(tmp_path)
    project_id = _project_id(engine)
    service = DeviceService(engine)
    device = service.create_object(project_id, "旧库服务器")
    details = service.load_details(device.id)
    with session_scope(engine) as session:
        stale_detail = session.get(models.DeviceLogIntegrityDetail, details.log_integrity.id)
        session.delete(stale_detail)

    result = service.delete_object(device.id)

    assert result.success is True
    assert "missing_device_detail:log_integrity" in result.warnings
    with session_scope(engine) as session:
        assert session.get(models.DeviceObject, device.id) is None
