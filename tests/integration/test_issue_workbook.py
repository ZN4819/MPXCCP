from __future__ import annotations

from pathlib import Path

from mpxccp.domain.constants import CHECK
from mpxccp.repositories.session import create_engine_for_path, init_database
from mpxccp.services.application_service import ApplicationService
from mpxccp.services.basic_info_service import BasicInfoService
from mpxccp.services.device_service import DeviceService
from mpxccp.services.export_service import ExportService
from mpxccp.services.import_service import ImportService
from mpxccp.services.network_service import NetworkService
from mpxccp.services.physical_service import PhysicalService
from tests.fixtures.workbook_builders import WorkbookBuilders

ISSUE_HEADERS = [
    "测评层面",
    "测评要求",
    "问题编号",
    "系统名称",
    "被测对象名称",
    "现状描述",
    "问题说明",
    "风险分析与缓释机制",
    "风险等级",
    "整改建议",
    "说明",
    "主要责任部门（建议）",
]


def _engine(tmp_path: Path):
    engine = create_engine_for_path(tmp_path / "issue-workbook.sqlite3")
    init_database(engine)
    return engine


def _project_id(engine) -> int:
    result = BasicInfoService(engine).save_basic_info(
        flow_no="ISSUE-001",
        system_name="问题清单测试系统",
        client_name="委托方",
        assessment_org="测评机构",
    )
    assert result.success
    assert result.project_id is not None
    return result.project_id


def _risk_fill(sheet, row: int) -> str:
    value = sheet.cell(row=row, column=9).fill.fgColor.rgb
    return "" if value is None else value[-6:]


def test_issue_workbook_has_fixed_title_headers_widths_and_physical_rows(tmp_path):
    engine = _engine(tmp_path)
    project_id = _project_id(engine)
    imported = ImportService(engine).import_interview_template(
        project_id,
        WorkbookBuilders().physical_workbook(),
        mode="替换",
    )
    assert imported.success

    workbook = ExportService(engine).export_issue_workbook(project_id)
    sheet = workbook["问题清单"]

    assert workbook.sheetnames == ["问题清单"]
    assert sheet["A1"].value == "【三级标准】 问题清单测试系统 密码应用安全性评估问题清单"
    assert "A1:L1" in {str(item) for item in sheet.merged_cells.ranges}
    assert [sheet.cell(2, col).value for col in range(1, 13)] == ISSUE_HEADERS
    assert [sheet.column_dimensions[column].width for column in ("A", "B", "C", "D")] == [
        15,
        30,
        10,
        20,
    ]
    assert sheet.cell(row=3, column=1).value == "物理和环境"
    assert sheet.cell(row=3, column=3).value == 1
    assert sheet.cell(row=3, column=4).value == "问题清单测试系统"
    assert sheet.cell(row=3, column=5).value == "主机房"
    assert "身份鉴别" in sheet.cell(row=3, column=6).value
    assert "实时监控" in sheet.cell(row=3, column=6).value
    assert "专人值守" in sheet.cell(row=3, column=6).value
    assert sheet.cell(row=3, column=8).value == "身份鉴别风险可控"
    assert sheet.cell(row=3, column=9).value == "中风险"
    assert sheet.cell(row=3, column=10).value == "完善值守登记"
    assert _risk_fill(sheet, 3) == "FFA500"


def test_issue_workbook_uses_mitigation_text_and_mitigated_level_for_high_risk(tmp_path):
    engine = _engine(tmp_path)
    project_id = _project_id(engine)
    physical = PhysicalService(engine)
    obj = physical.create_object(project_id, "主机房")
    details = physical.load_details(obj.id)
    saved = physical.save_detail(
        obj.id,
        {
            "object": {"location": "一层"},
            "units": {
                "auth": {
                    "implementation": "已使用",
                    "auth_methods": "口令",
                    "algorithm": "SM4",
                    "risk_level": "高风险",
                    "risk_analysis": "原始高风险分析",
                    "mitigation_available": "是",
                    "mitigation_note": "双人值守并留痕",
                    "mitigated_level": "低风险",
                    "remediation": "完善机房访问审批",
                    "quant": {"d": CHECK, "a": CHECK, "k": CHECK, "ra": 1, "rk": 1},
                }
            },
        },
    )
    assert saved.success
    assert details.auth.id

    sheet = ExportService(engine).export_issue_workbook(project_id)["问题清单"]

    assert sheet.cell(row=3, column=8).value == "双人值守并留痕"
    assert sheet.cell(row=3, column=9).value == "低风险"
    assert _risk_fill(sheet, 3) == "FFFF00"


