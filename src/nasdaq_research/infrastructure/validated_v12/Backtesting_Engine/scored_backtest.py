"""Version 1.2, Step 6: point-in-time technical-score backtesting.

This is additive. Version 1.1's strict momentum backtester is unchanged.
For the selected current-day tickers, evaluate historical 21-session price/gain
signals WITHOUT mandatory momentum confirmation; assign each signal the five-
condition score computed on the signal date; simulate trades once across all
scores using the existing nonoverlap/cost assumptions; summarize by score.

No report or interactive screener changes occur in this step (Step 7 integrates).
This is current-candidate-conditioned research, not a market-wide strategy test.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import date
import math
import re

import pandas as pd

from Backtesting_Engine.backtest_analysis import (
    BacktestAnalysis,
    analyze_historical_signals,
)
from Backtesting_Engine.historical_data import validate_historical_data
from Backtesting_Engine.performance_statistics import (
    PerformanceStatistics,
    calculate_performance_statistics,
)
from Backtesting_Engine.signal_engine import HistoricalSignal, SESSION_COUNT
from Shared_Analytics.indicators import compute_indicators
from Shared_Analytics.technical_scoring import TechnicalScore, evaluate_technical_score


@dataclass(frozen=True)
class ScoredSignal:
    """A price/gain signal and its signal-date-only technical assessment."""

    signal: HistoricalSignal
    assessment: TechnicalScore


@dataclass(frozen=True)
class ScorePerformance:
    """One score's signal count and accepted trades (0-5, or None = N/A)."""

    score: int | None
    signal_count: int
    completed_trades: int
    statistics: PerformanceStatistics | None


@dataclass(frozen=True)
class ScoredBacktestResult:
    """Research output, including explicit symbol-coverage exclusions."""

    requested_tickers: tuple[str, ...]
    analyzed_tickers: tuple[str, ...]
    excluded_tickers: tuple[tuple[str, str], ...]
    evaluation_start: date
    evaluation_end: date
    signal_counts: tuple[tuple[str, int], ...]
    scored_signals: tuple[ScoredSignal, ...]
    analysis: BacktestAnalysis
    score_groups: tuple[ScorePerformance, ...]


def _validate_parameters(
    tickers: Sequence[str],
    trading_dates: Sequence[date],
    start_date: date | None,
    end_date: date | None,
    min_gain_pct: float,
    min_price: float,
    max_price: float,
    holding_sessions: int,
    round_trip_cost_pct: float,
) -> tuple[tuple[str, ...], tuple[date, ...], date, date]:
    if isinstance(tickers, (str, bytes)):
        raise TypeError("Tickers must be a sequence of symbols.")
    symbols = []
    for raw in tickers:
        if not isinstance(raw, str):
            raise TypeError("Each ticker must be a string.")
        symbol = raw.strip().upper()
        if not re.fullmatch(r"[A-Z0-9][A-Z0-9.\-]{0,19}", symbol):
            raise ValueError(f"Invalid ticker symbol: {raw!r}")
        symbols.append(symbol)
    if not symbols or len(set(symbols)) != len(symbols):
        raise ValueError("Require at least one distinct ticker.")

    dates = list(trading_dates)
    if len(dates) < SESSION_COUNT or any(type(d) is not date for d in dates):
        raise ValueError("At least 21 valid trading dates are required.")
    if dates != sorted(set(dates)):
        raise ValueError("Trading dates must be unique and chronological.")

    for boundary in (start_date, end_date):
        if boundary is not None and type(boundary) is not date:
            raise TypeError("Evaluation boundaries must be dates.")
    first = dates[SESSION_COUNT - 1] if start_date is None else start_date
    last = dates[-1] if end_date is None else end_date
    if first > last or first < dates[0] or last > dates[-1] or last < dates[SESSION_COUNT - 1]:
        raise ValueError("Evaluation dates are outside the usable trading calendar.")

    for value in (min_gain_pct, min_price, max_price, round_trip_cost_pct):
        if (isinstance(value, bool) or not isinstance(value, (int, float))
                or not math.isfinite(value)):
            raise ValueError("Screening and cost parameters must be finite numbers.")
    if min_gain_pct < 0 or min_price <= 0 or max_price < min_price:
        raise ValueError("Invalid price or percentage filters.")
    if type(holding_sessions) is not int or holding_sessions < 1:
        raise ValueError("Holding sessions must be a positive integer.")
    if not 0 <= round_trip_cost_pct <= 100:
        raise ValueError("Round-trip cost must be between 0 and 100%.")
    return tuple(symbols), tuple(dates), first, last


