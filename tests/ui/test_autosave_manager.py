from PySide6.QtCore import QDate
from PySide6.QtWidgets import QCheckBox, QComboBox, QDateEdit, QLineEdit, QVBoxLayout, QWidget
from pytestqt.qtbot import QtBot

from mpxccp.ui.widgets.autosave_manager import AutoSaveManager


def test_autosave_manager_debounces_changes(qtbot: QtBot):
    editor = QLineEdit()
    qtbot.addWidget(editor)
    called: list[bool] = []
    manager = AutoSaveManager(editor, delay_ms=50)
    manager.save_requested.connect(lambda: called.append(True))

    editor.setText("changed")
    editor.setText("changed again")
    qtbot.wait(80)

    assert called == [True]


def test_autosave_manager_recursively_scans_input_widgets(qtbot: QtBot):
    page = QWidget()
    layout = QVBoxLayout(page)
    text = QLineEdit(page)
    combo = QComboBox(page)
    checkbox = QCheckBox(page)
    combo.addItems(["符合", "不符合"])
    layout.addWidget(text)
    layout.addWidget(combo)
    layout.addWidget(checkbox)
    qtbot.addWidget(page)
    called: list[bool] = []
    manager = AutoSaveManager(page, delay_ms=50)
    manager.save_requested.connect(lambda: called.append(True))

    combo.setCurrentIndex(1)
    checkbox.setChecked(True)
    qtbot.wait(80)

    assert called == [True]


def test_autosave_manager_save_now_emits_immediately(qtbot: QtBot):
    editor = QLineEdit()
    qtbot.addWidget(editor)
    called: list[bool] = []
    manager = AutoSaveManager(editor, delay_ms=500)
    manager.save_requested.connect(lambda: called.append(True))
    editor.setText("pending")

    manager.save_now()

    assert called == [True]


def test_autosave_manager_listens_to_date_edits(qtbot: QtBot):
    editor = QDateEdit()
    qtbot.addWidget(editor)
    called: list[bool] = []
    manager = AutoSaveManager(editor, delay_ms=50)
    manager.save_requested.connect(lambda: called.append(True))

    editor.setDate(QDate(2026, 6, 24))
    qtbot.wait(80)

    assert called == [True]
