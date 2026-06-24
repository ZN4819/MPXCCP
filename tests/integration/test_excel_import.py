from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import func, select

import mpxccp.models as models
from mpxccp.domain.constants import CHECK, CROSS
from mpxccp.domain.enums import MeasureUnit
from mpxccp.integration.excel.import_reader import (
    ImportCellContext,
    ImportDataError,
    ImportReader,
)
from mpxccp.repositories.session import create_engine_for_path, init_database, session_scope
from mpxccp.services.application_service import ApplicationService
from mpxccp.services.basic_info_service import BasicInfoService
from mpxccp.services.device_service import DeviceService
from mpxccp.services.import_service import ImportService
from mpxccp.services.network_service import NetworkService
from mpxccp.services.physical_service import PhysicalService
from mpxccp.services.product_service import ProductService
from mpxccp.services.quant_service import QuantService
from tests.fixtures.workbook_builders import WorkbookBuilders


def _engine(tmp_path: Path):
    engine = create_engine_for_path(tmp_path / "excel-import.sqlite3")
    init_database(engine)
    return engine


def _project_id(engine, flow_no: str = "IMP-001") -> int:
    result = BasicInfoService(engine).save_basic_info(
        flow_no=flow_no,
        system_name=f"导入测试系统 {flow_no}",
        client_name="委托方",
        assessment_org="测评机构",
    )
    assert result.success
    assert result.project_id is not None
    return result.project_id


def test_import_rolls_back_previous_rows_on_invalid_ra(tmp_path):
    engine = _engine(tmp_path)
    project_id = _project_id(engine)
    workbook = WorkbookBuilders().physical_workbook_with_invalid_ra()

    result = ImportService(engine).import_interview_template(project_id, workbook, mode="替换")

    assert result.success is False
    assert "物理和环境安全" in result.message
    assert "第3行" in result.message
    assert "第15列" in result.message
    assert "Ra" in result.message
    assert PhysicalService(engine).list_objects(project_id) == []
    with session_scope(engine) as session:
        assert session.scalar(select(func.count()).select_from(models.QuantitativeAssessment)) == 0
        assert session.scalar(select(func.count()).select_from(models.CryptoProduct)) == 0


def test_replace_mode_imports_physical_rows_quant_and_products(tmp_path):
    engine = _engine(tmp_path)
    project_id = _project_id(engine)

    result = ImportService(engine).import_interview_template(
        project_id,
        WorkbookBuilders().physical_workbook(),
        mode="替换",
    )

    assert result.success is True
    assert "未找到'系统基本信息'工作表，已跳过" in result.warnings
    objects = PhysicalService(engine).list_objects(project_id)
    assert [item.name for item in objects] == ["主机房"]
    details = PhysicalService(engine).load_details(objects[0].id)
    quant = QuantService(engine, project_id=project_id).load(
        MeasureUnit.PHYSICAL_AUTH.value,
        details.auth.id,
    )
    products = ProductService(engine).load_products(
        project_id,
        MeasureUnit.PHYSICAL_AUTH.value,
        objects[0].id,
    )
    access_products = ProductService(engine).load_products(
        project_id,
        MeasureUnit.PHYSICAL_ACCESS_INTEGRITY.value,
        objects[0].id,
    )
    video_products = ProductService(engine).load_products(
        project_id,
        MeasureUnit.PHYSICAL_VIDEO_INTEGRITY.value,
        objects[0].id,
    )
    assert details.object.location == "一层东侧"
    assert details.auth.auth_methods == "口令、门禁卡"
    assert details.auth.extra_data["mitigated_level"] == "低风险"
    assert (quant.d, quant.a, quant.k, quant.ra) == (CHECK, CHECK, CHECK, 1.2)
    assert [item.product_name for item in products] == ["机房身份鉴别模块"]
    assert products[0].vendor == "厂商A"
    assert products[0].certificate_no == "CERT-主机房"
    assert [item.product_name for item in access_products] == ["主机房门禁完整性产品"]
    assert [item.product_name for item in video_products] == ["主机房视频完整性产品"]


def test_basic_info_import_rebuilds_empty_subsystems_and_crypto_info(tmp_path):
    engine = _engine(tmp_path)
    project_id = _project_id(engine)
    BasicInfoService(engine).sync_subsystems(project_id, ["旧子系统"])

    result = ImportService(engine).import_interview_template(
        project_id,
        WorkbookBuilders().basic_info_workbook(subsystems=""),
        mode="替换",
    )

    assert result.success is True
    loaded = BasicInfoService(engine).load_full_basic_info(project_id)
    assert loaded.payload["basic_info"]["flow_no"] == "IMP-FLOW"
    assert loaded.payload["basic_info"]["system_name"] == "导入后的系统"
    assert loaded.payload["subsystems"] == []
    assert loaded.payload["crypto_application_info"]["last_assessment_status"] == "已做过密评"
    assert loaded.payload["crypto_application_info"]["last_assessment_org"] == "历史测评机构"
    assert loaded.payload["crypto_application_info"]["last_assessment_date"] == "2025-06-01"
    assert loaded.payload["crypto_application_info"]["last_assessment_score"] == "82"
    assert loaded.payload["crypto_application_info"]["review_date"] == "2025-12-01"


