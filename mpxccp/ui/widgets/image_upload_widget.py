from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QListWidget, QPushButton, QVBoxLayout, QWidget

SUPPORTED_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png"}


class ImageUploadWidget(QWidget):
    files_changed = Signal(list)
    upload_requested = Signal(list)

    def __init__(
        self,
        *,
        max_files: int = 10,
        max_size_bytes: int = 3 * 1024 * 1024,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("imageUploadWidget")
        self.max_files = max_files
        self.max_size_bytes = max_size_bytes
        self._files: list[Path] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self._list = QListWidget(self)
        layout.addWidget(self._list)

        actions = QHBoxLayout()
        self._upload_button = QPushButton("选择图片", self)
        self._clear_button = QPushButton("清空", self)
        actions.addWidget(self._upload_button)
        actions.addWidget(self._clear_button)
        actions.addStretch(1)
        layout.addLayout(actions)

        self._upload_button.clicked.connect(lambda: self.upload_requested.emit(self._files))
        self._clear_button.clicked.connect(self.clear)

    def set_files(self, files: list[Path]) -> list[str]:
        errors = self.validate_files(files)
        if errors:
            return errors
        self._files = list(files)
        self._refresh()
        self.files_changed.emit(self._files)
        return []

    def files(self) -> list[Path]:
        return list(self._files)

    def clear(self) -> None:
        self._files = []
        self._refresh()
        self.files_changed.emit([])

    def validate_files(self, files: list[Path]) -> list[str]:
        errors: list[str] = []
        if len(files) > self.max_files:
            errors.append("too_many_files")
        for path in files:
            if path.suffix.lower() not in SUPPORTED_IMAGE_SUFFIXES:
                errors.append(f"unsupported:{path.name}")
            if path.exists() and path.stat().st_size > self.max_size_bytes:
                errors.append(f"too_large:{path.name}")
        return errors

    def _refresh(self) -> None:
        self._list.clear()
        for path in self._files:
            self._list.addItem(path.name)
