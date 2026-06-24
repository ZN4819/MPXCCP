from __future__ import annotations

from typing import Any

from mpxccp.domain.enums import RiskLevel, RiskMode

RECTIFICATION_LEVELS = {
    RiskLevel.HIGH.value,
    RiskLevel.MEDIUM.value,
    RiskLevel.LOW.value,
}
TRUE_VALUES = {True, "true", "True", "1", "是", "具备", "有", "启用"}


class RiskService:
    def final_risk_level(
        self,
        risk_level: str | None,
        mitigation_enabled: bool | str | None,
        mitigated_level: str | None,
        mode: str | None,
    ) -> str:
        original = str(risk_level or "").strip()
        if mode == RiskMode.SIMPLE.value:
            return original
        if original == RiskLevel.HIGH.value and self._enabled(mitigation_enabled):
            return str(mitigated_level or original).strip() or original
        return original

    def should_show_rectification(self, final_level: str | None) -> bool:
        return str(final_level or "").strip() in RECTIFICATION_LEVELS

    def normalize_risk_fields(self, data: dict[str, Any], mode: str | None) -> dict[str, Any]:
        result = dict(data)
        final_level = self.final_risk_level(
            result.get("risk_level"),
            result.get("mitigation_enabled"),
            result.get("mitigated_level"),
            mode,
        )
        result["final_risk_level"] = final_level
        result["show_rectification"] = self.should_show_rectification(final_level)
        if not result["show_rectification"]:
            result["rectification"] = ""
        return result

    def _enabled(self, value: bool | str | None) -> bool:
        return value in TRUE_VALUES