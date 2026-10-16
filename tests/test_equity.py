import math

import numpy
import pandas
import pytest

from traccess import Access, Demographic, EquityComputer


def computer(access, demographics):
    ids = list(range(1, len(access) + 1))
    return EquityComputer(
        Access(pandas.DataFrame({"id": ids, "jobs": access}), id_column="id"),
        Demographic(pandas.DataFrame({"id": ids, **demographics}), id_column="id"),
    )


def test_gini_is_zero_for_equal_access_and_half_for_all_in_one_of_two():
    assert computer([10, 10], {"pop": [1, 1]}).gini_index("jobs")["pop"] == pytest.approx(0)
    assert computer([0, 10], {"pop": [1, 1]}).gini_index("jobs")["pop"] == pytest.approx(0.5)


def test_theil_t():
    assert computer([10, 10], {"pop": [1, 1]}).theil_t("jobs")["pop"] == pytest.approx(0)
    expected = (0.5 * math.log(0.5) + 1.5 * math.log(1.5)) / 2
    assert computer([5, 15], {"pop": [1, 1]}).theil_t("jobs")["pop"] == pytest.approx(expected)


def test_theil_t_decomposition_adds_up_to_the_total():
    rng = numpy.random.default_rng(1)
    eq = computer(
        list(rng.uniform(1, 100, 40)),
        {"pop": list(rng.integers(1, 50, 40)), "decile": list(rng.integers(1, 5, 40))},
    )
    parts = eq.theil_t_decomposition("jobs", "decile").loc["pop"]
    assert parts["between_group"] + parts["within_group"] == pytest.approx(parts["total"])
    assert parts["total"] == pytest.approx(
        eq.theil_t("jobs", population_columns=["pop"])["pop"]
    )


def test_palma_ratio():
    income = list(range(1, 11))
    eq = computer([i * 10 for i in income], {"pop": [1] * 10, "income": income})
    # Poorest 40%: incomes 1-4 (mean access 25). Wealthiest 10%: income 10 (100).
    assert eq.palma_ratio("jobs", "income")["pop"] == pytest.approx(4.0)
    assert list(eq.palma_ratio("jobs", "income").index) == ["pop"]


def test_concentration_index():
    eq = computer([0, 10], {"pop": [1, 1], "income": [1, 2]})
    assert eq.concentration_index("jobs", "income")["pop"] == pytest.approx(0.5)
    assert eq.concentration_index("jobs", "income", type="corrected")["pop"] == pytest.approx(1.0)
    pro_poor = computer([10, 0], {"pop": [1, 1], "income": [1, 2]})
    assert pro_poor.concentration_index("jobs", "income")["pop"] == pytest.approx(-0.5)
    with pytest.raises(ValueError):
        eq.concentration_index("jobs", "income", type="other")


def test_population_columns_excludes_non_count_columns():
    eq = computer([10, 20], {"pop": [1, 3], "income": [50_000, 20_000]})
    averages = eq.weighted_average("jobs", population_columns=["pop"])
    assert list(averages.index) == ["pop"]
    assert averages["pop"] == pytest.approx(17.5)
    fgt = eq.fgt_poverty("jobs", poverty_line=15, alpha=0, population_columns=["pop"])
    assert list(fgt.index) == ["pop"]
    with pytest.raises(ValueError):
        eq.gini_index("jobs", population_columns=["nope"])


def test_in_poverty_dual_returns_a_result():
    eq = computer([10, 40], {"pop": [1, 3]})
    assert eq.in_poverty("jobs", poverty_line=30, is_dual=True)["pop"] == 3
