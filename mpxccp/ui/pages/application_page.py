from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSplitter,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from mpxccp.domain.enums import MeasureUnit
from mpxccp.services.application_service import (
    ApplicationObjectRecord,
    ApplicationService,
    ApplicationSubsystemRecord,
)
from mpxccp.services.network_service import NetworkService
from mpxccp.ui.widgets import EvidenceDialog, ProductListWidget, QuantWidget, RiskWidget

OBJECT_KINDS = [
    ("user", "应用用户"),
    ("access_control", "访问控制信息"),
    ("important_data", "重要数据"),
    ("business_action", "关键业务行为"),
]
UNIT_ORDER = [
    ("user_auth", "用户身份鉴别", MeasureUnit.APP_USER_AUTH.value, True, "user"),
    (
        "access_integrity",
        "访问控制信息完整性",
        MeasureUnit.APP_ACCESS_INTEGRITY.value,
        False,
        "access_control",
    ),
    (
        "transport_confidentiality",
        "重要数据传输机密性",
        MeasureUnit.DATA_TRANSPORT_CONFIDENTIALITY.value,
        True,
        "important_data",
    ),
    (
        "storage_confidentiality",
        "重要数据存储机密性",
        MeasureUnit.DATA_STORAGE_CONFIDENTIALITY.value,
        True,
        "important_data",
    ),
    (
        "transport_integrity",
        "重要数据传输完整性",
        MeasureUnit.DATA_TRANSPORT_INTEGRITY.value,
        False,
        "important_data",
    ),
    (
        "storage_integrity",
        "重要数据存储完整性",
        MeasureUnit.DATA_STORAGE_INTEGRITY.value,
        True,
        "important_data",
    ),
    (
        "non_repudiation",
        "关键业务行为不可否认性",
        MeasureUnit.BUSINESS_ACTION_NON_REPUDIATION.value,
        True,
        "business_action",
    ),
]
OBJECT_FIELD_LABELS = {
    "user": {
        "name": "用户名称",
        "role": "用户类型",
        "login_method": "登录方式",
        "interview_record": "现场访谈记录",
    },
    "access_control": {
        "name": "访问控制信息名称",
        "scope": "保护范围",
        "policy_description": "访问控制策略",
        "interview_record": "现场访谈记录",
    },
    "important_data": {
        "name": "数据名称",
        "data_type": "数据类别",
        "data_location": "数据位置",
        "business_description": "业务说明",
        "interview_record": "现场访谈记录",
    },
    "business_action": {
        "name": "业务行为名称",
        "description": "业务行为说明",
        "responsibility_subject": "责任主体",
        "interview_record": "现场访谈记录",
    },
}
UNIT_FIELD_LABELS = {
    "user_auth": [
        ("auth_methods", "鉴别方式", True, "text"),
        ("auth_data", "身份鉴别数据", True, "text"),
        ("crypto_usage", "密码技术使用情况", False, "usage_combo"),
        ("algorithm", "算法", False, "text"),
        ("compliance_status", "密码技术合规", False, "combo"),
        ("product_compliance", "密码产品合规", False, "combo"),
        ("key_management", "密钥管理", True, "text"),
    ],
    "access_integrity": [
        ("implementation_status", "实现状态", False, "implementation_status_combo"),
        ("access_control_policy", "访问控制信息", True, "text"),
        ("integrity_method", "完整性保护方式", True, "text"),
        ("algorithm", "算法", False, "text"),
        ("compliance_status", "密码技术合规", False, "combo"),
        ("product_compliance", "密码产品合规", False, "combo"),
        ("key_management", "密钥管理", True, "text"),
    ],
    "transport_confidentiality": [
        ("network_channel_id", "关联通信信道", False, "channel_combo"),
        ("implementation_status", "实现状态", False, "implementation_status_combo"),
        ("encryption_method", "传输保护方式", True, "text"),
        ("mechanism_description", "机制说明", True, "text"),
        ("image_path", "图片路径", False, "text"),
        ("algorithm", "算法", False, "text"),
        ("compliance_status", "密码技术合规", False, "combo"),
        ("product_compliance", "密码产品合规", False, "combo"),
        ("key_management", "密钥管理", True, "text"),
    ],
    "storage_confidentiality": [
        ("implementation_status", "实现状态", False, "implementation_status_combo"),
        ("storage_location", "存储位置", False, "text"),
        ("encryption_method", "存储保护方式", True, "text"),
        ("mechanism_description", "机制说明", True, "text"),
        ("image_path", "图片路径", False, "text"),
        ("algorithm", "算法", False, "text"),
        ("compliance_status", "密码技术合规", False, "combo"),
        ("product_compliance", "密码产品合规", False, "combo"),
        ("key_management", "密钥管理", True, "text"),
    ],
    "transport_integrity": [
        ("network_channel_id", "关联通信信道", False, "channel_combo"),
        ("implementation_status", "实现状态", False, "implementation_status_combo"),
        ("integrity_method", "传输完整性保护方式", True, "text"),
        ("mechanism_description", "机制说明", True, "text"),
        ("image_path", "图片路径", False, "text"),
        ("algorithm", "算法", False, "text"),
        ("compliance_status", "密码技术合规", False, "combo"),
        ("product_compliance", "密码产品合规", False, "combo"),
        ("key_management", "密钥管理", True, "text"),
    ],
    "storage_integrity": [
        ("implementation_status", "实现状态", False, "implementation_status_combo"),
        ("storage_location", "存储位置", False, "text"),
        ("integrity_method", "存储完整性保护方式", True, "text"),
        ("mechanism_description", "机制说明", True, "text"),
        ("image_path", "图片路径", False, "text"),
        ("algorithm", "算法", False, "text"),
        ("compliance_status", "密码技术合规", False, "combo"),
        ("product_compliance", "密码产品合规", False, "combo"),
        ("key_management", "密钥管理", True, "text"),
    ],
    "non_repudiation": [
        ("implementation_status", "实现状态", False, "implementation_status_combo"),
        ("signature_method", "签名或不可否认机制", True, "text"),
        ("timestamp_method", "时间戳机制", True, "text"),
        ("certificate_usage", "证书使用情况", True, "text"),
        ("mechanism_description", "机制说明", True, "text"),
        ("image_path", "图片路径", False, "text"),
        ("algorithm", "算法", False, "text"),
        ("compliance_status", "密码技术合规", False, "combo"),
        ("product_compliance", "密码产品合规", False, "combo"),
        ("key_management", "密钥管理", True, "text"),
    ],
}


