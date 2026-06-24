from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QDialog, QHBoxLayout, QListWidget, QPushButton, QVBoxLayout, QWidget


class EvidenceDialog(QDialog):
    import_requested = Signal()
    files_selected = Signal(list)
    delete_requested = Signal(list)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("evidenceDialog")
        self.setWindowTitle("测评证据")

        layout = QVBoxLayout(self)
        self._records = QListWidget(self)
        self._records.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        layout.addWidget(self._records)

        actions = QHBoxLayout()
        self._import_button = QPushButton("导入图片", self)
        self._delete_button = QPushButton("删除选中", self)
        actions.addWidget(self._import_button)
        actions.addWidget(self._delete_button)
        actions.addStretch(1)
        layout.addLayout(actions)

        self._import_button.clicked.connect(self.import_requested.emit)
        self._delete_button.clicked.connect(self._emit_delete_requested)

    def import_button(self) -> QPushButton:
        return self._import_button

    def set_records(self, records: list[dict[str, object]]) -> None:
        self._records.clear()
        for record in records:
            label = str(record.get("file_name", ""))
            self._records.addItem(label)
            self._records.item(self._records.count() - 1).setData(256, record.get("id"))

    def selected_record_ids(self) -> list[int]:
        ids: list[int] = []
        for item in self._records.selectedItems():
            value = item.data(256)
            if value is not None:
                ids.append(int(value))
        return ids

    def request_import(self, paths: list[Path]) -> None:
        self.files_selected.emit(paths)

    def _emit_delete_requested(self) -> None:
        self.delete_requested.emit(self.selected_record_ids())
