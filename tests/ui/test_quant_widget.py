from pytestqt.qtbot import QtBot

from mpxccp.domain.constants import CHECK, CROSS, EMPTY, SLASH
from mpxccp.ui.widgets.quant_widget import QuantWidget


def test_quant_widget_disables_a_k_when_d_is_cross(qtbot: QtBot):
    widget = QuantWidget()
    qtbot.addWidget(widget)

    widget.set_d(CROSS)

    assert widget.a_value() == SLASH
    assert widget.k_value() == SLASH
    assert widget.a_enabled() is False
    assert widget.k_enabled() is False


def test_quant_widget_reenables_a_k_when_d_returns_to_check(qtbot: QtBot):
    widget = QuantWidget()
    qtbot.addWidget(widget)
    widget.set_d(CROSS)

    widget.set_d(CHECK)

    assert widget.a_enabled() is True
    assert widget.k_enabled() is True
    assert widget.a_value() == EMPTY
    assert widget.k_value() == EMPTY


def test_quant_widget_emits_values_changed(qtbot: QtBot):
    widget = QuantWidget()
    qtbot.addWidget(widget)

    with qtbot.waitSignal(widget.values_changed, timeout=500):
        widget.set_values(d=CHECK, a=CHECK, k=CHECK, ra=0.5, rk=1.2)

    assert widget.values() == {
        "d": CHECK,
        "a": CHECK,
        "k": CHECK,
        "ra": 0.5,
        "rk": 1.2,
    }


def test_quant_widget_normalizes_loaded_cross_values(qtbot: QtBot):
    widget = QuantWidget()
    qtbot.addWidget(widget)

    widget.set_values(d=CROSS, a=CHECK, k=CHECK, ra=1, rk=1)

    assert widget.a_value() == SLASH
    assert widget.k_value() == SLASH
    assert widget.a_enabled() is False
    assert widget.k_enabled() is False
