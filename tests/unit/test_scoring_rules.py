from mpxccp.domain.scoring_rules import (
    FIXED_NOT_APPLICABLE_INDICATORS,
    build_default_indicators,
    calculate_total_score,
    calculate_weighted_layer_score,
    classify_compliance,
    map_indicator_to_units,
)


def test_default_indicators_cover_1_to_41():
    indicators = build_default_indicators()

    assert [item.no for item in indicators] == list(range(1, 42))


def test_fixed_not_applicable_indicators():
    assert FIXED_NOT_APPLICABLE_INDICATORS == {8, 12, 17}


def test_default_indicators_mark_fixed_not_applicable_items():
    indicators = {item.no: item for item in build_default_indicators()}

    assert indicators[8].always_not_applicable is True
    assert indicators[12].always_not_applicable is True
    assert indicators[17].always_not_applicable is True


def test_layer_score_ignores_not_applicable_items():
    score = calculate_weighted_layer_score([(1.0, 1.0), (None, 1.0), (0.5, 2.0)])

    assert score == 2.0 / 3.0


def test_layer_score_returns_none_when_all_items_not_applicable():
    assert calculate_weighted_layer_score([(None, 1.0), (None, 2.0)]) is None


def test_total_score_uses_70_30_split():
    assert calculate_total_score(technical_score=0.8, management_score=0.5) == 71.0


def test_classify_compliance_matches_score_thresholds_and_none():
    assert classify_compliance(None) == "不适用"
    assert classify_compliance(1.0) == "符合"
    assert classify_compliance(0.5) == "部分符合"
    assert classify_compliance(0.0) == "不符合"


def test_indicator_mapping_contains_known_units_and_fixed_gaps():
    assert map_indicator_to_units(1) == ("物理访问身份鉴别",)
    assert map_indicator_to_units(4) == ("通信实体身份鉴别",)
    assert map_indicator_to_units(8) == ()
    assert map_indicator_to_units(12) == ()
    assert map_indicator_to_units(17) == ()
