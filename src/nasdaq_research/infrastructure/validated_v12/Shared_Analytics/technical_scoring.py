"""Transparent five-condition technical scores for Nasdaq research.

A score counts existing momentum conditions; it is not an investment ranking
or a forecast of returns. Unavailable inputs result in an unscored assessment,
not a zero. This module deliberately does not change eligibility rules.
"""

from __future__ import annotations

from dataclasses import dataclass
import math

CONDITION_NAMES = (
    "macd_positive",
    "histogram_positive",
    "histogram_rising_three",
    "rsi_50_to_70",
    "relative_volume_above_one",
)


@dataclass(frozen=True)
class TechnicalScore:
    score: int | None
    conditions: dict[str, bool | None]
    unavailable: tuple[str, ...]

    @property
    def label(self) -> str:
        return "N/A" if self.score is None else f"{self.score}/5"


def _finite_number(value: object) -> float | None:
    """Accept numeric readings only; distinguish unavailable from a failed rule."""
    if isinstance(value, (bool, str, bytes)):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return number if math.isfinite(number) else None


def evaluate_technical_score(*, macd: object, histogram: object,
                             rising_days: object, rsi: object,
                             relative_volume: object) -> TechnicalScore:
    """Apply the five original momentum rules without filtering any stocks.

    Missing, NaN, nonfinite, invalid, or fractional rising-day readings are
    unavailable. Any unavailable input makes the total score N/A, while valid
    individual condition flags remain visible for diagnosis.
    """
    macd_n = _finite_number(macd)
    histogram_n = _finite_number(histogram)
    rising_n = _finite_number(rising_days)
    rsi_n = _finite_number(rsi)
    volume_n = _finite_number(relative_volume)

    if rising_n is not None and (rising_n < 0 or not rising_n.is_integer()):
        rising_n = None

    conditions: dict[str, bool | None] = {
        "macd_positive": None if macd_n is None else macd_n > 0,
        "histogram_positive": None if histogram_n is None else histogram_n > 0,
        "histogram_rising_three": None if rising_n is None else rising_n >= 3,
        "rsi_50_to_70": None if rsi_n is None else 50 <= rsi_n <= 70,
        "relative_volume_above_one": None if volume_n is None else volume_n > 1,
    }
    missing = tuple(k for k, v in conditions.items() if v is None)
    score = None if missing else sum(v is True for v in conditions.values())
    return TechnicalScore(score=score, conditions=conditions, unavailable=missing)
