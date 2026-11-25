
"""Historical trade simulation for Nasdaq quantitative research."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import math
from typing import Sequence

import pandas as pd

from Backtesting_Engine.historical_data import (
    validate_historical_data,
)

from Backtesting_Engine.signal_engine import (
    HistoricalSignal,
)


@dataclass(frozen=True)
class SimulatedTrade:
    """Results of a completed historical trade."""

    ticker: str
    signal_date: date
    entry_date: date
    exit_date: date
    holding_sessions: int
    entry_price: float
    exit_price: float
    gross_return_pct: float
    round_trip_cost_pct: float
    net_return_pct: float


def simulate_trade(
    signal: HistoricalSignal,
    history: pd.DataFrame,
    trading_dates: Sequence[date],
    *,
    holding_sessions: int = 5,
    round_trip_cost_pct: float = 0.50,
) -> SimulatedTrade | None:
    """
    Simulate a historical stock trade.

    Entry:
        Opening price of the first trading session
        following the screening signal.

    Exit:
        Closing price of the final holding session.

    Costs:
        A simplified percentage-of-entry-capital
        estimate for the complete round trip.

    Returns:
        SimulatedTrade if sufficient future sessions
        exist, otherwise None.

    Missing required OHLCV records raise an error.
    """

    if not isinstance(signal, HistoricalSignal):
        raise TypeError(
            "Signal must be a HistoricalSignal."
        )

    if type(holding_sessions) is not int:
        raise TypeError(
            "Holding sessions must be an integer."
        )

    if holding_sessions < 1:
        raise ValueError(
            "Holding sessions must be positive."
        )

    if (
        not math.isfinite(round_trip_cost_pct)
        or not 0 <= round_trip_cost_pct <= 100
    ):
        raise ValueError(
            "Round-trip cost must be between 0 and 100%."
        )

    dates = list(trading_dates)

    if not all(type(d) is date for d in dates):
        raise TypeError(
            "Trading dates must be date objects."
        )

    if dates != sorted(set(dates)):
        raise ValueError(
            "Trading dates must be unique and chronological."
        )

    if signal.signal_date not in dates:
        raise ValueError(
            "Signal date is not in the trading calendar."
        )

    signal_position = dates.index(
        signal.signal_date
    )

    entry_position = signal_position + 1

    exit_position = (
        signal_position + holding_sessions
    )

    # A trade cannot be completed without
    # sufficient subsequent trading sessions.
    if exit_position >= len(dates):
        return None

    entry_date = dates[entry_position]
    exit_date = dates[exit_position]

    # Validate historical OHLCV information.
    clean = validate_historical_data(history)

    entry_timestamp = pd.Timestamp(entry_date)
    exit_timestamp = pd.Timestamp(exit_date)

    if (
        entry_timestamp not in clean.index
        or exit_timestamp not in clean.index
    ):
        raise ValueError(
            "Missing required entry or exit price data."
        )

    entry_price = float(
        clean.loc[entry_timestamp, "Open"]
    )

    exit_price = float(
        clean.loc[exit_timestamp, "Close"]
    )

    # Percentage return before trading costs.
    gross_return_pct = (
        (exit_price / entry_price) - 1.0
    ) * 100.0

    # Initial simplified round-trip cost model.
    net_return_pct = (
        gross_return_pct - round_trip_cost_pct
    )

    return SimulatedTrade(
        ticker=signal.ticker,
        signal_date=signal.signal_date,
        entry_date=entry_date,
        exit_date=exit_date,
        holding_sessions=holding_sessions,
        entry_price=entry_price,
        exit_price=exit_price,
        gross_return_pct=gross_return_pct,
        round_trip_cost_pct=round_trip_cost_pct,
        net_return_pct=net_return_pct,
    )
