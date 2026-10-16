import math

import pandas
import pytest

from traccess import decay


def test_binary_is_inclusive_at_the_cutoff():
    fn = decay.binary(30)
    assert [fn(t) for t in (0, 30, 30.01)] == [1.0, 1.0, 0.0]


def test_exponential():
    fn = decay.exponential(0.2)
    assert fn(0) == 1.0
    assert fn(10) == pytest.approx(math.exp(-2))


def test_linear_reaches_zero_at_the_cutoff():
    fn = decay.linear(30)
    assert [fn(t) for t in (0, 15, 30, 45)] == [1.0, 0.5, 0.0, 0.0]


def test_power_is_capped_at_one_below_one_minute():
    fn = decay.power(1)
    assert fn(0) == 1.0
    assert fn(0.5) == 1.0
    assert fn(20) == pytest.approx(0.05)
    assert decay.power(0)(50) == 1.0


def test_logistic_matches_the_r_formula():
    fn = decay.logistic(cutoff=30, sd=5)
    g = lambda t: 1 + math.exp(math.pi * (t - 30) / (5 * math.sqrt(3)))  # noqa: E731
    for t in (0, 15, 30, 45, 60):
        assert fn(t) == pytest.approx(g(0) / g(t))
    assert fn(0) == 1.0
    assert fn(10_000) == 0.0  # no overflow


def test_stepped_steps_take_effect_at_the_step():
    fn = decay.stepped(steps=[10, 20, 30], weights=[0.66, 0.33, 0])
    assert [fn(t) for t in (0, 9.9, 10, 25, 30, 99)] == [1.0, 1.0, 0.66, 0.33, 0.0, 0.0]


@pytest.mark.parametrize(
    "fn",
    [
        decay.binary(30),
        decay.exponential(0.1),
        decay.linear(30),
        decay.power(1),
        decay.logistic(30, 5),
        decay.stepped([10], [0.5]),
    ],
)
def test_unreachable_costs_get_zero_weight(fn):
    assert fn(float("nan")) == 0.0


@pytest.mark.parametrize(
    "make",
    [
        lambda: decay.binary(-1),
        lambda: decay.exponential(0),
        lambda: decay.linear(0),
        lambda: decay.power(-1),
        lambda: decay.logistic(30, 0),
        lambda: decay.logistic(-1, 5),
        lambda: decay.stepped([], []),
        lambda: decay.stepped([10, 5], [0.5, 0.2]),
        lambda: decay.stepped([0, 10], [0.5, 0.2]),
        lambda: decay.stepped([10], [1.5]),
        lambda: decay.stepped([10, 20], [0.5]),
    ],
)
def test_invalid_parameters_raise(make):
    with pytest.raises(ValueError):
        make()


def test_binary_decay_matches_cumulative_cutoff(access_object):
    cost_column = access_object.cost.columns[0]
    cutoff = access_object.cumulative_cutoff([cost_column], [29]).data.sort_index()
    decayed = access_object.cumulative_decay(
        [cost_column], decay.binary(29)
    ).data.sort_index()
    pandas.testing.assert_frame_equal(cutoff, decayed, check_dtype=False)
