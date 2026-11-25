
from __future__ import annotations
import math

import pandas as pd


# MACD configuration
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9
RSI_PERIOD = 14
RVOL_PERIOD = 20


def compute_macd(prices: pd.Series) -> pd.DataFrame:
    """
    Calculate MACD(12,26,9), signal line, and histogram.

    Uses recursive exponential moving averages.
    Leading warmup readings remain missing.
    """

    close = pd.to_numeric(prices, errors="coerce")

    # Ignore nonpositive closing prices.
    close = close.where(close > 0)

    fast = close.ewm(
        span=MACD_FAST,
        adjust=False,
        min_periods=MACD_FAST
    ).mean()

    slow = close.ewm(
        span=MACD_SLOW,
        adjust=False,
        min_periods=MACD_SLOW
    ).mean()

    macd = fast - slow

    signal = macd.ewm(
        span=MACD_SIGNAL,
        adjust=False,
        min_periods=MACD_SIGNAL
    ).mean()

    return pd.DataFrame({
        "MACD": macd,
        "Signal": signal,
        "Histogram": macd - signal
    })

def compute_rsi(
    prices: pd.Series,
    period: int = RSI_PERIOD
) -> pd.Series:
    """
    Calculate RSI using Wilder's smoothing method.

    Missing or invalid closing prices reset the
    calculation. Flat prices produce neutral RSI 50.
    """

    result = pd.Series(
        float("nan"),
        index=prices.index,
        dtype=float
    )

    prev = None
    gains, losses = [], []
    avg_gain = avg_loss = None

    for i, value in enumerate(
        pd.to_numeric(prices, errors="coerce")
    ):
        if not math.isfinite(value) or value <= 0:
            prev = avg_gain = avg_loss = None
            gains, losses = [], []
            continue

        if prev is None:
            prev = value
            continue

        change = value - prev
        prev = value

        gain = max(change, 0)
        loss = max(-change, 0)

        if avg_gain is None:
            gains.append(gain)
            losses.append(loss)

            if len(gains) < period:
                continue

            avg_gain = sum(gains) / period
            avg_loss = sum(losses) / period

        else:
            avg_gain = (
                avg_gain * (period - 1) + gain
            ) / period

            avg_loss = (
                avg_loss * (period - 1) + loss
            ) / period

        result.iloc[i] = (
            50.0 if avg_gain == avg_loss == 0
            else 100.0 if avg_loss == 0
            else 100 - 100 / (1 + avg_gain / avg_loss)
        )

    return result


def compute_relative_volume(
    volumes: pd.Series,
    period: int = RVOL_PERIOD
) -> pd.Series:
    """
    Calculate relative trading volume (RVOL).

    Compare each session's volume against the
    average of the preceding 20 sessions.

    Excludes the current session from the
    historical average.
    """

    volume = volumes.where(
        volumes.ge(0) & volumes.map(math.isfinite)
    )

    baseline = volume.shift(1).rolling(
        period,
        min_periods=period
    ).mean()

    relative_volume = volume / baseline.where(
        baseline > 0
    )

    return relative_volume



def compute_histogram_trend(
    histogram: pd.Series
) -> pd.DataFrame:
    """
    Measure changes in the MACD histogram.

    HistogramChange:
        Current histogram minus previous histogram.

    RisingDays:
        Number of consecutive sessions during which
        the histogram increased.

    A flat, decreasing, or missing observation
    resets the consecutive-increase count.
    """

    histogram_change = histogram.diff()

    rising = histogram_change.gt(0)

    rising_days = (
        rising.astype(int)
        .groupby((~rising).cumsum())
        .cumsum()
    )

    return pd.DataFrame({
        "HistogramChange": histogram_change,
        "RisingDays": rising_days
    })



def compute_indicators(
    history: pd.DataFrame
) -> pd.DataFrame:
    """
    Calculate all technical indicators using
    the shared analytics functions.

    Preserves the original Nasdaq screener's
    calculation methodology and column names.
    """

    close = history["Close"].where(
        history["Close"].gt(0)
        & history["Close"].map(math.isfinite)
    )

    volume = history["Volume"].where(
        history["Volume"].ge(0)
        & history["Volume"].map(math.isfinite)
    )

    # Reset MACD warmup after missing closes.
    groups = close.isna().cumsum()

    indicators = pd.concat([
        compute_macd(part)
        for _, part in close.groupby(groups)
    ]).reindex(history.index)

    histogram = indicators["Histogram"].where(
        close.notna()
    )

    indicators["Histogram"] = histogram

    indicators.loc[
        close.isna(), ["MACD", "Signal"]
    ] = float("nan")

    # Histogram momentum calculations.
    trend = compute_histogram_trend(histogram)

    indicators["RisingDays"] = trend["RisingDays"]

    # Normalize histogram by closing price.
    indicators["NormalizedHistogram"] = (
        100 * histogram / close
    )

    # Relative Strength Index.
    indicators["RSI"] = compute_rsi(close)

    # Relative trading volume.
    indicators["RelativeVolume"] = (
        compute_relative_volume(volume)
    )

    return indicators


