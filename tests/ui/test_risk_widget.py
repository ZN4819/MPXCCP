from pytestqt.qtbot import QtBot

from mpxccp.ui.widgets.risk_widget import RiskWidget


def test_risk_widget_only_applies_mitigation_to_high_risk(qtbot: QtBot):
    widget = RiskWidget()
    qtbot.addWidget(widget)
    widget.set_values(
        {
            "risk_level": "中风险",
            "mitigation_available": True,
            "mitigated_level": "低风险",
        }
    )

    assert widget.values()["final_level"] == "中风险"


def test_risk_widget_applies_mitigation_to_high_risk(qtbot: QtBot):
    widget = RiskWidget()
    qtbot.addWidget(widget)
    widget.set_values(
        {
            "risk_level": "高风险",
            "mitigation_available": True,
            "mitigated_level": "低风险",
        }
    )

    assert widget.values()["final_level"] == "低风险"
