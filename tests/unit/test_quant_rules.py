from mpxccp.domain.quant_rules import (
    apply_quant_auto_rule,
    calculate_object_score,
    is_effective_d,
    normalize_quant_values,
)


def test_d_cross_disables_a_k_as_slash():
    result = apply_quant_auto_rule(d="×", a="", k="", ra=None, rk=None)

    assert result.d == "×"
    assert result.a == "/"
    assert result.k == "/"
    assert result.a_enabled is False
    assert result.k_enabled is False


def test_first_level_product_forces_a_pass_k_fail_and_rk_1_2():
    result = apply_quant_auto_rule(product_level="一级")

    assert (result.d, result.a, result.k, result.ra, result.rk) == ("√", "√", "×", 1.0, 1.2)


def test_second_or_third_level_product_forces_full_pass():
    result = apply_quant_auto_rule(product_level="二级")

    assert (result.d, result.a, result.k, result.ra, result.rk) == ("√", "√", "√", 1.0, 1.0)


def test_not_applicable_clears_d_a_k_but_keeps_default_ra_rk():
    result = apply_quant_auto_rule(usage_status="不适用", d="√", a="√", k="√", ra=0.5, rk=1.2)

    assert (result.d, result.a, result.k, result.ra, result.rk) == ("", "", "", 0.5, 1.2)


def test_object_score_uses_ra_when_a_fails_k_passes():
    assert calculate_object_score(d="√", a="×", k="√", ra=0.5, rk=1.0) == 0.25


def test_object_score_uses_rk_when_a_passes_k_fails():
    assert calculate_object_score(d="√", a="√", k="×", ra=1.0, rk=1.2) == 0.6


def test_object_score_returns_none_when_d_is_empty_or_invalid():
    assert calculate_object_score(d="", a="√", k="√", ra=1.0, rk=1.0) is None
    assert calculate_object_score(d="?", a="√", k="√", ra=1.0, rk=1.0) is None


def test_normalize_quant_values_defaults_empty_ra_rk_to_one():
    values = normalize_quant_values(d="√", a="√", k="√", ra=None, rk="")

    assert values.ra == 1.0
    assert values.rk == 1.0


def test_effective_d_only_accepts_check_mark():
    assert is_effective_d("√") is True
    assert is_effective_d("×") is False
    assert is_effective_d("") is False
