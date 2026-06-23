from mpxccp.domain.association_rules import (
    ASSOCIATION_RULES,
    get_association_rule,
    list_measure_units,
)


def test_all_documented_measure_units_have_association_rules():
    assert len(ASSOCIATION_RULES) == 19
    assert "关键业务行为不可否认性" in list_measure_units()


def test_physical_auth_quant_and_evidence_use_detail_reference():
    rule = get_association_rule("物理访问身份鉴别")

    assert rule.quant_reference == "detail"
    assert rule.evidence_reference == "detail"
    assert rule.product_write_reference == "outer_object"
    assert "outer_object" in rule.product_compatible_references


def test_network_boundary_has_no_current_product_write_entry():
    rule = get_association_rule("网络边界访问控制完整性")

    assert rule.product_write_reference is None
    assert rule.quant_reference == "detail"
    assert rule.evidence_reference == "detail"


def test_application_important_data_products_write_to_outer_object():
    rule = get_association_rule("重要数据传输机密性")

    assert rule.product_write_reference == "outer_object"
    assert rule.outer_object_kind == "重要数据"
    assert rule.detail_kind == "传输机密性详情"


def test_unknown_measure_unit_raises_key_error():
    try:
        get_association_rule("不存在的测评单元")
    except KeyError as exc:
        assert "不存在的测评单元" in str(exc)
    else:
        raise AssertionError("expected KeyError")