def test_issue_workbook_uses_boolean_mitigation_and_cleans_multi_select_values(tmp_path):
    engine = _engine(tmp_path)
    project_id = _project_id(engine)
    physical = PhysicalService(engine)
    obj = physical.create_object(project_id, "主机房")
    saved = physical.save_detail(
        obj.id,
        {
            "units": {
                "auth": {
                    "implementation": "已使用",
                    "auth_methods": "指纹,其他:虹膜",
                    "algorithm": "SM4",
                    "risk_level": "高风险",
                    "risk_analysis": "原始高风险分析",
                    "mitigation_available": True,
                    "mitigation_note": "双人值守并留痕",
                    "mitigated_level": "低风险",
                    "remediation": "完善机房访问审批",
                    "quant": {"d": CHECK, "a": CHECK, "k": CHECK, "ra": 1, "rk": 1},
                }
            },
        },
    )
    assert saved.success

    sheet = ExportService(engine).export_issue_workbook(project_id)["问题清单"]

    assert "指纹、虹膜" in sheet.cell(row=3, column=6).value
    assert sheet.cell(row=3, column=8).value == "双人值守并留痕"
    assert sheet.cell(row=3, column=9).value == "低风险"


def test_issue_workbook_network_combined_row_uses_worst_integrity_or_confidentiality(tmp_path):
    engine = _engine(tmp_path)
    project_id = _project_id(engine)
    BasicInfoService(engine).sync_subsystems(project_id, ["业务系统"])
    network = NetworkService(engine)
    network.sync_from_basic_subsystems(project_id)
    subsystem = network.list_subsystems(project_id)[0]
    channel = network.create_channel(subsystem.id, "业务信道")
    saved = network.save_channel_detail(
        channel.id,
        {
            "channel": {"protocol": "HTTPS", "network_environment": "互联网"},
            "units": {
                "integrity": {
                    "implementation": "未实现",
                    "risk_level": "高风险",
                    "risk_analysis": "完整性高风险",
                    "remediation": "补充完整性保护",
                },
                "confidentiality": {
                    "implementation": "已实现",
                    "risk_level": "低风险",
                    "risk_analysis": "机密性低风险",
                    "remediation": "保持加密传输",
                },
            },
        },
    )
    assert saved.success

    sheet = ExportService(engine).export_issue_workbook(project_id)["问题清单"]

    assert sheet.cell(row=3, column=1).value == "网络和通信"
    assert "机密性和完整性" in sheet.cell(row=3, column=6).value
    assert "未实现" in sheet.cell(row=3, column=6).value
    assert sheet.cell(row=3, column=8).value == "完整性高风险"
    assert sheet.cell(row=3, column=9).value == "高风险"
    assert sheet.cell(row=3, column=10).value == "补充完整性保护"


def test_issue_workbook_network_combined_row_ranks_by_effective_mitigated_risk(tmp_path):
    engine = _engine(tmp_path)
    project_id = _project_id(engine)
    BasicInfoService(engine).sync_subsystems(project_id, ["业务系统"])
    network = NetworkService(engine)
    network.sync_from_basic_subsystems(project_id)
    subsystem = network.list_subsystems(project_id)[0]
    channel = network.create_channel(subsystem.id, "业务信道")
    saved = network.save_channel_detail(
        channel.id,
        {
            "channel": {"protocol": "HTTPS", "network_environment": "互联网"},
            "units": {
                "integrity": {
                    "implementation": "已实现",
                    "risk_level": "高风险",
                    "risk_analysis": "完整性高风险",
                    "mitigation_available": True,
                    "mitigation_note": "完整性风险已缓释",
                    "mitigated_level": "低风险",
                    "remediation": "维持完整性保护",
                },
                "confidentiality": {
                    "implementation": "已实现",
                    "risk_level": "中风险",
                    "risk_analysis": "机密性中风险",
                    "remediation": "补充机密性保护",
                },
            },
        },
    )
    assert saved.success

    sheet = ExportService(engine).export_issue_workbook(project_id)["问题清单"]

    assert sheet.cell(row=3, column=8).value == "机密性中风险"
    assert sheet.cell(row=3, column=9).value == "中风险"
    assert sheet.cell(row=3, column=10).value == "补充机密性保护"


