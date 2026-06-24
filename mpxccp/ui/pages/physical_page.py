from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt
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
from mpxccp.services.physical_service import PhysicalObjectRecord, PhysicalService
from mpxccp.ui.widgets import EvidenceDialog, ProductListWidget, QuantWidget, RiskWidget

UNIT_ORDER = [
    ("auth", "物理访问身份鉴别", MeasureUnit.PHYSICAL_AUTH.value, True),
    ("access_integrity", "门禁记录完整性", MeasureUnit.PHYSICAL_ACCESS_INTEGRITY.value, False),
    ("video_integrity", "视频记录完整性", MeasureUnit.PHYSICAL_VIDEO_INTEGRITY.value, False),
]
OBJECT_FIELD_LABELS = {
    "name": "测评对象名称",
    "location": "物理地址",
    "access_control_system": "门禁系统",
    "video_system": "视频监控系统",
    "interview_record": "现场访谈记录",
}


class PhysicalPage(QWidget):
    def __init__(
        self,
        physical_service: PhysicalService | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("physicalPage")
        self._service = physical_service
        self._project_id: int | None = None
        self._current_object_id: int | None = None
        self._objects: list[PhysicalObjectRecord] = []
        self._current_details = None
        self._current_evidence_context: dict[str, object] | None = None
        self._loading = False
        self._selecting = False
        self._object_fields: dict[str, QLineEdit | QPlainTextEdit] = {}
        self._unit_fields: dict[str, dict[str, QLineEdit | QPlainTextEdit | QComboBox]] = {}
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
        self._current_object_id = None
        self.refresh_objects()

    def object_list(self) -> QListWidget:
        return self._object_list

    def object_names(self) -> list[str]:
        return [self._object_list.item(index).text() for index in range(self._object_list.count())]

    def selected_object_id(self) -> int | None:
        return self._current_object_id

    def project_id(self) -> int | None:
        return self._project_id

    def object_field(self, name: str) -> QLineEdit | QPlainTextEdit:
        return self._object_fields[name]

    def evidence_buttons(self) -> list[QPushButton]:
        return self._evidence_buttons

    def current_evidence_dialog(self) -> EvidenceDialog | None:
        return self._current_evidence_dialog

    def current_evidence_context(self) -> dict[str, object] | None:
        return self._current_evidence_context

    def delete_confirmation_text(self) -> str:
        return f"确认删除物理测评对象“{self._current_object_name()}”？"

    def add_object(self, name: str | None = None) -> PhysicalObjectRecord:
        self._require_ready()
        self.save_current_detail(silent=True)
        obj = self._service.create_object(self._project_id, str(name or "未命名物理对象"))
        self.refresh_objects(select_object_id=obj.id)
        return obj

    def select_object(self, object_id: int) -> None:
        if self._selecting:
            return
        if self._current_object_id == object_id:
            self._select_item(object_id)
            return
        if self._current_object_id is not None and not self._loading:
            self.save_current_detail(silent=True)
        self._select_item(object_id)
        self._load_details(object_id)

    def save_current_detail(self, *, silent: bool = True):
        if (
            self._service is None
            or self._project_id is None
            or self._current_object_id is None
            or self._loading
        ):
            return None
        result = self._service.save_detail(
            self._current_object_id,
            self._collect_payload(),
            silent=silent,
        )
        if result.success:
            self._update_current_list_item(str(result.payload.get("object_name", "")))
        return result

    def delete_current_object(self, *, confirm: bool = False):
        if self._service is None or self._current_object_id is None:
            return None
        if not confirm:
            answer = QMessageBox.question(
                self,
                "删除物理测评对象",
                self.delete_confirmation_text(),
            )
            if answer != QMessageBox.StandardButton.Yes:
                return None
        result = self._service.delete_object(self._current_object_id)
        if result.success:
            self._current_object_id = None
            self._current_details = None
            self._current_evidence_context = None
            self.refresh_objects()
        return result

    def refresh_objects(
        self,
        *,
        select_object_id: int | None = None,
        reload_detail: bool = True,
    ) -> None:
        self._selecting = True
        self._object_list.blockSignals(True)
        try:
            self._object_list.clear()
            self._objects = []
            if self._service is None or self._project_id is None:
                self._clear_detail()
                return
            self._objects = self._service.list_objects(self._project_id)
            for obj in self._objects:
                item = QListWidgetItem(obj.name)
                item.setData(Qt.ItemDataRole.UserRole, obj.id)
                self._object_list.addItem(item)
        finally:
            self._object_list.blockSignals(False)
            self._selecting = False
        target_id = select_object_id
        if target_id is None and self._objects:
            target_id = self._current_object_id or self._objects[0].id
        if target_id is None:
            self._clear_detail()
            return
        self._select_item(target_id)
        if reload_detail:
            self._load_details(target_id)

    def _header(self) -> QFrame:
        header = QFrame(self)
        header.setObjectName("pageHeader")
        layout = QHBoxLayout(header)
        layout.setContentsMargins(0, 0, 0, 0)
        title = QLabel("物理和环境安全", header)
        title.setObjectName("pageTitle")
        layout.addWidget(title, 1)
        self._add_button = QPushButton("新增对象", header)
        self._delete_button = QPushButton("删除对象", header)
        self._save_button = QPushButton("保存", header)
        layout.addWidget(self._add_button)
        layout.addWidget(self._delete_button)
        layout.addWidget(self._save_button)
        self._add_button.clicked.connect(lambda: self.add_object("未命名物理对象"))
        self._delete_button.clicked.connect(lambda: self.delete_current_object())
        self._save_button.clicked.connect(lambda: self.save_current_detail(silent=False))
        return header

    def _body(self) -> QSplitter:
        splitter = QSplitter(Qt.Orientation.Horizontal, self)
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(6)

        self._object_list = QListWidget(splitter)
        self._object_list.setObjectName("objectNavigator")
        self._object_list.setMinimumWidth(240)
        self._object_list.setMaximumWidth(360)
        self._object_list.currentItemChanged.connect(self._on_current_item_changed)
        splitter.addWidget(self._object_list)

        scroll = QScrollArea(splitter)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        detail = QWidget(scroll)
        detail_layout = QVBoxLayout(detail)
        detail_layout.setContentsMargins(0, 0, 0, 0)
        detail_layout.setSpacing(12)
        detail_layout.addWidget(self._object_section())
        for unit_key, title, _unit_type, full_mode in UNIT_ORDER:
            detail_layout.addWidget(self._unit_section(unit_key, title, full_mode))
        detail_layout.addStretch(1)
        scroll.setWidget(detail)
        splitter.addWidget(scroll)
        splitter.setSizes([280, 880])
        return splitter

    def _object_section(self) -> QGroupBox:
        group = QGroupBox("测评对象基本信息", self)
        layout = QFormLayout(group)
        layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        for field, label in OBJECT_FIELD_LABELS.items():
            if field == "interview_record":
                widget = QPlainTextEdit(group)
                widget.setMinimumHeight(88)
            else:
                widget = QLineEdit(group)
                widget.setMinimumHeight(30)
            self._object_fields[field] = widget
            layout.addRow(f"{label}：", widget)
        return group

    def _unit_section(self, unit_key: str, title: str, full_mode: bool) -> QGroupBox:
        group = QGroupBox(title, self)
        layout = QVBoxLayout(group)
        fields: dict[str, QLineEdit | QPlainTextEdit | QComboBox] = {}
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        for field, label, multiline in [
            ("implementation", "实现情况", True),
            ("algorithm", "算法", False),
            ("compliance_status", "密码技术合规", False),
            ("product_compliance", "密码产品合规", False),
        ]:
            if field.endswith("compliance_status") or field == "product_compliance":
                widget = QComboBox(group)
                widget.addItems(["", "符合", "部分符合", "不符合", "不适用"])
            elif multiline:
                widget = QPlainTextEdit(group)
                widget.setMinimumHeight(72)
            else:
                widget = QLineEdit(group)
            fields[field] = widget
            form.addRow(f"{label}：", widget)
        layout.addLayout(form)

        quant = QuantWidget(group)
        products = ProductListWidget(group)
        risk = RiskWidget(full_mode=full_mode, parent=group)
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
        self._risk_widgets[unit_key] = risk
        self._product_widgets[unit_key] = products
        self._evidence_buttons.append(evidence)
        return group

    def _load_details(self, object_id: int) -> None:
        if self._service is None:
            return
        details = self._service.load_details(object_id)
        self._loading = True
        try:
            self._current_object_id = object_id
            self._current_details = details
            self._set_object_fields(details.object)
            self._set_unit_fields("auth", details.auth)
            self._set_unit_fields("access_integrity", details.access_integrity)
            self._set_unit_fields("video_integrity", details.video_integrity)
        finally:
            self._loading = False

    def _set_object_fields(self, obj: PhysicalObjectRecord) -> None:
        for field in OBJECT_FIELD_LABELS:
            self._set_widget_value(self._object_fields[field], getattr(obj, field))

    def _set_unit_fields(self, unit_key: str, detail) -> None:
        for field, widget in self._unit_fields[unit_key].items():
            self._set_widget_value(widget, getattr(detail, field, ""))
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
        if detail.products is not None:
            self._product_widgets[unit_key].set_products(detail.products)

    def _collect_payload(self) -> dict[str, Any]:
        return {
            "object": {
                field: self._widget_value(widget)
                for field, widget in self._object_fields.items()
            },
            "units": {
                unit_key: self._collect_unit_payload(unit_key) for unit_key, *_ in UNIT_ORDER
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

    def _clear_detail(self) -> None:
        self._loading = True
        try:
            self._current_object_id = None
            self._current_details = None
            self._current_evidence_context = None
            for widget in self._object_fields.values():
                self._set_widget_value(widget, "")
            for unit_key in self._unit_fields:
                for widget in self._unit_fields[unit_key].values():
                    self._set_widget_value(widget, "")
                self._risk_widgets[unit_key].set_values({})
                self._product_widgets[unit_key].set_products([])
        finally:
            self._loading = False

    def _on_current_item_changed(
        self,
        current: QListWidgetItem | None,
        _previous: QListWidgetItem | None,
    ) -> None:
        if current is None or self._selecting:
            return
        object_id = current.data(Qt.ItemDataRole.UserRole)
        if object_id is not None:
            self.select_object(int(object_id))

    def _select_item(self, object_id: int) -> None:
        self._selecting = True
        try:
            for row in range(self._object_list.count()):
                item = self._object_list.item(row)
                if item.data(Qt.ItemDataRole.UserRole) == object_id:
                    self._object_list.setCurrentRow(row)
                    break
        finally:
            self._selecting = False

    def _update_current_list_item(self, name: str) -> None:
        if self._current_object_id is None or not name:
            return
        for row in range(self._object_list.count()):
            item = self._object_list.item(row)
            if item.data(Qt.ItemDataRole.UserRole) == self._current_object_id:
                item.setText(name)
                break

    def _set_widget_value(self, widget: QLineEdit | QPlainTextEdit | QComboBox, value: str) -> None:
        if isinstance(widget, QPlainTextEdit):
            widget.setPlainText(value)
        elif isinstance(widget, QComboBox):
            index = widget.findText(value)
            widget.setCurrentIndex(index if index >= 0 else 0)
        else:
            widget.setText(value)

    def _widget_value(self, widget: QLineEdit | QPlainTextEdit | QComboBox) -> str:
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
            "object_name": self._current_object_name(),
        }

    def _current_object_name(self) -> str:
        current = self._object_list.currentItem()
        if current is not None:
            return current.text()
        if self._current_details is not None:
            return self._current_details.object.name
        return ""

    def _require_ready(self) -> None:
        if self._service is None:
            raise RuntimeError("physical service is required")
        if self._project_id is None:
            raise RuntimeError("project_id is required")
