from __future__ import annotations

from PySide6.QtCore import QDate, Signal
from PySide6.QtWidgets import (
    QCalendarWidget,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class DateInput(QWidget):
    date_changed = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("dateInput")
        self._date: QDate | None = None
        self._minimum: QDate | None = None
        self._maximum: QDate | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        row = QWidget(self)
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(6)

        self._editor = QLineEdit(row)
        self._editor.setPlaceholderText("YYYY-MM-DD")
        self._clear_button = QPushButton("清空", row)
        self._calendar_button = QPushButton("选择日期", row)
        self._clear_button.setObjectName("dateClearButton")
        self._calendar_button.setObjectName("dateCalendarButton")

        row_layout.addWidget(self._editor, 1)
        row_layout.addWidget(self._clear_button)
        row_layout.addWidget(self._calendar_button)
        layout.addWidget(row)

        self._calendar = QCalendarWidget(self)
        self._calendar.setObjectName("datePopupCalendar")
        self._calendar.setGridVisible(True)
        self._calendar.hide()
        layout.addWidget(self._calendar)

        self._editor.editingFinished.connect(self.commit_text)
        self._clear_button.clicked.connect(self.clear)
        self._calendar_button.clicked.connect(self.show_calendar)
        self._calendar.clicked.connect(self._select_calendar_date)

    def line_edit(self) -> QLineEdit:
        return self._editor

    def calendar(self) -> QCalendarWidget:
        return self._calendar

    def set_text(self, text: str) -> None:
        self._editor.setText(text)

    def set_date(self, value: str | QDate | None) -> None:
        if value in (None, ""):
            self.clear()
            return
        date = value if isinstance(value, QDate) else QDate.fromString(str(value), "yyyy-MM-dd")
        if not date.isValid() or not self._in_range(date):
            return
        self._date = date
        self._editor.setText(date.toString("yyyy-MM-dd"))
        self._calendar.setSelectedDate(date)
        self.date_changed.emit(self.date_text())

    def date_text(self) -> str:
        return "" if self._date is None else self._date.toString("yyyy-MM-dd")

    def clear(self) -> None:
        self._date = None
        self._editor.clear()
        self.date_changed.emit("")

    def set_date_range(self, minimum: QDate | None, maximum: QDate | None) -> None:
        self._minimum = minimum if minimum and minimum.isValid() else None
        self._maximum = maximum if maximum and maximum.isValid() else None
        if self._minimum is not None:
            self._calendar.setMinimumDate(self._minimum)
        if self._maximum is not None:
            self._calendar.setMaximumDate(self._maximum)

    def commit_text(self) -> None:
        text = self._editor.text().strip()
        if not text:
            self.clear()
            return
        date = QDate.fromString(text, "yyyy-MM-dd")
        if not date.isValid() or not self._in_range(date):
            self._editor.setText(self.date_text())
            return
        self.set_date(date)

    def show_calendar(self) -> QCalendarWidget:
        if self._date is not None:
            self._calendar.setSelectedDate(self._date)
        self.show()
        self._calendar.show()
        return self._calendar

    def _select_calendar_date(self, date: QDate) -> None:
        self.set_date(date)
        self._calendar.hide()

    def _in_range(self, date: QDate) -> bool:
        if self._minimum is not None and date < self._minimum:
            return False
        if self._maximum is not None and date > self._maximum:
            return False
        return True