def test_issue_workbook_device_product_judgement_state_matches_description(tmp_path):
    engine = _engine(tmp_path)
    project_id = _project_id(engine)
    device = DeviceService(engine)
    obj = device.create_object(project_id, "密码设备")
    saved = device.save_detail(
        obj.id,
        {
            "units": {
                "access_integrity": {
                    "product_used": "是",
                    "product_level": "一级",
                    "risk_level": "低风险",
                    "risk_analysis": "产品等级偏低",
                    "remediation": "替换二级及以上产品",
                }
            }
        },
    )
    assert saved.success

    sheet = ExportService(engine).export_issue_workbook(project_id)["问题清单"]

    assert sheet.cell(row=3, column=6).value == sheet.cell(row=3, column=7).value
    assert "产品认证等级为一级" in sheet.cell(row=3, column=6).value
    assert "二级及以上" in sheet.cell(row=3, column=6).value


def test_issue_workbook_device_regular_related_product_is_not_product_judgement(tmp_path):
    engine = _engine(tmp_path)
    project_id = _project_id(engine)
    device = DeviceService(engine)
    obj = device.create_object(project_id, "服务器A")
    saved = device.save_detail(
        obj.id,
        {
            "units": {
                "access_integrity": {
                    "implementation": "已实现",
                    "algorithm": "SM3",
                    "risk_level": "低风险",
                    "risk_analysis": "访问控制完整性风险可控",
                    "remediation": "保持策略维护",
                    "products": [
                        {
                            "name": "访问控制完整性产品",
                            "level": "二级",
                            "usage": "访问控制完整性",
                        }
                    ],
                }
            }
        },
    )
    assert saved.success

    sheet = ExportService(engine).export_issue_workbook(project_id)["问题清单"]

    assert "是合规的密码产品" not in sheet.cell(row=3, column=7).value
    assert "访问控制完整性产品" in sheet.cell(row=3, column=7).value


def test_issue_workbook_merges_only_continuous_same_values(tmp_path):
    engine = _engine(tmp_path)
    project_id = _project_id(engine)
    physical = PhysicalService(engine)
    for name, remediation in (
        ("机房A", "统一整改"),
        ("机房B", "统一整改"),
        ("机房C", "单独整改"),
    ):
        obj = physical.create_object(project_id, name)
        saved = physical.save_detail(
            obj.id,
            {
                "units": {
                    "auth": {
                        "implementation": "已使用",
                        "auth_methods": "口令",
                        "risk_level": "低风险",
                        "risk_analysis": f"{name}风险分析",
                        "remediation": remediation,
                    }
                }
            },
        )
        assert saved.success

    sheet = ExportService(engine).export_issue_workbook(project_id)["问题清单"]
    merged_ranges = {str(item) for item in sheet.merged_cells.ranges}

    assert "A3:A5" in merged_ranges
    assert "B3:B5" in merged_ranges
    assert "D3:D5" in merged_ranges
    assert "J3:J4" in merged_ranges
    assert "J3:J5" not in merged_ranges
    assert not any(item.startswith("C3:") for item in merged_ranges)


def test_issue_workbook_application_user_auth_cleans_multi_select_values(tmp_path):
    engine = _engine(tmp_path)
    project_id = _project_id(engine)
    BasicInfoService(engine).sync_subsystems(project_id, ["业务系统"])
    application = ApplicationService(engine)
    application.sync_from_basic_subsystems(project_id)
    subsystem = application.list_subsystems(project_id)[0]
    user = application.create_user(subsystem.id, "管理员")
    saved = application.save_user_detail(
        user.id,
        {
            "units": {
                "user_auth": {
                    "implementation": "已使用",
                    "auth_methods": "口令,其他:动态令牌",
                    "algorithm": "SM3",
                    "risk_level": "低风险",
                    "risk_analysis": "用户身份鉴别风险可控",
                    "remediation": "持续审计账号权限",
                }
            }
        },
    )
    assert saved.success

    sheet = ExportService(engine).export_issue_workbook(project_id)["问题清单"]

    assert "口令、动态令牌" in sheet.cell(row=3, column=6).value
    assert "使用了密码技术" in sheet.cell(row=3, column=6).value
    assert "可以保证登录设备用户身份鉴别的真实性" in sheet.cell(row=3, column=7).value


def test_issue_workbook_keeps_empty_structure_when_no_issue_rows(tmp_path):
    engine = _engine(tmp_path)
    project_id = _project_id(engine)

    sheet = ExportService(engine).export_issue_workbook(project_id)["问题清单"]

    assert sheet.max_row == 2
    assert [sheet.cell(2, col).value for col in range(1, 13)] == ISSUE_HEADERS


def test_issue_workbook_does_not_emit_rows_for_default_empty_details(tmp_path):
    engine = _engine(tmp_path)
    project_id = _project_id(engine)
    PhysicalService(engine).create_object(project_id, "空机房")

    sheet = ExportService(engine).export_issue_workbook(project_id)["问题清单"]

    assert sheet.max_row == 2
