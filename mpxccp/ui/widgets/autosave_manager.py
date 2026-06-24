from __future__ import annotations

import logging

from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtWidgets import (
    QAbstractSpinBox,
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDoubleSpinBox,
    QLineEdit,
    QPlainTextEdit,
    QRadioButton,
    QSpinBox,
    QTextEdit,
)

logger = logging.getLogger(__name__)


class AutoSaveManager(QObject):
    save_requested = Signal()

    def __init__(
        self,
        root: QObject,
        *,
        delay_ms: int = 600,
        max_depth: int = 20,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent or root)
        self.root = root
        self.delay_ms = delay_ms
        self.max_depth = max_depth
        self._connected_ids: set[int] = set()
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(delay_ms)
        self._timer.timeout.connect(self._emit_save_requested)
        self.scan()

    def scan(self) -> None:
        self._scan_object(self.root, depth=0)

    def save_now(self) -> None:
        self._timer.stop()
        self._emit_save_requested()

    def schedule_save(self) -> None:
        self._timer.start(self.delay_ms)

    def _scan_object(self, obj: QObject, *, depth: int) -> None:
        if depth > self.max_depth:
            return
        try:
            self._connect_input(obj)
            children = obj.children()
        except RuntimeError:
            return
        for child in children:
            if isinstance(child, QObject):
                self._scan_object(child, depth=depth + 1)

    def _connect_input(self, obj: QObject) -> None:
        object_id = id(obj)
        if object_id in self._connected_ids:
            return

        connected = True
        if isinstance(obj, QLineEdit):
            obj.textChanged.connect(self.schedule_save)
        elif isinstance(obj, (QPlainTextEdit, QTextEdit)):
            obj.textChanged.connect(self.schedule_save)
        elif isinstance(obj, QComboBox):
            obj.currentIndexChanged.connect(self.schedule_save)
        elif isinstance(obj, QDateEdit):
            obj.dateChanged.connect(self.schedule_save)
        elif isinstance(obj, (QSpinBox, QDoubleSpinBox, QAbstractSpinBox)):
            if hasattr(obj, "valueChanged"):
                obj.valueChanged.connect(self.schedule_save)
            else:
                obj.editingFinished.connect(self.schedule_save)
        elif isinstance(obj, (QCheckBox, QRadioButton)):
            obj.toggled.connect(self.schedule_save)
        elif hasattr(obj, "date_changed"):
            obj.date_changed.connect(self.schedule_save)
        else:
            connected = False

        if connected:
            self._connected_ids.add(object_id)

    def _emit_save_requested(self) -> None:
        try:
            self.save_requested.emit()
        except RuntimeError as exc:
            logger.warning("自动保存失败: %s", exc)
