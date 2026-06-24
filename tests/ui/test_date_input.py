from PySide6.QtCore import QDate
from pytestqt.qtbot import QtBot

from mpxccp.ui.widgets.date_input import DateInput


def test_date_input_sets_and_clears_date(qtbot: QtBot):
    widget = DateInput()
    qtbot.addWidget(widget)

    widget.set_date("2026-06-24")
    widget.clear()

    assert widget.date_text() == ""


def test_date_input_commits_manual_text(qtbot: QtBot):
    widget = DateInput()
    qtbot.addWidget(widget)

    widget.set_text("2026-06-25")
    widget.commit_text()

    assert widget.date_text() == "2026-06-25"


def test_date_input_respects_min_max_range(qtbot: QtBot):
    widget = DateInput()
    qtbot.addWidget(widget)
    widget.set_date_range(QDate(2026, 6, 1), QDate(2026, 6, 30))
    widget.set_date("2026-06-15")

    widget.set_text("2026-07-01")
    widget.commit_text()

    assert widget.date_text() == "2026-06-15"


def test_date_input_calendar_popup_is_child_widget(qtbot: QtBot):
    widget = DateInput()
    qtbot.addWidget(widget)

    calendar = widget.show_calendar()

    assert calendar.parent() is widget
    assert calendar.isVisible()
