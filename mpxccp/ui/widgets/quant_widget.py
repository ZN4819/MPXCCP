from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QComboBox, QFormLayout, QHBoxLayout, QLabel, QWidget

from mpxccp.domain.constants import CHECK, CROSS, EMPTY, SLASH
from mpxccp.domain.quant_rules import apply_quant_auto_rule


class QuantWidget(QWidget):
    values_changed = Signal(dict)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("quantWidget")
        self._updating = False

        layout = QFormLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setHorizontalSpacing(12)
        layout.setVerticalSpacing(8)

        row = QWidget(self)
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(8)

        self._d = self._combo([EMPTY, CHECK, CROSS])
        self._a = self._combo([EMPTY, CHECK, CROSS, SLASH])
        self._k = self._combo([EMPTY, CHECK, CROSS, SLASH])
        self._ra = self._combo(["1", "0.5", "0.2"])
        self._rk = self._combo(["1", "1.2"])

        for label, combo in [
            ("D", self._d),
            ("A", self._a),
            ("K", self._k),
            ("Ra", self._ra),
            ("Rk", self._rk),
        ]:
            row_layout.addWidget(QLabel(label, row))
            row_layout.addWidget(combo)

        layout.addRow("量化评估：", row)

        for combo in [self._d, self._a, self._k, self._ra, self._rk]:
            combo.currentIndexChanged.connect(self._on_values_changed)

    def set_values(
        self,
        *,
        d: str = EMPTY,
        a: str = EMPTY,
        k: str = EMPTY,
        ra: float | str = 1.0,
        rk: float | str = 1.0,
    ) -> None:
        result = apply_quant_auto_rule(d=d, a=a, k=k, ra=ra, rk=rk)
        self._set_values(
            d=result.d,
            a=result.a,
            k=result.k,
            ra=result.ra,
            rk=result.rk,
            a_enabled=result.a_enabled,
            k_enabled=result.k_enabled,
            emit=True,
        )

    def values(self) -> dict[str, str | float]:
        return {
            "d": self._d.currentText(),
            "a": self._a.currentText(),
            "k": self._k.currentText(),
            "ra": float(self._ra.currentText()),
            "rk": float(self._rk.currentText()),
        }

    def set_d(self, value: str) -> None:
        self._set_combo_text(self._d, value)
        self._apply_auto_rule(emit=True)

    def a_value(self) -> str:
        return self._a.currentText()

    def k_value(self) -> str:
        return self._k.currentText()

    def a_enabled(self) -> bool:
        return self._a.isEnabled()

    def k_enabled(self) -> bool:
        return self._k.isEnabled()

    def apply_status_rule(
        self,
        *,
        usage_status: str | None = None,
        implementation_status: str | None = None,
        product_level: str | None = None,
    ) -> None:
        values = self.values()
        result = apply_quant_auto_rule(
            d=values["d"],
            a=values["a"],
            k=values["k"],
            ra=values["ra"],
            rk=values["rk"],
            usage_status=usage_status,
            implementation_status=implementation_status,
            product_level=product_level,
        )
        self._set_values(
            d=result.d,
            a=result.a,
            k=result.k,
            ra=result.ra,
            rk=result.rk,
            a_enabled=result.a_enabled,
            k_enabled=result.k_enabled,
            emit=True,
        )

    def _combo(self, values: list[str]) -> QComboBox:
        combo = QComboBox(self)
        combo.addItems(values)
        combo.setMinimumHeight(28)
        combo.setMinimumWidth(64)
        return combo

    def _on_values_changed(self) -> None:
        if self._updating:
            return
        self._apply_auto_rule(emit=True)

    def _apply_auto_rule(self, *, emit: bool) -> None:
        values = self.values()
        result = apply_quant_auto_rule(
            d=values["d"],
            a=values["a"],
            k=values["k"],
            ra=values["ra"],
            rk=values["rk"],
        )
        self._set_values(
            d=result.d,
            a=result.a,
            k=result.k,
            ra=result.ra,
            rk=result.rk,
            a_enabled=result.a_enabled,
            k_enabled=result.k_enabled,
            emit=emit,
        )

    def _set_values(
        self,
        *,
        d: str,
        a: str,
        k: str,
        ra: float | str,
        rk: float | str,
        a_enabled: bool = True,
        k_enabled: bool = True,
        emit: bool,
    ) -> None:
        self._updating = True
        try:
            self._set_combo_text(self._d, d)
            self._set_combo_text(self._a, a)
            self._set_combo_text(self._k, k)
            self._set_combo_text(self._ra, str(float(ra)).rstrip("0").rstrip("."))
            self._set_combo_text(self._rk, str(float(rk)).rstrip("0").rstrip("."))
            self._a.setEnabled(a_enabled)
            self._k.setEnabled(k_enabled)
        finally:
            self._updating = False
        if emit:
            self.values_changed.emit(self.values())

    def _set_combo_text(self, combo: QComboBox, value: str) -> None:
        index = combo.findText(str(value))
        combo.setCurrentIndex(index if index >= 0 else 0)
