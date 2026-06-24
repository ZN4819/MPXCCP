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
    QVBoxLayout,
    QWidget,
)

from mpxccp.domain.enums import MeasureUnit
from mpxccp.services.network_service import (
    NetworkChannelRecord,
    NetworkService,
    NetworkSubsystemRecord,
)
from mpxccp.ui.widgets import DateInput, EvidenceDialog, ProductListWidget, QuantWidget, RiskWidget

UNIT_ORDER = [
    ("auth", "通信实体身份鉴别", MeasureUnit.NETWORK_AUTH.value, True),
    ("integrity", "通信过程数据完整性", MeasureUnit.NETWORK_INTEGRITY.value, True),
    (
        "confidentiality",
        "通信过程数据机密性",
        MeasureUnit.NETWORK_CONFIDENTIALITY.value,
        True,
    ),
    ("boundary", "网络边界访问控制完整性", MeasureUnit.NETWORK_BOUNDARY_INTEGRITY.value, False),
]
CHANNEL_FIELD_LABELS = {
    "name": "通信信道名称",
    "source": "访问来源",
    "target": "访问目标",
    "protocol": "通信协议",
    "network_environment": "网络环境",
    "client_type": "客户端形态",
    "server_type": "服务端形态",
    "interview_record": "现场访谈记录",
    "description": "信道说明",
}
UNIT_FIELD_LABELS = {
    "auth": [
        ("implementation_status", "实现状态", False, "implementation_status_combo"),
        ("auth_methods", "鉴别方式", True, "text"),
        ("crypto_usage", "密码技术使用情况", False, "usage_combo"),
        ("algorithm", "实现算法", False, "text"),
        ("compliance_status", "密码技术合规", False, "combo"),
        ("product_compliance", "密码产品合规", False, "combo"),
        ("certificate_usage", "证书使用情况", True, "text"),
        ("certificate_algorithm", "证书算法", False, "text"),
        ("certificate_source", "证书来源", False, "text"),
        ("certificate_start_date", "证书起始日期", False, "date"),
        ("certificate_end_date", "证书失效日期", False, "date"),
        ("certificate_other_info", "证书其他信息", True, "text"),
    ],
    "integrity": [
        ("implementation_status", "实现状态", False, "implementation_status_combo"),
        ("integrity_method", "完整性保护方式", True, "text"),
        ("crypto_usage", "密码技术使用情况", False, "usage_combo"),
        ("algorithm", "完整性算法", False, "text"),
        ("compliance_status", "密码技术合规", False, "combo"),
        ("product_compliance", "密码产品合规", False, "combo"),
        ("certificate_usage", "证书使用情况", True, "text"),
    ],
    "confidentiality": [
        ("implementation_status", "实现状态", False, "implementation_status_combo"),
        ("encryption_method", "机密性保护方式", True, "text"),
        ("crypto_usage", "密码技术使用情况", False, "usage_combo"),
        ("algorithm", "机密性算法", False, "text"),
        ("compliance_status", "密码技术合规", False, "combo"),
        ("product_compliance", "密码产品合规", False, "combo"),
        ("certificate_usage", "证书使用情况", True, "text"),
    ],
    "boundary": [
        ("implementation_status", "实现状态", False, "implementation_status_combo"),
        ("boundary_device", "边界访问控制信息", True, "text"),
        ("integrity_method", "完整性保护方式", True, "text"),
        ("boundary_product_level", "产品认证等级", False, "product_level_combo"),
        ("algorithm", "实现算法", False, "text"),
        ("compliance_status", "技术合规", False, "combo"),
        ("product_compliance", "产品合规", False, "combo"),
    ],
}


