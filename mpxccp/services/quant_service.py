from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import Engine

from mpxccp.domain.constants import CHECK
from mpxccp.domain.enums import MeasureUnit
from mpxccp.domain.quant_rules import (
    QuantRuleResult,
    apply_quant_auto_rule,
    calculate_object_score,
    normalize_quant_values,
)
from mpxccp.models.shared import QuantitativeAssessment
from mpxccp.repositories.session import readonly_session_scope, session_scope
from mpxccp.repositories.shared_repo import SharedRepository

EFFECTIVE_D_UNITS = {
    MeasureUnit.PHYSICAL_AUTH.value,
    MeasureUnit.PHYSICAL_ACCESS_INTEGRITY.value,
    MeasureUnit.PHYSICAL_VIDEO_INTEGRITY.value,
    MeasureUnit.DEVICE_AUTH.value,
    MeasureUnit.DEVICE_REMOTE.value,
    MeasureUnit.NETWORK_AUTH.value,
    MeasureUnit.NETWORK_INTEGRITY.value,
    MeasureUnit.NETWORK_CONFIDENTIALITY.value,
    MeasureUnit.APP_USER_AUTH.value,
    MeasureUnit.APP_ACCESS_INTEGRITY.value,
    MeasureUnit.DATA_TRANSPORT_CONFIDENTIALITY.value,
    MeasureUnit.DATA_STORAGE_CONFIDENTIALITY.value,
    MeasureUnit.DATA_TRANSPORT_INTEGRITY.value,
    MeasureUnit.DATA_STORAGE_INTEGRITY.value,
    MeasureUnit.BUSINESS_ACTION_NON_REPUDIATION.value,
}


@dataclass(frozen=True)
class QuantRecord:
    record_id: int | None
    project_id: int | None
    unit_type: str
    related_id: int
    d: str
    a: str
    k: str
    ra: float
    rk: float
    score: float | None
    changed: bool = False


class QuantService:
    def __init__(
        self,
        engine: Engine,
        *,
        project_id: int | None = None,
        shared_repo: SharedRepository | None = None,
    ) -> None:
        self.engine = engine
        self.project_id = project_id
        self.shared_repo = shared_repo or SharedRepository()

    def load(
        self,
        unit_type: str,
        related_id: int,
        project_id: int | None = None,
    ) -> QuantRecord:
        resolved_project_id = self._resolve_project_id(project_id)
        with readonly_session_scope(self.engine) as session:
            record = self.shared_repo.get_quant(session, resolved_project_id, unit_type, related_id)
            if record is None:
                return QuantRecord(
                    record_id=None,
                    project_id=resolved_project_id,
                    unit_type=unit_type,
                    related_id=related_id,
                    d="",
                    a="",
                    k="",
                    ra=1.0,
                    rk=1.0,
                    score=None,
                )
            return self._record_payload(record)

    def save(
        self,
        unit_type: str,
        related_id: int,
        d: Any,
        a: Any,
        k: Any,
        ra: Any,
        rk: Any,
        project_id: int | None = None,
    ) -> QuantRecord:
        resolved_project_id = self._resolve_project_id(project_id)
        values = normalize_quant_values(d=d, a=a, k=k, ra=ra, rk=rk)
        score = calculate_object_score(
            d=values.d,
            a=values.a,
            k=values.k,
            ra=values.ra,
            rk=values.rk,
        )
        with session_scope(self.engine) as session:
            record = self.shared_repo.get_quant(session, resolved_project_id, unit_type, related_id)
            if record is None:
                record = self.shared_repo.add_quant(
                    session,
                    project_id=resolved_project_id,
                    unit_type=unit_type,
                    related_id=related_id,
                )
                changed = True
            else:
                changed = not self._same_values(
                    record,
                    values.d,
                    values.a,
                    values.k,
                    values.ra,
                    values.rk,
                    score,
                )
            if changed:
                record.d_value = values.d
                record.a_value = values.a
                record.k_value = values.k
                record.ra_value = self._format_number(values.ra)
                record.rk_value = self._format_number(values.rk)
                record.score = score
            return self._record_payload(record, changed=changed)

    def apply_auto_rule(self, **kwargs: Any) -> QuantRuleResult:
        return apply_quant_auto_rule(**kwargs)

    def count_effective_d(self, project_id: int) -> int:
        with readonly_session_scope(self.engine) as session:
            return sum(
                1
                for record in self.shared_repo.list_quant_by_project(session, project_id)
                if record.unit_type in EFFECTIVE_D_UNITS and record.d_value == CHECK
            )

    def _resolve_project_id(self, project_id: int | None) -> int:
        resolved = project_id if project_id is not None else self.project_id
        if resolved is None:
            raise ValueError("project_id is required for quant service operations")
        return resolved

    def _same_values(
        self,
        record: QuantitativeAssessment,
        d: str,
        a: str,
        k: str,
        ra: float,
        rk: float,
        score: float | None,
    ) -> bool:
        return (
            (record.d_value or "") == d
            and (record.a_value or "") == a
            and (record.k_value or "") == k
            and (record.ra_value or "") == self._format_number(ra)
            and (record.rk_value or "") == self._format_number(rk)
            and record.score == score
        )

    def _record_payload(
        self,
        record: QuantitativeAssessment,
        *,
        changed: bool = False,
    ) -> QuantRecord:
        values = normalize_quant_values(
            d=record.d_value,
            a=record.a_value,
            k=record.k_value,
            ra=record.ra_value,
            rk=record.rk_value,
        )
        return QuantRecord(
            record_id=record.id,
            project_id=record.project_id,
            unit_type=record.unit_type,
            related_id=record.related_id,
            d=values.d,
            a=values.a,
            k=values.k,
            ra=values.ra,
            rk=values.rk,
            score=record.score,
            changed=changed,
        )

    def _format_number(self, value: float) -> str:
        return str(float(value))