
"""Shared momentum qualification rules for Nasdaq research."""

import math

MIN_RISING_DAYS = 3
RSI_MIN = 50.0
RSI_MAX = 70.0
RVOL_MIN = 1.0


def passes_momentum_screen(
    macd: float,
    histogram: float,
    rising_days: int,
    rsi: float,
    relative_volume: float
) -> bool:
    """
    Determine whether a stock meets the momentum criteria.

    All required indicators must be valid finite numbers.
    """

    values = (
        macd,
        histogram,
        rsi,
        relative_volume
    )

    if not all(math.isfinite(x) for x in values):
        return False

    return (
        macd > 0
        and histogram > 0
        and rising_days >= MIN_RISING_DAYS
        and RSI_MIN <= rsi <= RSI_MAX
        and relative_volume > RVOL_MIN
    )