def test_append_mode_imports_only_new_network_and_application_subsystems(tmp_path):
    engine = _engine(tmp_path)
    project_id = _project_id(engine)
    BasicInfoService(engine).sync_subsystems(project_id, ["已有子系统"])
    NetworkService(engine).sync_from_basic_subsystems(project_id)
    ApplicationService(engine).sync_from_basic_subsystems(project_id)

    result = ImportService(engine).import_interview_template(
        project_id,
        WorkbookBuilders().network_application_with_existing_and_new_subsystems(),
        mode="追加",
    )

    assert result.success is True
    assert "追加模式：仅导入网络和应用模块的新子系统数据" in result.warnings
    network = NetworkService(engine)
    application = ApplicationService(engine)
    network_by_name = {item.name: item for item in network.list_subsystems(project_id)}
    application_by_name = {item.name: item for item in application.list_subsystems(project_id)}
    assert set(network_by_name) == {"已有子系统", "新子系统"}
    assert network.list_channels(network_by_name["已有子系统"].id) == []
    assert [item.name for item in network.list_channels(network_by_name["新子系统"].id)] == [
        "新信道"
    ]
    assert application.list_users(application_by_name["已有子系统"].id) == []
    assert [item.name for item in application.list_users(application_by_name["新子系统"].id)] == [
        "新用户"
    ]


def test_replace_network_import_clears_stale_application_channel_references(tmp_path):
    engine = _engine(tmp_path)
    project_id = _project_id(engine)
    BasicInfoService(engine).sync_subsystems(project_id, ["业务系统"])
    network = NetworkService(engine)
    application = ApplicationService(engine)
    network.sync_from_basic_subsystems(project_id)
    application.sync_from_basic_subsystems(project_id)
    network_subsystem = network.list_subsystems(project_id)[0]
    old_channel = network.create_channel(network_subsystem.id, "旧信道")
    app_subsystem = application.list_subsystems(project_id)[0]
    data = application.create_important_data(app_subsystem.id, "交易数据", "业务数据")
    application.save_important_data_detail(
        data.id,
        {
            "object": {"related_channel_id": old_channel.id},
            "units": {
                "transport_confidentiality": {"network_channel_id": old_channel.id},
                "transport_integrity": {"network_channel_id": old_channel.id},
            },
        },
    )

    result = ImportService(engine).import_interview_template(
        project_id,
        WorkbookBuilders().network_workbook("新网络", "新信道"),
        mode="替换",
    )

    assert result.success is True
    with session_scope(engine) as session:
        old_channel_name = session.scalar(
            select(models.NetworkChannel.name).where(
                models.NetworkChannel.project_id == project_id,
                models.NetworkChannel.name == "旧信道",
            )
        )
        app_data = session.get(models.ImportantData, data.id)
        transport_conf = session.scalar(
            select(models.DataTransportConfidentialityDetail).where(
                models.DataTransportConfidentialityDetail.important_data_id == data.id
            )
        )
        transport_integrity = session.scalar(
            select(models.DataTransportIntegrityDetail).where(
                models.DataTransportIntegrityDetail.important_data_id == data.id
            )
        )
        assert old_channel_name is None
        assert app_data is not None
        assert app_data.related_channel_id is None
        assert transport_conf.network_channel_id is None
        assert transport_integrity.network_channel_id is None
    assert [item.name for item in network.list_subsystems(project_id)] == ["新网络"]
    new_subsystem = network.list_subsystems(project_id)[0]
    assert [item.name for item in network.list_channels(new_subsystem.id)] == ["新信道"]


