
"""Persistent configuration storage for Nasdaq backtesting."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path, PureWindowsPath
import json
import re

from Backtesting_Engine.backtest_config import BacktestConfig


# Store configurations separately from performance reports.
CONFIGURATIONS_DIRECTORY = (
    Path(__file__).resolve().parent / "Configurations"
)

SCHEMA_VERSION = 1


def save_backtest_config(
    config: BacktestConfig,
    *,
    filename: str | None = None,
) -> Path:
    """
    Save a validated BacktestConfig as a JSON file.

    Features:
        Automatic timestamped filenames
        JSON schema version
        UTC save timestamp
        Filename validation
        Protection against overwriting files

    Returns:
        Absolute path of the saved configuration.
    """

    if not isinstance(config, BacktestConfig):
        raise TypeError(
            "Configuration must be a BacktestConfig object."
        )

    saved_at = datetime.now(timezone.utc)

    # Generate a unique timestamped filename.
    if filename is None:
        timestamp = saved_at.strftime(
            "%Y%m%d_%H%M%S_%f"
        )

        filename = (
            f"Backtest_Config_{timestamp}.json"
        )

    # Validate filenames and prevent path traversal.
    if (
        not isinstance(filename, str)
        or len(filename) > 125
        or not re.fullmatch(
            r"[A-Za-z0-9][A-Za-z0-9_.-]*\.json",
            filename,
            flags=re.IGNORECASE
        )
        or filename != Path(filename).name
        or filename != PureWindowsPath(filename).name
        or re.match(
            r"^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\.|$)",
            filename,
            flags=re.IGNORECASE
        )
    ):
        raise ValueError(
            "Provide a simple, valid .json filename."
        )

    # Prepare the complete configuration record.
    payload = {
        "schema_version": SCHEMA_VERSION,
        "saved_at_utc": saved_at.isoformat(),
        "configuration": config.to_record(),
    }

    # Serialize before creating the output file.
    content = json.dumps(
        payload,
        indent=2,
        allow_nan=False
    ) + "\n"

    # Create the destination directory if necessary.
    CONFIGURATIONS_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True
    )

    output_path = CONFIGURATIONS_DIRECTORY / filename

    # Exclusive creation prevents accidental overwrites.
    with output_path.open(
        mode="x",
        encoding="utf-8"
    ) as output_file:
        output_file.write(content)

    return output_path
