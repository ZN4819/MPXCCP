from __future__ import annotations

from pathlib import Path

import pytest

from mpxccp.domain.constants import CHECK
from mpxccp.integration.excel.schema import APPLICATION_SECTIONS, SHEET_NAMES
from mpxccp.repositories.session import create_engine_for_path, init_database
from mpxccp.services.basic_info_service import BasicInfoService
from mpxccp.services.export_service import ExportService
from mpxccp.services.import_service import ImportService
from tests.fixtures.workbook_builders import WorkbookBuilders

EXPECTED_ALL_DATA_SHEETS = [
    "系统基本信息",
    "物理和环境安全",
    "设备和计算安全",
    "网络和通信安全",
    "应用和数据安全",
]


def _engine(tmp_path: Path):
    engine = create_engine_for_path(tmp_path / "excel-export.sqlite3")
    init_database(engine)
    return engine


def _project_id(engine) -> int:
    result = BasicInfoService(engine).save_basic_info(
        flow_no="EXP-001",
        system_name="导出测试系统",
        client_name="委托方",
        assessment_org="测评机构",
        assessor_name="评估人员",
        assessor_phone="13900000000",
        interview_time="2026-06-24",
    )
    assert result.success
    assert result.project_id is not None
    return result.project_id


def test_export_all_data_has_expected_sheets_and_basic_info(tmp_path):
    engine = _engine(tmp_path)
    project_id = _project_id(engine)
    BasicInfoService(engine).sync_subsystems(project_id, ["业务系统", "管理端"])

    workbook = ExportService(engine).export_all_data(project_id)

    assert workbook.sheetnames == EXPECTED_ALL_DATA_SHEETS
    basic = workbook[SHEET_NAMES.basic_info]
    assert basic["A1"].value == "一、项目基本信息"
    assert basic["A2"].value == "流转单编号"
    assert basic["B2"].value == "EXP-001"
    assert basic["A3"].value == "信息系统名称"
    assert basic["B3"].value == "导出测试系统"
    assert basic["A10"].value == "二、系统基本信息"
    assert basic["B12"].value == "业务系统、管理端"
    assert basic.column_dimensions["A"].width == 20
    assert basic.column_dimensions["B"].width == 50


def test_export_basic_info_includes_scheme_review_organization(tmp_path):
    engine = _engine(tmp_path)
    project_id = _project_id(engine)
    result = BasicInfoService(engine).save_full_basic_info(
        project_id=project_id,
        flow_no="EXP-001",
        system_name="导出测试系统",
        client_name="委托方",
        assessment_org="测评机构",
        crypto_application_info={
            "review_method": "专家评审",
            "review_org": "方案评审机构",
            "review_date": "2026-01-15",
        },
    )
    assert result.success

    workbook = ExportService(engine).export_selected_modules(project_id, [SHEET_NAMES.basic_info])
    sheet = workbook[SHEET_NAMES.basic_info]

    assert sheet["A36"].value == "方案评审方式"
    assert sheet["B36"].value == "专家评审"
    assert sheet["A37"].value == "方案评审机构"
    assert sheet["B37"].value == "方案评审机构"
    assert sheet["A38"].value == "方案评审时间"
    assert sheet["B38"].value == "2026-01-15"


def test_export_physical_row_keeps_product_text_and_quant_order(tmp_path):
    engine = _engine(tmp_path)
    project_id = _project_id(engine)
    imported = ImportService(engine).import_interview_template(
        project_id,
        WorkbookBuilders().physical_workbook(),
        mode="替换",
    )
    assert imported.success

    workbook = ExportService(engine).export_selected_modules(project_id, [SHEET_NAMES.physical])

    assert workbook.sheetnames == [SHEET_NAMES.physical]
    sheet = workbook[SHEET_NAMES.physical]
    headers = [cell.value for cell in sheet[1]]
    product_col = headers.index("身份鉴别密码产品") + 1
    assert headers[product_col - 1 : product_col + 5] == [
        "身份鉴别密码产品",
        "D",
        "A",
        "K",
        "Ra",
        "Rk",
    ]
    assert sheet.cell(row=2, column=1).value == "主机房"
    assert sheet.cell(row=2, column=product_col).value == (
        "机房身份鉴别模块(厂商A, 证书:CERT-主机房, 等级:二级, 用途:身份鉴别)"
    )
    assert [sheet.cell(row=2, column=product_col + offset).value for offset in range(1, 6)] == [
        CHECK,
        CHECK,
        CHECK,
        1.2,
        1.0,
    ]


def test_export_selected_modules_rejects_empty_selection(tmp_path):
    engine = _engine(tmp_path)
    project_id = _project_id(engine)

    with pytest.raises(ValueError, match="至少选择一个导出模块"):
        ExportService(engine).export_selected_modules(project_id, [])


def test_export_network_integrity_columns_do_not_shift_confidentiality(tmp_path):
    engine = _engine(tmp_path)
    project_id = _project_id(engine)
    imported = ImportService(engine).import_interview_template(
        project_id,
        WorkbookBuilders().network_workbook("业务系统", "业务信道"),
        mode="替换",
    )
    assert imported.success

    workbook = ExportService(engine).export_selected_modules(project_id, [SHEET_NAMES.network])
    headers = [cell.value for cell in workbook[SHEET_NAMES.network][1]]

    risk_analysis_column = headers.index("完整性风险分析")
    assert headers[risk_analysis_column + 1 : risk_analysis_column + 3] == [
        "完整性整改建议",
        "机密性判定",
    ]


def test_export_application_section_places_data_immediately_after_header(tmp_path):
    engine = _engine(tmp_path)
    project_id = _project_id(engine)
    imported = ImportService(engine).import_interview_template(
        project_id,
        WorkbookBuilders().application_workbook_with_data_and_business(),
        mode="替换",
    )
    assert imported.success

    workbook = ExportService(engine).export_selected_modules(project_id, [SHEET_NAMES.application])
    sheet = workbook[SHEET_NAMES.application]
    important_data_title_row = next(
        row
        for row in range(1, sheet.max_row + 1)
        if sheet.cell(row=row, column=1).value == APPLICATION_SECTIONS.important_data
    )

    assert sheet.cell(row=important_data_title_row + 1, column=1).value == "子系统"
    assert sheet.cell(row=important_data_title_row + 2, column=1).value == "业务系统"
