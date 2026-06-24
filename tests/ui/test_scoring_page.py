from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QAbstractItemView, QComboBox

from mpxccp.domain.constants import CHECK, CROSS
from mpxccp.domain.enums import MeasureUnit
from mpxccp.repositories.session import create_engine_for_path, init_database
from mpxccp.services.basic_info_service import BasicInfoService
from mpxccp.services.physical_service import PhysicalService
from mpxccp.services.quant_service import QuantService
from mpxccp.services.scoring_service import ScoringService
from mpxccp.ui.main_window import MainWindow
from mpxccp.ui.pages.scoring_page import ScoringPage


def _engine(tmp_path: Path):
    engine = create_engine_for_path(tmp_path / "scoring-page.sqlite3")
    init_database(engine)
    return engine


def _project_id(engine) -> int:
    result = BasicInfoService(engine).save_basic_info(
        flow_no="SCORE-UI-001",
        system_name="评分页测试系统",
        client_name="委托方",
        assessment_org="测评机构",
    )
    assert result.success
    assert result.project_id is not None
    return result.project_id


def test_scoring_page_dirty_button_text(qtbot):
    page = ScoringPage()
    qtbot.addWidget(page)

    page.mark_dirty()

    assert page.recalculate_button_text() == "⚠ 分数待更新 - 点击重新计算"


def test_scoring_page_has_summary_cards_and_tables(qtbot, tmp_path):
    engine = _engine(tmp_path)
    project_id = _project_id(engine)
    page = ScoringPage(ScoringService(engine))
    qtbot.addWidget(page)

    page.set_project_id(project_id)

    assert page.total_score_text() == "0.00"
    assert page.compliance_count_texts() == {
        "符合": "0",
        "部分符合": "0",
        "不符合": "0",
        "不适用": "0",
    }
    assert page.layer_card_names() == [
        "物理和环境安全",
        "网络和通信安全",
        "设备和计算安全",
        "应用和数据安全",
        "管理制度",
        "人员管理",
        "建设运行",
        "应急处置",
    ]
    assert page.technical_table().editTriggers() == QAbstractItemView.EditTrigger.NoEditTriggers
    assert page.management_table().rowCount() == 19


def test_scoring_page_management_combo_saves_and_recalculates(qtbot, tmp_path):
    engine = _engine(tmp_path)
    project_id = _project_id(engine)
    service = ScoringService(engine)
    page = ScoringPage(service)
    qtbot.addWidget(page)

    page.set_project_id(project_id)
    combo = page.management_combo(23)

    assert isinstance(combo, QComboBox)
    combo.setCurrentText("符合")

    summary = service.load_summary(project_id)
    assert summary is not None
    assert summary.compliant_count == 1
    assert summary.total_score == 30.0
    assert page.recalculate_button_text() == "重新计算"
    assert page.total_score_text() == "30.00"


def test_scoring_page_recalculate_creates_missing_empty_quant_records(qtbot, tmp_path):
    engine = _engine(tmp_path)
    project_id = _project_id(engine)
    physical = PhysicalService(engine)
    obj = physical.create_object(project_id, "主机房")
    detail_id = physical.load_details(obj.id).auth.id
    page = ScoringPage(ScoringService(engine))
    qtbot.addWidget(page)

    page.set_project_id(project_id)
    page.mark_dirty()
    page.recalculate_button().click()

    created = QuantService(engine, project_id=project_id).load(
        MeasureUnit.PHYSICAL_AUTH.value,
        detail_id,
    )
    assert created.record_id is not None
    assert created.d == ""


