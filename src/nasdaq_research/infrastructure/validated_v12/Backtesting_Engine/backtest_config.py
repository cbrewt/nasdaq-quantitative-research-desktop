
"""Validated configuration for Nasdaq backtesting experiments."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
import math
import re


@dataclass(frozen=True)
class BacktestConfig:
    """
    Configuration for a historical backtesting experiment.

    Settings are validated at initialization.
    The resulting configuration is immutable.
    """

    tickers: tuple[str, ...]
    start_date: date
    end_date: date

    min_gain_pct: float = 10.0
    min_price: float = 1.0
    max_price: float = 10.0

    holding_sessions: int = 5
    round_trip_cost_pct: float = 0.50

    data_provider: str = "Yahoo Finance"

    created_at_utc: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    def __post_init__(self):
        """Validate and normalize configuration values."""

        # Validate ticker collection.
        if not isinstance(self.tickers, (tuple, list)):
            raise TypeError(
                "Tickers must be a tuple or list."
            )

        symbols = []

        for ticker in self.tickers:
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
                "At least one ticker is required."
            )

        if len(set(symbols)) != len(symbols):
            raise ValueError(
                "Duplicate tickers are not permitted."
            )

        # Normalize symbols and preserve their order.
        object.__setattr__(
            self, "tickers", tuple(symbols)
        )

        # Validate historical date range.
        if (
            type(self.start_date) is not date
            or type(self.end_date) is not date
        ):
            raise TypeError(
                "Start and end must be date objects."
            )

        if self.start_date > self.end_date:
            raise ValueError(
                "Start date cannot exceed end date."
            )

        # Validate numeric screening parameters.
        numeric_values = (
            self.min_gain_pct,
            self.min_price,
            self.max_price,
            self.round_trip_cost_pct,
        )

        if not all(
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and math.isfinite(value)
            for value in numeric_values
        ):
            raise ValueError(
                "Numeric parameters must be finite."
            )

        if (
            self.min_gain_pct < 0
            or self.min_price <= 0
            or self.max_price < self.min_price
        ):
            raise ValueError(
                "Invalid price or gain filters."
            )

        if type(self.holding_sessions) is not int:
            raise TypeError(
                "Holding sessions must be an integer."
            )

        if self.holding_sessions < 1:
            raise ValueError(
                "Holding sessions must be positive."
            )

        if not 0 <= self.round_trip_cost_pct <= 100:
            raise ValueError(
                "Trading costs must be between 0 and 100%."
            )

        if (
            not isinstance(self.data_provider, str)
            or not self.data_provider.strip()
        ):
            raise ValueError(
                "A data provider must be specified."
            )

        if (
            not isinstance(self.created_at_utc, datetime)
            or self.created_at_utc.tzinfo is None
            or self.created_at_utc.utcoffset() is None
        ):
            raise ValueError(
                "Configuration timestamp must be timezone-aware."
            )

    def to_record(self) -> dict:
        """
        Return a JSON-compatible configuration record.

        Dates and timestamps are converted to
        ISO 8601 strings for future persistence.
        """

        return {
            "tickers": list(self.tickers),
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "min_gain_pct": self.min_gain_pct,
            "min_price": self.min_price,
            "max_price": self.max_price,
            "holding_sessions": self.holding_sessions,
            "round_trip_cost_pct": self.round_trip_cost_pct,
            "data_provider": self.data_provider,
            "created_at_utc": (
                self.created_at_utc
                .astimezone(timezone.utc)
                .isoformat()
            ),
        }
