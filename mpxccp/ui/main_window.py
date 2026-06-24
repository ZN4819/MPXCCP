from __future__ import annotations

from collections import OrderedDict
from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QPlainTextEdit,
    QSplitter,
    QStatusBar,
    QStyle,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from mpxccp.services.physical_service import PhysicalService
from mpxccp.ui.pages import PhysicalPage

MAIN_WINDOW_TITLE = "商用密码应用安全性评估实施工具"

TAB_NAMES = [
    "被测系统基本信息",
    "物理和环境安全",
    "设备和计算安全",
    "网络和通信安全",
    "应用和数据安全",
    "打分",
]

MENU_ACTION_TEXTS: OrderedDict[str, list[str]] = OrderedDict(
    [
        (
            "文件",
            [
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
        ),
        ("工具", ["知识库"]),
        ("帮助", ["关于"]),
    ]
)

TOOLBAR_ACTION_TEXTS = ["新建", "打开", "保存", "导出全部", "问题清单", "删除"]

PROJECT_REQUIRED_ACTIONS = {
    "导入数据",
    "导出全部",
    "导出所选模块",
    "导出打分表",
    "导入打分表",
    "导出问题清单",
    "问题清单",
    "删除",
}

ACTION_TOOLTIPS = {
    "新建": "新建测评项目",
    "打开": "打开已有项目",
    "保存": "保存当前项目",
    "导入数据": "导入项目数据",
    "导出全部": "导出全部模块",
    "导出所选模块": "导出所选模块",
    "导出打分表": "导出打分表",
    "导入打分表": "导入打分表",
    "导出问题清单": "导出问题清单",
    "问题清单": "导出问题清单",
    "删除": "删除当前项目",
    "恢复项目": "恢复已删除项目",
    "知识库": "打开知识库",
    "退出": "退出应用",
    "关于": "查看应用信息",
}

ACTION_ICONS = {
    "新建": QStyle.StandardPixmap.SP_FileIcon,
    "打开": QStyle.StandardPixmap.SP_DirOpenIcon,
    "保存": QStyle.StandardPixmap.SP_DialogSaveButton,
    "导入数据": QStyle.StandardPixmap.SP_ArrowDown,
    "导出全部": QStyle.StandardPixmap.SP_ArrowUp,
    "导出所选模块": QStyle.StandardPixmap.SP_ArrowUp,
    "导出打分表": QStyle.StandardPixmap.SP_FileDialogDetailedView,
    "导入打分表": QStyle.StandardPixmap.SP_FileDialogListView,
    "导出问题清单": QStyle.StandardPixmap.SP_MessageBoxWarning,
    "问题清单": QStyle.StandardPixmap.SP_MessageBoxWarning,
    "恢复项目": QStyle.StandardPixmap.SP_BrowserReload,
    "知识库": QStyle.StandardPixmap.SP_DialogHelpButton,
    "退出": QStyle.StandardPixmap.SP_DialogCloseButton,
    "关于": QStyle.StandardPixmap.SP_MessageBoxInformation,
}

_TRASH_ICON = getattr(
    QStyle.StandardPixmap,
    "SP_TrashIcon",
    QStyle.StandardPixmap.SP_DialogDiscardButton,
)
ACTION_ICONS["删除"] = _TRASH_ICON


class MainWindow(QMainWindow):
    """Desktop shell for the commercial cryptography assessment workflow."""

    def __init__(self, *, physical_service: PhysicalService | None = None) -> None:
        super().__init__()
        self._physical_service = physical_service
        self.current_project_id: int | None = None
        self.current_project_name = "未打开"
        self.current_flow_no = "--"
        self.effective_d_count = 0
        self.is_scoring_dirty = False
        self._last_tab_index = 0
        self._basic_info_save_handler: Callable[[], Any] | None = None
        self._menu_actions: OrderedDict[str, list[QAction]] = OrderedDict()
        self._toolbar_actions: list[QAction] = []

        self.setWindowTitle(MAIN_WINDOW_TITLE)
        self.resize(1280, 820)
        self.setMinimumSize(1080, 680)

        self._build_menus()
        self._build_toolbar()
        self._build_status_bar()
        self._build_tabs()
        self._refresh_status_bar()

    def switch_to_tab(self, index: int) -> None:
        self._tabs.setCurrentIndex(index)

    def tab_names(self) -> list[str]:
        return [self._tabs.tabText(index) for index in range(self._tabs.count())]

    def menu_action_texts(self) -> dict[str, list[str]]:
        return {
            menu_name: [action.text() for action in actions]
            for menu_name, actions in self._menu_actions.items()
        }

    def toolbar_action_texts(self) -> list[str]:
        return [action.text() for action in self._toolbar_actions]

    def status_snapshot(self) -> dict[str, str]:
        return {
            "project": self._project_status.text(),
            "flow": self._flow_status.text(),
            "effective_d": self._effective_d_status.text(),
        }

    def set_basic_info_save_handler(self, handler: Callable[[], Any] | None) -> None:
        self._basic_info_save_handler = handler

    def set_project_context(self, project_id: int | None, system_name: str, flow_no: str) -> None:
        self.current_project_id = project_id
        self.current_project_name = system_name.strip() or "未命名项目"
        self.current_flow_no = flow_no.strip() or "--"
        self._physical_page.set_project_id(project_id)
        self._refresh_status_bar()

    def physical_page(self) -> PhysicalPage:
        return self._physical_page

    def set_effective_d_count(self, count: int | None) -> None:
        self.effective_d_count = max(count or 0, 0)
        self._refresh_status_bar()

    def mark_scoring_dirty(self) -> None:
        self.is_scoring_dirty = True
        self.statusBar().showMessage("评分待更新")

    def trigger_action(self, action_text: str) -> None:
        if action_text in PROJECT_REQUIRED_ACTIONS and self.current_project_id is None:
            self.statusBar().showMessage("请先打开或保存项目")
            return
        self._notify_action(action_text)

    def _build_menus(self) -> None:
        for menu_name, action_texts in MENU_ACTION_TEXTS.items():
            menu = self.menuBar().addMenu(menu_name)
            self._menu_actions[menu_name] = []
            for text in action_texts:
                action = self._create_action(text)
                menu.addAction(action)
                self._menu_actions[menu_name].append(action)

    def _build_toolbar(self) -> None:
        toolbar = QToolBar("主工具栏", self)
        toolbar.setObjectName("mainToolbar")
        toolbar.setMovable(False)
        toolbar.setFloatable(False)
        toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        toolbar.setIconSize(QSize(18, 18))
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, toolbar)

        for text in TOOLBAR_ACTION_TEXTS:
            action = self._create_action(text)
            toolbar.addAction(action)
            button = toolbar.widgetForAction(action)
            if button is not None and text == "删除":
                button.setProperty("danger", True)
            self._toolbar_actions.append(action)

    def _build_status_bar(self) -> None:
        status_bar = QStatusBar(self)
        self.setStatusBar(status_bar)

        self._project_status = QLabel(self)
        self._flow_status = QLabel(self)
        self._effective_d_status = QLabel(self)
        self._project_status.setObjectName("statusProject")
        self._flow_status.setObjectName("statusFlow")
        self._effective_d_status.setObjectName("statusEffectiveD")

        status_bar.addPermanentWidget(self._project_status, 2)
        status_bar.addPermanentWidget(self._flow_status, 1)
        status_bar.addPermanentWidget(self._effective_d_status, 0)

    def _build_tabs(self) -> None:
        self._tabs = QTabWidget(self)
        self._tabs.setObjectName("workspaceTabs")
        self._tabs.setDocumentMode(True)
        self._tabs.addTab(self._build_basic_info_page(), TAB_NAMES[0])
        self._physical_page = PhysicalPage(self._physical_service, parent=self)
        self._tabs.addTab(self._physical_page, TAB_NAMES[1])
        self._tabs.addTab(
            self._build_domain_page(
                title="设备和计算安全",
                objects=["服务器", "终端设备", "密码设备", "运维管理"],
                detail_labels=["设备名称", "身份鉴别", "安全配置"],
            ),
            TAB_NAMES[2],
        )
        self._tabs.addTab(
            self._build_domain_page(
                title="网络和通信安全",
                objects=["边界链路", "通信信道", "远程接入", "子网区域"],
                detail_labels=["网络对象", "传输保护", "完整性措施"],
            ),
            TAB_NAMES[3],
        )
        self._tabs.addTab(
            self._build_domain_page(
                title="应用和数据安全",
                objects=["业务应用", "用户鉴别", "数据传输", "数据存储"],
                detail_labels=["应用对象", "数据类型", "密码应用措施"],
            ),
            TAB_NAMES[4],
        )
        self._tabs.addTab(self._build_scoring_page(), TAB_NAMES[5])
        self._tabs.currentChanged.connect(self._on_tab_changed)
        self.setCentralWidget(self._tabs)

    def _build_basic_info_page(self) -> QWidget:
        page = QWidget(self)
        page.setObjectName("basicInfoPage")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(18, 16, 18, 18)
        layout.setSpacing(14)

        layout.addWidget(self._page_header("被测系统基本信息", "保存"))

        form_frame = QFrame(page)
        form_frame.setObjectName("sectionPanel")
        form_layout = QFormLayout(form_frame)
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        form_layout.setFormAlignment(Qt.AlignmentFlag.AlignTop)
        form_layout.setHorizontalSpacing(16)
        form_layout.setVerticalSpacing(10)

        for label in ["系统名称", "单位名称", "测评机构", "流转编号"]:
            field = QLineEdit(form_frame)
            field.setMinimumHeight(30)
            form_layout.addRow(f"{label}：", field)

        layout.addWidget(form_frame)
        layout.addStretch(1)
        return page

    def _build_domain_page(
        self,
        *,
        title: str,
        objects: list[str],
        detail_labels: list[str],
    ) -> QWidget:
        page = QWidget(self)
        layout = QVBoxLayout(page)
        layout.setContentsMargins(18, 16, 18, 18)
        layout.setSpacing(14)
        layout.addWidget(self._page_header(title, "保存"))

        splitter = QSplitter(Qt.Orientation.Horizontal, page)
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(6)

        object_list = QListWidget(splitter)
        object_list.setObjectName("objectNavigator")
        object_list.addItems(objects)
        object_list.setCurrentRow(0)
        object_list.setMinimumWidth(240)
        object_list.setMaximumWidth(340)
        splitter.addWidget(object_list)

        detail_panel = QFrame(splitter)
        detail_panel.setObjectName("detailPanel")
        detail_layout = QFormLayout(detail_panel)
        detail_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        detail_layout.setHorizontalSpacing(16)
        detail_layout.setVerticalSpacing(10)

        for label in detail_labels:
            field = QLineEdit(detail_panel)
            field.setMinimumHeight(30)
            detail_layout.addRow(f"{label}：", field)

        conclusion = QComboBox(detail_panel)
        conclusion.addItems(["符合", "部分符合", "不符合", "不适用"])
        conclusion.setMinimumHeight(30)
        detail_layout.addRow("符合情况：", conclusion)

        risk_note = QPlainTextEdit(detail_panel)
        risk_note.setMinimumHeight(130)
        detail_layout.addRow("测评记录：", risk_note)
        splitter.addWidget(detail_panel)
        splitter.setSizes([280, 860])

        layout.addWidget(splitter, 1)
        return page

    def _build_scoring_page(self) -> QWidget:
        page = QWidget(self)
        layout = QVBoxLayout(page)
        layout.setContentsMargins(18, 16, 18, 18)
        layout.setSpacing(14)
        layout.addWidget(self._page_header("打分", "刷新"))

        table = QTableWidget(4, 4, page)
        table.setObjectName("scoringSummaryTable")
        table.setHorizontalHeaderLabels(["安全层面", "有效D", "层面得分", "风险等级"])
        for row, layer in enumerate(["物理和环境", "设备和计算", "网络和通信", "应用和数据"]):
            table.setItem(row, 0, QTableWidgetItem(layer))
            table.setItem(row, 1, QTableWidgetItem("0"))
            table.setItem(row, 2, QTableWidgetItem("--"))
            table.setItem(row, 3, QTableWidgetItem("--"))
        table.verticalHeader().setVisible(False)
        table.horizontalHeader().setStretchLastSection(True)
        table.setAlternatingRowColors(True)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(table, 1)
        return page

    def _page_header(self, title: str, action_text: str) -> QFrame:
        header = QFrame(self)
        header.setObjectName("pageHeader")
        layout = QHBoxLayout(header)
        layout.setContentsMargins(0, 0, 0, 0)

        label = QLabel(title, header)
        label.setObjectName("pageTitle")
        layout.addWidget(label, 1)

        action = self._create_action(action_text)
        button = self._toolbar_button_for_action(action, header)
        layout.addWidget(button)
        return header

    def _create_action(self, text: str) -> QAction:
        icon = self.style().standardIcon(ACTION_ICONS.get(text, QStyle.StandardPixmap.SP_FileIcon))
        action = QAction(icon, text, self)
        action.setToolTip(ACTION_TOOLTIPS.get(text, text))
        action.triggered.connect(
            lambda _checked=False, action_text=text: self.trigger_action(action_text)
        )
        return action

    def _toolbar_button_for_action(self, action: QAction, parent: QWidget) -> QWidget:
        from PySide6.QtWidgets import QToolButton

        button = QToolButton(parent)
        button.setDefaultAction(action)
        button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        return button

    def _notify_action(self, action_text: str) -> None:
        self.statusBar().showMessage(f"{action_text}入口已就绪", 2500)

    def _on_tab_changed(self, index: int) -> None:
        previous_index = self._last_tab_index
        self._last_tab_index = index
        if previous_index == 0 and index != 0:
            self._save_basic_info_silently()

    def _save_basic_info_silently(self) -> None:
        if self._basic_info_save_handler is None:
            return
        try:
            result = self._basic_info_save_handler()
        except Exception:
            self.statusBar().showMessage("基本信息保存失败")
            return
        self._sync_project_context_from_save_result(result)

    def _sync_project_context_from_save_result(self, result: Any) -> None:
        project_id = self._read_result_value(result, "project_id")
        if project_id is None:
            return
        system_name = self._read_result_value(result, "system_name") or self.current_project_name
        flow_no = self._read_result_value(result, "flow_no") or self.current_flow_no
        self.set_project_context(int(project_id), str(system_name), str(flow_no))

    def _read_result_value(self, result: Any, key: str) -> Any:
        if isinstance(result, dict):
            return result.get(key)
        return getattr(result, key, None)

    def _refresh_status_bar(self) -> None:
        self._project_status.setText(f"当前项目：{self.current_project_name}")
        self._flow_status.setText(f"流转编号：{self.current_flow_no}")
        self._effective_d_status.setText(f"有效D：{self.effective_d_count}")
