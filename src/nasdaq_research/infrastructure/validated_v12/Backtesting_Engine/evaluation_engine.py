
"""Evaluate historical Nasdaq screening signals over time."""

from __future__ import annotations

from datetime import date
from typing import Sequence

import pandas as pd

from Backtesting_Engine.signal_engine import (
    HistoricalSignal,
    generate_historical_signal,
    SESSION_COUNT,
)


def evaluate_historical_period(
    ticker: str,
    history: pd.DataFrame,
    trading_dates: Sequence[date],
    *,
    start_date: date | None = None,
    end_date: date | None = None,
    min_gain_pct: float = 10.0,
    min_price: float = 1.0,
    max_price: float = 10.0,
) -> list[HistoricalSignal]:
    """
    Evaluate a stock across multiple historical sessions.

    Use an explicit exchange trading calendar.
    Each signal uses exactly 21 trading dates.

    Returns a chronological list of qualifying signals.
    Missing required sessions raise an error rather
    than being silently skipped.
    """

    dates = list(trading_dates)

    if len(dates) < SESSION_COUNT:
        raise ValueError(
            "At least 21 trading dates are required."
        )

    if not all(type(d) is date for d in dates):
        raise TypeError(
            "Trading dates must be date objects."
        )

    if dates != sorted(set(dates)):
        raise ValueError(
            "Trading dates must be unique and chronological."
        )

    if not ticker or not ticker.strip():
        raise ValueError("Ticker cannot be empty.")

    if not isinstance(history, pd.DataFrame):
        raise TypeError("History must be a DataFrame.")

    if not isinstance(history.index, pd.DatetimeIndex):
        raise TypeError(
            "History must use a DatetimeIndex."
        )

    for boundary in (start_date, end_date):
        if boundary is not None and type(boundary) is not date:
            raise TypeError(
                "Start and end dates must be date objects."
            )

    if (
        start_date is not None
        and end_date is not None
        and start_date > end_date
    ):
        raise ValueError(
            "Start date cannot exceed end date."
        )

    # Interpret timezone-aware timestamps in New York.
    index_dates = history.index

    if index_dates.tz is not None:
        index_dates = index_dates.tz_convert(
            "America/New_York"
        )

    signals: list[HistoricalSignal] = []

    # First eligible session has 20 preceding sessions.
    for position in range(SESSION_COUNT - 1, len(dates)):

        signal_date = dates[position]

        if start_date is not None and signal_date < start_date:
            continue

        if end_date is not None and signal_date > end_date:
            break

        window = dates[
            position - SESSION_COUNT + 1:position + 1
        ]

        # Exclude future rows before validating or
        # calculating indicators for this signal date.
        history_to_date = history.loc[
            index_dates.date <= signal_date
        ].copy()

        signal = generate_historical_signal(
            ticker=ticker,
            history=history_to_date,
            cutoff=signal_date,
            session_dates=window,
            min_gain_pct=min_gain_pct,
            min_price=min_price,
            max_price=max_price,
        )

        if signal is not None:
            signals.append(signal)

    return signals
