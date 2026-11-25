
"""Integrated trade simulation and statistical analysis."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date

import pandas as pd

from Backtesting_Engine.signal_engine import (
    HistoricalSignal,
)

from Backtesting_Engine.multi_trade_simulator import (
    MultipleTradeResult,
    simulate_multiple_trades,
)

from Backtesting_Engine.performance_statistics import (
    PerformanceStatistics,
    calculate_performance_statistics,
)


@dataclass(frozen=True)
class BacktestAnalysis:
    """Combined simulation and performance results."""

    simulation: MultipleTradeResult
    statistics: PerformanceStatistics | None


def analyze_historical_signals(
    signals: Sequence[HistoricalSignal],
    histories: Mapping[str, pd.DataFrame],
    trading_dates: Sequence[date],
    *,
    holding_sessions: int = 5,
    round_trip_cost_pct: float = 0.50,
) -> BacktestAnalysis:
    """
    Simulate historical signals and analyze returns.

    Uses the existing multiple-trade simulator
    and statistical performance calculator.

    If no completed trades exist, statistics
    is None rather than an invalid summary.
    """

    # Step 1: Simulate historical trades.
    simulation = simulate_multiple_trades(
        signals=signals,
        histories=histories,
        trading_dates=trading_dates,
        holding_sessions=holding_sessions,
        round_trip_cost_pct=round_trip_cost_pct,
    )

    # Step 2: Calculate statistical performance.
    if simulation.trades:
        statistics = calculate_performance_statistics(
            simulation.trades
        )
    else:
        statistics = None

    # Step 3: Return both results.
    return BacktestAnalysis(
        simulation=simulation,
        statistics=statistics,
    )
