
"""Multiple-trade simulation for Nasdaq quantitative research."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
import math

import pandas as pd

from Backtesting_Engine.signal_engine import (
    HistoricalSignal,
)

from Backtesting_Engine.trade_simulator import (
    SimulatedTrade,
    simulate_trade,
)


@dataclass(frozen=True)
class MultipleTradeResult:
    """Completed trades and simulation accounting."""

    trades: tuple[SimulatedTrade, ...]
    total_signals: int
    skipped_overlapping: int
    skipped_incomplete: int


def simulate_multiple_trades(
    signals: Sequence[HistoricalSignal],
    histories: Mapping[str, pd.DataFrame],
    trading_dates: Sequence[date],
    *,
    holding_sessions: int = 5,
    round_trip_cost_pct: float = 0.50,
) -> MultipleTradeResult:
    """
    Simulate multiple historical screening signals.

    Rules:
      - Process signals chronologically.
      - Enter on the next trading session.
      - Permit only one active trade per ticker.
      - Permit simultaneous trades in different stocks.
      - Count skipped overlapping signals.
      - Count trades lacking future exit sessions.

    Returns a structured result containing completed
    trades and exclusion counts.
    """

    # Validate configuration.
    if type(holding_sessions) is not int:
        raise TypeError(
            "Holding sessions must be an integer."
        )

    if holding_sessions < 1:
        raise ValueError(
            "Holding sessions must be positive."
        )

    if (
        isinstance(round_trip_cost_pct, bool)
        or not isinstance(round_trip_cost_pct, (int, float))
        or not math.isfinite(round_trip_cost_pct)
        or not 0 <= round_trip_cost_pct <= 100
    ):
        raise ValueError(
            "Invalid round-trip transaction cost."
        )

    if not isinstance(histories, Mapping):
        raise TypeError(
            "Histories must map tickers to DataFrames."
        )

    dates = list(trading_dates)

    if not dates or not all(
        type(d) is date for d in dates
    ):
        raise ValueError(
            "A valid trading calendar is required."
        )

    if dates != sorted(set(dates)):
        raise ValueError(
            "Trading dates must be unique and ordered."
        )

    signal_list = list(signals)

    if not all(
        isinstance(s, HistoricalSignal)
        for s in signal_list
    ):
        raise TypeError(
            "All signals must be HistoricalSignal objects."
        )

    date_positions = {
        day: position
        for position, day in enumerate(dates)
    }

    # Validate references before processing trades.
    for signal in signal_list:
        if signal.signal_date not in date_positions:
            raise ValueError(
                "Signal date is missing from trading calendar."
            )

        if signal.ticker not in histories:
            raise KeyError(
                f"Missing historical data for {signal.ticker}"
            )

    # Chronological processing, with ticker tie-breaker.
    ordered_signals = sorted(
        signal_list,
        key=lambda s: (s.signal_date, s.ticker)
    )

    completed: list[SimulatedTrade] = []

    # Track the last occupied session per stock.
    occupied_through: dict[str, date] = {}

    skipped_overlapping = 0
    skipped_incomplete = 0

    for signal in ordered_signals:

        ticker = signal.ticker

        signal_position = date_positions[
            signal.signal_date
        ]

        entry_position = signal_position + 1

        # No next trading session is available.
        if entry_position >= len(dates):
            skipped_incomplete += 1
            continue

        proposed_entry_date = dates[entry_position]

        # Prevent simultaneous positions in one stock.
        last_exit = occupied_through.get(ticker)

        if (
            last_exit is not None
            and proposed_entry_date <= last_exit
        ):
            skipped_overlapping += 1
            continue

        # Reuse our tested single-trade simulator.
        trade = simulate_trade(
            signal=signal,
            history=histories[ticker],
            trading_dates=dates,
            holding_sessions=holding_sessions,
            round_trip_cost_pct=round_trip_cost_pct,
        )

        # Not enough future sessions to close the trade.
        if trade is None:
            skipped_incomplete += 1
            continue

        completed.append(trade)

        # Occupied through the exit session's close.
        occupied_through[ticker] = trade.exit_date

    return MultipleTradeResult(
        trades=tuple(completed),
        total_signals=len(signal_list),
        skipped_overlapping=skipped_overlapping,
        skipped_incomplete=skipped_incomplete,
    )
