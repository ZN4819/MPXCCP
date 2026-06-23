from __future__ import annotations

from dataclasses import dataclass

from mpxccp.domain.constants import (
    FIXED_NOT_APPLICABLE_INDICATOR_NOS,
    MANAGEMENT_FULL_SCORE,
    TECHNICAL_FULL_SCORE,
)
from mpxccp.domain.enums import SecurityLayer

FIXED_NOT_APPLICABLE_INDICATORS = set(FIXED_NOT_APPLICABLE_INDICATOR_NOS)


@dataclass(frozen=True)
class ScoringIndicator:
    no: int
    name: str
    layer: str
    weight: float = 1.0
    always_not_applicable: bool = False


INDICATOR_UNIT_MAP: dict[int, tuple[str, ...]] = {
    1: ("物理访问身份鉴别",),
    2: ("门禁记录完整性",),
    3: ("视频记录完整性",),
    4: ("通信实体身份鉴别",),
    5: ("通信过程数据完整性",),
    6: ("通信过程数据机密性",),
    7: ("网络边界访问控制完整性",),
    8: (),
    9: ("设备登录身份鉴别",),
    10: ("远程管理通道",),
    11: ("设备访问控制完整性",),
    12: (),
    13: ("设备日志完整性",),
    14: ("可执行程序完整性",),
    15: ("应用用户身份鉴别",),
    16: ("应用访问控制完整性",),
    17: (),
    18: ("重要数据传输机密性",),
    19: ("重要数据存储机密性",),
    20: ("重要数据传输完整性",),
    21: ("重要数据存储完整性",),
    22: ("关键业务行为不可否认性",),
}


def _layer_for_indicator(no: int) -> str:
    if 1 <= no <= 3:
        return SecurityLayer.PHYSICAL.value
    if 4 <= no <= 8:
        return SecurityLayer.NETWORK.value
    if 9 <= no <= 14:
        return SecurityLayer.DEVICE.value
    if 15 <= no <= 22:
        return SecurityLayer.APPLICATION.value
    if 23 <= no <= 28:
        return SecurityLayer.MANAGEMENT_SYSTEM.value
    if 29 <= no <= 33:
        return SecurityLayer.PERSONNEL.value
    if 34 <= no <= 38:
        return SecurityLayer.CONSTRUCTION.value
    return SecurityLayer.EMERGENCY.value


def build_default_indicators() -> list[ScoringIndicator]:
    return [
        ScoringIndicator(
            no=no,
            name=f"{_layer_for_indicator(no)}指标{no}",
            layer=_layer_for_indicator(no),
            weight=1.0,
            always_not_applicable=no in FIXED_NOT_APPLICABLE_INDICATORS,
        )
        for no in range(1, 42)
    ]


def map_indicator_to_units(indicator_no: int) -> tuple[str, ...]:
    return INDICATOR_UNIT_MAP.get(indicator_no, ())


def calculate_weighted_layer_score(items: list[tuple[float | None, float]]) -> float | None:
    weighted_sum = 0.0
    weight_sum = 0.0
    for score, weight in items:
        if score is None:
            continue
        weighted_sum += score * weight
        weight_sum += weight
    if weight_sum == 0:
        return None
    return weighted_sum / weight_sum


def calculate_total_score(technical_score: float | None, management_score: float | None) -> float:
    technical = 0.0 if technical_score is None else technical_score * TECHNICAL_FULL_SCORE
    management = 0.0 if management_score is None else management_score * MANAGEMENT_FULL_SCORE
    return round(technical + management, 2)


def classify_compliance(unit_score: float | None) -> str:
    if unit_score is None:
        return "不适用"
    if unit_score >= 1.0:
        return "符合"
    if unit_score > 0:
        return "部分符合"
    return "不符合"
