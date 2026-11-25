
"""Historical market data validation for Nasdaq backtesting."""

from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd
from Shared_Analytics.indicators import compute_indicators



REQUIRED_COLUMNS = (
    "Open",
    "High",
    "Low",
    "Close",
    "Volume",
)


def validate_historical_data(
    history: pd.DataFrame
) -> pd.DataFrame:
    """
    Validate daily OHLCV market data.

    Requires a chronological DatetimeIndex with
    one observation per trading date.

    Timezone-aware dates are converted to
    America/New_York before validation.

    Returns a validated copy of the data.
    """

    if not isinstance(history, pd.DataFrame):
        raise TypeError("History must be a DataFrame.")

    if history.empty:
        raise ValueError("Historical data is empty.")

    missing = [
        col for col in REQUIRED_COLUMNS
        if col not in history.columns
    ]

    if missing:
        raise ValueError(
            f"Missing required columns: {missing}"
        )

    if not isinstance(history.index, pd.DatetimeIndex):
        raise ValueError(
            "History must use a DatetimeIndex."
        )

    # Standardize trading dates to New York time.
    dates = history.index

    if dates.tz is not None:
        dates = dates.tz_convert(
            "America/New_York"
        ).tz_localize(None)

    if dates.hasnans:
        raise ValueError("Invalid trading dates found.")

    if not dates.equals(dates.normalize()):
        raise ValueError(
            "Expected daily bars dated at midnight."
        )

    if dates.has_duplicates:
        raise ValueError("Duplicate trading dates found.")

    if not dates.is_monotonic_increasing:
        raise ValueError(
            "Trading dates must be chronological."
        )

    # Convert market values to numeric types.
    clean = history.loc[
        :, list(REQUIRED_COLUMNS)
    ].apply(pd.to_numeric, errors="coerce")

    if not np.isfinite(
        clean.to_numpy(dtype=float)
    ).all():
        raise ValueError(
            "Missing or non-finite market values."
        )

    prices = clean[
        ["Open", "High", "Low", "Close"]
    ]

    if (prices <= 0).any().any():
        raise ValueError(
            "Stock prices must be positive."
        )

    if (clean["Volume"] < 0).any():
        raise ValueError(
            "Trading volume cannot be negative."
        )

    if (
        clean["High"] < prices.max(axis=1)
    ).any():
        raise ValueError(
            "High price is inconsistent with OHLC."
        )

    if (
        clean["Low"] > prices.min(axis=1)
    ).any():
        raise ValueError(
            "Low price is inconsistent with OHLC."
        )

    clean.index = dates

    return clean


def history_as_of(
    history: pd.DataFrame,
    cutoff: date
) -> pd.DataFrame:
    """
    Return validated daily data available through
    the specified historical trading date.

    Future trading sessions are excluded.
    """

    if not isinstance(cutoff, date):
        raise TypeError("Cutoff must be a date.")

    clean = validate_historical_data(history)

    result = clean.loc[
        clean.index.date <= cutoff
    ].copy()

    if result.empty:
        raise ValueError(
            "No historical data exists before cutoff."
        )

    return result


def calculate_historical_indicators(
    history: pd.DataFrame,
    cutoff: date
) -> pd.DataFrame:
    """
    Calculate technical indicators using only
    historical observations through the cutoff.

    Uses the same shared indicator calculations
    as the operational Nasdaq Stock Screener.

    Returns validated OHLCV data combined
    with the calculated technical indicators.
    """

    # Validate market data and exclude future dates.
    historical = history_as_of(
        history,
        cutoff
    )

    # Calculate indicators from historical data only.
    indicators = compute_indicators(
        historical
    )

    # Combine prices, volume, and indicators.
    result = historical.join(
        indicators
    )

    return result

