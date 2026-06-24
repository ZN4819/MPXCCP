from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QCheckBox, QComboBox, QFormLayout, QPlainTextEdit, QWidget

RISK_LEVELS = ["", "高风险", "中风险", "低风险", "无风险", "不适用"]


class RiskWidget(QWidget):
    values_changed = Signal(dict)
    knowledge_requested = Signal(str)

    def __init__(self, *, full_mode: bool = True, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("riskWidget")
        self.full_mode = full_mode
        layout = QFormLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._risk_level = QComboBox(self)
        self._risk_level.addItems(RISK_LEVELS)
        self._analysis = QPlainTextEdit(self)
        self._rectification = QPlainTextEdit(self)
        self._mitigation_available = QCheckBox("具备缓释机制", self)
        self._mitigation_note = QPlainTextEdit(self)
        self._mitigated_level = QComboBox(self)
        self._mitigated_level.addItems(RISK_LEVELS)

        layout.addRow("风险等级：", self._risk_level)
        layout.addRow("风险分析：", self._analysis)
        if full_mode:
            layout.addRow("", self._mitigation_available)
            layout.addRow("缓释说明：", self._mitigation_note)
            layout.addRow("缓释后等级：", self._mitigated_level)
        layout.addRow("整改建议：", self._rectification)

        self._risk_level.currentIndexChanged.connect(self._emit_values_changed)
        self._analysis.textChanged.connect(self._emit_values_changed)
        self._rectification.textChanged.connect(self._emit_values_changed)
        self._mitigation_available.toggled.connect(self._emit_values_changed)
        self._mitigation_note.textChanged.connect(self._emit_values_changed)
        self._mitigated_level.currentIndexChanged.connect(self._emit_values_changed)

    def values(self) -> dict[str, str | bool]:
        risk_level = self._risk_level.currentText()
        mitigation_available = self._mitigation_available.isChecked()
        mitigated_level = self._mitigated_level.currentText()
        final_level = (
            mitigated_level
            if self.full_mode
            and risk_level == "高风险"
            and mitigation_available
            and mitigated_level
            else risk_level
        )
        return {
            "risk_level": risk_level,
            "risk_analysis": self._analysis.toPlainText(),
            "mitigation_available": mitigation_available,
            "mitigation_note": self._mitigation_note.toPlainText(),
            "mitigated_level": mitigated_level,
            "final_level": final_level,
            "rectification": self._rectification.toPlainText(),
        }

    def set_values(self, values: dict[str, str | bool]) -> None:
        self._set_combo(self._risk_level, str(values.get("risk_level", "")))
        self._analysis.setPlainText(str(values.get("risk_analysis", "")))
        self._mitigation_available.setChecked(bool(values.get("mitigation_available", False)))
        self._mitigation_note.setPlainText(str(values.get("mitigation_note", "")))
        self._set_combo(self._mitigated_level, str(values.get("mitigated_level", "")))
        self._rectification.setPlainText(str(values.get("rectification", "")))

    def _set_combo(self, combo: QComboBox, text: str) -> None:
        index = combo.findText(text)
        combo.setCurrentIndex(index if index >= 0 else 0)

    def _emit_values_changed(self) -> None:
        self.values_changed.emit(self.values())
