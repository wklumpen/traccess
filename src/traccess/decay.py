"""Decay (weighting) functions for ``AccessComputer.cumulative_decay``.

Each function here takes its parameters and returns a weighting function
that maps a single travel cost to a weight, where a cost of 0 always gets
weight 1. The library mirrors the decay functions in IPEA's R
``accessibility`` package (``decay_binary``, ``decay_exponential``,
``decay_linear``, ``decay_logistic``, ``decay_power``, ``decay_stepped``),
with the same formulas and parameter names, so results can be checked
against it.

A missing cost (NaN, typically an unreachable destination) always gets
weight 0.
"""

import bisect
import math
from typing import Callable, Sequence


def _is_missing(cost: float) -> bool:
    return cost is None or (isinstance(cost, float) and math.isnan(cost))


def binary(cutoff: float) -> Callable[[float], float]:
    """Returns a binary (step) decay function.

    Weights are:

        f(t) = 1 if t <= cutoff, otherwise 0

    This is the weighting behind cumulative opportunity measures; it gives
    the same result as ``AccessComputer.cumulative_cutoff``.

    Args:
        cutoff: The travel cost up to and including which opportunities get
            full weight. Must be 0 or greater.

    Returns:
        A function that takes a travel cost (float) and returns a weight (float).

    Examples:
        >>> fn = binary(cutoff=30)
        >>> fn(20), fn(35)
        (1.0, 0.0)
    """
    if cutoff < 0:
        raise ValueError(f"cutoff must be 0 or greater, got {cutoff}")

    def _decay(cost: float) -> float:
        if _is_missing(cost):
            return 0.0
        return 1.0 if cost <= cutoff else 0.0

    return _decay


def exponential(decay_value: float) -> Callable[[float], float]:
    """Returns a negative exponential decay function.

    Weights decay according to:

        f(t) = exp(-decay_value * t)

    where ``decay_value`` (β) controls the rate of decay. Higher values
    produce steeper decay. The weight equals 1 at t=0 and approaches 0
    as t increases.

    Note:
        This is equivalent to the scale (λ) parameterization used in some
        formulations (e.g. Statistics Canada) where λ = 1 / decay_value,
        giving f(t) = exp(-t / λ). To convert: decay_value = 1 / lambda.

    Args:
        decay_value: The decay rate parameter (β). Must be greater than 0.

    Returns:
        A function that takes a travel cost (float) and returns a weight (float).

    Examples:
        >>> fn = exponential(decay_value=0.2)
        >>> fn(10)
        0.1353352832366127
        >>> fn(0)
        1.0
    """

    if decay_value <= 0:
        raise ValueError(f"decay_value must be greater than 0, got {decay_value}")

    def _decay(cost: float) -> float:
        if _is_missing(cost):
            return 0.0
        return math.exp(-decay_value * cost)

    return _decay


def linear(cutoff: float) -> Callable[[float], float]:
    """Returns a linear decay function.

    Weights fall in a straight line from 1 at t=0 to 0 at the cutoff:

        f(t) = max(0, 1 - t / cutoff)

    Args:
        cutoff: The travel cost at which the weight reaches 0. Must be
            greater than 0.

    Returns:
        A function that takes a travel cost (float) and returns a weight (float).

    Examples:
        >>> fn = linear(cutoff=30)
        >>> fn(15), fn(45)
        (0.5, 0.0)
    """
    if cutoff <= 0:
        raise ValueError(f"cutoff must be greater than 0, got {cutoff}")

    def _decay(cost: float) -> float:
        if _is_missing(cost):
            return 0.0
        return max(0.0, 1.0 - cost / cutoff)

    return _decay


def power(decay_value: float) -> Callable[[float], float]:
    """Returns an inverse power decay function.

    Weights decay according to:

        f(t) = min(1, t ** -decay_value)

    The cap at 1 matters for costs below 1, where the raw power would exceed
    1 (and is infinite at t=0).

    Args:
        decay_value: The exponent (β). Must be 0 or greater; 0 gives every
            reachable opportunity full weight.

    Returns:
        A function that takes a travel cost (float) and returns a weight (float).

    Examples:
        >>> fn = power(decay_value=1)
        >>> fn(20)
        0.05
        >>> fn(0.5)
        1.0
    """
    if decay_value < 0:
        raise ValueError(f"decay_value must be 0 or greater, got {decay_value}")

    def _decay(cost: float) -> float:
        if _is_missing(cost):
            return 0.0
        if cost <= 1:
            return 1.0
        return min(1.0, cost ** (-decay_value))

    return _decay


def logistic(cutoff: float, sd: float) -> Callable[[float], float]:
    """Returns a logistic decay function.

    Weights follow a reversed cumulative logistic curve centred on
    ``cutoff`` (its inflection point), with steepness set by ``sd``,
    normalized so that f(0) = 1:

        g(t) = 1 + exp(π (t - cutoff) / (sd √3))
        f(t) = g(0) / g(t)

    Args:
        cutoff: The travel cost at the curve's inflection point. Must be 0
            or greater.
        sd: The standard deviation of the logistic distribution; larger
            values give a gentler slope. Must be greater than 0.

    Returns:
        A function that takes a travel cost (float) and returns a weight (float).

    Examples:
        >>> fn = logistic(cutoff=30, sd=5)
        >>> round(fn(30), 4)
        0.5
    """
    if cutoff < 0:
        raise ValueError(f"cutoff must be 0 or greater, got {cutoff}")
    if sd <= 0:
        raise ValueError(f"sd must be greater than 0, got {sd}")

    scale = math.pi / (sd * math.sqrt(3))

    def _g(cost: float) -> float:
        exponent = scale * (cost - cutoff)
        # exp() overflows past ~709; the weight is effectively 0 by then.
        return math.inf if exponent > 700 else 1.0 + math.exp(exponent)

    g0 = _g(0.0)

    def _decay(cost: float) -> float:
        if _is_missing(cost):
            return 0.0
        return g0 / _g(cost)

    return _decay


def stepped(
    steps: Sequence[float], weights: Sequence[float]
) -> Callable[[float], float]:
    """Returns a stepped decay function.

    The weight is 1 below the first step, then takes ``weights[i]`` from
    ``steps[i]`` (inclusive) up to the next step:

        f(t) = 1            if t < steps[0]
        f(t) = weights[i]   if steps[i] <= t < steps[i + 1]

    Do not include a step at 0 or a leading weight of 1; both are implied.

    Args:
        steps: Travel cost steps, strictly ascending and greater than 0.
        weights: The weight from each step onward, each between 0 and 1,
            the same length as ``steps``.

    Returns:
        A function that takes a travel cost (float) and returns a weight (float).

    Examples:
        >>> fn = stepped(steps=[10, 20, 30], weights=[0.66, 0.33, 0])
        >>> fn(5), fn(10), fn(25), fn(40)
        (1.0, 0.66, 0.33, 0.0)
    """
    steps = list(steps)
    weights = [float(w) for w in weights]
    if not steps:
        raise ValueError("steps must not be empty")
    if len(steps) != len(weights):
        raise ValueError(
            f"steps ({len(steps)}) and weights ({len(weights)}) must be the same length"
        )
    if steps[0] <= 0 or any(b <= a for a, b in zip(steps, steps[1:])):
        raise ValueError("steps must be greater than 0 and strictly ascending")
    if any(not 0 <= w <= 1 for w in weights):
        raise ValueError("weights must be between 0 and 1")

    def _decay(cost: float) -> float:
        if _is_missing(cost):
            return 0.0
        index = bisect.bisect_right(steps, cost)
        return 1.0 if index == 0 else weights[index - 1]

    return _decay
