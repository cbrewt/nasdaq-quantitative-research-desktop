#!/usr/bin/env python3
"""Run a historical backtest from an approved Nasdaq Stock Screener handoff.

Nasdaq Research Integration V1.1, Step 5.

From the project root (PowerShell):
    py -m Backtesting_Engine.screener_backtest

Optionally supply a specific handoff:
    py -m Backtesting_Engine.screener_backtest ".\\Stock_Screener\\Reports\\Nasdaq_Screen_Handoff_....json"

This module leaves the original screener, JSON handoff and existing Word
report untouched. If --screener-report is supplied, Step 7 writes a separate integrated Word report.

Research limitations:
    - Backtests only the symbols selected by the CURRENT screener; this is
      subject to selection/survivorship bias and does not validate the strategy.
    - The historical engine does not reproduce past Nasdaq membership or
      point-in-time reverse-split exclusion.
    - History before a ticker's listing date may not exist.
    - Simulated fills and costs are simplified; results are not predictions.
"""

from __future__ import annotations

import argparse
import calendar
from dataclasses import dataclass
from datetime import date
from pathlib import Path
import sys
from typing import Any, Sequence

from .screener_handoff import (
    HandoffValidationError,
    ScreenerHandoff,
    latest_screener_handoff,
    load_screener_handoff,
)


class HandoffBacktestError(RuntimeError):
    """The handoff cannot be backtested using the supported V1.0 engine."""


@dataclass(frozen=True)
class ScreenerBacktestResult:
    handoff: ScreenerHandoff
    start_date: date
    end_date: date                  # inclusive historical cutoff
    trading_dates: tuple[date, ...]
    backtest: Any | None           # MultiStockBacktestResult, None if zero tickers


def subtract_years(day: date, years: int) -> date:
    """Subtract whole calendar years; clip Feb 29 to Feb 28 if necessary."""
    target_year = day.year - years
    if target_year < 1:
        raise HandoffBacktestError("Requested historical start date is out of range.")
    return date(target_year, day.month, min(day.day, calendar.monthrange(target_year, day.month)[1]))


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
    from .market_data_provider import download_historical_prices
    from .multi_stock_backtest import run_multi_stock_backtest

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


def run_latest_screener_backtest(path: str | Path | None = None) -> ScreenerBacktestResult:
    source = Path(path) if path is not None else latest_screener_handoff()
    return run_screener_backtest(load_screener_handoff(source))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Backtest validated screener candidates; optionally generate integrated Word research report.")
    parser.add_argument("handoff", nargs="?", help="Optional JSON path; default: latest handoff")
    parser.add_argument("--screener-report", type=Path, default=None,
                        help="Original Word screener report for the SAME scan; generate integrated report")
    args = parser.parse_args(argv)
    try:
        result = run_latest_screener_backtest(args.handoff)
    except (HandoffValidationError, HandoffBacktestError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    handoff = result.handoff
    print("\nNASDAQ SCREENER-TO-BACKTEST — HISTORICAL ANALYSIS")
    print(f"Source scan: {handoff.scan_id} | Session: {handoff.scan_date}")
    print(f"Selected stocks: {', '.join(handoff.qualifying_tickers) or '(none)'}")
    print(f"Historical period: {result.start_date} through {result.end_date}")
    if result.backtest is None:
        print("SKIPPED: No qualifying stocks. Nothing to backtest.")
        return 0
    print(f"Reference trading sessions: {len(result.trading_dates)}")
    analysis = getattr(result.backtest, "analysis", None)
    simulation = getattr(analysis, "simulation", None)
    statistics = getattr(analysis, "statistics", None)
    if simulation is not None:
        if hasattr(simulation, "total_signals"):
            print(f"Historical qualifying signals: {simulation.total_signals}")
        if hasattr(simulation, "trades"):
            print(f"Completed simulated trades: {len(simulation.trades)}")
    if statistics is not None:
        if hasattr(statistics, "win_rate_pct"):
            print(f"Historical win rate: {statistics.win_rate_pct:.2f}%")
        if hasattr(statistics, "expectancy_pct"):
            print(f"Historical net expectancy: {statistics.expectancy_pct:+.4f}%")
        if hasattr(statistics, "profit_factor"):
            print(f"Historical profit factor: {statistics.profit_factor}")
    print("PASS: Historical backtest executed using the imported screener parameters.")
    if args.screener_report is not None:
        try:
            from .integrated_report import generate_integrated_report
            report_path = generate_integrated_report(result, args.screener_report)
        except (OSError, ValueError, TypeError) as exc:
            print(f"ERROR: Integrated Word report could not be created: {exc}", file=sys.stderr)
            return 1
        print(f"PASS: Integrated Word research report generated: {report_path.resolve()}")
    print("RESEARCH LIMITATION: Current-candidate historical results do not validate "
          "the strategy across a point-in-time Nasdaq universe.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
