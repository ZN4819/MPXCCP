from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

PRODUCT_COLUMNS = ["产品名称", "厂商", "证书编号", "认证等级", "使用用途"]


class ProductListWidget(QWidget):
    products_changed = Signal(list)
    import_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("productListWidget")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._table = QTableWidget(0, len(PRODUCT_COLUMNS), self)
        self._table.setHorizontalHeaderLabels(PRODUCT_COLUMNS)
        self._table.verticalHeader().setVisible(False)
        self._table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self._table)

        actions = QHBoxLayout()
        self._add_button = QPushButton("新增", self)
        self._remove_button = QPushButton("删除", self)
        self._move_up_button = QPushButton("上移", self)
        self._move_down_button = QPushButton("下移", self)
        self._import_button = QPushButton("批量导入", self)
        actions.addWidget(self._add_button)
        actions.addWidget(self._remove_button)
        actions.addWidget(self._move_up_button)
        actions.addWidget(self._move_down_button)
        actions.addStretch(1)
        actions.addWidget(self._import_button)
        layout.addLayout(actions)

        self._add_button.clicked.connect(self.add_product)
        self._remove_button.clicked.connect(self.remove_selected)
        self._move_up_button.clicked.connect(self.move_selected_up)
        self._move_down_button.clicked.connect(self.move_selected_down)
        self._import_button.clicked.connect(self.import_requested.emit)
        self._table.itemChanged.connect(lambda _item: self.products_changed.emit(self.products()))

    def table(self) -> QTableWidget:
        return self._table

    def set_products(self, products: list[dict[str, str]]) -> None:
        self._table.blockSignals(True)
        try:
            self._table.setRowCount(0)
            for product in products:
                self.add_product(product, emit=False)
        finally:
            self._table.blockSignals(False)
        self.products_changed.emit(self.products())

    def products(self) -> list[dict[str, str]]:
        rows: list[dict[str, str]] = []
        for row in range(self._table.rowCount()):
            item = {
                key: (self._table.item(row, column).text() if self._table.item(row, column) else "")
                for column, key in enumerate(
                    ["name", "vendor", "certificate_no", "level", "usage"]
                )
            }
            rows.append(item)
        return rows

    def add_product(self, product: dict[str, str] | None = None, *, emit: bool = True) -> None:
        product = product or {}
        row = self._table.rowCount()
        self._table.insertRow(row)
        for column, key in enumerate(["name", "vendor", "certificate_no", "level", "usage"]):
            self._table.setItem(row, column, QTableWidgetItem(str(product.get(key, ""))))
        if emit:
            self.products_changed.emit(self.products())

    def remove_selected(self) -> None:
        rows = sorted({index.row() for index in self._table.selectedIndexes()}, reverse=True)
        for row in rows:
            self._table.removeRow(row)
        if rows:
            self.products_changed.emit(self.products())

    def move_selected_up(self) -> None:
        row = self._current_row()
        if row <= 0:
            return
        self._swap_rows(row, row - 1)
        self._table.selectRow(row - 1)
        self.products_changed.emit(self.products())

    def move_selected_down(self) -> None:
        row = self._current_row()
        if row < 0 or row >= self._table.rowCount() - 1:
            return
        self._swap_rows(row, row + 1)
        self._table.selectRow(row + 1)
        self.products_changed.emit(self.products())

    def _current_row(self) -> int:
        indexes = self._table.selectedIndexes()
        if not indexes:
            return -1
        return indexes[0].row()

    def _swap_rows(self, first: int, second: int) -> None:
        for column in range(self._table.columnCount()):
            first_item = self._table.takeItem(first, column)
            second_item = self._table.takeItem(second, column)
            self._table.setItem(first, column, second_item)
            self._table.setItem(second, column, first_item)