class NetworkPage(QWidget):
    scoring_dirty = Signal()

    def __init__(
        self,
        network_service: NetworkService | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("networkPage")
        self._service = network_service
        self._project_id: int | None = None
        self._current_subsystem_id: int | None = None
        self._current_channel_id: int | None = None
        self._subsystems: list[NetworkSubsystemRecord] = []
        self._channels: list[NetworkChannelRecord] = []
        self._current_details = None
        self._current_evidence_context: dict[str, object] | None = None
        self._loading = False
        self._selecting_subsystem = False
        self._selecting_channel = False
        self._channel_fields: dict[str, QLineEdit | QPlainTextEdit] = {}
        self._unit_fields: dict[str, dict[str, QLineEdit | QPlainTextEdit | QComboBox | DateInput]]
        self._unit_fields = {}
        self._quant_widgets: dict[str, QuantWidget] = {}
        self._risk_widgets: dict[str, RiskWidget] = {}
        self._product_widgets: dict[str, ProductListWidget] = {}
        self._evidence_buttons: list[QPushButton] = []
        self._current_evidence_dialog: EvidenceDialog | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 18)
        layout.setSpacing(14)
        layout.addWidget(self._header())
        layout.addWidget(self._body(), 1)

    def set_project_id(self, project_id: int | None) -> None:
        self._project_id = project_id
        self._current_subsystem_id = None
        self._current_channel_id = None
        self.refresh_subsystems()

    def project_id(self) -> int | None:
        return self._project_id

    def subsystem_list(self) -> QListWidget:
        return self._subsystem_list

    def channel_list(self) -> QListWidget:
        return self._channel_list

    def subsystem_names(self) -> list[str]:
        return [
            self._subsystem_list.item(index).text()
            for index in range(self._subsystem_list.count())
        ]

    def channel_names(self) -> list[str]:
        return [
            self._channel_list.item(index).text()
            for index in range(self._channel_list.count())
        ]

    def selected_subsystem_id(self) -> int | None:
        return self._current_subsystem_id

    def selected_channel_id(self) -> int | None:
        return self._current_channel_id

    def channel_field(self, name: str) -> QLineEdit | QPlainTextEdit:
        return self._channel_fields[name]

    def unit_field(
        self,
        unit_key: str,
        name: str,
    ) -> QLineEdit | QPlainTextEdit | QComboBox | DateInput:
        return self._unit_fields[unit_key][name]

    def quant_widget(self, unit_key: str) -> QuantWidget:
        return self._quant_widgets[unit_key]

    def product_widget(self, unit_key: str) -> ProductListWidget | None:
        return self._product_widgets.get(unit_key)

    def evidence_buttons(self) -> list[QPushButton]:
        return self._evidence_buttons

    def current_evidence_dialog(self) -> EvidenceDialog | None:
        return self._current_evidence_dialog

    def current_evidence_context(self) -> dict[str, object] | None:
        return self._current_evidence_context

    def delete_confirmation_text(self) -> str:
        return f"确认删除通信信道“{self._current_channel_name()}”？"

    def sync_from_basic_subsystems(self) -> list[NetworkSubsystemRecord]:
        self._require_ready()
        self.save_current_detail(silent=True)
        synced = self._service.sync_from_basic_subsystems(self._project_id)
        self.refresh_subsystems()
        return synced

    def add_channel(self, name: str | None = None) -> NetworkChannelRecord:
        self._require_ready()
        if self._current_subsystem_id is None:
            self.refresh_subsystems()
        if self._current_subsystem_id is None:
            raise RuntimeError("network subsystem is required")
        self.save_current_detail(silent=True)
        channel = self._service.create_channel(
            self._current_subsystem_id,
            str(name or "未命名通信信道"),
        )
        self.scoring_dirty.emit()
        self.refresh_channels(select_channel_id=channel.id)
        return channel

    def select_subsystem(self, subsystem_id: int) -> None:
        if self._selecting_subsystem:
            return
        if self._current_subsystem_id == subsystem_id:
            self._select_subsystem_item(subsystem_id)
            return
        if self._current_channel_id is not None and not self._loading:
            self.save_current_detail(silent=True)
        self._current_subsystem_id = subsystem_id
        self._current_channel_id = None
        self._select_subsystem_item(subsystem_id)
        self.refresh_channels()

    def select_channel(self, channel_id: int) -> None:
        if self._selecting_channel:
            return
        if self._current_channel_id == channel_id:
            self._select_channel_item(channel_id)
            return
        if self._current_channel_id is not None and not self._loading:
            self.save_current_detail(silent=True)
        self._select_channel_item(channel_id)
        self._load_details(channel_id)

    def save_current_detail(self, *, silent: bool = True):
        if (
            self._service is None
            or self._project_id is None
            or self._current_channel_id is None
            or self._loading
        ):
            return None
        result = self._service.save_channel_detail(
            self._current_channel_id,
            self._collect_payload(),
            silent=silent,
        )
        if result.success:
            self._update_current_channel_item(str(result.payload.get("channel_name", "")))
            self.scoring_dirty.emit()
        return result

    def delete_current_channel(self, *, confirm: bool = False):
        if self._service is None or self._current_channel_id is None:
            return None
        if not confirm:
            answer = QMessageBox.question(
                self,
                "删除通信信道",
                self.delete_confirmation_text(),
            )
            if answer != QMessageBox.StandardButton.Yes:
                return None
        result = self._service.delete_channel(self._current_channel_id)
        if result.success:
            self._current_channel_id = None
            self._current_details = None
            self._current_evidence_context = None
            self.scoring_dirty.emit()
            self.refresh_channels()
        return result

    def refresh_subsystems(
        self,
        *,
        select_subsystem_id: int | None = None,
        reload_channels: bool = True,
    ) -> None:
        self._selecting_subsystem = True
        self._subsystem_list.blockSignals(True)
        try:
            self._subsystem_list.clear()
            self._subsystems = []
            if self._service is None or self._project_id is None:
                self._clear_channels()
                return
            self._subsystems = self._service.list_subsystems(self._project_id)
            for subsystem in self._subsystems:
                item = QListWidgetItem(subsystem.name)
                item.setData(Qt.ItemDataRole.UserRole, subsystem.id)
                self._subsystem_list.addItem(item)
        finally:
            self._subsystem_list.blockSignals(False)
            self._selecting_subsystem = False
        target_id = select_subsystem_id
        if target_id is None and self._subsystems:
            target_id = self._current_subsystem_id or self._subsystems[0].id
        if target_id is None:
            self._clear_channels()
            return
        self._current_subsystem_id = target_id
        self._select_subsystem_item(target_id)
        if reload_channels:
            self.refresh_channels()

    def refresh_channels(
        self,
        *,
        select_channel_id: int | None = None,
        reload_detail: bool = True,
    ) -> None:
        self._selecting_channel = True
        self._channel_list.blockSignals(True)
        try:
            self._channel_list.clear()
            self._channels = []
            if self._service is None or self._current_subsystem_id is None:
                self._clear_detail()
                return
            self._channels = self._service.list_channels(self._current_subsystem_id)
            for channel in self._channels:
                item = QListWidgetItem(channel.name)
                item.setData(Qt.ItemDataRole.UserRole, channel.id)
                self._channel_list.addItem(item)
        finally:
            self._channel_list.blockSignals(False)
            self._selecting_channel = False
        target_id = select_channel_id
        if target_id is None and self._channels:
            target_id = self._current_channel_id or self._channels[0].id
        if target_id is None:
            self._clear_detail()
            return
        self._select_channel_item(target_id)
        if reload_detail:
            self._load_details(target_id)

    def _header(self) -> QFrame:
        header = QFrame(self)
        header.setObjectName("pageHeader")
        layout = QHBoxLayout(header)
        layout.setContentsMargins(0, 0, 0, 0)
        title = QLabel("网络和通信安全", header)
        title.setObjectName("pageTitle")
        layout.addWidget(title, 1)
        self._sync_button = QPushButton("同步子系统", header)
        self._add_button = QPushButton("新增信道", header)
        self._delete_button = QPushButton("删除信道", header)
        self._save_button = QPushButton("保存", header)
        layout.addWidget(self._sync_button)
        layout.addWidget(self._add_button)
        layout.addWidget(self._delete_button)
        layout.addWidget(self._save_button)
        self._sync_button.clicked.connect(lambda: self.sync_from_basic_subsystems())
        self._add_button.clicked.connect(lambda: self.add_channel("未命名通信信道"))
        self._delete_button.clicked.connect(lambda: self.delete_current_channel())
        self._save_button.clicked.connect(lambda: self.save_current_detail(silent=False))
        return header

    def _body(self) -> QSplitter:
        splitter = QSplitter(Qt.Orientation.Horizontal, self)
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(6)

        navigator = QWidget(splitter)
        navigator_layout = QVBoxLayout(navigator)
        navigator_layout.setContentsMargins(0, 0, 0, 0)
        navigator_layout.setSpacing(8)
        navigator_layout.addWidget(QLabel("子系统", navigator))
        self._subsystem_list = QListWidget(navigator)
        self._subsystem_list.setObjectName("subsystemNavigator")
        self._subsystem_list.setWordWrap(True)
        self._subsystem_list.currentItemChanged.connect(self._on_subsystem_item_changed)
        navigator_layout.addWidget(self._subsystem_list, 1)
        navigator_layout.addWidget(QLabel("通信信道", navigator))
        self._channel_list = QListWidget(navigator)
        self._channel_list.setObjectName("channelNavigator")
        self._channel_list.setWordWrap(True)
        self._channel_list.currentItemChanged.connect(self._on_channel_item_changed)
        navigator_layout.addWidget(self._channel_list, 2)
        navigator.setMinimumWidth(260)
        navigator.setMaximumWidth(380)
        splitter.addWidget(navigator)

        scroll = QScrollArea(splitter)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        detail = QWidget(scroll)
        detail_layout = QVBoxLayout(detail)
        detail_layout.setContentsMargins(0, 0, 0, 0)
        detail_layout.setSpacing(12)
        detail_layout.addWidget(self._channel_section())
        for unit_key, title, _unit_type, full_mode in UNIT_ORDER:
            detail_layout.addWidget(self._unit_section(unit_key, title, full_mode))
        detail_layout.addStretch(1)
        scroll.setWidget(detail)
        splitter.addWidget(scroll)
        splitter.setSizes([300, 860])
        return splitter

    def _channel_section(self) -> QGroupBox:
        group = QGroupBox("通信信道基本信息", self)
        layout = QFormLayout(group)
        layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        for field, label in CHANNEL_FIELD_LABELS.items():
            if field in {"interview_record", "description"}:
                widget = QPlainTextEdit(group)
                widget.setMinimumHeight(82)
            else:
                widget = QLineEdit(group)
                widget.setMinimumHeight(30)
            self._channel_fields[field] = widget
            layout.addRow(f"{label}：", widget)
        return group

    def _unit_section(self, unit_key: str, title: str, full_mode: bool) -> QGroupBox:
        group = QGroupBox(title, self)
        layout = QVBoxLayout(group)
        fields: dict[str, QLineEdit | QPlainTextEdit | QComboBox | DateInput] = {}
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        for field, label, multiline, widget_type in UNIT_FIELD_LABELS[unit_key]:
            widget = self._create_field_widget(group, multiline=multiline, widget_type=widget_type)
            fields[field] = widget
            form.addRow(f"{label}：", widget)
        layout.addLayout(form)

        quant = QuantWidget(group)
        risk = RiskWidget(full_mode=full_mode, parent=group)
        products: ProductListWidget | None = None
        if unit_key != "boundary":
            products = ProductListWidget(group)
            self._connect_auto_rules(unit_key, fields, quant, products)
            layout.addWidget(products)
            self._product_widgets[unit_key] = products
        else:
            self._connect_auto_rules(unit_key, fields, quant, None)
        evidence = QPushButton("提交测评证据", group)
        evidence.clicked.connect(
            lambda _checked=False, key=unit_key: self._show_evidence_ready(key)
        )

        layout.addWidget(quant)
        layout.addWidget(risk)
        layout.addWidget(evidence, alignment=Qt.AlignmentFlag.AlignRight)

        self._unit_fields[unit_key] = fields
        self._quant_widgets[unit_key] = quant
        self._risk_widgets[unit_key] = risk
        self._evidence_buttons.append(evidence)
        return group

    def _create_field_widget(
        self,
        parent: QWidget,
        *,
        multiline: bool,
        widget_type: str,
    ) -> QLineEdit | QPlainTextEdit | QComboBox | DateInput:
        if widget_type == "date":
            return DateInput(parent)
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
        if widget_type == "product_level_combo":
            combo = QComboBox(parent)
            combo.addItems(["", "一级", "二级", "三级"])
            return combo
        if multiline:
            editor = QPlainTextEdit(parent)
            editor.setMinimumHeight(72)
            return editor
        return QLineEdit(parent)

    def _connect_auto_rules(
        self,
        unit_key: str,
        fields: dict[str, QLineEdit | QPlainTextEdit | QComboBox | DateInput],
        quant: QuantWidget,
        products: ProductListWidget | None,
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
        product_level = fields.get("boundary_product_level")
        if isinstance(product_level, QComboBox):
            product_level.currentTextChanged.connect(
                lambda _text, key=unit_key: self._refresh_quant_auto_rule(key)
            )
        if products is not None:
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

    def _combo_text(
        self,
        widget: QLineEdit | QPlainTextEdit | QComboBox | DateInput | None,
    ) -> str:
        return widget.currentText() if isinstance(widget, QComboBox) else ""

    def _current_product_level(self, unit_key: str) -> str:
        fields = self._unit_fields[unit_key]
        selected_level = self._combo_text(fields.get("boundary_product_level"))
        if selected_level:
            return selected_level
        product_widget = self._product_widgets.get(unit_key)
        if product_widget is None:
            return ""
        return next(
            (
                str(product.get("level", "")).strip()
                for product in product_widget.products()
                if str(product.get("level", "")).strip()
            ),
            "",
        )

    def _load_details(self, channel_id: int) -> None:
        if self._service is None:
            return
        details = self._service.load_details(channel_id)
        self._loading = True
        try:
            self._current_channel_id = channel_id
            self._current_details = details
            self._set_channel_fields(details.channel)
            for unit_key, *_ in UNIT_ORDER:
                self._set_unit_fields(unit_key, getattr(details, unit_key))
        finally:
            self._loading = False

    def _set_channel_fields(self, channel: NetworkChannelRecord) -> None:
        for field in CHANNEL_FIELD_LABELS:
            self._set_widget_value(self._channel_fields[field], getattr(channel, field))

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
        product_widget = self._product_widgets.get(unit_key)
        if product_widget is not None:
            product_widget.set_products(detail.products or [])

    def _collect_payload(self) -> dict[str, Any]:
        return {
            "channel": {
                field: self._widget_value(widget)
                for field, widget in self._channel_fields.items()
            },
            "units": {
                unit_key: self._collect_unit_payload(unit_key) for unit_key, *_ in UNIT_ORDER
            },
        }

    def _collect_unit_payload(self, unit_key: str) -> dict[str, Any]:
        risk = self._risk_widgets[unit_key].values()
        payload: dict[str, Any] = {
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
        }
        product_widget = self._product_widgets.get(unit_key)
        if product_widget is not None:
            payload["products"] = product_widget.products()
        return payload

    def _clear_channels(self) -> None:
        self._channel_list.clear()
        self._channels = []
        self._current_subsystem_id = None
        self._clear_detail()

    def _clear_detail(self) -> None:
        self._loading = True
        try:
            self._current_channel_id = None
            self._current_details = None
            self._current_evidence_context = None
            for widget in self._channel_fields.values():
                self._set_widget_value(widget, "")
            for unit_key in self._unit_fields:
                for widget in self._unit_fields[unit_key].values():
                    self._set_widget_value(widget, "")
                self._risk_widgets[unit_key].set_values({})
                product_widget = self._product_widgets.get(unit_key)
                if product_widget is not None:
                    product_widget.set_products([])
        finally:
            self._loading = False

    def _on_subsystem_item_changed(
        self,
        current: QListWidgetItem | None,
        _previous: QListWidgetItem | None,
    ) -> None:
        if current is None or self._selecting_subsystem:
            return
        subsystem_id = current.data(Qt.ItemDataRole.UserRole)
        if subsystem_id is not None:
            self.select_subsystem(int(subsystem_id))

    def _on_channel_item_changed(
        self,
        current: QListWidgetItem | None,
        _previous: QListWidgetItem | None,
    ) -> None:
        if current is None or self._selecting_channel:
            return
        channel_id = current.data(Qt.ItemDataRole.UserRole)
        if channel_id is not None:
            self.select_channel(int(channel_id))

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

    def _select_channel_item(self, channel_id: int) -> None:
        self._selecting_channel = True
        try:
            for row in range(self._channel_list.count()):
                item = self._channel_list.item(row)
                if item.data(Qt.ItemDataRole.UserRole) == channel_id:
                    self._channel_list.setCurrentRow(row)
                    break
        finally:
            self._selecting_channel = False

    def _update_current_channel_item(self, name: str) -> None:
        if self._current_channel_id is None or not name:
            return
        for row in range(self._channel_list.count()):
            item = self._channel_list.item(row)
            if item.data(Qt.ItemDataRole.UserRole) == self._current_channel_id:
                item.setText(name)
                break

    def _set_widget_value(
        self,
        widget: QLineEdit | QPlainTextEdit | QComboBox | DateInput,
        value: str,
    ) -> None:
        if isinstance(widget, DateInput):
            widget.set_date(value)
        elif isinstance(widget, QPlainTextEdit):
            widget.setPlainText(value)
        elif isinstance(widget, QComboBox):
            index = widget.findText(value)
            widget.setCurrentIndex(index if index >= 0 else 0)
        else:
            widget.setText(value)

    def _widget_value(self, widget: QLineEdit | QPlainTextEdit | QComboBox | DateInput) -> str:
        if isinstance(widget, DateInput):
            widget.commit_text()
            return widget.date_text()
        if isinstance(widget, QPlainTextEdit):
            return widget.toPlainText()
        if isinstance(widget, QComboBox):
            return widget.currentText()
        return widget.text()

    def _show_evidence_ready(self, unit_key: str) -> None:
        self._current_evidence_context = self._evidence_context(unit_key)
        dialog = EvidenceDialog(self)
        self._current_evidence_dialog = dialog
        dialog.open()

    def _evidence_context(self, unit_key: str) -> dict[str, object]:
        if self._project_id is None or self._current_details is None:
            return {}
        unit_type = next(unit_type for key, _title, unit_type, *_ in UNIT_ORDER if key == unit_key)
        detail = getattr(self._current_details, unit_key)
        return {
            "project_id": self._project_id,
            "unit_type": unit_type,
            "related_id": detail.id,
            "object_name": self._current_channel_name(),
        }

    def _current_channel_name(self) -> str:
        current = self._channel_list.currentItem()
        if current is not None:
            return current.text()
        if self._current_details is not None:
            return self._current_details.channel.name
        return ""

    def _require_ready(self) -> None:
        if self._service is None:
            raise RuntimeError("network service is required")
        if self._project_id is None:
            raise RuntimeError("project_id is required")
