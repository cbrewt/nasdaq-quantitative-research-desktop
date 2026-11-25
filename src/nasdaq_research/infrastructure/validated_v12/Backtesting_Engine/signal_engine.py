
"""Historical Nasdaq momentum signal generation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Sequence

import pandas as pd

from Backtesting_Engine.historical_data import (
    calculate_historical_indicators
)

from Shared_Analytics.screening_rules import (
    passes_momentum_screen
)


SESSION_COUNT = 21


@dataclass(frozen=True)
class HistoricalSignal:
    """A stock satisfying the historical momentum screen."""

    ticker: str
    signal_date: date
    first_close: float
    last_close: float
    gain_pct: float
    macd: float
    histogram: float
    rising_days: int
    rsi: float
    relative_volume: float


def generate_historical_signal(
    ticker: str,
    history: pd.DataFrame,
    cutoff: date,
    session_dates: Sequence[date],
    *,
    min_gain_pct: float = 10.0,
    min_price: float = 1.0,
    max_price: float = 10.0
) -> HistoricalSignal | None:
    """
    Evaluate a stock against historical momentum criteria.

    Return a HistoricalSignal if all criteria pass.
    Return None when the stock does not qualify.

    session_dates must contain the 21 expected
    trading dates ending at the signal session.
    """

    dates = list(session_dates)

    if len(dates) != SESSION_COUNT:
        raise ValueError(
            "Exactly 21 trading dates are required."
        )

    if any(
        not isinstance(d, date) for d in dates
    ):
        raise TypeError("Trading dates must be dates.")

    if dates != sorted(set(dates)):
        raise ValueError(
            "Trading dates must be unique and ordered."
        )

    if dates[-1] > cutoff:
        raise ValueError(
            "Signal date cannot exceed the cutoff."
        )

    if not (
        min_price > 0
        and max_price >= min_price
        and min_gain_pct >= 0
    ):
        raise ValueError("Invalid screening parameters.")

    # Calculate indicators using historical data.
    analyzed = calculate_historical_indicators(
        history,
        cutoff
    )

    # Ensure all required trading sessions exist.
    available = set(analyzed.index.date)

    if not set(dates).issubset(available):
        raise ValueError(
            "Historical data is missing required sessions."
        )

    # Select precisely the expected 21 sessions.
    daily = analyzed.loc[
        [pd.Timestamp(d) for d in dates]
    ]

    first_close = float(daily["Close"].iloc[0])
    last_close = float(daily["Close"].iloc[-1])

    if not min_price <= last_close <= max_price:
        return None

    gain_pct = (
        last_close / first_close - 1.0
    ) * 100.0

    if gain_pct + 1e-9 < min_gain_pct:
        return None

    # Evaluate technical indicators.
    latest = daily.iloc[-1]

    macd = float(latest["MACD"])
    histogram = float(latest["Histogram"])
    rising_days = int(latest["RisingDays"])
    rsi = float(latest["RSI"])
    relative_volume = float(
        latest["RelativeVolume"]
    )

    qualifies = passes_momentum_screen(
        macd=macd,
        histogram=histogram,
        rising_days=rising_days,
        rsi=rsi,
        relative_volume=relative_volume
    )

    if not qualifies:
        return None

    return HistoricalSignal(
        ticker=ticker,
        signal_date=dates[-1],
        first_close=first_close,
        last_close=last_close,
        gain_pct=gain_pct,
        macd=macd,
        histogram=histogram,
        rising_days=rising_days,
        rsi=rsi,
        relative_volume=relative_volume
    )