def _evaluate_symbol(
    ticker: str,
    history: pd.DataFrame,
    trading_dates: tuple[date, ...],
    *,
    start_date: date,
    end_date: date,
    min_gain_pct: float,
    min_price: float,
    max_price: float,
) -> tuple[ScoredSignal, ...]:
    """Compute shared *causal* indicators once; read only signal-date rows.

    Shared_Analytics.compute_indicators uses trailing/recursive computations,
    never centered or forward windows. The verification suite checks that
    adding/changing future prices cannot affect earlier indicator values.
    """
    clean = validate_historical_data(history)
    # Preserve the explicit exchange calendar; do not treat missing days as
    # consecutive trading sessions. Coverage is checked by the caller.
    analyzed = clean.join(compute_indicators(clean))
    observations: list[ScoredSignal] = []

    for idx in range(SESSION_COUNT - 1, len(trading_dates)):
        signal_date = trading_dates[idx]
        if signal_date < start_date:
            continue
        if signal_date > end_date:
            break
        window = trading_dates[idx - SESSION_COUNT + 1:idx + 1]
        # Skip windows before this ticker's first listing observation.
        if pd.Timestamp(window[0]) not in clean.index:
            continue
        latest = analyzed.loc[pd.Timestamp(signal_date)]
        first_close = float(clean.loc[pd.Timestamp(window[0]), "Close"])
        last_close = float(latest["Close"])
        if not min_price <= last_close <= max_price:
            continue
        gain_pct = 100.0 * (last_close / first_close - 1.0)
        if gain_pct + 1e-9 < min_gain_pct:
            continue

        score = evaluate_technical_score(
            macd=latest["MACD"],
            histogram=latest["Histogram"],
            rising_days=latest["RisingDays"],
            rsi=latest["RSI"],
            relative_volume=latest["RelativeVolume"],
        )
        # HistoricalSignal is the existing tested trade-simulator interface.
        signal = HistoricalSignal(
            ticker=ticker,
            signal_date=signal_date,
            first_close=first_close,
            last_close=last_close,
            gain_pct=gain_pct,
            macd=float(latest["MACD"]),
            histogram=float(latest["Histogram"]),
            rising_days=int(latest["RisingDays"]),
            rsi=float(latest["RSI"]),
            relative_volume=float(latest["RelativeVolume"]),
        )
        observations.append(ScoredSignal(signal=signal, assessment=score))
    return tuple(observations)


