
"""Statistical performance analysis for Nasdaq backtesting."""

from __future__ import annotations

from dataclasses import dataclass
import math
from collections.abc import Sequence

from Backtesting_Engine.trade_simulator import (
    SimulatedTrade,
)


@dataclass(frozen=True)
class PerformanceStatistics:
    """Statistical summary of completed simulated trades."""

    total_trades: int
    winning_trades: int
    losing_trades: int
    breakeven_trades: int

    win_rate_pct: float

    average_gross_return_pct: float
    average_net_return_pct: float

    average_winning_return_pct: float | None
    average_losing_return_pct: float | None

    expectancy_pct: float
    profit_factor: float | None

    best_trade_pct: float
    worst_trade_pct: float

    average_transaction_cost_pct: float


def calculate_performance_statistics(
    trades: Sequence[SimulatedTrade]
) -> PerformanceStatistics:
    """
    Calculate statistical performance measurements.

    Uses net percentage returns after estimated
    transaction costs.

    Assumes equal weight per completed trade when
    calculating percentage-based profit factor.

    Does not model portfolio capital allocation,
    compounding, or overlapping capital exposure.
    """

    trade_list = list(trades)

    if not trade_list:
        raise ValueError(
            "At least one completed trade is required."
        )

    if not all(
        isinstance(trade, SimulatedTrade)
        for trade in trade_list
    ):
        raise TypeError(
            "All items must be SimulatedTrade objects."
        )

    # Collect and validate return measurements.
    net_returns = []
    gross_returns = []
    transaction_costs = []

    for trade in trade_list:

        values = (
            trade.net_return_pct,
            trade.gross_return_pct,
            trade.round_trip_cost_pct
        )

        if not all(math.isfinite(x) for x in values):
            raise ValueError(
                "Trade returns must be finite numbers."
            )

        net_returns.append(
            trade.net_return_pct
        )

        gross_returns.append(
            trade.gross_return_pct
        )

        transaction_costs.append(
            trade.round_trip_cost_pct
        )

    total = len(net_returns)

    winners = [
        value for value in net_returns
        if value > 0
    ]

    losers = [
        value for value in net_returns
        if value < 0
    ]

    breakeven = [
        value for value in net_returns
        if value == 0
    ]

    winning_count = len(winners)
    losing_count = len(losers)
    breakeven_count = len(breakeven)

    # Percentage of profitable completed trades.
    win_rate = (
        winning_count / total
    ) * 100.0

    # Average returns per completed trade.
    average_gross = (
        math.fsum(gross_returns) / total
    )

    average_net = (
        math.fsum(net_returns) / total
    )

    # Average winning and losing returns.
    average_win = (
        math.fsum(winners) / winning_count
        if winners
        else None
    )

    average_loss = (
        math.fsum(losers) / losing_count
        if losers
        else None
    )

    # Statistical expectancy per completed trade.
    expectancy = average_net

    # Percentage-based profit factor.
    total_profit = math.fsum(winners)
    total_loss = abs(math.fsum(losers))

    if total_loss > 0:
        profit_factor = (
            total_profit / total_loss
        )
    elif total_profit > 0:
        profit_factor = float("inf")
    else:
        profit_factor = None

    average_cost = (
        math.fsum(transaction_costs) / total
    )

    return PerformanceStatistics(
        total_trades=total,
        winning_trades=winning_count,
        losing_trades=losing_count,
        breakeven_trades=breakeven_count,
        win_rate_pct=win_rate,
        average_gross_return_pct=average_gross,
        average_net_return_pct=average_net,
        average_winning_return_pct=average_win,
        average_losing_return_pct=average_loss,
        expectancy_pct=expectancy,
        profit_factor=profit_factor,
        best_trade_pct=max(net_returns),
        worst_trade_pct=min(net_returns),
        average_transaction_cost_pct=average_cost,
    )
