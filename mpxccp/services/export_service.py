from __future__ import annotations

from pathlib import Path

from openpyxl import Workbook

from mpxccp.integration.excel.export_writer import (
    ALL_DATA_SHEETS,
    ExportWriter,
    normalize_module_names,
)
from mpxccp.integration.excel.score_workbook import ScoreWorkbook
from mpxccp.services.result import ServiceResult


class ExportService:
    def __init__(
        self,
        engine,
        *,
        export_writer: ExportWriter | None = None,
        score_workbook: ScoreWorkbook | None = None,
    ) -> None:
        self.engine = engine
        self.export_writer = export_writer or ExportWriter(engine)
        self.score_workbook = score_workbook or ScoreWorkbook(engine)

    def export_all_data(self, project_id: int) -> Workbook:
        return self._export_modules(project_id, list(ALL_DATA_SHEETS))

    def export_selected_modules(
        self,
        project_id: int,
        modules: list[str] | tuple[str, ...],
    ) -> Workbook:
        if not modules:
            raise ValueError("至少选择一个导出模块")
        return self._export_modules(project_id, normalize_module_names(modules))

    def export_score_workbook(self, project_id: int) -> Workbook:
        return self.score_workbook.export(project_id)

    def import_score_workbook(
        self,
        project_id: int,
        source: str | Path | Workbook,
        mode: str,
    ) -> ServiceResult:
        return self.score_workbook.import_management_scores(project_id, source, mode=mode)

    def _export_modules(self, project_id: int, sheet_names: list[str]) -> Workbook:
        workbook = Workbook()
        workbook.remove(workbook.active)
        writers = {
            ALL_DATA_SHEETS[0]: self.export_writer.write_system_basic_info,
            ALL_DATA_SHEETS[1]: self.export_writer.write_physical,
            ALL_DATA_SHEETS[2]: self.export_writer.write_device,
            ALL_DATA_SHEETS[3]: self.export_writer.write_network,
            ALL_DATA_SHEETS[4]: self.export_writer.write_application,
        }
        for sheet_name in sheet_names:
            writers[sheet_name](workbook, project_id)
        return workbook