def test_scoring_page_technical_table_shows_object_quant_columns(qtbot, tmp_path):
    engine = _engine(tmp_path)
    project_id = _project_id(engine)
    physical = PhysicalService(engine)
    obj = physical.create_object(project_id, "主机房")
    detail_id = physical.load_details(obj.id).auth.id
    QuantService(engine, project_id=project_id).save(
        MeasureUnit.PHYSICAL_AUTH.value,
        detail_id,
        d=CROSS,
        a="/",
        k="/",
        ra=1,
        rk=1,
    )
    page = ScoringPage(ScoringService(engine))
    qtbot.addWidget(page)

    page.set_project_id(project_id)
    page.recalculate_button().click()
    table = page.technical_table()
    headers = [table.horizontalHeaderItem(index).text() for index in range(table.columnCount())]
    table_values = {
        table.item(row, column).text()
        for row in range(table.rowCount())
        for column in range(table.columnCount())
        if table.item(row, column) is not None
    }

    assert ["D", "A", "K", "Ra", "Rk", "对象得分"] == headers[3:9]
    assert "×" in table_values
    assert "/" in table_values
    assert "0.00" in table_values


def test_scoring_page_management_table_shows_allocated_earned_and_lost(qtbot, tmp_path):
    engine = _engine(tmp_path)
    project_id = _project_id(engine)
    page = ScoringPage(ScoringService(engine))
    qtbot.addWidget(page)

    page.set_project_id(project_id)
    page.management_combo(23).setCurrentText("符合")

    headers = [
        page.management_table().horizontalHeaderItem(index).text()
        for index in range(page.management_table().columnCount())
    ]
    row_values = [
        page.management_table().item(0, column).text()
        for column in range(page.management_table().columnCount())
        if page.management_table().item(0, column) is not None
    ]
    assert "所占" in headers
    assert "已得" in headers
    assert "丢失" in headers
    assert "30.00" in row_values
    assert "0.00" in row_values


def test_main_window_wires_scoring_page_and_dirty_state(qtbot, tmp_path):
    engine = _engine(tmp_path)
    project_id = _project_id(engine)
    window = MainWindow(scoring_service=ScoringService(engine))
    qtbot.addWidget(window)

    window.set_project_context(
        project_id=project_id,
        system_name="评分页测试系统",
        flow_no="SCORE-UI-001",
    )
    window.mark_scoring_dirty()

    page = window.scoring_page()
    assert page.project_id() == project_id
    assert page.recalculate_button_text() == "⚠ 分数待更新 - 点击重新计算"


def test_main_window_marks_scoring_dirty_after_physical_detail_save(qtbot, tmp_path):
    engine = _engine(tmp_path)
    project_id = _project_id(engine)
    window = MainWindow(
        physical_service=PhysicalService(engine),
        scoring_service=ScoringService(engine),
    )
    qtbot.addWidget(window)

    window.set_project_context(
        project_id=project_id,
        system_name="评分页测试系统",
        flow_no="SCORE-UI-001",
    )
    physical_page = window.physical_page()
    physical_page.add_object("主机房")
    window.is_scoring_dirty = False

    physical_page.object_field("name").setText("主机房A")
    physical_page.save_current_detail(silent=True)

    assert window.is_scoring_dirty is True
    assert window.scoring_page().recalculate_button_text() == "⚠ 分数待更新 - 点击重新计算"


def test_main_window_refreshes_effective_d_count_on_tab_switch(qtbot, tmp_path):
    engine = _engine(tmp_path)
    project_id = _project_id(engine)
    physical = PhysicalService(engine)
    obj = physical.create_object(project_id, "主机房")
    detail_id = physical.load_details(obj.id).auth.id
    QuantService(engine, project_id=project_id).save(
        MeasureUnit.PHYSICAL_AUTH.value,
        detail_id,
        d=CHECK,
        a=CHECK,
        k=CHECK,
        ra=1,
        rk=1,
    )
    window = MainWindow(
        physical_service=physical,
        scoring_service=ScoringService(engine),
    )
    qtbot.addWidget(window)

    window.set_project_context(
        project_id=project_id,
        system_name="评分页测试系统",
        flow_no="SCORE-UI-001",
    )
    window.switch_to_tab(5)

    assert window.status_snapshot()["effective_d"] == "有效D：1"
