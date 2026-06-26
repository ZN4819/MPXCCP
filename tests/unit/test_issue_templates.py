from __future__ import annotations

from mpxccp.domain.issue_templates import (
    append_first_level_product_note,
    clean_other_prefix,
    describe_product,
    effective_issue_risk,
    join_multi_select,
)


def test_issue_description_cleans_other_prefix_and_multi_select():
    assert clean_other_prefix("其他:短信令牌") == "短信令牌"
    assert join_multi_select("指纹,其他:门禁卡") == "指纹、门禁卡"


def test_describe_product_lists_names_and_first_level_note():
    products = [
        {"name": "门禁模块", "level": "一级"},
        {"name": "签名验签服务器", "level": "二级"},
    ]

    assert describe_product(products) == "使用了门禁模块、签名验签服务器密码产品"
    assert "门禁模块" in append_first_level_product_note(products)
    assert "二级及以上" in append_first_level_product_note(products)


def test_effective_issue_risk_uses_mitigated_level_only_for_high_risk_with_mitigation():
    assert (
        effective_issue_risk(
            {
                "risk_level": "高风险",
                "mitigation_available": "是",
                "mitigated_level": "低风险",
            }
        )
        == "低风险"
    )
    assert (
        effective_issue_risk(
            {
                "risk_level": "中风险",
                "mitigation_available": "是",
                "mitigated_level": "低风险",
            }
        )
        == "中风险"
    )


def test_effective_issue_risk_accepts_boolean_mitigation_from_ui_widget():
    assert (
        effective_issue_risk(
            {
                "risk_level": "高风险",
                "mitigation_available": True,
                "mitigated_level": "低风险",
            }
        )
        == "低风险"
    )
