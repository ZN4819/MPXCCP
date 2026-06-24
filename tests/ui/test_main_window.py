from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import QWheelEvent
from PySide6.QtWidgets import QApplication, QComboBox

from mpxccp.bootstrap import install_combo_box_wheel_protection
from mpxccp.ui.main_window import MainWindow

MAIN_WINDOW_TITLE = "商用密码应用安全性评估实施工具"
EXPECTED_MENU_ACTIONS = {
    "文件": [
        "新建",
        "打开",
        "保存",
        "导入数据",
        "导出全部",
        "导出所选模块",
        "导出打分表",
        "导入打分表",
        "导出问题清单",
        "删除",
        "恢复项目",
        "退出",
    ],
    "工具": ["知识库"],
    "帮助": ["关于"],
}
EXPECTED_TOOLBAR_ACTIONS = ["新建", "打开", "保存", "导出全部", "问题清单", "删除"]


def test_main_window_has_required_tabs(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)

    assert window.windowTitle() == MAIN_WINDOW_TITLE
    assert window.tab_names() == [
        "被测系统基本信息",
        "物理和环境安全",
        "设备和计算安全",
        "网络和通信安全",
        "应用和数据安全",
        "打分",
    ]


def test_main_window_exposes_menu_toolbar_and_status_context(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)

    assert window.menu_action_texts() == EXPECTED_MENU_ACTIONS
    assert window.toolbar_action_texts() == EXPECTED_TOOLBAR_ACTIONS

    window.set_project_context(project_id=42, system_name="示例业务系统", flow_no="MP-2026-001")

    assert window.current_project_id == 42
    assert window.status_snapshot() == {
        "project": "当前项目：示例业务系统",
        "flow": "流转编号：MP-2026-001",
        "effective_d": "有效D：0",
    }


def test_main_window_marks_scoring_dirty(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)

    assert window.is_scoring_dirty is False

    window.mark_scoring_dirty()

    assert window.is_scoring_dirty is True
    assert window.statusBar().currentMessage() == "评分待更新"


def test_leaving_basic_info_tab_saves_basic_info_and_syncs_project(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)
    calls: list[str] = []

    def save_basic_info():
        calls.append("saved")
        return {"project_id": 77, "system_name": "同步后的系统", "flow_no": "FLOW-77"}

    window.set_basic_info_save_handler(save_basic_info)

    window.switch_to_tab(1)

    assert calls == ["saved"]
    assert window.current_project_id == 77
    assert window.status_snapshot() == {
        "project": "当前项目：同步后的系统",
        "flow": "流转编号：FLOW-77",
        "effective_d": "有效D：0",
    }


def test_project_required_actions_prompt_before_project_is_open(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)

    window.trigger_action("导出全部")

    assert window.statusBar().currentMessage() == "请先打开或保存项目"


def test_combo_box_wheel_protection_consumes_collapsed_wheel_events(qtbot):
    app = QApplication.instance()
    wheel_filter = install_combo_box_wheel_protection(app)
    combo = QComboBox()
    combo.addItems(["符合", "部分符合", "不符合"])
    qtbot.addWidget(combo)

    event = QWheelEvent(
        QPointF(1, 1),
        QPointF(1, 1),
        QPoint(0, 120),
        QPoint(0, 120),
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
        Qt.ScrollPhase.NoScrollPhase,
        False,
    )

    assert wheel_filter.eventFilter(combo, event) is True
