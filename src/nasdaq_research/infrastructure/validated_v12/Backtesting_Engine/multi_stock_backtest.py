
"""Multiple-stock historical backtesting for Nasdaq research."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
import math
import re

import pandas as pd

from Backtesting_Engine.market_data_provider import (
    download_historical_prices,
)

from Backtesting_Engine.evaluation_engine import (
    evaluate_historical_period,
)

from Backtesting_Engine.backtest_analysis import (
    BacktestAnalysis,
    analyze_historical_signals,
)

from Backtesting_Engine.signal_engine import (
    HistoricalSignal,
    SESSION_COUNT,
)


@dataclass(frozen=True)
class MultiStockBacktestResult:
    """Results of a multiple-stock historical backtest."""

    tickers: tuple[str, ...]
    evaluation_start: date
    evaluation_end: date
    signal_counts: tuple[tuple[str, int], ...]
    analysis: BacktestAnalysis


def run_multi_stock_backtest(
    tickers: Sequence[str],
    trading_dates: Sequence[date],
    *,
    start_date: date | None = None,
    end_date: date | None = None,
    min_gain_pct: float = 10.0,
    min_price: float = 1.0,
    max_price: float = 10.0,
    holding_sessions: int = 5,
    round_trip_cost_pct: float = 0.50,
) -> MultiStockBacktestResult:
    """
    Evaluate multiple stocks over a historical period.

    Uses existing modules for:
        Historical market data retrieval
        Historical momentum signal generation
        Multiple-trade simulation
        Statistical performance analysis

    trading_dates:
        An explicit, ordered exchange trading calendar.

        Include at least 21 sessions before or
        through the first desired signal.

        Include future sessions after the last
        signal when completed exits are required.

    Missing or mismatched market-data sessions
    raise an error rather than being silently
    excluded from the research sample.

    Returns combined simulation results and
    individual stock signal counts.
    """

    # Validate ticker collection.
    if isinstance(tickers, (str, bytes)):
        raise TypeError(
            "Tickers must be a collection of symbols."
        )

    symbols = []

    for ticker in tickers:

        if not isinstance(ticker, str):
            raise TypeError(
                "Each ticker must be a string."
            )

        symbol = ticker.strip().upper()

        if not re.fullmatch(
            r"[A-Z0-9][A-Z0-9.\-]{0,19}",
            symbol
        ):
            raise ValueError(
                f"Invalid ticker: {ticker}"
            )

        symbols.append(symbol)

    if not symbols:
        raise ValueError(
            "At least one stock is required."
        )

    if len(set(symbols)) != len(symbols):
        raise ValueError(
            "Duplicate stock symbols are not allowed."
        )

    # Validate the historical trading calendar.
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
            "Trading dates must be unique and ordered."
        )

    # Default to the first session with a
    # complete 21-session observation window.
    first_eligible = dates[SESSION_COUNT - 1]

    evaluation_start = (
        first_eligible
        if start_date is None
        else start_date
    )

    evaluation_end = (
        dates[-1]
        if end_date is None
        else end_date
    )

    if (
        type(evaluation_start) is not date
        or type(evaluation_end) is not date
    ):
        raise TypeError(
            "Evaluation boundaries must be dates."
        )

    if evaluation_start > evaluation_end:
        raise ValueError(
            "Start date cannot exceed end date."
        )

    if (
        evaluation_start < dates[0]
        or evaluation_end > dates[-1]
        or evaluation_end < first_eligible
    ):
        raise ValueError(
            "Evaluation dates are outside the "
            "usable trading calendar."
        )

    # Validate screening parameters.
    parameters = (
        min_gain_pct,
        min_price,
        max_price,
    )

    if not all(
        isinstance(x, (int, float))
        and not isinstance(x, bool)
        and math.isfinite(x)
        for x in parameters
    ):
        raise ValueError(
            "Screening parameters must be finite numbers."
        )

    if (
        min_gain_pct < 0
        or min_price <= 0
        or max_price < min_price
    ):
        raise ValueError(
            "Invalid price or percentage filters."
        )

    # These settings are also validated by the
    # existing multiple-trade simulator.
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

    # Collect historical data and signals.
    histories: dict[str, pd.DataFrame] = {}

    all_signals: list[HistoricalSignal] = []

    signal_counts: list[tuple[str, int]] = []

    for symbol in symbols:

        print(
            f"Downloading historical prices for {symbol}..."
        )

        history = download_historical_prices(
            ticker=symbol,
            start_date=dates[0],
            end_date=dates[-1],
        )

        # Require every expected exchange session
        # to exist, with no unexpected extra dates.
        # This strict policy is intended for the
        # initial small-universe research prototype.
        observed_dates = list(history.index.date)

        if observed_dates != dates:
            raise ValueError(
                f"Historical trading-calendar mismatch "
                f"for {symbol}. Review missing or "
                f"unexpected observations."
            )

        histories[symbol] = history

        # Generate historical momentum signals.
        signals = evaluate_historical_period(
            ticker=symbol,
            history=history,
            trading_dates=dates,
            start_date=evaluation_start,
            end_date=evaluation_end,
            min_gain_pct=min_gain_pct,
            min_price=min_price,
            max_price=max_price,
        )

        all_signals.extend(signals)

        signal_counts.append(
            (symbol, len(signals))
        )

        print(
            f"{symbol}: {len(signals)} "
            f"qualifying historical signals."
        )

    # Simulate trades across all selected stocks.
    analysis = analyze_historical_signals(
        signals=all_signals,
        histories=histories,
        trading_dates=dates,
        holding_sessions=holding_sessions,
        round_trip_cost_pct=round_trip_cost_pct,
    )

    return MultiStockBacktestResult(
        tickers=tuple(symbols),
        evaluation_start=evaluation_start,
        evaluation_end=evaluation_end,
        signal_counts=tuple(signal_counts),
        analysis=analysis,
    )
