"""Version 1.2, Step 7: run score-based historical research from a discovery scan.

A validated screener JSON handoff supplies candidate symbols and historical
settings. The original strict momentum backtester is not modified; the Stock
Screener dispatches discovery scans to this module and strict scans to V1.1.

Research on today's candidate set has selection/survivorship bias. This tool
is not a point-in-time Nasdaq-universe backtest or investment advice.

PowerShell (project root):
  py -m Backtesting_Engine.scored_screener_integration --screener-report ".\\Stock_Screener\\Reports\\Nasdaq_21_Session_Screen_YYYYMMDD.docx"
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import date
from pathlib import Path
import sys
from typing import Any, Sequence

from .screener_handoff import (
    HandoffValidationError, ScreenerHandoff,
    latest_screener_handoff, load_screener_handoff,
)
from .screener_backtest import HandoffBacktestError, subtract_years


@dataclass(frozen=True)
class ScoredScreenerRun:
    handoff: ScreenerHandoff
    start_date: date
    end_date: date
    trading_dates: tuple[date, ...]
    backtest: Any | None


def run_scored_screener_backtest(handoff: ScreenerHandoff) -> ScoredScreenerRun:
    """Evaluate historical scored price/gain events for a discovery-mode handoff."""
    if handoff.screener_settings.momentum_confirmation_required:
        raise HandoffBacktestError(
            "This source scan requires strict momentum. Use the existing V1.1 "
            "screener_backtest command for strict-mode results."
        )
    first_date = subtract_years(handoff.scan_date, handoff.backtest_settings.history_years)
    last_date = handoff.scan_date
    if not handoff.qualifying_tickers:
        return ScoredScreenerRun(handoff, first_date, last_date, (), None)

    # Delayed imports preserve screener independence when backtesting is skipped.
    from .market_data_provider import download_historical_prices
    from .scored_backtest import run_scored_multi_stock_backtest

    reference = download_historical_prices("QQQ", first_date, last_date)
    if reference is None or reference.empty:
        raise HandoffBacktestError("QQQ returned no reference trading sessions.")
    sessions = set()
    for timestamp in reference.index:
        day = timestamp if type(timestamp) is date else timestamp.date()
        if type(day) is not date:
            raise HandoffBacktestError("The reference calendar contains an invalid date.")
        if first_date <= day <= last_date:
            sessions.add(day)
    trading_dates = tuple(sorted(sessions))
    b = handoff.backtest_settings
    if len(trading_dates) < 21 + b.holding_sessions:
        raise HandoffBacktestError("Not enough historical reference sessions for the requested holding period.")

    s = handoff.screener_settings
    backtest = run_scored_multi_stock_backtest(
        tickers=handoff.qualifying_tickers,
        trading_dates=trading_dates,
        start_date=trading_dates[0],
        end_date=trading_dates[-1],
        min_gain_pct=s.min_gain_pct,
        min_price=s.min_price,
        max_price=s.max_price,
        holding_sessions=b.holding_sessions,
        round_trip_cost_pct=b.round_trip_cost_pct,
    )
    return ScoredScreenerRun(handoff, first_date, last_date, trading_dates, backtest)


def run_latest_scored_backtest(path: str | Path | None = None) -> ScoredScreenerRun:
    source = Path(path) if path is not None else latest_screener_handoff()
    return run_scored_screener_backtest(load_screener_handoff(source))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluate historical technical-score groups for a validated Discovery Mode scan.")
    parser.add_argument("handoff", nargs="?", help="JSON handoff path (default: newest)")
    parser.add_argument("--screener-report", type=Path, default=None,
                        help="Word screener report from the same scan; append a score-based analysis")
    args = parser.parse_args(argv)
    try:
        result = run_latest_scored_backtest(args.handoff)
        h = result.handoff
        print("\nNASDAQ V1.2 — DISCOVERY SCORE-BASED HISTORICAL ANALYSIS")
        print(f"Source scan: {h.scan_id} | Session: {h.scan_date}")
        print(f"Discovery candidates: {len(h.qualifying_tickers)}")
        print(f"Historical period: {result.start_date} through {result.end_date}")
        if result.backtest is None:
            print("SKIPPED: No discovery candidates to backtest.")
            return 0
        backtest = result.backtest
        sim = backtest.analysis.simulation
        print(f"Trading sessions: {len(result.trading_dates)}")
        print(f"Symbols analyzed: {len(backtest.analyzed_tickers)}")
        print(f"Symbols excluded for historical data quality: {len(backtest.excluded_tickers)}")
        print(f"Historical price/gain signals: {sim.total_signals}")
        print(f"Completed simulated trades: {len(sim.trades)}")
        print("Score | Signals | Trades | Win rate | Net expectancy | Profit factor")
        for group in backtest.score_groups:
            stats = group.statistics
            score_label = "N/A" if group.score is None else str(group.score)
            win_rate = f"{stats.win_rate_pct:.2f}%" if stats is not None else "N/A"
            expectancy = f"{stats.expectancy_pct:+.4f}%" if stats is not None else "N/A"
            factor = "N/A" if stats is None or stats.profit_factor is None else (
                "Infinity" if stats.profit_factor == float("inf") else f"{stats.profit_factor:.4f}")
            print(f"{score_label:>5} | {group.signal_count:>7} | {group.completed_trades:>6} | {win_rate:>8} | {expectancy:>14} | {factor}")
        print("PASS: Historical technical-score analysis completed.")
        if args.screener_report is not None:
            from .scored_integrated_report import generate_scored_integrated_report
            path = generate_scored_integrated_report(result, args.screener_report)
            print(f"PASS: Integrated scored research report generated: {path.resolve()}")
        print("RESEARCH LIMITATION: Only today's qualifying tickers are studied historically; "
              "this does not validate a point-in-time Nasdaq strategy.")
        return 0
    except (HandoffValidationError, HandoffBacktestError, OSError, ValueError, TypeError, KeyError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
