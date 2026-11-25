#!/usr/bin/env python3
"""Validate and import Nasdaq Stock Screener JSON handoffs (schema version 1).

Version 1.1 integration, Step 4. This module reads an existing handoff and
returns typed, validated settings. It does NOT download prices, simulate trades,
modify the Stock Screener, or write reports.

From the Nasdaq_Quant_Research project root (PowerShell):
    py -m Backtesting_Engine.screener_handoff

To inspect a particular JSON file:
    py -m Backtesting_Engine.screener_handoff "path\\to\\handoff.json"
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import date
import json
import math
from pathlib import Path
import re
from typing import Any, Sequence

SCHEMA_VERSION = 1
HANDOFF_GLOB = "Nasdaq_Screen_Handoff_*.json"


class HandoffValidationError(ValueError):
    """The handoff is missing, malformed, or incompatible with schema v1."""


@dataclass(frozen=True)
class ScreenerSettings:
    min_gain_pct: float
    min_price: float
    max_price: float
    momentum_confirmation_required: bool


@dataclass(frozen=True)
class BacktestSettings:
    history_years: int
    holding_sessions: int
    round_trip_cost_pct: float


@dataclass(frozen=True)
class ScreenerHandoff:
    schema_version: int
    scan_id: str
    scan_date: date
    qualifying_tickers: tuple[str, ...]
    screener_settings: ScreenerSettings
    backtest_settings: BacktestSettings
    source_path: Path


def _object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise HandoffValidationError(f"'{label}' must be a JSON object.")
    return value


def _required(obj: dict[str, Any], key: str, section: str) -> Any:
    if key not in obj:
        raise HandoffValidationError(f"Missing required field: {section}.{key}")
    return obj[key]


def _finite_number(obj: dict[str, Any], key: str, section: str, *,
                   minimum: float = 0.0, strictly_positive: bool = False) -> float:
    value = _required(obj, key, section)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise HandoffValidationError(f"{section}.{key} must be a number.")
    try:
        numeric = float(value)
    except (OverflowError, ValueError) as exc:
        raise HandoffValidationError(f"{section}.{key} is not a valid finite number.") from exc
    if not math.isfinite(numeric) or numeric < minimum or (strictly_positive and numeric == 0):
        comparison = "greater than zero" if strictly_positive else f"at least {minimum:g}"
        raise HandoffValidationError(f"{section}.{key} must be finite and {comparison}.")
    return numeric


def _positive_integer(obj: dict[str, Any], key: str, section: str) -> int:
    value = _required(obj, key, section)
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise HandoffValidationError(f"{section}.{key} must be a positive integer.")
    return value


def _no_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    obj: dict[str, Any] = {}
    for key, value in pairs:
        if key in obj:
            raise HandoffValidationError(f"Duplicate JSON field: {key}")
        obj[key] = value
    return obj


def load_screener_handoff(path: str | Path) -> ScreenerHandoff:
    """Load one handoff file and validate all fields in the approved contract.

    An empty ticker list is valid: the caller must skip a historical backtest
    when no stocks qualified. Extra fields are ignored for forward compatibility.
    """
    source = Path(path).expanduser()
    if not source.is_file() or source.suffix.lower() != ".json":
        raise HandoffValidationError(f"JSON handoff file not found: {source}")
    try:
        with source.open("r", encoding="utf-8") as handle:
            data = json.load(handle, object_pairs_hook=_no_duplicate_keys)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise HandoffValidationError(f"Invalid JSON handoff '{source.name}': {exc}") from exc
    root = _object(data, "handoff")

    version = _required(root, "schema_version", "handoff")
    if isinstance(version, bool) or not isinstance(version, int) or version != SCHEMA_VERSION:
        raise HandoffValidationError(
            f"Unsupported schema_version: {version!r}; expected {SCHEMA_VERSION}."
        )

    scan_id = _required(root, "scan_id", "handoff")
    if not isinstance(scan_id, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", scan_id):
        raise HandoffValidationError("handoff.scan_id must be a nonempty alphanumeric identifier.")

    raw_date = _required(root, "scan_date", "handoff")
    if not isinstance(raw_date, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw_date):
        raise HandoffValidationError("handoff.scan_date must be in YYYY-MM-DD format.")
    try:
        scan_date = date.fromisoformat(raw_date)
    except ValueError as exc:
        raise HandoffValidationError(f"Invalid scan_date: {raw_date!r}") from exc

    raw_tickers = _required(root, "qualifying_tickers", "handoff")
    if not isinstance(raw_tickers, list):
        raise HandoffValidationError("handoff.qualifying_tickers must be a JSON array.")
    if any(not isinstance(t, str) or not re.fullmatch(r"[A-Z0-9.\-]+", t)
           for t in raw_tickers):
        raise HandoffValidationError(
            "handoff.qualifying_tickers must contain only uppercase Nasdaq ticker symbols."
        )
    if len(set(raw_tickers)) != len(raw_tickers):
        raise HandoffValidationError("handoff.qualifying_tickers contains duplicate symbols.")

    raw_screen = _object(_required(root, "screener_settings", "handoff"), "screener_settings")
    min_gain = _finite_number(raw_screen, "min_gain_pct", "screener_settings")
    min_price = _finite_number(raw_screen, "min_price", "screener_settings", strictly_positive=True)
    max_price = _finite_number(raw_screen, "max_price", "screener_settings", strictly_positive=True)
    if max_price < min_price:
        raise HandoffValidationError("screener_settings.max_price must be >= min_price.")
    momentum = _required(raw_screen, "momentum_confirmation_required", "screener_settings")
    if not isinstance(momentum, bool):
        raise HandoffValidationError("screener_settings.momentum_confirmation_required must be boolean.")

    raw_backtest = _object(_required(root, "backtest_settings", "handoff"), "backtest_settings")
    history_years = _positive_integer(raw_backtest, "history_years", "backtest_settings")
    holding_sessions = _positive_integer(raw_backtest, "holding_sessions", "backtest_settings")
    costs = _finite_number(raw_backtest, "round_trip_cost_pct", "backtest_settings")

    return ScreenerHandoff(
        schema_version=version,
        scan_id=scan_id,
        scan_date=scan_date,
        qualifying_tickers=tuple(raw_tickers),
        screener_settings=ScreenerSettings(min_gain, min_price, max_price, momentum),
        backtest_settings=BacktestSettings(history_years, holding_sessions, costs),
        source_path=source.resolve(),
    )


def latest_screener_handoff(reports_directory: str | Path | None = None) -> Path:
    """Return the most recently written handoff, without changing any files."""
    reports = (Path(reports_directory) if reports_directory is not None
               else Path(__file__).resolve().parent.parent / "Stock_Screener" / "Reports")
    candidates = [p for p in reports.glob(HANDOFF_GLOB) if p.is_file()]
    if not candidates:
        raise HandoffValidationError(f"No screener handoff JSON files found in: {reports}")
    return max(candidates, key=lambda p: (p.stat().st_mtime_ns, p.name))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate a Nasdaq screener JSON handoff (Step 4).")
    parser.add_argument("handoff", nargs="?", help="JSON file; defaults to the newest screener handoff")
    args = parser.parse_args(argv)
    try:
        path = Path(args.handoff) if args.handoff else latest_screener_handoff()
        handoff = load_screener_handoff(path)
    except (HandoffValidationError, OSError) as exc:
        parser.exit(1, f"ERROR: {exc}\n")
    print("PASS: Screener JSON handoff imported and validated.")
    print(f"Scan ID: {handoff.scan_id}")
    print(f"Scan date: {handoff.scan_date.isoformat()}")
    print(f"Qualifying tickers ({len(handoff.qualifying_tickers)}): "
          f"{', '.join(handoff.qualifying_tickers) if handoff.qualifying_tickers else '(none)'}")
    s = handoff.screener_settings
    b = handoff.backtest_settings
    print(f"Screen filters: gain >= {s.min_gain_pct:g}%, "
          f"price ${s.min_price:g} to ${s.max_price:g}, "
          f"momentum confirmation: {'Yes' if s.momentum_confirmation_required else 'No'}")
    print(f"Backtest settings: history {b.history_years} years, "
          f"hold {b.holding_sessions} sessions, round-trip costs {b.round_trip_cost_pct:g}%")
    if not handoff.qualifying_tickers:
        print("STATUS: Valid handoff, but no qualifying stocks; backtest must be skipped.")
    else:
        print("STATUS: Handoff ready for Step 5 historical analysis.")
    print(f"Source: {handoff.source_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
