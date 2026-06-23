from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass


@dataclass(frozen=True)
class IssueTemplate:
    clause: str
    layer: str
    current_state_template: str
    issue_description_template: str


def clean_other_prefix(value: str | None) -> str:
    if not value:
        return ""
    text = value.strip()
    return text.removeprefix("其他:")


def join_multi_select(value: str | None) -> str:
    if not value:
        return ""
    parts = [clean_other_prefix(part.strip()) for part in value.split(",")]
    return "、".join(part for part in parts if part)


def describe_product(products: Iterable[dict[str, str]]) -> str:
    names = [item.get("name", "").strip() for item in products if item.get("name", "").strip()]
    if not names:
        return "未使用合规的密码产品"
    return f"使用了{'、'.join(names)}密码产品"


def append_first_level_product_note(products: Iterable[dict[str, str]]) -> str:
    names = [
        item.get("name", "").strip()
        for item in products
        if item.get("level") == "一级" and item.get("name", "").strip()
    ]
    if not names:
        return ""
    product_names = "、".join(names)
    return (
        f"补充说明：{product_names} 的商用密码产品认证等级为一级，"
        "不符合三级系统使用二级及以上密码产品的要求。"
    )


def effective_issue_risk(fields: dict[str, str]) -> str:
    if fields.get("risk_level") == "高风险" and fields.get("mitigation") == "具备":
        return fields.get("mitigated_risk_level") or fields.get("risk_level", "")
    return fields.get("risk_level", "")


ISSUE_TEMPLATES: dict[str, IssueTemplate] = {
    "应8.1 a）": IssueTemplate(
        clause="应8.1 a）",
        layer="物理和环境",
        current_state_template="{对象}采用的身份鉴别方式为{方式}。",
        issue_description_template="{对象}采取的身份鉴别方式{技术描述}，{产品描述}。",
    ),
    "应8.2 a）": IssueTemplate(
        clause="应8.2 a）",
        layer="网络和通信",
        current_state_template="{信道}通过{网络环境}进行访问，使用{协议}协议。",
        issue_description_template="{信道}使用{协议}协议实现通信实体身份鉴别。",
    ),
}
