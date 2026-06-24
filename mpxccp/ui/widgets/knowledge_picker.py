from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class KnowledgePicker(QWidget):
    knowledge_selected = Signal(list)
    add_requested = Signal(dict)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("knowledgePicker")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        filters = QHBoxLayout()
        self._module = QComboBox(self)
        self._module.addItems(
            ["通用要求", "物理和环境", "设备和计算", "网络和通信", "应用和数据", "其他"]
        )
        self._type = QComboBox(self)
        self._type.addItems(["风险分析", "风险缓释", "整改建议"])
        self._show_all = QCheckBox("显示全部模块", self)
        filters.addWidget(self._module)
        filters.addWidget(self._type)
        filters.addWidget(self._show_all)
        layout.addLayout(filters)

        self._items = QListWidget(self)
        self._items.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        layout.addWidget(self._items)

        actions = QHBoxLayout()
        self._select_button = QPushButton("回填选中", self)
        self._add_button = QPushButton("加入知识库", self)
        actions.addWidget(self._select_button)
        actions.addWidget(self._add_button)
        actions.addStretch(1)
        layout.addLayout(actions)

        self._select_button.clicked.connect(
            lambda: self.knowledge_selected.emit(self.selected_texts())
        )
        self._add_button.clicked.connect(self._emit_add_requested)

    def set_items(self, items: list[dict[str, str]]) -> None:
        self._items.clear()
        for item in items:
            entry = QListWidgetItem(item.get("content", ""))
            entry.setData(256, item)
            self._items.addItem(entry)

    def selected_texts(self) -> list[str]:
        return [item.text() for item in self._items.selectedItems()]

    def filter_state(self) -> dict[str, str | bool]:
        return {
            "module": self._module.currentText(),
            "knowledge_type": self._type.currentText(),
            "show_all": self._show_all.isChecked(),
        }

    def _emit_add_requested(self) -> None:
        self.add_requested.emit(self.filter_state())
