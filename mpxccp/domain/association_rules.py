from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AssociationRule:
    measure_unit: str
    quant_reference: str
    evidence_reference: str
    product_write_reference: str | None
    product_compatible_references: tuple[str, ...]
    detail_kind: str
    outer_object_kind: str


def _rule(
    unit: str,
    detail_kind: str,
    outer_kind: str,
    product_write_reference: str | None = "outer_object",
) -> AssociationRule:
    compatible = ("detail", "outer_object")
    return AssociationRule(
        measure_unit=unit,
        quant_reference="detail",
        evidence_reference="detail",
        product_write_reference=product_write_reference,
        product_compatible_references=compatible,
        detail_kind=detail_kind,
        outer_object_kind=outer_kind,
    )


_RULES = [
    _rule("物理访问身份鉴别", "身份鉴别详情", "物理测评对象"),
    _rule("门禁记录完整性", "门禁记录完整性详情", "物理测评对象"),
    _rule("视频记录完整性", "视频记录完整性详情", "物理测评对象"),
    _rule("设备登录身份鉴别", "设备身份鉴别详情", "设备测评对象"),
    _rule("远程管理通道", "远程管理通道详情", "设备测评对象"),
    _rule("设备访问控制完整性", "访问控制完整性详情", "设备测评对象"),
    _rule("设备日志完整性", "日志完整性详情", "设备测评对象"),
    _rule("可执行程序完整性", "可执行程序完整性详情", "设备测评对象"),
    _rule("通信实体身份鉴别", "通信实体身份鉴别详情", "通信信道"),
    _rule("通信过程数据完整性", "通信数据完整性详情", "通信信道"),
    _rule("通信过程数据机密性", "通信数据机密性详情", "通信信道"),
    _rule("网络边界访问控制完整性", "网络边界完整性详情", "通信信道", None),
    _rule("应用用户身份鉴别", "用户身份鉴别详情", "应用用户"),
    _rule("应用访问控制完整性", "访问控制完整性详情", "访问控制信息"),
    _rule("重要数据传输机密性", "传输机密性详情", "重要数据"),
    _rule("重要数据存储机密性", "存储机密性详情", "重要数据"),
    _rule("重要数据传输完整性", "传输完整性详情", "重要数据"),
    _rule("重要数据存储完整性", "存储完整性详情", "重要数据"),
    _rule("关键业务行为不可否认性", "不可否认性详情", "关键业务行为"),
]

ASSOCIATION_RULES: dict[str, AssociationRule] = {rule.measure_unit: rule for rule in _RULES}


def get_association_rule(measure_unit: str) -> AssociationRule:
    try:
        return ASSOCIATION_RULES[measure_unit]
    except KeyError as exc:
        raise KeyError(f"未知测评单元: {measure_unit}") from exc


def list_measure_units() -> tuple[str, ...]:
    return tuple(ASSOCIATION_RULES)
