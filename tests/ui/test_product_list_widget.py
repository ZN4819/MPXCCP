from pytestqt.qtbot import QtBot

from mpxccp.ui.widgets.product_list_widget import ProductListWidget


def test_product_list_widget_moves_selected_product(qtbot: QtBot):
    widget = ProductListWidget()
    qtbot.addWidget(widget)
    widget.set_products(
        [
            {"name": "产品A", "certificate_no": "A"},
            {"name": "产品B", "certificate_no": "B"},
        ]
    )

    widget.table().selectRow(1)
    widget.move_selected_up()

    assert [product["name"] for product in widget.products()] == ["产品B", "产品A"]

    widget.move_selected_down()

    assert [product["name"] for product in widget.products()] == ["产品A", "产品B"]
