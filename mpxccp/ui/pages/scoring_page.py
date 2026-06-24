from __future__ import annotations

from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from mpxccp.domain.enums import SecurityLayer
from mpxccp.domain.scoring_rules import build_default_indicators
from mpxccp.services.scoring_service import ScoreSummaryRecord, ScoringService

DIRTY_BUTTON_TEXT = "⚠ 分数待更新 - 点击重新计算"
NORMAL_BUTTON_TEXT = "重新计算"
COMPLIANCE_OPTIONS = ["", "符合", "部分符合", "不符合", "不适用"]
LAYER_NAMES = [
    SecurityLayer.PHYSICAL.value,
    SecurityLayer.NETWORK.value,
    SecurityLayer.DEVICE.value,
    SecurityLayer.APPLICATION.value,
    SecurityLayer.MANAGEMENT_SYSTEM.value,
    SecurityLayer.PERSONNEL.value,
    SecurityLayer.CONSTRUCTION.value,
    SecurityLayer.EMERGENCY.value,
]


class ScoringPage(QWidget):
    def __init__(
        self,
        scoring_service: ScoringService | None = None,
        *,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("scoringPage")
        self._service = scoring_service
        self._project_id: int | None = None
        self._loading = False
        self._count_labels: dict[str, QLabel] = {}
        self._layer_labels: dict[str, QLabel] = {}
        self._management_combos: dict[int, QComboBox] = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 18)
        layout.setSpacing(14)
        layout.addWidget(self._header())
        layout.addWidget(self._summary_band())
        layout.addWidget(self._layer_band())
        layout.addWidget(self._tables(), 1)
        self._populate_management_table()

    def set_project_id(self, project_id: int | None) -> None:
        self._project_id = project_id
        if self._service is not None:
            self._service.ensure_indicators()
        self._populate_management_table()
        summary = self._service.load_summary(project_id) if self._service and project_id else None
        self._apply_summary(summary)

    def project_id(self) -> int | None:
        return self._project_id

    def mark_dirty(self) -> None:
        if self._service is not None and self._project_id is not None:
            self._service.mark_dirty(self._project_id)
        self._recalculate_button.setText(DIRTY_BUTTON_TEXT)

    def recalculate_button_text(self) -> str:
        return self._recalculate_button.text()

    def recalculate_button(self) -> QPushButton:
        return self._recalculate_button

    def total_score_text(self) -> str:
        return self._total_score.text()

    def compliance_count_texts(self) -> dict[str, str]:
        return {name: label.text() for name, label in self._count_labels.items()}

    def layer_card_names(self) -> list[str]:
        return list(self._layer_labels)

    def technical_table(self) -> QTableWidget:
        return self._technical_table

    def management_table(self) -> QTableWidget:
        return self._management_table

    def management_combo(self, indicator_no: int) -> QComboBox:
        return self._management_combos[indicator_no]

    def _header(self) -> QFrame:
        header = QFrame(self)
        header.setObjectName("pageHeader")
        layout = QHBoxLayout(header)
        layout.setContentsMargins(0, 0, 0, 0)
        title = QLabel("打分", header)
        title.setObjectName("pageTitle")
        layout.addWidget(title, 1)
        self._recalculate_button = QPushButton(NORMAL_BUTTON_TEXT, header)
        self._recalculate_button.clicked.connect(self._recalculate)
        layout.addWidget(self._recalculate_button)
        return header

    def _summary_band(self) -> QFrame:
        frame = QFrame(self)
        frame.setObjectName("sectionPanel")
        layout = QGridLayout(frame)
        layout.setHorizontalSpacing(12)
        layout.setVerticalSpacing(8)
        self._total_score = QLabel("0.00", frame)
        self._total_score.setObjectName("scoreTotal")
        layout.addWidget(QLabel("总分", frame), 0, 0)
        layout.addWidget(self._total_score, 1, 0)
        for index, name in enumerate(["符合", "部分符合", "不符合", "不适用"], start=1):
            label = QLabel("0", frame)
            label.setObjectName(f"scoreCount{index}")
            self._count_labels[name] = label
            layout.addWidget(QLabel(name, frame), 0, index)
            layout.addWidget(label, 1, index)
        return frame

    def _layer_band(self) -> QFrame:
        frame = QFrame(self)
        frame.setObjectName("sectionPanel")
        layout = QGridLayout(frame)
        layout.setHorizontalSpacing(10)
        layout.setVerticalSpacing(8)
        for index, name in enumerate(LAYER_NAMES):
            value = QLabel("N/A", frame)
            self._layer_labels[name] = value
            layout.addWidget(QLabel(name, frame), (index // 4) * 2, index % 4)
            layout.addWidget(value, (index // 4) * 2 + 1, index % 4)
        return frame

    def _tables(self) -> QTabWidget:
        tabs = QTabWidget(self)
        self._technical_table = QTableWidget(0, 14, tabs)
        self._technical_table.setHorizontalHeaderLabels(
            [
                "指标",
                "层面",
                "测评单元",
                "D",
                "A",
                "K",
                "Ra",
                "Rk",
                "对象得分",
                "指标得分",
                "有效对象",
                "所占",
                "已得",
                "丢失",
            ]
        )
        self._technical_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._technical_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        tabs.addTab(self._technical_table, "技术域明细")

        self._management_table = QTableWidget(0, 9, tabs)
        self._management_table.setHorizontalHeaderLabels(
            ["指标", "层面", "测评指标", "权重", "符合情况", "得分", "所占", "已得", "丢失"]
        )
        self._management_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        tabs.addTab(self._management_table, "管理域评分")
        return tabs

    def _populate_management_table(self) -> None:
        indicators = (
            self._service.list_indicators()
            if self._service is not None
            else [
                type(
                    "Indicator",
                    (),
                    {
                        "no": item.no,
                        "name": item.name,
                        "layer": item.layer,
                        "weight": item.weight,
                        "always_not_applicable": item.always_not_applicable,
                    },
                )
                for item in build_default_indicators()
            ]
        )
        management_indicators = [item for item in indicators if item.no >= 23]
        self._loading = True
        try:
            self._management_table.setRowCount(len(management_indicators))
            self._management_combos.clear()
            for row, indicator in enumerate(management_indicators):
                self._management_table.setItem(row, 0, QTableWidgetItem(str(indicator.no)))
                self._management_table.setItem(row, 1, QTableWidgetItem(indicator.layer))
                self._management_table.setItem(row, 2, QTableWidgetItem(indicator.name))
                self._management_table.setItem(row, 3, QTableWidgetItem(str(indicator.weight)))
                combo = QComboBox(self._management_table)
                combo.addItems(COMPLIANCE_OPTIONS)
                combo.setFixedHeight(28)
                combo.currentTextChanged.connect(
                    lambda text, no=indicator.no: self._save_management_score(no, text)
                )
                self._management_table.setCellWidget(row, 4, combo)
                self._management_table.setItem(row, 5, QTableWidgetItem("N/A"))
                self._management_table.setItem(row, 6, QTableWidgetItem(""))
                self._management_table.setItem(row, 7, QTableWidgetItem(""))
                self._management_table.setItem(row, 8, QTableWidgetItem(""))
                self._management_combos[indicator.no] = combo
        finally:
            self._loading = False

    def _save_management_score(self, indicator_no: int, text: str) -> None:
        if self._loading or self._service is None or self._project_id is None:
            return
        summary = self._service.save_management_score(self._project_id, indicator_no, text)
        self._apply_summary(summary)

    def _recalculate(self) -> None:
        if self._service is None or self._project_id is None:
            self._recalculate_button.setText(NORMAL_BUTTON_TEXT)
            return
        self._apply_summary(self._service.refresh_all_technical_domains(self._project_id))

    def _apply_summary(self, summary: ScoreSummaryRecord | None) -> None:
        self._loading = True
        try:
            if summary is None:
                self._total_score.setText("0.00")
                for label in self._count_labels.values():
                    label.setText("0")
                for label in self._layer_labels.values():
                    label.setText("N/A")
                self._technical_table.setRowCount(0)
                self._recalculate_button.setText(NORMAL_BUTTON_TEXT)
                return
            self._total_score.setText(f"{summary.total_score:.2f}")
            self._count_labels["符合"].setText(str(summary.compliant_count))
            self._count_labels["部分符合"].setText(str(summary.partial_count))
            self._count_labels["不符合"].setText(str(summary.non_compliant_count))
            self._count_labels["不适用"].setText(str(summary.not_applicable_count))
            layer_map = {item.name: item for item in summary.layer_scores}
            for name, label in self._layer_labels.items():
                layer = layer_map.get(name)
                label.setText(
                    "N/A" if layer is None or layer.score is None else f"{layer.score:.2f}"
                )
            self._populate_technical_table(summary)
            self._sync_management_rows(summary)
            self._recalculate_button.setText(
                DIRTY_BUTTON_TEXT if summary.dirty else NORMAL_BUTTON_TEXT
            )
        finally:
            self._loading = False

    def _populate_technical_table(self, summary: ScoreSummaryRecord) -> None:
        technical_details = [item for item in summary.details if item.indicator_no <= 22]
        row_count = sum(max(len(detail.object_rows), 1) + 1 for detail in technical_details)
        self._technical_table.setRowCount(row_count)
        row = 0
        for detail in technical_details:
            start_row = row
            self._set_technical_row(
                row,
                [
                    str(detail.indicator_no),
                    detail.layer,
                    detail.unit_type or "（暂无测评数据）",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "N/A" if detail.score is None else f"{detail.score:.2f}",
                    str(detail.effective_object_count),
                    self._score_text(detail.allocated_score),
                    self._score_text(detail.earned_score),
                    self._score_text(detail.lost_score),
                ],
            )
            row += 1
            object_rows = detail.object_rows or []
            if not object_rows:
                self._set_technical_row(
                    row,
                    ["", "", "（暂无测评数据）", "", "", "", "", "", "N/A", "", "", "", "", ""],
                )
                row += 1
            for object_row in object_rows:
                values = [
                    str(detail.indicator_no),
                    detail.layer,
                    object_row.object_name,
                    object_row.d,
                    object_row.a,
                    object_row.k,
                    f"{object_row.ra:g}",
                    f"{object_row.rk:g}",
                    "N/A" if object_row.score is None else f"{object_row.score:.2f}",
                    "",
                    "",
                    "",
                    "",
                    "",
                ]
                self._set_technical_row(row, values, disabled=object_row.d == "×")
                row += 1
            span_rows = row - start_row
            if span_rows > 1:
                self._technical_table.setSpan(start_row, 0, span_rows, 1)
                self._technical_table.setSpan(start_row, 1, span_rows, 1)

    def _sync_management_rows(self, summary: ScoreSummaryRecord) -> None:
        details = {item.indicator_no: item for item in summary.details if item.indicator_no >= 23}
        for row in range(self._management_table.rowCount()):
            no_item = self._management_table.item(row, 0)
            if no_item is None:
                continue
            indicator_no = int(no_item.text())
            detail = details.get(indicator_no)
            if detail is None:
                continue
            combo = self._management_combos[indicator_no]
            combo.setCurrentText(detail.compliance_status)
            self._management_table.setItem(
                row,
                5,
                QTableWidgetItem("N/A" if detail.score is None else f"{detail.score:.2f}"),
            )
            self._management_table.setItem(
                row,
                6,
                QTableWidgetItem(self._score_text(detail.allocated_score)),
            )
            self._management_table.setItem(
                row,
                7,
                QTableWidgetItem(self._score_text(detail.earned_score)),
            )
            self._management_table.setItem(
                row,
                8,
                QTableWidgetItem(self._score_text(detail.lost_score)),
            )

    def _score_text(self, value: float | None) -> str:
        return "" if value is None else f"{value:.2f}"

    def _set_technical_row(
        self,
        row: int,
        values: list[str],
        *,
        disabled: bool = False,
    ) -> None:
        background = QColor("#f3f4f6") if disabled else None
        for column, value in enumerate(values):
            item = QTableWidgetItem(value)
            if background is not None:
                item.setBackground(background)
            self._technical_table.setItem(row, column, item)
