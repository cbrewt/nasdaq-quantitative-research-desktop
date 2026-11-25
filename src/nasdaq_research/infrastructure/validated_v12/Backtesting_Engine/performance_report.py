
"""Microsoft Word performance reports for Nasdaq backtesting."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import math

from docx import Document
from docx.enum.section import WD_ORIENT
from docx.shared import Inches, Pt, RGBColor

from Backtesting_Engine.backtest_analysis import (
    BacktestAnalysis,
)


# Save reports beside the Backtesting Engine.
REPORTS_DIRECTORY = Path(__file__).resolve().parent / "Reports"


def format_percent(value: float | None) -> str:
    """Format percentage values for the report."""

    if value is None:
        return "N/A"

    if math.isinf(value):
        return "Infinity"

    if not math.isfinite(value):
        return "N/A"

    return f"{value:+.2f}%"


def format_number(value: float | None) -> str:
    """Format statistical values."""

    if value is None:
        return "N/A"

    if math.isinf(value):
        return "Infinity"

    if not math.isfinite(value):
        return "N/A"

    return f"{value:.4f}"


def add_summary_table(document, rows):
    """Add a two-column summary table."""

    table = document.add_table(
        rows=1,
        cols=2
    )

    table.style = "Table Grid"

    table.rows[0].cells[0].text = "Measurement"
    table.rows[0].cells[1].text = "Result"

    for label, value in rows:
        cells = table.add_row().cells
        cells[0].text = str(label)
        cells[1].text = str(value)

    return table


def generate_performance_report(
    analysis: BacktestAnalysis,
    *,
    strategy_name: str = "Nasdaq Momentum Strategy",
    filename: str | None = None,
) -> Path:
    """
    Generate a formatted Microsoft Word report.

    Includes:
        Simulation accounting
        Statistical performance
        Completed trade details
        Research limitations

    Returns the path of the generated document.
    """

    if not isinstance(analysis, BacktestAnalysis):
        raise TypeError(
            "Analysis must be a BacktestAnalysis object."
        )

    if not strategy_name or not strategy_name.strip():
        raise ValueError("Strategy name cannot be empty.")

    # Prepare the reports directory.
    REPORTS_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True
    )

    # Create a timestamped filename by default.
    if filename is None:
        timestamp = datetime.now().strftime(
            "%Y%m%d_%H%M%S_%f"
        )

        filename = (
            f"Backtest_Performance_{timestamp}.docx"
        )

    # Prevent path traversal and invalid filenames.
    from pathlib import PureWindowsPath
    import re

    if (
        not isinstance(filename, str)
        or not re.fullmatch(
            r"[A-Za-z0-9][A-Za-z0-9_.-]*\.docx",
            filename,
            flags=re.IGNORECASE
        )
        or Path(filename).name != filename
        or PureWindowsPath(filename).name != filename
        or re.match(
            r"^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\.|$)",
            filename,
            flags=re.IGNORECASE
        )
    ):
        raise ValueError("Provide a simple .docx filename.")

    output_path = REPORTS_DIRECTORY / filename

    if output_path.exists():
        raise FileExistsError(
            f"Report already exists: {output_path}"
        )

    document = Document()

    # Configure landscape layout.
    section = document.sections[0]

    section.orientation = WD_ORIENT.LANDSCAPE
    section.page_width = Inches(11)
    section.page_height = Inches(8.5)

    section.left_margin = Inches(0.65)
    section.right_margin = Inches(0.65)
    section.top_margin = Inches(0.65)
    section.bottom_margin = Inches(0.65)

    # Default document font.
    normal = document.styles["Normal"]
    normal.font.name = "Arial"
    normal.font.size = Pt(9)

    # Report heading.
    document.add_heading(
        "NASDAQ QUANTITATIVE RESEARCH",
        level=0
    )

    document.add_heading(
        "Historical Backtesting Performance Report",
        level=1
    )

    document.add_paragraph(
        f"Strategy: {strategy_name}"
    )

    document.add_paragraph(
        "Generated: "
        + datetime.now().strftime(
            "%B %d, %Y at %I:%M %p"
        )
    )

    document.add_paragraph(
        "Status: Research prototype — "
        "historical strategy not yet validated."
    )

    # Simulation accounting.
    simulation = analysis.simulation
    statistics = analysis.statistics

    document.add_heading(
        "1. Simulation Summary",
        level=2
    )

    summary_rows = [
        ("Total screening signals",
         simulation.total_signals),

        ("Completed trades",
         len(simulation.trades)),

        ("Overlapping signals excluded",
         simulation.skipped_overlapping),

        ("Incomplete trades excluded",
         simulation.skipped_incomplete),
    ]

    add_summary_table(
        document,
        summary_rows
    )

    # Statistical measurements.
    document.add_heading(
        "2. Performance Statistics",
        level=2
    )

    if statistics is None:

        document.add_paragraph(
            "No completed trades are available "
            "for statistical analysis."
        )

    else:

        performance_rows = [
            ("Completed trades",
             statistics.total_trades),

            ("Winning trades",
             statistics.winning_trades),

            ("Losing trades",
             statistics.losing_trades),

            ("Break-even trades",
             statistics.breakeven_trades),

            ("Win rate",
             format_percent(
                 statistics.win_rate_pct
             )),

            ("Average gross return",
             format_percent(
                 statistics.average_gross_return_pct
             )),

            ("Average net return",
             format_percent(
                 statistics.average_net_return_pct
             )),

            ("Statistical expectancy",
             format_percent(
                 statistics.expectancy_pct
             )),

            ("Average winning return",
             format_percent(
                 statistics.average_winning_return_pct
             )),

            ("Average losing return",
             format_percent(
                 statistics.average_losing_return_pct
             )),

            ("Profit factor",
             format_number(
                 statistics.profit_factor
             )),

            ("Best trade",
             format_percent(
                 statistics.best_trade_pct
             )),

            ("Worst trade",
             format_percent(
                 statistics.worst_trade_pct
             )),

            ("Average trading costs",
             format_percent(
                 statistics.average_transaction_cost_pct
             )),
        ]

        add_summary_table(
            document,
            performance_rows
        )

    # Individual completed trades.
    document.add_heading(
        "3. Completed Simulated Trades",
        level=2
    )

    trades = simulation.trades

    if not trades:

        document.add_paragraph(
            "No completed simulated trades."
        )

    else:

        headers = [
            "Symbol",
            "Signal",
            "Entry",
            "Exit",
            "Days",
            "Entry $",
            "Exit $",
            "Gross %",
            "Cost %",
            "Net %",
        ]

        table = document.add_table(
            rows=1,
            cols=len(headers)
        )

        table.style = "Table Grid"

        for cell, header in zip(
            table.rows[0].cells,
            headers
        ):
            cell.text = header

        for trade in trades:

            values = [
                trade.ticker,
                str(trade.signal_date),
                str(trade.entry_date),
                str(trade.exit_date),
                str(trade.holding_sessions),
                f"{trade.entry_price:.2f}",
                f"{trade.exit_price:.2f}",
                format_percent(
                    trade.gross_return_pct
                ),
                format_percent(
                    trade.round_trip_cost_pct
                ),
                format_percent(
                    trade.net_return_pct
                ),
            ]

            cells = table.add_row().cells

            for cell, value in zip(cells, values):
                cell.text = value

        # Keep the trade table compact.
        for row in table.rows:
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    for run in paragraph.runs:
                        run.font.size = Pt(7.5)

    # Research disclosures.
    document.add_heading(
        "4. Research Limitations",
        level=2
    )

    document.add_paragraph(
        "This report contains simulated historical "
        "trades. Returns are based on hypothetical "
        "execution prices and estimated transaction "
        "costs."
    )

    document.add_paragraph(
        "Performance statistics summarize individual "
        "trade percentage returns. They do not "
        "represent a fully funded investment portfolio, "
        "portfolio drawdown, or compounded returns."
    )

    document.add_paragraph(
        "Historical universe membership, delistings, "
        "corporate-action adjustments, liquidity, "
        "and realistic trade execution require "
        "additional validation."
    )

    document.add_paragraph(
        "Positive historical expectancy does not "
        "establish statistical significance or "
        "guarantee future investment performance."
    )

    document.add_paragraph(
        "This report is for quantitative research "
        "and educational purposes only."
    )

    # Save and verify the document.
    document.save(output_path)

    if (
        not output_path.exists()
        or output_path.stat().st_size == 0
    ):
        raise OSError(
            "The Word performance report was not created."
        )

    return output_path