def run_scored_multi_stock_backtest(
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
    price_loader: Callable[[str, date, date], pd.DataFrame] | None = None,
) -> ScoredBacktestResult:
    """Evaluate current candidate tickers historically, grouped by signal score.

    Requires an exchange reference calendar, with at least 21 prior sessions.
    Late-listed symbols may have a CONTIGUOUS suffix of that calendar; no
    fabricated prices are permitted. An unusable/missing/internal-gap history
    is excluded with a visible reason, not silently counted as no signals.
    All scores compete for the SAME one-position-per-stock trade simulation.

    price_loader (ticker,start,end) allows deterministic offline verification.
    The normal loader uses Yahoo Finance via the existing provider.
    """
    symbols, dates, first, last = _validate_parameters(
        tickers, trading_dates, start_date, end_date,
        min_gain_pct, min_price, max_price,
        holding_sessions, round_trip_cost_pct,
    )
    if price_loader is None:
        from Backtesting_Engine.market_data_provider import download_historical_prices
        price_loader = download_historical_prices
    elif not callable(price_loader):
        raise TypeError("price_loader must be callable.")

    histories: dict[str, pd.DataFrame] = {}
    excluded: list[tuple[str, str]] = []
    counts: list[tuple[str, int]] = []
    scored: list[ScoredSignal] = []
    for ticker in symbols:
        print(f"Downloading historical prices for {ticker}...")
        try:
            clean = validate_historical_data(price_loader(ticker, dates[0], dates[-1]))
        except (TypeError, ValueError, RuntimeError, OSError) as exc:
            excluded.append((ticker, f"Historical data unavailable or invalid: {exc}"))
            print(f"{ticker}: EXCLUDED — {excluded[-1][1]}")
            continue

        observed = tuple(clean.index.date)
        # Only a contiguous suffix is accepted. For IPOs, the early part of
        # the reference calendar may be unavailable; internal and trailing
        # gaps are not interpreted as quiet no-signal days.
        try:
            offset = dates.index(observed[0])
        except ValueError:
            offset = -1
        if offset < 0 or observed != dates[offset:]:
            reason = "Historical bars do not form a contiguous suffix of the reference calendar."
            excluded.append((ticker, reason))
            print(f"{ticker}: EXCLUDED — {reason}")
            continue
        if len(observed) < SESSION_COUNT:
            reason = "Fewer than 21 consecutive market sessions are available."
            excluded.append((ticker, reason))
            print(f"{ticker}: EXCLUDED — {reason}")
            continue

        histories[ticker] = clean
        observations = _evaluate_symbol(
            ticker, clean, dates, start_date=first, end_date=last,
            min_gain_pct=min_gain_pct, min_price=min_price,
            max_price=max_price,
        )
        counts.append((ticker, len(observations)))
        scored.extend(observations)
        print(f"{ticker}: {len(observations)} historical price/gain signals.")

    if not histories:
        details = "; ".join(f"{ticker}: {reason}" for ticker, reason in excluded)
        raise ValueError(f"No selected stocks have usable historical data. {details}")

    # One combined simulation prevents a stock's 3/5 and 4/5 signals from
    # creating simultaneous competing positions (the old engine's rule).
    analysis = analyze_historical_signals(
        signals=[observation.signal for observation in scored],
        histories=histories,
        trading_dates=dates,
        holding_sessions=holding_sessions,
        round_trip_cost_pct=round_trip_cost_pct,
    )

    # Associate completed trades with the score known on their signal date.
    lookup = {(o.signal.ticker, o.signal.signal_date): o.assessment.score for o in scored}
    groups: list[ScorePerformance] = []
    for score in (5, 4, 3, 2, 1, 0, None):
        signal_count = sum(o.assessment.score == score for o in scored)
        trades = [trade for trade in analysis.simulation.trades
                  if lookup[(trade.ticker, trade.signal_date)] == score]
        statistics = calculate_performance_statistics(trades) if trades else None
        groups.append(ScorePerformance(score, signal_count, len(trades), statistics))

    assert sum(group.signal_count for group in groups) == analysis.simulation.total_signals
    assert sum(group.completed_trades for group in groups) == len(analysis.simulation.trades)
    assert (analysis.simulation.total_signals == len(analysis.simulation.trades)
            + analysis.simulation.skipped_overlapping
            + analysis.simulation.skipped_incomplete)

    return ScoredBacktestResult(
        requested_tickers=symbols,
        analyzed_tickers=tuple(histories),
        excluded_tickers=tuple(excluded),
        evaluation_start=first,
        evaluation_end=last,
        signal_counts=tuple(counts),
        scored_signals=tuple(scored),
        analysis=analysis,
        score_groups=tuple(groups),
    )
