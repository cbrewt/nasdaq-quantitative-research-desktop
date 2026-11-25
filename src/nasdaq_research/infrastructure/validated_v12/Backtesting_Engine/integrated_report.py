#!/usr/bin/env python3
"""Version 1.1 Step 7: append a labelled historical analysis to a COPY of the Word screener report.

The original Word document and JSON handoff are never modified. Historical
statistics cover only current screener candidates, not a point-in-time universe.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import math
from typing import Any

from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt

REPORTS_DIR = Path(__file__).resolve().parent / "Reports"


def _attr(obj: Any, *keys: str) -> Any:
    for key in keys:
        if obj is not None and hasattr(obj, key):
            return getattr(obj, key)
    return None


def _pct(value: Any, *, signed: bool = False, decimals: int = 2) -> str:
    try:
        num = float(value)
    except (ValueError, TypeError):
        return "N/A"
    if not math.isfinite(num):
        return "N/A"
    return f"{num:+.{decimals}f}%" if signed else f"{num:.{decimals}f}%"


def _factor(value: Any) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "N/A"
    if math.isnan(number):
        return "N/A"
    if math.isinf(number):
        return "Infinity (no net losing trades)" if number > 0 else "N/A"
    return f"{number:.4f}"


def _label_value(doc: Any, label: str, value: Any) -> None:
    p = doc.add_paragraph()
    p.add_run(label + ": ").bold = True
    p.add_run(str(value))


def _table(doc: Any, headers: tuple[str, ...], values: list[tuple[str, ...]]) -> None:
    table = doc.add_table(rows=1, cols=len(headers))
    table.style = "Table Grid"
    for cell, value in zip(table.rows[0].cells, headers):
        cell.text = value
        for p in cell.paragraphs:
            for r in p.runs:
                r.bold = True

    # Repeat the column headings whenever a Word table flows to a new page.
    # Particularly important for the multi-page Completed Simulated Trades table.
    header_properties = table.rows[0]._tr.get_or_add_trPr()
    if header_properties.find(qn("w:tblHeader")) is None:
        repeat_header = OxmlElement("w:tblHeader")
        repeat_header.set(qn("w:val"), "1")
        header_properties.append(repeat_header)

    for values_row in values:
        cells = table.add_row().cells
        for cell, value in zip(cells, values_row):
            cell.text = str(value)


def _verify_screener_document(doc: Any, handoff: Any) -> None:
    # An unrelated/stale Word report must not be presented as this scan.
    text = "\n".join(p.text for p in doc.paragraphs)
    if "NASDAQ 21-SESSION STOCK SCREEN" not in text:
        raise ValueError("The supplied Word document is not the expected Nasdaq screener report.")
    if f"{handoff.scan_date:%b %d, %Y}" not in text:
        raise ValueError("Word screener report observation date does not match the JSON scan date.")
    tickers = set(handoff.qualifying_tickers)
    if tickers:
        rows = [t for t in doc.tables if t.rows and t.rows[0].cells[0].text == "Symbol"]
        if not rows:
            raise ValueError("Word screener report does not contain a qualifying-stocks table.")
        symbols = {row.cells[0].text.strip() for row in rows[0].rows[1:]}
        if not tickers.issubset(symbols):
            raise ValueError("Word screener report tickers do not agree with the JSON handoff.")


def generate_integrated_report(result: Any, screener_report: str | Path, *,
                               output_dir: str | Path | None = None) -> Path:
    """Return a distinct Word file containing original screen + historical analysis.

    result: ScreenerBacktestResult from screener_backtest.run_screener_backtest.
    screener_report: Word report produced by the SAME screening run.
    """
    if result.backtest is None or not result.handoff.qualifying_tickers:
        raise ValueError("An integrated report requires a completed nonempty historical backtest.")
    source = Path(screener_report)
    if not source.is_file() or source.suffix.lower() != ".docx":
        raise FileNotFoundError(f"Original Word screening report not found: {source}")
    doc = Document(source)
    handoff = result.handoff
    _verify_screener_document(doc, handoff)

    analysis = _attr(result.backtest, "analysis")
    simulation = _attr(analysis, "simulation")
    statistics = _attr(analysis, "statistics")
    if simulation is None or statistics is None:
        raise ValueError("Backtesting Engine did not return the required simulation/statistics.")
    trades = list(_attr(simulation, "trades") or [])
    signals = _attr(simulation, "total_signals")
    if signals is None:
        raise ValueError("Backtesting Engine did not return a signal count.")

    doc.add_page_break()
    doc.add_heading("HISTORICAL BACKTESTING ANALYSIS", level=1)
    doc.add_paragraph("Supplemental research for the current qualifying stocks — not a strategy-wide performance validation.")
    _label_value(doc, "Scan ID", handoff.scan_id)
    _label_value(doc, "Scan session", handoff.scan_date.isoformat())
    _label_value(doc, "Selected candidate stocks", ", ".join(handoff.qualifying_tickers))
    _label_value(doc, "Historical window", f"{result.start_date} through {result.end_date} (inclusive)")
    _label_value(doc, "Available reference trading sessions", len(result.trading_dates))
    _label_value(doc, "Generated (UTC)", datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"))

    doc.add_heading("Screening and Simulation Settings", level=2)
    s = handoff.screener_settings
    b = handoff.backtest_settings
    _table(doc, ("Parameter", "Value"), [
        ("Minimum 21-session gain", _pct(s.min_gain_pct)),
        ("Latest closing price", f"${s.min_price:.2f}–${s.max_price:.2f}"),
        ("Momentum confirmation", "Required" if s.momentum_confirmation_required else "Not required"),
        ("Historical lookback", f"{b.history_years} calendar years"),
        ("Trade holding period", f"{b.holding_sessions} trading sessions"),
        ("Estimated round-trip transaction cost", _pct(b.round_trip_cost_pct)),
    ])

    doc.add_heading("Historical Performance — Selected Candidates", level=2)
    _table(doc, ("Measurement", "Result"), [
        ("Qualifying historical signals", str(signals)),
        ("Completed simulated trades", str(len(trades))),
        ("Overlapping signals skipped", str(_attr(simulation, "skipped_overlapping") if _attr(simulation, "skipped_overlapping") is not None else "N/A")),
        ("Incomplete trades skipped", str(_attr(simulation, "skipped_incomplete") if _attr(simulation, "skipped_incomplete") is not None else "N/A")),
        ("Historical win rate", _pct(_attr(statistics, "win_rate_pct"))),
        ("Historical net expectancy per completed trade", _pct(_attr(statistics, "expectancy_pct"), signed=True, decimals=4)),
        ("Historical profit factor", _factor(_attr(statistics, "profit_factor"))),
    ])

    if trades:
        doc.add_heading("Completed Simulated Trades", level=2)
        table_rows = []
        for trade in trades:
            ticker = _attr(trade, "ticker", "symbol", "stock")
            signal_date = _attr(trade, "signal_date")
            entry_date = _attr(trade, "entry_date")
            exit_date = _attr(trade, "exit_date")
            net_return = _attr(trade, "net_return_pct", "net_pct", "net_return_percent")
            table_rows.append((str(ticker or "N/A"), str(signal_date or "N/A"),
                               str(entry_date or "N/A"), str(exit_date or "N/A"),
                               _pct(net_return, signed=True)))
        _table(doc, ("Ticker", "Signal date", "Entry date", "Exit date", "Net return"), table_rows)
        if any(r[0] != "N/A" for r in table_rows):
            counts = Counter(r[0] for r in table_rows if r[0] != "N/A")
            doc.add_paragraph("Completed trades by ticker: " + ", ".join(
                f"{ticker} {counts.get(ticker, 0)}" for ticker in handoff.qualifying_tickers))

    doc.add_heading("Limitations and Interpretation", level=2)
    for sentence in (
        "The historical analysis includes only stocks selected by the present-day Stock Screener. "
        "This candidate-conditioned sample is affected by selection and survivorship bias and cannot validate the strategy across a historical Nasdaq universe.",
        "Historical signal evaluation does not reconstruct point-in-time Nasdaq membership or historical reverse-split eligibility. "
        "Today's screener excludes reverse splits, but its historical backtest does not apply that same historical exclusion.",
        "Yahoo Finance price histories and corporate actions can be revised or adjusted; ticker histories may be incomplete or start after the requested period.",
        "Simulated entry/exit prices and the fixed round-trip cost are simplified assumptions. "
        "Execution slippage, liquidity constraints and portfolio capital allocation are not modeled.",
        "A high historical win rate or positive expectancy on a handful of trades is not proof of predictive performance. "
        "These results are educational research, not an investment recommendation.",
    ):
        doc.add_paragraph(sentence, style="Normal")

    footer = doc.add_paragraph("END OF INTEGRATED RESEARCH REPORT")
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for run in footer.runs:
        run.bold = True
        run.font.size = Pt(8)

    destination = Path(output_dir) if output_dir is not None else REPORTS_DIR
    destination.mkdir(parents=True, exist_ok=True)
    stem = f"Integrated_Nasdaq_Research_{handoff.scan_id}"
    path = destination / f"{stem}.docx"
    suffix = 2
    while path.exists():
        path = destination / f"{stem}_{suffix}.docx"
        suffix += 1
        if suffix > 9999:
            raise FileExistsError("Too many reports already exist for this scan.")
    doc.save(path)
    if not path.is_file() or path.stat().st_size == 0:
        raise OSError(f"Integrated Word report was not saved: {path}")
    return path
