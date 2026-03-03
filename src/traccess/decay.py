import math
from typing import Callable


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
        return math.exp(-decay_value * cost)

    return _decay