def test_application_imports_important_data_business_quant_and_products(tmp_path):
    engine = _engine(tmp_path)
    project_id = _project_id(engine)

    result = ImportService(engine).import_interview_template(
        project_id,
        WorkbookBuilders().application_workbook_with_data_and_business(),
        mode="替换",
    )

    assert result.success is True
    application = ApplicationService(engine)
    subsystem = application.list_subsystems(project_id)[0]
    data = application.list_important_data(subsystem.id)[0]
    action = application.list_business_actions(subsystem.id)[0]
    data_details = application.load_important_data_details(data.id)
    action_details = application.load_business_action_details(action.id)
    quant = QuantService(engine, project_id=project_id)
    data_products = ProductService(engine).load_products(
        project_id,
        MeasureUnit.DATA_TRANSPORT_CONFIDENTIALITY.value,
        data.id,
    )
    action_products = ProductService(engine).load_products(
        project_id,
        MeasureUnit.BUSINESS_ACTION_NON_REPUDIATION.value,
        action.id,
    )

    assert data.name == "交易数据"
    assert data.extra_data["interview_record"] == "业务系统重要数据访谈"
    assert action.name == "订单提交"
    assert data_details.transport_confidentiality.extra_data["implementation_status"] == "已实现"
    assert data_details.transport_confidentiality.extra_data["key_management"] == "集中密钥管理"
    assert action_details.non_repudiation.extra_data["mechanism_description"] == (
        "已使用签名和时间戳"
    )
    assert (
        quant.load(
            MeasureUnit.DATA_TRANSPORT_CONFIDENTIALITY.value,
            data_details.transport_confidentiality.id,
        ).d
        == CHECK
    )
    assert (
        quant.load(
            MeasureUnit.DATA_STORAGE_INTEGRITY.value,
            data_details.storage_integrity.id,
        ).d
        == CROSS
    )
    assert (
        quant.load(
            MeasureUnit.DATA_TRANSPORT_INTEGRITY.value,
            data_details.transport_integrity.id,
        ).d
        == CHECK
    )
    assert (
        quant.load(
            MeasureUnit.BUSINESS_ACTION_NON_REPUDIATION.value,
            action_details.non_repudiation.id,
        ).d
        == CHECK
    )
    assert [item.product_name for item in data_products] == ["交易数据传输机密性产品"]
    assert [item.product_name for item in action_products] == ["订单提交签名产品"]


def test_device_import_splits_integrity_product_usage_and_level(tmp_path):
    engine = _engine(tmp_path)
    project_id = _project_id(engine)

    result = ImportService(engine).import_interview_template(
        project_id,
        WorkbookBuilders().device_workbook_with_split_integrity_status(),
        mode="替换",
    )

    assert result.success is True
    device = DeviceService(engine).list_objects(project_id)[0]
    details = DeviceService(engine).load_details(device.id)
    products = ProductService(engine).load_products(
        project_id,
        MeasureUnit.DEVICE_ACCESS_INTEGRITY.value,
        device.id,
    )
    assert details.access_integrity.extra_data["product_used"] == "是"
    assert details.access_integrity.extra_data["product_level"] == "二级"
    assert details.access_integrity.implementation == ""
    assert [item.product_name for item in products] == ["设备访问控制产品"]


def test_reader_parses_products_quant_values_and_contextual_errors():
    reader = ImportReader()

    products = reader.parse_product_text(
        "门禁模块(厂商A,证书:CERT-1,等级:二级,用途:身份鉴别)；裸产品"
    )
    quant = reader.parse_quant_values(
        d="√",
        a="勾",
        k="×",
        ra="",
        rk="1.2",
        context=ImportCellContext(module="物理", sheet="物理和环境安全", row=2),
    )

    assert products == [
        {
            "name": "门禁模块",
            "vendor": "厂商A",
            "certificate_no": "CERT-1",
            "level": "二级",
            "usage": "身份鉴别",
        },
        {
            "name": "裸产品",
            "vendor": "",
            "certificate_no": "",
            "level": "一级",
            "usage": "",
        },
    ]
    assert quant == {"d": CHECK, "a": CHECK, "k": CROSS, "ra": 1.0, "rk": 1.2}
    with pytest.raises(ImportDataError) as exc_info:
        reader.parse_quant_values(
            d=CHECK,
            a=CHECK,
            k=CHECK,
            ra="bad",
            rk=1,
            context=ImportCellContext(
                module="物理",
                sheet="物理和环境安全",
                row=8,
                field_name="Ra",
            ),
        )
    assert "物理" in str(exc_info.value)
    assert "物理和环境安全" in str(exc_info.value)
    assert "第8行" in str(exc_info.value)
    assert "Ra" in str(exc_info.value)


def test_import_rejects_non_xlsx_file_without_writing(tmp_path):
    engine = _engine(tmp_path)
    project_id = _project_id(engine)
    bad_file = tmp_path / "interview.txt"
    bad_file.write_text("not a workbook", encoding="utf-8")

    result = ImportService(engine).import_interview_template(project_id, bad_file, mode="替换")

    assert result.success is False
    assert ".xlsx" in result.message
    assert PhysicalService(engine).list_objects(project_id) == []
