
"""Run configured Nasdaq backtests with associated research records."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from uuid import uuid4

from Backtesting_Engine.backtest_config import BacktestConfig

from Backtesting_Engine.config_storage import (
    save_backtest_config,
)

from Backtesting_Engine.multi_stock_backtest import (
    MultiStockBacktestResult,
    run_multi_stock_backtest,
)

from Backtesting_Engine.performance_report import (
    generate_performance_report,
)


@dataclass(frozen=True)
class ConfiguredBacktestResult:
    """Backtest results and associated output files."""

    run_id: str
    configuration: BacktestConfig
    backtest: MultiStockBacktestResult
    configuration_file: Path
    report_file: Path


def run_configured_backtest(
    config: BacktestConfig,
    trading_dates: Sequence[date],
    *,
    strategy_name: str = "Nasdaq Momentum Strategy",
) -> ConfiguredBacktestResult:
    """
    Execute a backtest using a validated configuration.

    Steps:
        1. Verify configuration and provider.
        2. Execute the existing multi-stock backtest.
        3. Generate a unique research run identifier.
        4. Save the configuration as JSON.
        5. Generate the associated Word report.
        6. Return results and file locations.

    The supplied trading calendar must include
    historical indicator warmup sessions and
    subsequent sessions needed for trade exits.
    """

    if not isinstance(config, BacktestConfig):
        raise TypeError(
            "Expected a BacktestConfig object."
        )

    # The current provider implementation
    # supports Yahoo Finance only.
    if config.data_provider.strip().casefold() != "yahoo finance":
        raise ValueError(
            "Only Yahoo Finance is currently supported."
        )

    # Execute using the saved configuration values.
    backtest = run_multi_stock_backtest(
        tickers=config.tickers,
        trading_dates=trading_dates,
        start_date=config.start_date,
        end_date=config.end_date,
        min_gain_pct=config.min_gain_pct,
        min_price=config.min_price,
        max_price=config.max_price,
        holding_sessions=config.holding_sessions,
        round_trip_cost_pct=config.round_trip_cost_pct,
    )

    # Generate a unique identifier for this run.
    timestamp = datetime.now(timezone.utc).strftime(
        "%Y%m%d_%H%M%S_%f"
    )

    run_id = f"{timestamp}_{uuid4().hex[:8]}"

    # Associate both outputs through the run ID.
    config_filename = (
        f"Backtest_Config_{run_id}.json"
    )

    report_filename = (
        f"Backtest_Report_{run_id}.docx"
    )

    # Save the configuration only after the
    # backtest computation has succeeded.
    configuration_file = save_backtest_config(
        config,
        filename=config_filename,
    )

    # Generate the corresponding Word report.
    report_file = generate_performance_report(
        backtest.analysis,
        strategy_name=(
            f"{strategy_name} | Run ID: {run_id}"
        ),
        filename=report_filename,
    )

    return ConfiguredBacktestResult(
        run_id=run_id,
        configuration=config,
        backtest=backtest,
        configuration_file=configuration_file,
        report_file=report_file,
    )
