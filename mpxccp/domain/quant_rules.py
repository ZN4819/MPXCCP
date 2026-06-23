from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from mpxccp.domain.constants import CHECK, CROSS, EMPTY, SLASH


@dataclass(frozen=True)
class QuantValues:
    d: str = EMPTY
    a: str = EMPTY
    k: str = EMPTY
    ra: float = 1.0
    rk: float = 1.0


@dataclass(frozen=True)
class QuantRuleResult(QuantValues):
    a_enabled: bool = True
    k_enabled: bool = True


def _normalize_symbol(value: Any, *, allow_slash: bool = False) -> str:
    if value is None:
        return EMPTY
    text = str(value).strip()
    allowed = {EMPTY, CHECK, CROSS}
    if allow_slash:
        allowed.add(SLASH)
    return text if text in allowed else EMPTY


def _normalize_float(value: Any, default: float = 1.0) -> float:
    if value is None or value == "":
        return default
    return float(value)


def normalize_quant_values(
    d: Any = EMPTY,
    a: Any = EMPTY,
    k: Any = EMPTY,
    ra: Any = None,
    rk: Any = None,
) -> QuantValues:
    return QuantValues(
        d=_normalize_symbol(d),
        a=_normalize_symbol(a, allow_slash=True),
        k=_normalize_symbol(k, allow_slash=True),
        ra=_normalize_float(ra),
        rk=_normalize_float(rk),
    )


def apply_quant_auto_rule(
    *,
    d: Any = EMPTY,
    a: Any = EMPTY,
    k: Any = EMPTY,
    ra: Any = None,
    rk: Any = None,
    usage_status: str | None = None,
    implementation_status: str | None = None,
    product_level: str | None = None,
) -> QuantRuleResult:
    values = normalize_quant_values(d=d, a=a, k=k, ra=ra, rk=rk)

    if product_level == "一级":
        return QuantRuleResult(d=CHECK, a=CHECK, k=CROSS, ra=1.0, rk=1.2)
    if product_level in {"二级", "三级"}:
        return QuantRuleResult(d=CHECK, a=CHECK, k=CHECK, ra=1.0, rk=1.0)

    state = implementation_status or usage_status
    if state in {"不适用", "不涉及"}:
        return QuantRuleResult(d=EMPTY, a=EMPTY, k=EMPTY, ra=values.ra, rk=values.rk)
    if state in {"未使用", "未实现"}:
        return QuantRuleResult(
            d=CROSS,
            a=SLASH,
            k=SLASH,
            ra=values.ra,
            rk=values.rk,
            a_enabled=False,
            k_enabled=False,
        )
    if state in {"已使用", "已实现"}:
        a_value = EMPTY if values.a == SLASH else values.a
        k_value = EMPTY if values.k == SLASH else values.k
        return QuantRuleResult(d=CHECK, a=a_value, k=k_value, ra=values.ra, rk=values.rk)

    if values.d == CROSS:
        return QuantRuleResult(
            d=CROSS,
            a=SLASH,
            k=SLASH,
            ra=values.ra,
            rk=values.rk,
            a_enabled=False,
            k_enabled=False,
        )
    if values.d == CHECK:
        a_value = EMPTY if values.a == SLASH else values.a
        k_value = EMPTY if values.k == SLASH else values.k
        return QuantRuleResult(d=CHECK, a=a_value, k=k_value, ra=values.ra, rk=values.rk)
    return QuantRuleResult(**values.__dict__)


def calculate_object_score(
    *,
    d: Any,
    a: Any,
    k: Any,
    ra: Any = None,
    rk: Any = None,
) -> float | None:
    values = normalize_quant_values(d=d, a=a, k=k, ra=ra, rk=rk)
    if values.d not in {CHECK, CROSS}:
        return None
    if values.d == CROSS:
        return 0.0
    a_passed = values.a == CHECK
    k_passed = values.k == CHECK
    if a_passed and k_passed:
        return 1.0
    if not a_passed and k_passed:
        return 0.5 * values.ra
    if a_passed and not k_passed:
        return 0.5 * values.rk
    return 0.25 * values.ra * values.rk


def is_effective_d(value: Any) -> bool:
    return str(value).strip() == CHECK
