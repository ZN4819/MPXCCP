from pytestqt.qtbot import QtBot

from mpxccp.ui.widgets.evidence_dialog import EvidenceDialog


def test_evidence_dialog_import_button_emits_request(qtbot: QtBot):
    dialog = EvidenceDialog()
    qtbot.addWidget(dialog)
    called: list[bool] = []
    dialog.import_requested.connect(lambda: called.append(True))

    dialog.import_button().click()

    assert called == [True]
