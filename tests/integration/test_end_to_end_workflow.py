from __future__ import annotations

from mpxccp.repositories.session import create_engine_for_path, init_database
from mpxccp.services.export_service import ExportService
from mpxccp.services.product_service import ProductService
from mpxccp.services.project_service import ProjectService
from mpxccp.services.scoring_service import ScoringService
from tests.fixtures.sample_data import SampleDataBuilder

EXPECTED_ALL_DATA_SHEETS = [
    "系统基本信息",
    "物理和环境安全",
    "设备和计算安全",
    "网络和通信安全",
    "应用和数据安全",
]

EXPECTED_SCORE_SHEETS = [
    "整体测评",
    "1物理和环境安全",
    "2网络和通信安全",
    "3设备和计算安全",
    "4应用和数据安全",
    "5管理制度",
    "6人员管理",
    "7建设运行",
    "8应急处置",
]


def test_core_end_to_end_workflow(tmp_path):
    engine = create_engine_for_path(tmp_path / "end-to-end.sqlite3")
    init_database(engine)
    sample_data = SampleDataBuilder(engine)

    project_id = sample_data.create_full_project()
    summary = ScoringService(engine).refresh_all_technical_domains(project_id)
    exporter = ExportService(engine)
    score_book = exporter.export_score_workbook(project_id)
    issue_book = exporter.export_issue_workbook(project_id)
    all_data = exporter.export_all_data(project_id)

    assert sample_data.last_refs is not None
    assert sample_data.last_refs.project_id == project_id
    assert len(sample_data.last_refs.subsystems) == 2
    assert sample_data.last_refs.physical_object_id is not None
    assert sample_data.last_refs.device_object_id is not None
    assert sample_data.last_refs.network_channel_id is not None
    assert sample_data.last_refs.application_user_id is not None
    assert sample_data.last_refs.certified_product_name
    assert sample_data.last_refs.uncertified_product_name
    assert {"符合", "部分符合", "不符合", "不适用"}.issubset(
        {detail.compliance_status for detail in summary.details}
    )
    assert summary.total_allocated_score == 100.0
    assert summary.total_earned_score == summary.total_score
    assert summary.total_lost_score == round(100.0 - summary.total_score, 2)
    assert summary.compliant_count >= 1
    assert summary.partial_count >= 1
    assert summary.non_compliant_count >= 1
    assert summary.not_applicable_count >= 1
    assert {
        detail.indicator_no
        for detail in summary.details
        if detail.not_applicable
    }.issuperset({8, 12, 17})
    assert score_book.sheetnames == EXPECTED_SCORE_SHEETS
    assert "问题清单" in issue_book.sheetnames
    issue_sheet = issue_book["问题清单"]
    assert issue_sheet["A1"].value == "【三级标准】 端到端验收系统 密码应用安全性评估问题清单"
    assert [issue_sheet.cell(2, column).value for column in range(1, 13)] == [
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
    assert issue_sheet.max_row >= 3
    assert issue_sheet.cell(3, 1).value in {
        "物理和环境",
        "网络和通信",
        "设备和计算",
        "应用和数据",
    }
    assert all_data.sheetnames == EXPECTED_ALL_DATA_SHEETS
    reusable_products = ProductService(engine).list_reusable_project_products(project_id)
    assert {item.product_name for item in reusable_products}.issuperset(
        {
            sample_data.last_refs.certified_product_name,
            sample_data.last_refs.uncertified_product_name,
        }
    )

    score_book["5管理制度"].cell(row=3, column=3, value="不符合")
    import_result = exporter.import_score_workbook(project_id, score_book, mode="合并")
    imported_summary = ScoringService(engine).load_summary(project_id)
    assert import_result.success is True
    assert imported_summary is not None
    assert {
        detail.indicator_no: detail.compliance_status
        for detail in imported_summary.details
    }[23] == "不符合"

    projects = ProjectService(engine)
    assert projects.soft_delete(project_id).success is True
    assert project_id not in [item["id"] for item in projects.list_openable()]
    assert projects.open_project(project_id).success is False
    assert projects.restore([project_id]).success is True
    opened = projects.open_project(project_id)
    assert opened.success is True
    assert opened.project_id == project_id
    assert ScoringService(engine).load_summary(project_id) is not None
