
"""Historical stock market data retrieval for Nasdaq backtesting."""

from __future__ import annotations

from datetime import date, timedelta
import re

import pandas as pd
import yfinance as yf

from Backtesting_Engine.historical_data import (
    validate_historical_data,
)


def download_historical_prices(
    ticker: str,
    start_date: date,
    end_date: date,
) -> pd.DataFrame:
    """
    Download and validate daily historical stock prices.

    Retrieves:
        Open, High, Low, Close, Volume

    Dates:
        start_date is inclusive.
        end_date is inclusive.

    Returns:
        Validated OHLCV DataFrame with a
        chronological, timezone-naive
        New York trading-date index.

    Raises:
        TypeError for invalid input types.
        ValueError for invalid dates, symbols,
        empty data, or invalid market records.
        RuntimeError for provider request failures.
    """

    # Validate ticker.
    if not isinstance(ticker, str):
        raise TypeError("Ticker must be a string.")

    symbol = ticker.strip().upper()

    if not re.fullmatch(
        r"[A-Z0-9][A-Z0-9.\-]{0,19}",
        symbol
    ):
        raise ValueError("Invalid ticker symbol.")

    # Validate date objects.
    if (
        type(start_date) is not date
        or type(end_date) is not date
    ):
        raise TypeError(
            "Start and end must be date objects."
        )

    if start_date > end_date:
        raise ValueError(
            "Start date cannot exceed end date."
        )

    if end_date == date.max:
        raise ValueError(
            "End date exceeds supported range."
        )

    # Yahoo uses an exclusive end date.
    exclusive_end = end_date + timedelta(days=1)

    # Yahoo represents some class shares with '-'.
    yahoo_symbol = symbol.replace(".", "-")

    try:
        history = yf.Ticker(
            yahoo_symbol
        ).history(
            start=start_date.isoformat(),
            end=exclusive_end.isoformat(),
            interval="1d",
            auto_adjust=False,
            actions=True,
            repair=False,
            prepost=False,
            timeout=30,
            raise_errors=True,
        )

    except Exception as exc:
        raise RuntimeError(
            f"Historical download failed "
            f"for {symbol}: {exc}"
        ) from exc

    if history is None or history.empty:
        raise ValueError(
            f"No historical prices returned for {symbol}."
        )

    # Validate dates, prices, and trading volume.
    # The validator also converts timezone-aware
    # daily bars to New York trading dates.
    clean = validate_historical_data(history)

    # Retain only the requested date range.
    mask = (
        (clean.index.date >= start_date)
        & (clean.index.date <= end_date)
    )

    result = clean.loc[mask].copy()

    if result.empty:
        raise ValueError(
            f"No valid daily prices found "
            f"for {symbol} in the requested range."
        )

    return result