class ApplicationPage(QWidget):
    scoring_dirty = Signal()

    def __init__(
        self,
        application_service: ApplicationService | None = None,
        *,
        network_service: NetworkService | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("applicationPage")
        self._service = application_service
        self._network_service = network_service
        self._project_id: int | None = None
        self._current_subsystem_id: int | None = None
        self._current_kind = "user"
        self._current_object_ids: dict[str, int | None] = {kind: None for kind, _ in OBJECT_KINDS}
        self._subsystems: list[ApplicationSubsystemRecord] = []
        self._objects: dict[str, list[ApplicationObjectRecord]] = {
            kind: [] for kind, _ in OBJECT_KINDS
        }
        self._current_details = None
        self._current_evidence_context: dict[str, object] | None = None
        self._loading = False
        self._selecting_subsystem = False
        self._selecting_object = False
        self._object_fields: dict[str, dict[str, QLineEdit | QPlainTextEdit]] = {}
        self._unit_fields: dict[str, dict[str, QLineEdit | QPlainTextEdit | QComboBox]] = {}
        self._quant_widgets: dict[str, QuantWidget] = {}
        self._risk_widgets: dict[str, RiskWidget] = {}
        self._product_widgets: dict[str, ProductListWidget] = {}
        self._evidence_buttons: dict[str, QPushButton] = {}
        self._object_lists: dict[str, QListWidget] = {}
        self._object_sections: dict[str, QGroupBox] = {}
        self._unit_sections: dict[str, QGroupBox] = {}
        self._current_evidence_dialog: EvidenceDialog | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 18)
        layout.setSpacing(14)
        layout.addWidget(self._header())
        layout.addWidget(self._body(), 1)

    def set_project_id(self, project_id: int | None) -> None:
        self._project_id = project_id
        self._current_subsystem_id = None
        self._current_object_ids = {kind: None for kind, _ in OBJECT_KINDS}
        self.refresh_network_channels()
        self.refresh_subsystems()

    def project_id(self) -> int | None:
        return self._project_id

    def subsystem_list(self) -> QListWidget:
        return self._subsystem_list

    def subsystem_names(self) -> list[str]:
        return [
            self._subsystem_list.item(index).text()
            for index in range(self._subsystem_list.count())
        ]

    def object_tab_names(self) -> list[str]:
        return [self._object_tabs.tabText(index) for index in range(self._object_tabs.count())]

    def current_kind(self) -> str:
        return self._current_kind

    def object_list(self, kind: str) -> QListWidget:
        return self._object_lists[kind]

    def object_names(self, kind: str) -> list[str]:
        object_list = self._object_lists[kind]
        return [object_list.item(index).text() for index in range(object_list.count())]

    def selected_subsystem_id(self) -> int | None:
        return self._current_subsystem_id

    def selected_object_id(self, kind: str | None = None) -> int | None:
        return self._current_object_ids[kind or self._current_kind]

    def object_field(self, kind: str, name: str) -> QLineEdit | QPlainTextEdit:
        return self._object_fields[kind][name]

    def unit_field(
        self,
        unit_key: str,
        name: str,
    ) -> QLineEdit | QPlainTextEdit | QComboBox:
        return self._unit_fields[unit_key][name]

    def quant_widget(self, unit_key: str) -> QuantWidget:
        return self._quant_widgets[unit_key]

    def risk_widget(self, unit_key: str) -> RiskWidget:
        return self._risk_widgets[unit_key]

    def product_widget(self, unit_key: str) -> ProductListWidget:
        return self._product_widgets[unit_key]

    def evidence_button(self, unit_key: str) -> QPushButton:
        return self._evidence_buttons[unit_key]

    def current_evidence_dialog(self) -> EvidenceDialog | None:
        return self._current_evidence_dialog

    def current_evidence_context(self) -> dict[str, object] | None:
        return self._current_evidence_context

    def refresh_network_channels(self) -> None:
        self._refresh_channel_combos()

    def sync_from_basic_subsystems(self) -> list[ApplicationSubsystemRecord]:
        self._require_ready()
        self.save_current_detail(silent=True)
        self.refresh_network_channels()
        synced = self._service.sync_from_basic_subsystems(self._project_id)
        self.refresh_subsystems()
        return synced

    def add_user(self, name: str | None = None) -> ApplicationObjectRecord:
        return self._add_object("user", name or "未命名应用用户")

    def add_access_control(self, name: str | None = None) -> ApplicationObjectRecord:
        return self._add_object("access_control", name or "未命名访问控制信息")

    def add_important_data(
        self,
        name: str | None = None,
        data_type: str | None = None,
    ) -> ApplicationObjectRecord:
        return self._add_object("important_data", name or "未命名重要数据", data_type or "")

    def add_business_action(self, name: str | None = None) -> ApplicationObjectRecord:
        return self._add_object("business_action", name or "未命名关键业务行为")

    def select_kind(self, kind: str) -> None:
        if kind == self._current_kind:
            self._select_tab(kind)
            return
        self.save_current_detail(silent=True)
        self._current_kind = kind
        self._select_tab(kind)
        self._show_kind(kind)
        current_id = self._current_object_ids[kind]
        if current_id is not None:
            self._load_details(kind, current_id)
        else:
            self._clear_detail()

    def select_subsystem(self, subsystem_id: int) -> None:
        if self._selecting_subsystem:
            return
        if self._current_subsystem_id == subsystem_id:
            self._select_subsystem_item(subsystem_id)
            return
        self.save_current_detail(silent=True)
        self._current_subsystem_id = subsystem_id
        self._current_object_ids = {kind: None for kind, _ in OBJECT_KINDS}
        self._select_subsystem_item(subsystem_id)
        self.refresh_objects()

    def select_object(self, kind: str, object_id: int) -> None:
        if self._selecting_object:
            return
        if self._current_kind != kind:
            self.select_kind(kind)
        if self._current_object_ids[kind] == object_id:
            self._select_object_item(kind, object_id)
            return
        self.save_current_detail(silent=True)
        self._select_object_item(kind, object_id)
        self._load_details(kind, object_id)

    def save_current_detail(self, *, silent: bool = True):
        if self._service is None or self._project_id is None or self._loading:
            return None
        object_id = self._current_object_ids[self._current_kind]
        if object_id is None:
            return None
        payload = self._collect_payload(self._current_kind)
        save_methods = {
            "user": self._service.save_user_detail,
            "access_control": self._service.save_access_control_detail,
            "important_data": self._service.save_important_data_detail,
            "business_action": self._service.save_business_action_detail,
        }
        result = save_methods[self._current_kind](object_id, payload, silent=silent)
        if result.success:
            self._update_current_object_item(str(result.payload.get("object_name", "")))
            self.scoring_dirty.emit()
        return result

    def delete_current_object(self, *, confirm: bool = False):
        if self._service is None:
            return None
        object_id = self._current_object_ids[self._current_kind]
        if object_id is None:
            return None
        if not confirm:
            answer = QMessageBox.question(
                self,
                "删除应用对象",
                f"确认删除“{self._current_object_name()}”？",
            )
            if answer != QMessageBox.StandardButton.Yes:
                return None
        result = self._service.delete_application_object(self._current_kind, object_id)
        if result.success:
            self._current_object_ids[self._current_kind] = None
            self.scoring_dirty.emit()
            self.refresh_objects(kind=self._current_kind)
        return result

    def refresh_subsystems(self) -> None:
        self._selecting_subsystem = True
        self._subsystem_list.blockSignals(True)
        try:
            self._subsystem_list.clear()
            self._subsystems = []
            if self._service is None or self._project_id is None:
                self._clear_all_object_lists()
                self._clear_detail()
                return
            self._subsystems = self._service.list_subsystems(self._project_id)
            for subsystem in self._subsystems:
                item = QListWidgetItem(subsystem.name)
                item.setData(Qt.ItemDataRole.UserRole, subsystem.id)
                self._subsystem_list.addItem(item)
        finally:
            self._subsystem_list.blockSignals(False)
            self._selecting_subsystem = False
        target_id = self._current_subsystem_id
        if target_id is None and self._subsystems:
            target_id = self._subsystems[0].id
        if target_id is None:
            self._clear_all_object_lists()
            self._clear_detail()
            return
        self._current_subsystem_id = target_id
        self._select_subsystem_item(target_id)
        self.refresh_objects()

    def refresh_objects(self, *, kind: str | None = None) -> None:
        kinds = [kind] if kind else [item[0] for item in OBJECT_KINDS]
        for current_kind in kinds:
            self._refresh_object_list(current_kind)
        current_id = self._current_object_ids[self._current_kind]
        if current_id is not None:
            self._load_details(self._current_kind, current_id)
        else:
            self._clear_detail()

    def _header(self) -> QFrame:
        header = QFrame(self)
        header.setObjectName("pageHeader")
        layout = QHBoxLayout(header)
        layout.setContentsMargins(0, 0, 0, 0)
        title = QLabel("应用和数据安全", header)
        title.setObjectName("pageTitle")
        layout.addWidget(title, 1)
        self._sync_button = QPushButton("同步子系统", header)
        self._delete_button = QPushButton("删除当前项", header)
        self._save_button = QPushButton("保存", header)
        layout.addWidget(self._sync_button)
        layout.addWidget(self._delete_button)
        layout.addWidget(self._save_button)
        self._sync_button.clicked.connect(lambda: self.sync_from_basic_subsystems())
        self._delete_button.clicked.connect(lambda: self.delete_current_object())
        self._save_button.clicked.connect(lambda: self.save_current_detail(silent=False))
        return header

    def _body(self) -> QSplitter:
        splitter = QSplitter(Qt.Orientation.Horizontal, self)
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(6)

        self._subsystem_list = QListWidget(splitter)
        self._subsystem_list.setObjectName("applicationSubsystemNavigator")
        self._subsystem_list.setWordWrap(True)
        self._subsystem_list.setMinimumWidth(240)
        self._subsystem_list.setMaximumWidth(360)
        self._subsystem_list.currentItemChanged.connect(self._on_subsystem_changed)
        splitter.addWidget(self._subsystem_list)

        right = QWidget(splitter)
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(10)
        right_layout.addWidget(self._object_tabs_widget())
        right_layout.addWidget(self._detail_scroll(), 1)
        splitter.addWidget(right)
        splitter.setSizes([280, 880])
        return splitter

    def _object_tabs_widget(self) -> QTabWidget:
        self._object_tabs = QTabWidget(self)
        self._object_tabs.setObjectName("applicationObjectTabs")
        for kind, title in OBJECT_KINDS:
            tab = QWidget(self._object_tabs)
            layout = QVBoxLayout(tab)
            layout.setContentsMargins(8, 8, 8, 8)
            actions = QHBoxLayout()
            add_button = QPushButton("新增", tab)
            actions.addWidget(add_button)
            actions.addStretch(1)
            layout.addLayout(actions)
            object_list = QListWidget(tab)
            object_list.setObjectName(f"{kind}ObjectList")
            object_list.currentItemChanged.connect(
                lambda current, _previous, item_kind=kind: self._on_object_changed(
                    item_kind,
                    current,
                )
            )
            layout.addWidget(object_list)
            self._object_lists[kind] = object_list
            self._object_tabs.addTab(tab, title)
            add_button.clicked.connect(
                lambda _checked=False, item_kind=kind: self._add_default(item_kind)
            )
        self._object_tabs.currentChanged.connect(self._on_tab_changed)
        return self._object_tabs

    def _detail_scroll(self) -> QScrollArea:
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        detail = QWidget(scroll)
        layout = QVBoxLayout(detail)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        for kind, _title in OBJECT_KINDS:
            section = self._object_section(kind)
            self._object_sections[kind] = section
            layout.addWidget(section)
        for unit_key, title, _unit_type, full_mode, _kind in UNIT_ORDER:
            section = self._unit_section(unit_key, title, full_mode)
            self._unit_sections[unit_key] = section
            layout.addWidget(section)
        layout.addStretch(1)
        scroll.setWidget(detail)
        self._show_kind("user")
        return scroll

    def _object_section(self, kind: str) -> QGroupBox:
        group = QGroupBox(dict(OBJECT_KINDS)[kind], self)
        layout = QFormLayout(group)
        layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        fields: dict[str, QLineEdit | QPlainTextEdit] = {}
        for field, label in OBJECT_FIELD_LABELS[kind].items():
            multiline_fields = {
                "interview_record",
                "policy_description",
                "business_description",
                "description",
            }
            if field in multiline_fields:
                widget = QPlainTextEdit(group)
                widget.setMinimumHeight(72)
            else:
                widget = QLineEdit(group)
                widget.setMinimumHeight(30)
            fields[field] = widget
            layout.addRow(f"{label}：", widget)
        self._object_fields[kind] = fields
        return group

    def _unit_section(self, unit_key: str, title: str, full_mode: bool) -> QGroupBox:
        group = QGroupBox(title, self)
        layout = QVBoxLayout(group)
        fields: dict[str, QLineEdit | QPlainTextEdit | QComboBox] = {}
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        for field, label, multiline, widget_type in UNIT_FIELD_LABELS[unit_key]:
            widget = self._create_field_widget(group, multiline=multiline, widget_type=widget_type)
            fields[field] = widget
            form.addRow(f"{label}：", widget)
        layout.addLayout(form)
        quant = QuantWidget(group)
        products = ProductListWidget(group)
        risk = RiskWidget(full_mode=full_mode, parent=group)
        self._connect_auto_rules(unit_key, fields, quant, products)
        evidence = QPushButton("提交测评证据", group)
        evidence.clicked.connect(
            lambda _checked=False, key=unit_key: self._show_evidence_ready(key)
        )
        layout.addWidget(quant)
        layout.addWidget(products)
        layout.addWidget(risk)
        layout.addWidget(evidence, alignment=Qt.AlignmentFlag.AlignRight)
        self._unit_fields[unit_key] = fields
        self._quant_widgets[unit_key] = quant
        self._product_widgets[unit_key] = products
        self._risk_widgets[unit_key] = risk
        self._evidence_buttons[unit_key] = evidence
        return group

    def _create_field_widget(
        self,
        parent: QWidget,
        *,
        multiline: bool,
        widget_type: str,
    ) -> QLineEdit | QPlainTextEdit | QComboBox:
        if widget_type == "combo":
            combo = QComboBox(parent)
            combo.addItems(["", "符合", "部分符合", "不符合", "不适用"])
            return combo
        if widget_type == "usage_combo":
            combo = QComboBox(parent)
            combo.addItems(["", "已使用", "未使用", "不适用", "不涉及"])
            return combo
        if widget_type == "implementation_status_combo":
            combo = QComboBox(parent)
            combo.addItems(["", "已实现", "未实现", "不适用", "不涉及"])
            return combo
        if widget_type == "channel_combo":
            combo = QComboBox(parent)
            combo.setProperty("valueMode", "data")
            combo.addItem("", None)
            return combo
        if multiline:
            editor = QPlainTextEdit(parent)
            editor.setMinimumHeight(72)
            return editor
        return QLineEdit(parent)

    def _connect_auto_rules(
        self,
        unit_key: str,
        fields: dict[str, QLineEdit | QPlainTextEdit | QComboBox],
        quant: QuantWidget,
        products: ProductListWidget,
    ) -> None:
        usage = fields.get("crypto_usage")
        if isinstance(usage, QComboBox):
            usage.currentTextChanged.connect(
                lambda _text, key=unit_key: self._refresh_quant_auto_rule(key)
            )
        implementation = fields.get("implementation_status")
        if isinstance(implementation, QComboBox):
            implementation.currentTextChanged.connect(
                lambda _text, key=unit_key: self._refresh_quant_auto_rule(key)
            )
        products.products_changed.connect(
            lambda _product_list, key=unit_key: self._refresh_quant_auto_rule(key)
        )

    def _refresh_quant_auto_rule(self, unit_key: str) -> None:
        if self._loading:
            return
        fields = self._unit_fields[unit_key]
        self._quant_widgets[unit_key].apply_status_rule(
            usage_status=self._combo_text(fields.get("crypto_usage")),
            implementation_status=self._combo_text(fields.get("implementation_status")),
            product_level=self._current_product_level(unit_key),
        )

    def _combo_text(self, widget: QLineEdit | QPlainTextEdit | QComboBox | None) -> str:
        return widget.currentText() if isinstance(widget, QComboBox) else ""

    def _current_product_level(self, unit_key: str) -> str:
        return next(
            (
                str(product.get("level", "")).strip()
                for product in self._product_widgets[unit_key].products()
                if str(product.get("level", "")).strip()
            ),
            "",
        )

    def _add_default(self, kind: str) -> None:
        if kind == "user":
            self.add_user()
        elif kind == "access_control":
            self.add_access_control()
        elif kind == "important_data":
            self.add_important_data()
        else:
            self.add_business_action()

    def _add_object(
        self,
        kind: str,
        name: str,
        data_type: str = "",
    ) -> ApplicationObjectRecord:
        self._require_ready()
        if self._current_subsystem_id is None:
            self.refresh_subsystems()
        if self._current_subsystem_id is None:
            raise RuntimeError("application subsystem is required")
        self.save_current_detail(silent=True)
        create_methods = {
            "user": lambda: self._service.create_user(self._current_subsystem_id, name),
            "access_control": lambda: self._service.create_access_control(
                self._current_subsystem_id,
                name,
            ),
            "important_data": lambda: self._service.create_important_data(
                self._current_subsystem_id,
                name,
                data_type,
            ),
            "business_action": lambda: self._service.create_business_action(
                self._current_subsystem_id,
                name,
            ),
        }
        record = create_methods[kind]()
        self._current_kind = kind
        self._select_tab(kind)
        self._refresh_object_list(kind, select_object_id=record.id)
        self._show_kind(kind)
        self._load_details(kind, record.id)
        return record

    def _refresh_object_list(
        self,
        kind: str,
        *,
        select_object_id: int | None = None,
    ) -> None:
        object_list = self._object_lists[kind]
        self._selecting_object = True
        object_list.blockSignals(True)
        try:
            object_list.clear()
            self._objects[kind] = []
            if self._service is None or self._current_subsystem_id is None:
                self._current_object_ids[kind] = None
                return
            list_methods = {
                "user": self._service.list_users,
                "access_control": self._service.list_access_controls,
                "important_data": self._service.list_important_data,
                "business_action": self._service.list_business_actions,
            }
            self._objects[kind] = list_methods[kind](self._current_subsystem_id)
            for record in self._objects[kind]:
                item = QListWidgetItem(record.name)
                item.setData(Qt.ItemDataRole.UserRole, record.id)
                object_list.addItem(item)
        finally:
            object_list.blockSignals(False)
            self._selecting_object = False
        target_id = select_object_id
        if target_id is None and self._objects[kind]:
            target_id = self._current_object_ids[kind] or self._objects[kind][0].id
        self._current_object_ids[kind] = target_id
        if target_id is not None:
            self._select_object_item(kind, target_id)

    def _load_details(self, kind: str, object_id: int) -> None:
        if self._service is None:
            return
        self.refresh_network_channels()
        load_methods = {
            "user": self._service.load_user_details,
            "access_control": self._service.load_access_control_details,
            "important_data": self._service.load_important_data_details,
            "business_action": self._service.load_business_action_details,
        }
        details = load_methods[kind](object_id)
        self._loading = True
        try:
            self._current_kind = kind
            self._current_object_ids[kind] = object_id
            self._current_details = details
            self._show_kind(kind)
            self._set_object_fields(kind, getattr(details, self._object_attr(kind)))
            for unit_key in self._units_for_kind(kind):
                self._set_unit_fields(unit_key, getattr(details, self._detail_attr(unit_key)))
        finally:
            self._loading = False

    def _set_object_fields(self, kind: str, record: ApplicationObjectRecord) -> None:
        for field, widget in self._object_fields[kind].items():
            value = getattr(record, field, None)
            if value is None and record.extra_data:
                value = record.extra_data.get(field, "")
            self._set_widget_value(widget, value or "")

    def _set_unit_fields(self, unit_key: str, detail) -> None:
        for field, widget in self._unit_fields[unit_key].items():
            value = getattr(detail, field, None)
            if value is None and detail.extra_data:
                value = detail.extra_data.get(field, "")
            self._set_widget_value(widget, value or "")
        self._risk_widgets[unit_key].set_values(
            {
                "risk_level": detail.risk_level,
                "risk_analysis": detail.risk_analysis,
                "mitigation_available": detail.extra_data.get("mitigation_available", False)
                if detail.extra_data
                else False,
                "mitigation_note": detail.extra_data.get("mitigation_note", "")
                if detail.extra_data
                else "",
                "mitigated_level": detail.extra_data.get("mitigated_level", "")
                if detail.extra_data
                else "",
                "rectification": detail.remediation,
            }
        )
        if detail.quant is not None:
            self._quant_widgets[unit_key].set_values(**detail.quant)
        self._product_widgets[unit_key].set_products(detail.products or [])

    def _collect_payload(self, kind: str) -> dict[str, Any]:
        return {
            "object": {
                field: self._widget_value(widget)
                for field, widget in self._object_fields[kind].items()
            },
            "units": {
                unit_key: self._collect_unit_payload(unit_key)
                for unit_key in self._units_for_kind(kind)
            },
        }

    def _collect_unit_payload(self, unit_key: str) -> dict[str, Any]:
        risk = self._risk_widgets[unit_key].values()
        return {
            **{
                field: self._widget_value(widget)
                for field, widget in self._unit_fields[unit_key].items()
            },
            "risk_level": risk["risk_level"],
            "risk_analysis": risk["risk_analysis"],
            "mitigation_available": risk["mitigation_available"],
            "mitigation_note": risk["mitigation_note"],
            "mitigated_level": risk["mitigated_level"],
            "remediation": risk["rectification"],
            "quant": self._quant_widgets[unit_key].values(),
            "products": self._product_widgets[unit_key].products(),
        }

    def _clear_all_object_lists(self) -> None:
        for object_list in self._object_lists.values():
            object_list.clear()
        self._objects = {kind: [] for kind, _ in OBJECT_KINDS}
        self._current_object_ids = {kind: None for kind, _ in OBJECT_KINDS}

    def _clear_detail(self) -> None:
        self._loading = True
        try:
            self._current_details = None
            self._current_evidence_context = None
            for fields in self._object_fields.values():
                for widget in fields.values():
                    self._set_widget_value(widget, "")
            for unit_key, fields in self._unit_fields.items():
                for widget in fields.values():
                    self._set_widget_value(widget, "")
                self._risk_widgets[unit_key].set_values({})
                self._product_widgets[unit_key].set_products([])
        finally:
            self._loading = False

    def _show_kind(self, kind: str) -> None:
        for section_kind, section in self._object_sections.items():
            section.setVisible(section_kind == kind)
        for unit_key, section in self._unit_sections.items():
            section.setVisible(self._unit_kind(unit_key) == kind)

    def _refresh_channel_combos(self) -> None:
        combos = [
            widget
            for fields in self._unit_fields.values()
            for widget in fields.values()
            if isinstance(widget, QComboBox) and widget.property("valueMode") == "data"
        ]
        if not combos:
            return
        channels: list[tuple[str, int]] = []
        if self._network_service is not None and self._project_id is not None:
            for subsystem in self._network_service.list_subsystems(self._project_id):
                for channel in self._network_service.list_channels(subsystem.id):
                    channels.append((f"{subsystem.name} / {channel.name}", channel.id))
        for combo in combos:
            current = combo.currentData()
            combo.blockSignals(True)
            try:
                combo.clear()
                combo.addItem("", None)
                for label, channel_id in channels:
                    combo.addItem(label, channel_id)
                self._set_combo_data(combo, current)
            finally:
                combo.blockSignals(False)

    def _on_subsystem_changed(
        self,
        current: QListWidgetItem | None,
        _previous: QListWidgetItem | None,
    ) -> None:
        if current is None or self._selecting_subsystem:
            return
        subsystem_id = current.data(Qt.ItemDataRole.UserRole)
        if subsystem_id is not None:
            self.select_subsystem(int(subsystem_id))

    def _on_object_changed(self, kind: str, current: QListWidgetItem | None) -> None:
        if current is None or self._selecting_object:
            return
        object_id = current.data(Qt.ItemDataRole.UserRole)
        if object_id is not None:
            self.select_object(kind, int(object_id))

    def _on_tab_changed(self, index: int) -> None:
        if index < 0:
            return
        kind = OBJECT_KINDS[index][0]
        if kind != self._current_kind:
            self.select_kind(kind)

    def _select_subsystem_item(self, subsystem_id: int) -> None:
        self._selecting_subsystem = True
        try:
            for row in range(self._subsystem_list.count()):
                item = self._subsystem_list.item(row)
                if item.data(Qt.ItemDataRole.UserRole) == subsystem_id:
                    self._subsystem_list.setCurrentRow(row)
                    break
        finally:
            self._selecting_subsystem = False

    def _select_object_item(self, kind: str, object_id: int) -> None:
        self._selecting_object = True
        try:
            object_list = self._object_lists[kind]
            for row in range(object_list.count()):
                item = object_list.item(row)
                if item.data(Qt.ItemDataRole.UserRole) == object_id:
                    object_list.setCurrentRow(row)
                    break
        finally:
            self._selecting_object = False

    def _select_tab(self, kind: str) -> None:
        for index, (candidate, _title) in enumerate(OBJECT_KINDS):
            if candidate == kind:
                self._object_tabs.setCurrentIndex(index)
                break

    def _update_current_object_item(self, name: str) -> None:
        if not name:
            return
        object_id = self._current_object_ids[self._current_kind]
        if object_id is None:
            return
        object_list = self._object_lists[self._current_kind]
        for row in range(object_list.count()):
            item = object_list.item(row)
            if item.data(Qt.ItemDataRole.UserRole) == object_id:
                item.setText(name)
                break

    def _set_widget_value(self, widget: QLineEdit | QPlainTextEdit | QComboBox, value) -> None:
        if isinstance(widget, QPlainTextEdit):
            widget.setPlainText(str(value))
        elif isinstance(widget, QComboBox):
            if widget.property("valueMode") == "data":
                self._set_combo_data(widget, value or None)
            else:
                index = widget.findText(str(value))
                widget.setCurrentIndex(index if index >= 0 else 0)
        else:
            widget.setText(str(value))

    def _widget_value(self, widget: QLineEdit | QPlainTextEdit | QComboBox) -> str | int | None:
        if isinstance(widget, QPlainTextEdit):
            return widget.toPlainText()
        if isinstance(widget, QComboBox):
            if widget.property("valueMode") == "data":
                return widget.currentData()
            return widget.currentText()
        return widget.text()

    def _set_combo_data(self, combo: QComboBox, value) -> None:
        for index in range(combo.count()):
            if combo.itemData(index) == value:
                combo.setCurrentIndex(index)
                return
        combo.setCurrentIndex(0)

    def _show_evidence_ready(self, unit_key: str) -> None:
        self._current_evidence_context = self._evidence_context(unit_key)
        dialog = EvidenceDialog(self)
        self._current_evidence_dialog = dialog
        dialog.open()

    def _evidence_context(self, unit_key: str) -> dict[str, object]:
        if self._project_id is None or self._current_details is None:
            return {}
        detail = getattr(self._current_details, self._detail_attr(unit_key))
        unit_type = next(unit_type for key, _title, unit_type, *_ in UNIT_ORDER if key == unit_key)
        return {
            "project_id": self._project_id,
            "unit_type": unit_type,
            "related_id": detail.id,
            "object_name": self._current_object_name(),
        }

    def _current_object_name(self) -> str:
        object_list = self._object_lists[self._current_kind]
        current = object_list.currentItem()
        if current is not None:
            return current.text()
        if self._current_details is None:
            return ""
        record = getattr(self._current_details, self._object_attr(self._current_kind))
        return record.name

    def _object_attr(self, kind: str) -> str:
        return {
            "user": "user",
            "access_control": "access_control",
            "important_data": "data",
            "business_action": "action",
        }[kind]

    def _detail_attr(self, unit_key: str) -> str:
        return {
            "user_auth": "auth",
            "access_integrity": "integrity",
            "transport_confidentiality": "transport_confidentiality",
            "storage_confidentiality": "storage_confidentiality",
            "transport_integrity": "transport_integrity",
            "storage_integrity": "storage_integrity",
            "non_repudiation": "non_repudiation",
        }[unit_key]

    def _units_for_kind(self, kind: str) -> list[str]:
        return [unit_key for unit_key, *_rest, unit_kind in UNIT_ORDER if unit_kind == kind]

    def _unit_kind(self, unit_key: str) -> str:
        return next(unit_kind for key, *_rest, unit_kind in UNIT_ORDER if key == unit_key)

    def _require_ready(self) -> None:
        if self._service is None:
            raise RuntimeError("application service is required")
        if self._project_id is None:
            raise RuntimeError("project_id is required")
