
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


# CAL-001: independently verified first trading sessions, not inferred from provider gaps.
VERIFIED_LISTINGS = {
    "STAK": (date(2025, 2, 26), "https://www.sec.gov/Archives/edgar/data/2002453/000149315225009229/ex99-1.htm"),
}


def eligible_calendar(symbol, dates, observed_dates):
    """Require the complete reference calendar from verified listing onward."""
    evidence = VERIFIED_LISTINGS.get(symbol)
    expected = [d for d in dates if evidence is None or d >= evidence[0]]
    if not expected or observed_dates != expected:
        missing = sorted(set(expected) - set(observed_dates))
        extra = sorted(set(observed_dates) - set(expected))
        raise ValueError(
            f"Historical trading-calendar mismatch for {symbol}: "
            f"missing={len(missing)}, unexpected={len(extra)}, "
            f"duplicate={len(observed_dates)-len(set(observed_dates))}; "
            f"first missing={missing[:3]}, first unexpected={extra[:3]}. "
            "Unverified leading absence, internal/trailing gaps and unordered dates are not accepted."
        )
    if len(expected) < len(dates):
        print(f"CAL-001: {symbol}: {len(dates)-len(expected)} verified pre-listing sessions excluded; "
              f"first trading date {evidence[0]}; source {evidence[1]}", flush=True)
    return expected


@dataclass(frozen=True)
class CapturedStrictResult:
    """Results of a multiple-stock historical backtest."""

    tickers: tuple[str, ...]
    evaluation_start: date
    evaluation_end: date
    signal_counts: tuple[tuple[str, int], ...]
    analysis: BacktestAnalysis
    signals: tuple[HistoricalSignal, ...]


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
) -> CapturedStrictResult:
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

    Only independently verified pre-listing absence is accepted.
    Other missing or mismatched sessions raise an error.

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

        # Only independently verified pre-listing sessions may be absent.
        observed_dates = list(history.index.date)
        symbol_dates = eligible_calendar(symbol, dates, observed_dates)
        histories[symbol] = history

        # The original evaluator enforces its 21-session window and indicator
        # eligibility. Do not fabricate pre-listing observations or warmup data.
        signals = []
        if len(symbol_dates) >= SESSION_COUNT:
            signals = evaluate_historical_period(
                ticker=symbol,
                history=history,
                trading_dates=symbol_dates,
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

    return CapturedStrictResult(
        tickers=tuple(symbols),
        evaluation_start=evaluation_start,
        evaluation_end=evaluation_end,
        signal_counts=tuple(signal_counts),
        analysis=analysis,
        signals=tuple(all_signals),
    )

from Backtesting_Engine.screener_backtest import ScreenerBacktestResult, ScreenerHandoff, HandoffBacktestError, subtract_years

def run_screener_backtest(handoff: ScreenerHandoff) -> ScreenerBacktestResult:
    """Run the installed Backtesting Engine over the handoff's historical window.

    Uses QQQ solely to obtain a trading-session calendar. The installed
    market_data_provider.download_historical_prices accepts an INCLUSIVE end_date
    and handles Yahoo's exclusive API boundary internally.
    """
    first_date = subtract_years(handoff.scan_date, handoff.backtest_settings.history_years)
    last_date = handoff.scan_date

    # No historical simulation can be performed without any selected tickers.
    if not handoff.qualifying_tickers:
        return ScreenerBacktestResult(handoff, first_date, last_date, (), None)

    # The V1.0 historical signal generator always applies momentum rules.
    # Explicitly reject research-mode handoffs instead of mislabeling the test.
    if not handoff.screener_settings.momentum_confirmation_required:
        raise HandoffBacktestError(
            "The source scan disabled momentum confirmation (research mode). "
            "The V1.0 Backtesting Engine cannot reproduce that mode; "
            "no backtest was performed."
        )

    # Import after checking the handoff so that empty scans do not require
    # market-data access or load the historical simulator unnecessarily.
    from Backtesting_Engine.market_data_provider import download_historical_prices

    reference = download_historical_prices("QQQ", first_date, last_date)
    if reference is None or reference.empty:
        raise HandoffBacktestError("QQQ returned no trading calendar for the requested period.")

    dates: set[date] = set()
    for timestamp in reference.index:
        trading_day = timestamp if isinstance(timestamp, date) and not hasattr(timestamp, "date") else timestamp.date()
        if not isinstance(trading_day, date):
            raise HandoffBacktestError("Reference data contained an invalid trading date.")
        if first_date <= trading_day <= last_date:
            dates.add(trading_day)

    trading_dates = tuple(sorted(dates))
    if len(trading_dates) < 21 + handoff.backtest_settings.holding_sessions:
        raise HandoffBacktestError(
            "Insufficient Nasdaq calendar sessions for the historical window "
            f"({len(trading_dates)} found)."
        )

    s = handoff.screener_settings
    b = handoff.backtest_settings
    result = run_multi_stock_backtest(
        tickers=handoff.qualifying_tickers,
        trading_dates=trading_dates,
        # The evaluator accepts inclusive dates inside the usable calendar.
        # Use actual trading sessions (the requested start may be a holiday).
        start_date=trading_dates[0],
        end_date=trading_dates[-1],
        min_gain_pct=s.min_gain_pct,
        min_price=s.min_price,
        max_price=s.max_price,
        holding_sessions=b.holding_sessions,
        round_trip_cost_pct=b.round_trip_cost_pct,
    )
    return ScreenerBacktestResult(handoff, first_date, last_date, trading_dates, result)
