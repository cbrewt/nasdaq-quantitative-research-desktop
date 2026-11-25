#!/usr/bin/env python3
"""Screen Nasdaq stocks using editable filters; create a 21-session Word report.

Installation (Windows Command Prompt, from the directory holding both files):
    py -m pip install -r Nasdaq_21_Session_Requirements.txt

Interactive run (prompts for gain %, minimum price, maximum price):
    py Nasdaq_21_Session_Screener.py

Optional automated, no-prompt run:
    py Nasdaq_21_Session_Screener.py --no-prompt --min-gain 15 --min-price 2 --max-price 20

Other options:
    py Nasdaq_21_Session_Screener.py --output "My_Stock_Report.docx"
    py Nasdaq_21_Session_Screener.py --batch-size 25 --delay 2
    py Nasdaq_21_Session_Screener.py --template "Nasdaq_21_Session_Report_TEMPLATE.docx"

Rules:
  * Nasdaq-listed common/ordinary shares and ADS/ADRs; not ETFs, warrants,
    preferred shares, rights, units, or other known non-common instruments.
  * Editable filters (defaults: minimum gain 10%; latest close $1-$10).
  * Gain = 100 * (last close / first close - 1) within the latest 21 completed
    Nasdaq sessions, which spans 20 close-to-close trading intervals.
  * Daily opening price, closing price and volume; 21-session averages.
  * Daily MACD(12,26), Signal(9) and Histogram = MACD - Signal based on a
    longer closing-price history (6 months), NOT only 21 dates. Indicators
    unavailable for short histories are shown as N/A; research-mode stocks are not omitted
    solely because they lack a valid MACD reading.
  * Momentum confirmation (strict/automated default): MACD > 0, histogram > 0, at least
    three successive histogram increases (four observations), RSI(14) 50-70,
    latest volume > mean of previous 20 sessions. Research mode reports all
    price/gain/split-qualified stocks regardless of these indicators.
  * Exclude stocks with ANY reverse split in the full split history returned by
    Yahoo Finance, not merely the most recent 21 sessions. A reverse split has
    a shares-new/shares-old ratio strictly between 0 and 1 (e.g. 1-for-10=0.1).
  * Split history is checked for stocks passing all active price/gain/momentum filters.
    If the split-history request fails or the response is unusable, EXCLUDE
    that stock rather than treating an unknown history as a clean history.
  * Yahoo OHLC data use auto_adjust=False; however, vendors may still apply
    split adjustments to older historical observations.
  * Symbols missing complete 21-session data are counted and disclosed.
  * Every generated Word report is saved to the fixed OneDrive Reports folder,
    even when an alternate output filename is requested.

Caution: The public Yahoo Finance source is for personal research and may
throttle or omit symbols. No data completeness or investment outcome is
assured. This is not a buy/sell recommendation.
"""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from io import StringIO
from pathlib import Path
import math
import re
from pathlib import PureWindowsPath
import sys
import time as sleep_time
from uuid import uuid4
from typing import Sequence
from zoneinfo import ZoneInfo

import pandas as pd
import requests
try:
    import yfinance as yf
except ImportError:
    yf = None  # --template works offline; live screening needs yfinance.
from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.section import WD_ORIENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

# Make the project's shared analytics package accessible.
PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Shared_Analytics.indicators import (
    compute_indicators as shared_compute_indicators
)

from Shared_Analytics.screening_rules import (
    passes_momentum_screen
)

from Shared_Analytics.technical_scoring import (
    TechnicalScore, evaluate_technical_score
)



DIRECTORY_URL = "https://www.nasdaqtrader.com/dynamic/symdir/nasdaqlisted.txt"
SESSION_COUNT = 21
DEFAULT_MIN_PRICE = 1.00
DEFAULT_MAX_PRICE = 10.00
DEFAULT_MIN_GAIN_PCT = 10.00
MACD_HISTORY_PERIOD = "6mo"
# This Windows path is intentionally fixed. --output changes only the filename.
REPORTS_DIRECTORY = Path(__file__).resolve().parent / "Reports"
SPLIT_HISTORY_PERIOD = "max"
EASTERN = ZoneInfo("America/New_York")
NAVY = RGBColor(22, 43, 71)
BLUE = RGBColor(31, 83, 133)
GRAY = RGBColor(90, 105, 120)
LIGHT = RGBColor(236, 243, 249)
WHITE = RGBColor(255, 255, 255)

# Exclude non-equity share types based on the exchange-provided security name.
# Do not exclude "American Depositary Shares", which represent ordinary equity.
NON_STOCK_NAME = re.compile(
    r"\b(?:warrants?|rights?|units?|preferred|preference shares?|"
    r"notes?|bonds?|debentures?|exchange.traded notes?|"
    r"subscription receipts?|trust preferred)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class Security:
    ticker: str
    name: str


@dataclass
class Match:
    security: Security
    daily: pd.DataFrame   # Date index; Open, Close, Volume, MACD, Signal, Histogram
    gain_pct: float
    avg_open: float
    avg_close: float
    avg_volume: float
    first_close: float
    last_close: float

    @property
    def latest_macd(self) -> float:
        return float(self.daily["MACD"].iloc[-1])

    @property
    def latest_signal(self) -> float:
        return float(self.daily["Signal"].iloc[-1])

    @property
    def latest_histogram(self) -> float:
        return float(self.daily["Histogram"].iloc[-1])


    @property
    def previous_histogram(self) -> float:
        return float(self.daily["Histogram"].iloc[-2])

    @property
    def histogram_change(self) -> float:
        return self.latest_histogram - self.previous_histogram

    @property
    def rising_days(self) -> int:
        return int(self.daily["RisingDays"].iloc[-1])

    @property
    def normalized_histogram(self) -> float:
        return float(self.daily["NormalizedHistogram"].iloc[-1])

    @property
    def rsi(self) -> float:
        return float(self.daily["RSI"].iloc[-1])

    @property
    def relative_volume(self) -> float:
        return float(self.daily["RelativeVolume"].iloc[-1])

    @property
    def median_daily_dollar_volume(self) -> float:
        """Median of close x shares traded for the 21 observed sessions.

        Robust to one-session volume spikes. Missing/invalid values are N/A;
        no missing values are silently converted to zero.
        """
        if self.daily.empty or not {"Close", "Volume"}.issubset(self.daily.columns):
            return float("nan")
        close = pd.to_numeric(self.daily["Close"], errors="coerce")
        volume = pd.to_numeric(self.daily["Volume"], errors="coerce")
        dollars = close * volume
        if (dollars.isna().any() or not dollars.map(math.isfinite).all()
                or (close <= 0).any() or (volume < 0).any()):
            return float("nan")
        return float(dollars.median())

    @property
    def technical_score(self) -> TechnicalScore:
        """Assess the latest completed session without excluding this stock."""
        latest = self.daily.iloc[-1]
        return evaluate_technical_score(
            macd=latest.get("MACD"),
            histogram=latest.get("Histogram"),
            rising_days=latest.get("RisingDays"),
            rsi=latest.get("RSI"),
            relative_volume=latest.get("RelativeVolume"),
        )

    @property
    def momentum_pass(self) -> bool:
        return passes_momentum_screen(
            macd=self.latest_macd,
            histogram=self.latest_histogram,
            rising_days=self.rising_days,
            rsi=self.rsi,
            relative_volume=self.relative_volume
        )



@dataclass
class ScanResult:
    matches: list[Match]
    missing: int
    checked: int
    initial_matches: int
    excluded_reverse: int
    excluded_unverified: int
    excluded_momentum: int = 0


def report_destination(filename: str) -> Path:
    """Always save inside the user's specified Windows Reports folder.

    --output and --template accept a simple .docx file name, not a path.
    An absolute or relative directory cannot override REPORTS_DIRECTORY.
    """
    if (not filename or filename != PureWindowsPath(filename).name or
            filename != Path(filename).name or filename in {".", ".."} or
            filename.endswith((" ", ".")) or not filename.lower().endswith(".docx") or
            re.search(r'[<>:"/\\|?*\x00-\x1f]', filename) or
            re.match(r'^(?:CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\.|$)',
                     filename, flags=re.IGNORECASE)):
        raise ValueError("Use a simple .docx filename without a folder path, e.g. My_Stock_Report.docx. "
                         "All reports are saved in the fixed OneDrive Reports folder.")
    return REPORTS_DIRECTORY / filename


def save_screening_handoff(matches: Sequence[Match], scan_date: date,
                           min_gain_pct: float, min_price: float,
                           max_price: float, momentum_only: bool) -> Path:
    """Export the approved Version 1.1 JSON contract for a completed screening run.

    The scan_date is the last *completed trading session*, not the wall-clock
    export date. The historical backtester will consume this file in Step 4;
    this function deliberately does not run a backtest or change screening.
    """
    scan_id = f"{datetime.now(EASTERN):%Y%m%dT%H%M%S%f}_{uuid4().hex[:8]}"
    payload = {
        "schema_version": 1,
        "scan_id": scan_id,
        "scan_date": scan_date.isoformat(),
        "qualifying_tickers": [match.security.ticker for match in matches],
        "screener_settings": {
            "min_gain_pct": min_gain_pct,
            "min_price": min_price,
            "max_price": max_price,
            "momentum_confirmation_required": momentum_only,
        },
        "backtest_settings": {
            "history_years": 2,
            "holding_sessions": 5,
            "round_trip_cost_pct": 0.50,
        },
    }
    REPORTS_DIRECTORY.mkdir(parents=True, exist_ok=True)
    destination = REPORTS_DIRECTORY / f"Nasdaq_Screen_Handoff_{scan_id}.json"
    # 'x' refuses to overwrite another scan's records.
    with destination.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, indent=2, allow_nan=False)
        handle.write("\n")
    return destination


def prompt_number(label: str, default: float, minimum: float, *,
                  maximum: float | None = None) -> float:
    """Prompt until a valid finite numeric entry is given; Enter uses default."""
    while True:
        try:
            raw = input(f"{label} [{default:g}]: ").strip()
        except (EOFError, KeyboardInterrupt) as exc:
            raise RuntimeError(
                "No interactive input is available. Run in Command Prompt or "
                "use --no-prompt with --min-gain/--min-price/--max-price."
            ) from exc
        cleaned = raw.replace(",", "").replace("$", "").replace("%", "").strip()
        try:
            value = default if not raw else float(cleaned)
        except ValueError:
            print("  Please enter a number, or press Enter for the default.")
            continue
        if not math.isfinite(value) or value < minimum:
            print(f"  Enter a finite number greater than or equal to {minimum:g}.")
            continue
        if maximum is not None and value > maximum:
            print(f"  Maximum allowed for this field is {maximum:g}.")
            continue
        return value


def get_filters(args: argparse.Namespace) -> tuple[float, float, float]:
    """Return (gain %, min price, max price). CLI overrides skip each prompt."""
    if args.no_prompt:
        gain = DEFAULT_MIN_GAIN_PCT if args.min_gain is None else args.min_gain
        min_price = DEFAULT_MIN_PRICE if args.min_price is None else args.min_price
        max_price = DEFAULT_MAX_PRICE if args.max_price is None else args.max_price
    else:
        print("\n" + "=" * 52)
        print("             NASDAQ STOCK SCREENER")
        print("=" * 52)
        print("Press Enter to accept the default shown in brackets.\n")
        gain = (args.min_gain if args.min_gain is not None else
                prompt_number("Minimum 21-session percentage gain (%)", DEFAULT_MIN_GAIN_PCT, 0))
        min_price = (args.min_price if args.min_price is not None else
                     prompt_number("Minimum latest closing price ($)", DEFAULT_MIN_PRICE, 0.01))
        max_price = (args.max_price if args.max_price is not None else
                     prompt_number("Maximum latest closing price ($)", max(DEFAULT_MAX_PRICE, min_price), min_price))
    for name, value in (("percentage gain", gain), ("minimum price", min_price), ("maximum price", max_price)):
        if not math.isfinite(value):
            raise ValueError(f"Invalid {name}: must be a finite number.")
    if gain < 0 or min_price <= 0 or max_price < min_price:
        raise ValueError("Minimum gain must be >= 0; prices must be > 0 and maximum >= minimum.")
    return gain, min_price, max_price


def fetch_nasdaq_symbols() -> list[Security]:
    """Read the current Nasdaq Trader directory; never use a stale bundled list."""
    response = requests.get(
        DIRECTORY_URL,
        headers={"User-Agent": "Mozilla/5.0 NasdaqDailyEquitiesResearch/1.0"},
        timeout=35,
    )
    response.raise_for_status()
    reader = csv.DictReader(StringIO(response.content.decode("utf-8-sig")), delimiter="|")
    if not reader.fieldnames or not {"Symbol", "Security Name", "Test Issue", "ETF"}.issubset(reader.fieldnames):
        raise ValueError("The Nasdaq symbol-directory format was not recognized.")
    by_symbol: dict[str, Security] = {}
    for row in reader:
        ticker = (row.get("Symbol") or "").strip()
        name = (row.get("Security Name") or "").strip()
        if not ticker or not name or ticker.startswith("File Creation Time"):
            continue
        if (row.get("Test Issue") or "").strip().upper() != "N":
            continue
        if (row.get("ETF") or "").strip().upper() != "N":
            continue
        if NON_STOCK_NAME.search(name) or not re.fullmatch(r"[A-Z0-9.\-]+", ticker):
            continue
        by_symbol[ticker] = Security(ticker=ticker, name=name)
    if len(by_symbol) < 500:
        raise RuntimeError(f"Only {len(by_symbol)} candidate symbols found; directory may be incomplete.")
    return sorted(by_symbol.values(), key=lambda s: s.ticker)


def last_completed_calendar_date(now: datetime | None = None) -> date:
    """Do not include an in-progress trading session; allow for closing data lag."""
    local_now = now.astimezone(EASTERN) if now else datetime.now(EASTERN)
    if local_now.time() < time(17, 0):
        return local_now.date() - timedelta(days=1)
    return local_now.date()


def get_session_dates(cutoff: date) -> list[date]:
    """Use Nasdaq Composite calendar, falling back to Nasdaq-100 ETF QQQ."""
    if yf is None:
        raise RuntimeError("Missing yfinance. Install: py -m pip install yfinance")
    for reference in ("^IXIC", "QQQ"):
        try:
            history = yf.Ticker(reference).history(
                period="3mo", interval="1d", auto_adjust=False,
                actions=False, prepost=False,
            )
            if history is None or history.empty:
                continue
            dates = sorted({dt.date() for dt in pd.DatetimeIndex(history.index) if dt.date() <= cutoff})
            if len(dates) >= SESSION_COUNT:
                return dates[-SESSION_COUNT:]
        except Exception as exc:
            print(f"Warning: session calendar from {reference} unavailable: {exc}", file=sys.stderr)
    raise RuntimeError("Could not obtain 21 completed Nasdaq trading dates from Yahoo Finance.")


def yahoo_symbol(ticker: str) -> str:
    # Yahoo generally represents a class separator as '-' rather than '.'.
    return ticker.replace(".", "-")


def extract_frame(data: pd.DataFrame, yahoo_ticker: str, single: bool) -> pd.DataFrame | None:
    if data is None or data.empty:
        return None
    if not isinstance(data.columns, pd.MultiIndex):
        if not single:
            return None
        frame = data
    elif yahoo_ticker in data.columns.get_level_values(0):
        frame = data.xs(yahoo_ticker, axis=1, level=0)
    elif yahoo_ticker in data.columns.get_level_values(1):
        frame = data.xs(yahoo_ticker, axis=1, level=1)
    else:
        return None
    if not {"Open", "Close", "Volume"}.issubset(frame.columns):
        return None
    return frame.loc[:, ["Open", "Close", "Volume"]].copy()


def evaluate_security(security: Security, frame: pd.DataFrame | None,
                      session_dates: Sequence[date], min_gain_pct: float,
                      min_last_close: float, max_last_close: float) -> Match | None:
    """Compute MACD from long history, then apply the editable 21-day filter."""
    if frame is None or frame.empty:
        return None
    history = frame.copy()
    history.index = pd.DatetimeIndex(history.index).date
    history = history.loc[~pd.Index(history.index).duplicated(keep="last")].sort_index()
    history = history.loc[history.index <= session_dates[-1]]  # no partial/future sessions
    if not set(session_dates).issubset(history.index):
        return None
    history = history.loc[:, ["Open", "Close", "Volume"]].apply(pd.to_numeric, errors="coerce")
    daily = history.loc[list(session_dates)].copy()
    if daily.isna().any().any() or not daily.map(math.isfinite).all().all():
        return None
    if (daily["Open"] <= 0).any() or (daily["Close"] <= 0).any() or (daily["Volume"] < 0).any():
        return None
    first_close = float(daily["Close"].iloc[0])
    last_close = float(daily["Close"].iloc[-1])
    if not (min_last_close <= last_close <= max_last_close):
        return None
    gain_pct = (last_close / first_close - 1.0) * 100.0
    if gain_pct + 1e-9 < min_gain_pct:
        return None
    indicators = shared_compute_indicators(history)
    daily = daily.join(indicators.loc[list(session_dates)])
    return Match(
        security=security, daily=daily, gain_pct=gain_pct,
        avg_open=float(daily["Open"].mean()),
        avg_close=float(daily["Close"].mean()),
        avg_volume=float(daily["Volume"].mean()),
        first_close=first_close, last_close=last_close,
    )


def has_complete_history(frame: pd.DataFrame, session_dates: Sequence[date]) -> bool:
    """Make incomplete/newly listed/nontrading histories visible in the coverage count."""
    try:
        daily = frame.copy()
        daily.index = pd.DatetimeIndex(daily.index).date
        if not set(session_dates).issubset(set(daily.index)):
            return False
        sample = daily.loc[list(session_dates), ["Open", "Close", "Volume"]].apply(pd.to_numeric, errors="coerce")
        return (not sample.isna().any().any() and sample.map(math.isfinite).all().all() and
                bool((sample["Open"] > 0).all()) and
                bool((sample["Close"] > 0).all()) and
                bool((sample["Volume"] >= 0).all()))
    except (ValueError, KeyError, TypeError):
        return False


def review_reverse_splits(ticker: str, cutoff: date, retries: int) -> str:
    """Return 'reverse', 'clear', or 'unverified' using full available history.

    Yahoo's split factor is new shares / old shares. A factor below 1 denotes
    a reverse split. `period=max` checks all split events Yahoo still carries,
    but cannot establish events omitted by the provider or predecessor tickers.

    Retrieve complete price history with `actions=True` rather than relying on
    an empty get_splits() Series, which can mask a failed history download.
    Missing, invalid, or failed responses cause conservative exclusion.
    """
    for attempt in range(retries + 1):
        try:
            events = yf.Ticker(ticker).history(
                period=SPLIT_HISTORY_PERIOD, interval="1d",
                auto_adjust=False, actions=True, prepost=False,
                repair=False, timeout=30, raise_errors=True,
            )
            if events is None or events.empty or "Stock Splits" not in events.columns:
                raise ValueError("No usable historical corporate actions returned")
            event_dates = pd.DatetimeIndex(events.index).date
            subset = events.loc[event_dates <= cutoff, "Stock Splits"]
            if subset.empty:
                raise ValueError("No historical records through report cutoff date")
            ratios = pd.to_numeric(subset, errors="coerce")
            # Zero denotes an ordinary session without a split, not an error.
            if ratios.isna().any() or (ratios < 0).any() or not all(math.isfinite(float(x)) for x in ratios):
                raise ValueError("Historical stock-split factors contain invalid values")
            if ((ratios > 0) & (ratios < 1.0 - 1e-10)).any():
                return "reverse"
            return "clear"
        except Exception as exc:
            if attempt == retries:
                print(f"  Split history for {ticker} cannot be verified; excluded: {exc}",
                      file=sys.stderr)
                return "unverified"
            sleep_time.sleep(min(2 * (attempt + 1), 6))
    return "unverified"


def scan(symbols: Sequence[Security], session_dates: Sequence[date],
         batch_size: int, delay: float, retries: int,
         min_gain_pct: float, min_last_close: float, max_last_close: float,
         momentum_only: bool = True) -> ScanResult:
    """Screen price/gain and optional momentum, then verify each remaining match for splits."""
    if yf is None:
        raise RuntimeError("Missing yfinance. Install: py -m pip install yfinance")
    matched: list[Match] = []
    missing = checked = initial_matches = excluded_reverse = excluded_unverified = 0
    excluded_momentum = 0
    total = len(symbols)
    for offset in range(0, total, batch_size):
        group = symbols[offset:offset + batch_size]
        yahoo_symbols = [yahoo_symbol(s.ticker) for s in group]
        batch_data = None
        for attempt in range(retries + 1):
            try:
                batch_data = yf.download(
                    tickers=yahoo_symbols,
                    period=MACD_HISTORY_PERIOD, interval="1d", auto_adjust=False,
                    group_by="ticker", threads=4, progress=False,
                    actions=False, repair=False, timeout=22,
                )
                if batch_data is not None and not batch_data.empty:
                    break
                raise ValueError("Yahoo Finance returned no rows")
            except Exception as exc:
                print(f"  Download attempt {attempt + 1} failed: {exc}", file=sys.stderr)
                if attempt < retries:
                    sleep_time.sleep(3 * (attempt + 1))
        for security in group:
            checked += 1
            frame = extract_frame(batch_data, yahoo_symbol(security.ticker), len(group) == 1)
            if frame is None or frame.empty or not has_complete_history(frame, session_dates):
                missing += 1
                continue
            item = evaluate_security(security, frame, session_dates,
                                     min_gain_pct, min_last_close, max_last_close)
            if item is None:
                continue
            initial_matches += 1
            if momentum_only and not item.momentum_pass:
                excluded_momentum += 1
                continue
            verdict = review_reverse_splits(yahoo_symbol(security.ticker), session_dates[-1], retries)
            if verdict == "reverse":
                excluded_reverse += 1
            elif verdict == "clear":
                matched.append(item)
            else:
                excluded_unverified += 1
        print(
            f"Checked {checked:,}/{total:,} | Qualifying: {len(matched):,} | "
            f"Momentum exclusions: {excluded_momentum:,} | "
            f"Reverse splits: {excluded_reverse:,} | "
            f"Unverified split histories: {excluded_unverified:,} | "
            f"Incomplete prices: {missing:,}", flush=True,
        )
        if offset + batch_size < total and delay:
            sleep_time.sleep(delay)
    matched.sort(key=lambda x: (-x.gain_pct, -x.avg_volume, x.security.ticker))
    return ScanResult(matched, missing, checked, initial_matches,
                      excluded_reverse, excluded_unverified, excluded_momentum)


def shade(cell, fill: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:fill"), fill)
    tc_pr.append(shd)


def set_repeat_header(row) -> None:
    tr_pr = row._tr.get_or_add_trPr()
    tbl_header = OxmlElement("w:tblHeader")
    tbl_header.set(qn("w:val"), "true")
    tr_pr.append(tbl_header)


def set_cant_split(row) -> None:
    tr_pr = row._tr.get_or_add_trPr()
    node = OxmlElement("w:cantSplit")
    tr_pr.append(node)


def add_field(paragraph, instruction: str) -> None:
    run = paragraph.add_run()
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = instruction
    separate = OxmlElement("w:fldChar")
    separate.set(qn("w:fldCharType"), "separate")
    placeholder = OxmlElement("w:t")
    placeholder.text = "1"
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    for elem in (begin, instr, separate, placeholder, end):
        run._r.append(elem)
    run.font.size = Pt(8)
    run.font.color.rgb = GRAY


def cell_text(cell, content: str, *, bold=False, color=None, align=None) -> None:
    cell.text = ""
    p = cell.paragraphs[0]
    p.paragraph_format.space_after = Pt(0)
    if align is not None:
        p.alignment = align
    run = p.add_run(content)
    run.bold = bold
    run.font.name = "Arial"
    run.font.size = Pt(8.1)
    if color is not None:
        run.font.color.rgb = color
    cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER


def make_table(doc: Document, headers: Sequence[str], rows: Sequence[Sequence[str]],
               widths: Sequence[float], numeric_cols: set[int] | None = None):
    """Styled table; header repeats on subsequent pages."""
    numeric_cols = numeric_cols or set()
    table = doc.add_table(rows=1, cols=len(headers))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    table.style = "Table Grid"
    for j, text in enumerate(headers):
        table.columns[j].width = Inches(widths[j])
        cell = table.rows[0].cells[j]
        cell.width = Inches(widths[j])
        shade(cell, "162B47")
        cell_text(cell, text, bold=True, color=WHITE,
                  align=WD_ALIGN_PARAGRAPH.RIGHT if j in numeric_cols else WD_ALIGN_PARAGRAPH.LEFT)
    set_repeat_header(table.rows[0])
    set_cant_split(table.rows[0])
    for idx, row_values in enumerate(rows):
        row = table.add_row()
        set_cant_split(row)
        for j, value in enumerate(row_values):
            cell = row.cells[j]
            cell.width = Inches(widths[j])
            if idx % 2:
                shade(cell, "ECF3F9")
            cell_text(cell, str(value),
                      align=WD_ALIGN_PARAGRAPH.RIGHT if j in numeric_cols else WD_ALIGN_PARAGRAPH.LEFT)
    return table


def add_h2(doc: Document, value: str) -> None:
    p = doc.add_paragraph(style="Heading 2")
    p.paragraph_format.space_before = Pt(11)
    p.paragraph_format.space_after = Pt(5)
    r = p.add_run(value)
    r.font.color.rgb = NAVY
    r.font.size = Pt(13)


def fmt_price(value: float) -> str:
    return f"${value:,.2f}"


def fmt_vol(value: float) -> str:
    return f"{value:,.0f}"


def fmt_macd(value: float) -> str:
    return f"{value:+.4f}" if math.isfinite(value) else "N/A"


def rank_discovered_stocks(matches: Sequence[Match]) -> list[Match]:
    """Rank candidates for presentation without changing discovery eligibility.

    Technical score descending (unscored last), median close*volume descending,
    21-session gain descending, then symbol ascending. Invalid liquidity is
    ordered after finite liquidity within the same score grouping.
    """
    def rank_key(item: Match):
        score = item.technical_score.score
        liquidity = item.median_daily_dollar_volume
        liquid = math.isfinite(liquidity) and liquidity >= 0
        return (score is None, -(score if score is not None else 0),
                not liquid, -liquidity if liquid else 0.0,
                -item.gain_pct, item.security.ticker)
    return sorted(matches, key=rank_key)


def fmt_dollar_volume(value: float) -> str:
    return f"${value:,.0f}" if math.isfinite(value) and value >= 0 else "N/A"


def technical_flag(value: bool | None) -> str:
    return "P" if value is True else "F" if value is False else "N/A"


def build_document(path: Path, matches: Sequence[Match],
                   session_dates: Sequence[date] | None,
                   symbols_count: int, missing_count: int,
                   min_gain_pct: float, min_last_close: float, max_last_close: float,
                   template: bool = False, excluded_reverse: int = 0,
                   excluded_unverified: int = 0,
                   preliminary_matches: int = 0, momentum_only: bool = True,
                   excluded_momentum: int = 0) -> None:
    doc = Document()
    # Rank in the report only. Preserve scan's original list, eligibility,
    # JSON handoff ordering and the existing strict-mode screening logic.
    ranked_matches = rank_discovered_stocks(matches)
    sec = doc.sections[0]
    sec.orientation = WD_ORIENT.LANDSCAPE
    sec.page_width, sec.page_height = Inches(11), Inches(8.5)
    sec.left_margin = Inches(0.58)
    sec.right_margin = Inches(0.58)
    sec.top_margin = Inches(0.58)
    sec.bottom_margin = Inches(0.60)
    sec.header_distance = Inches(0.26)
    sec.footer_distance = Inches(0.27)

    normal = doc.styles["Normal"]
    normal.font.name = "Arial"
    normal.font.size = Pt(9)
    normal.font.color.rgb = NAVY
    normal.paragraph_format.space_after = Pt(5)

    header = sec.header.paragraphs[0]
    header.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    r = header.add_run("NASDAQ EQUITY SCREEN  |  21 SESSIONS")
    r.bold = True
    r.font.name = "Arial"
    r.font.size = Pt(7)
    r.font.color.rgb = GRAY

    footer = sec.footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    footer.add_run("Nasdaq 21-Session Screen  |  Page ")
    add_field(footer, "PAGE")
    footer.add_run(" of ")
    add_field(footer, "NUMPAGES")

    title = doc.add_paragraph()
    title.paragraph_format.space_after = Pt(2)
    r = title.add_run("NASDAQ 21-SESSION STOCK SCREEN")
    r.bold = True
    r.font.name = "Arial"
    r.font.size = Pt(19)
    r.font.color.rgb = NAVY

    sub = doc.add_paragraph()
    sub.paragraph_format.space_after = Pt(8)
    date_text = "UNPOPULATED REPORT TEMPLATE" if template else f"Generated {datetime.now(EASTERN):%B %d, %Y at %I:%M %p ET}"
    r = sub.add_run(date_text)
    r.bold = True
    r.font.color.rgb = BLUE
    r.font.size = Pt(9)

    if template:
        metrics = "Status: TEMPLATE ONLY  |  No market quotes are included  |  Run the Python script to fill this report"
    else:
        assert session_dates is not None
        metrics = (f"Observation dates: {session_dates[0]:%b %d, %Y} - {session_dates[-1]:%b %d, %Y}  |  "
                   f"21 sessions  |  Candidates: {symbols_count:,}  |  Qualifying: {len(matches):,}  |  "
                   f"Incomplete histories: {missing_count:,}")
    p = doc.add_paragraph(metrics)
    p.paragraph_format.space_after = Pt(7)
    for run in p.runs:
        run.font.size = Pt(8.5)

    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(7)
    run = p.add_run("Filter: ")
    run.bold = True
    p.add_run(f"Latest completed close {fmt_price(min_last_close)}-{fmt_price(max_last_close)}; "
              f"at least +{min_gain_pct:g}% between first and last closes in the "
              "21-session window (20 close-to-close intervals). "
              "Averages use 21 sessions; MACD uses longer price history. "
              "Stocks with any documented reverse split are excluded.")

    p = doc.add_paragraph()
    p.add_run("Momentum mode: ").bold = True
    p.add_run(("Confirmation required." if momentum_only else "Research only; indicators do not filter stocks.") +
              " Criteria: MACD > 0; histogram > 0; at least 3 consecutive increases; "
              "RSI(14) 50-70 inclusive; relative volume > 1.00x. Missing readings fail confirmation.")
    if not template:
        p.add_run(f" Momentum exclusions: {excluded_momentum:,}.")

    if not template and missing_count:
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(8)
        r = p.add_run("DATA COVERAGE NOTICE: ")
        r.bold = True
        r.font.color.rgb = RGBColor(150, 74, 29)
        p.add_run(f"{missing_count:,} symbol(s) had no complete 21-session Yahoo Finance history; "
                  "the screen may omit qualifying stocks. Review download errors before relying on completeness.")

    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(7)
    r = p.add_run("Reverse-split exclusion: ")
    r.bold = True
    p.add_run("The screener searches each match remaining after active price, gain and momentum filters for its entire available Yahoo "
              "Finance stock-split history, not just the 21-session window. "
              "Any recorded reverse split excludes the stock; an unavailable or "
              "unusable split history also excludes it.")
    if not template:
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(8)
        p.add_run("Reverse-split review: ").bold = True
        p.add_run(f"{preliminary_matches:,} provisional matches; "
                  f"{excluded_momentum:,} momentum exclusions before split review; "
                  f"{excluded_reverse:,} reverse-split exclusions; "
                  f"{excluded_unverified:,} unverified histories excluded; "
                  f"{len(matches):,} cleared and reported.")
        if excluded_unverified:
            p = doc.add_paragraph()
            p.paragraph_format.space_after = Pt(7)
            r = p.add_run("CORPORATE-ACTIONS COVERAGE NOTICE: ")
            r.bold = True
            r.font.color.rgb = RGBColor(150, 74, 29)
            p.add_run(f"{excluded_unverified:,} otherwise eligible stock(s) were omitted "
                      "because reverse-split history could not be verified.")

    add_h2(doc, "Ranked Stock Discovery - Technical Overview")
    ranked_help = doc.add_paragraph(
        "All price/gain/split-qualified stocks are included in Discovery Mode. "
        "Rank: five-condition technical score (5 highest), then median daily "
        "dollar trading volume, 21-session gain, and ticker. "
        "Unscored stocks appear last. The score measures technical-rule agreement, "
        "not expected investment returns."
    )
    ranked_help.paragraph_format.space_after = Pt(4)
    flag_legend = doc.add_paragraph(
        "Flags: P = condition passed; F = failed; N/A = input unavailable. "
        "M+ = MACD > 0; H+ = histogram > 0; Rise = 3 successive histogram "
        "increases; RSI = 50-70 inclusive; RVOL = relative volume > 1. "
        "Median $vol = median of closing price x share volume over the 21 sessions. "
        "This is not a bid-ask spread or execution-liquidity measurement."
    )
    flag_legend.paragraph_format.space_after = Pt(6)
    rank_headers = ["Rank", "Symbol", "Gain", "Close", "Score", "RSI", "RVOL",
                    "Median $vol", "M+", "H+", "Rise", "RSI", "RVOL"]
    rank_widths = [0.52, 0.72, 0.82, 0.80, 0.72, 0.70, 0.70,
                   1.35, 0.68, 0.68, 0.73, 0.68, 0.68]
    rank_rows = []
    for position, m in enumerate(ranked_matches, start=1):
        assessment = m.technical_score
        flags = assessment.conditions
        rank_rows.append([
            str(position) if assessment.score is not None else "—",
            m.security.ticker,
            f"{m.gain_pct:+.2f}%",
            fmt_price(m.last_close),
            assessment.label,
            f"{m.rsi:.2f}" if math.isfinite(m.rsi) else "N/A",
            f"{m.relative_volume:.2f}x" if math.isfinite(m.relative_volume) else "N/A",
            fmt_dollar_volume(m.median_daily_dollar_volume),
            technical_flag(flags["macd_positive"]),
            technical_flag(flags["histogram_positive"]),
            technical_flag(flags["histogram_rising_three"]),
            technical_flag(flags["rsi_50_to_70"]),
            technical_flag(flags["relative_volume_above_one"]),
        ])
    make_table(doc, rank_headers, [[""] * len(rank_headers)] if template else rank_rows,
               rank_widths, set(range(len(rank_headers))) - {1})
    if not template and not ranked_matches:
        doc.add_paragraph("No eligible stocks to rank in the downloaded data.")
    doc.add_page_break()

    add_h2(doc, "Qualifying Stocks - Summary")
    summary_headers = ["Symbol", "Security name", "First close", "Last close", "Gain", "Avg open",
                       "Avg close", "Avg volume", "MACD", "Signal", "Histogram"]
    summary_widths = [0.67, 2.04, 0.73, 0.73, 0.66, 0.80, 0.80, 1.10, 0.73, 0.73, 0.73]
    summary_rows = [
        [m.security.ticker, m.security.name, fmt_price(m.first_close), fmt_price(m.last_close),
         f"{m.gain_pct:+.2f}%", fmt_price(m.avg_open), fmt_price(m.avg_close),
         fmt_vol(m.avg_volume), fmt_macd(m.latest_macd), fmt_macd(m.latest_signal),
         fmt_macd(m.latest_histogram)]
        for m in ranked_matches
    ]
    if template:
        summary_rows = [[""] * len(summary_headers)]
    make_table(doc, summary_headers, summary_rows, summary_widths, set(range(2, 11)))

    if not template and not matches:
        doc.add_paragraph("No stocks met all screening rules in the downloaded data.")

    doc.add_page_break()
    add_h2(doc, "Momentum Analysis - Latest Completed Session")
    doc.add_paragraph("Same ranked stocks and order as the price summary. Rising days count successive increases, not positive bars. "
                      "Normalized histogram = 100 x histogram / latest close; RVOL = latest volume / prior 20-session mean.")
    momentum_headers = ["Symbol", "MACD", "Signal", "Histogram", "Prior hist.", "Hist. change", "Rising days", "Norm. hist. (%)", "RSI (14)", "RVOL", "Criteria"]
    momentum_widths = [0.72, 0.82, 0.82, 0.89, 0.89, 0.89, 0.79, 0.99, 0.75, 0.70, 0.80]
    def fmt_metric(value: float, suffix: str = "") -> str:
        return f"{value:.2f}{suffix}" if math.isfinite(value) else "N/A"
    momentum_rows = [[m.security.ticker, fmt_macd(m.latest_macd), fmt_macd(m.latest_signal),
                      fmt_macd(m.latest_histogram), fmt_macd(m.previous_histogram), fmt_macd(m.histogram_change),
                      str(m.rising_days) if math.isfinite(m.latest_histogram) else "N/A",
                      fmt_metric(m.normalized_histogram), fmt_metric(m.rsi), fmt_metric(m.relative_volume, "x"),
                      "Pass" if m.momentum_pass else "Fail"] for m in ranked_matches]
    make_table(doc, momentum_headers, [[""] * len(momentum_headers)] if template else momentum_rows,
               momentum_widths, set(range(1, 10)))

    daily_headers = ["Trading date", "Open", "Close", "Volume", "MACD", "Signal", "Histogram", "RSI (14)", "RVOL"]
    daily_widths = [1.40, 0.85, 0.85, 1.25, 1.05, 1.05, 1.15, 1.05, 0.90]
    if template:
        doc.add_page_break()
        add_h2(doc, "Individual Stock - 21 Daily Sessions (layout template)")
        doc.add_paragraph("The script inserts a complete table per qualifying stock with real market data and calculated MACD indicators.")
        daily_rows = [[f"Session {i}"] + [""] * (len(daily_headers) - 1) for i in range(1, SESSION_COUNT + 1)]
        make_table(doc, daily_headers, daily_rows, daily_widths, set(range(1, 9)))
        doc.add_paragraph("21-session averages: Opening price [pending]  |  Closing price [pending]  |  Daily volume [pending]")
    else:
        for m in ranked_matches:
            doc.add_page_break()
            add_h2(doc, f"{m.security.ticker}  |  {m.security.name}")
            p = doc.add_paragraph()
            p.paragraph_format.space_after = Pt(6)
            r = p.add_run(
                f"21-session gain: {m.gain_pct:+.2f}%     "
                f"Avg open: {fmt_price(m.avg_open)}     "
                f"Avg close: {fmt_price(m.avg_close)}     "
                f"Avg daily volume: {fmt_vol(m.avg_volume)} shares"
            )
            r.bold = True
            r.font.color.rgb = BLUE
            r.font.size = Pt(9)
            p = doc.add_paragraph()
            p.paragraph_format.space_after = Pt(8)
            r = p.add_run(
                f"Latest MACD: {fmt_macd(m.latest_macd)}     "
                f"Signal: {fmt_macd(m.latest_signal)}     "
                f"Histogram: {fmt_macd(m.latest_histogram)}"
            )
            r.font.size = Pt(9)
            p = doc.add_paragraph(
                f"Prior histogram: {fmt_macd(m.previous_histogram)} | Change: {fmt_macd(m.histogram_change)} | "
                f"Rising days: {m.rising_days if math.isfinite(m.latest_histogram) else 'N/A'} | Normalized: {fmt_metric(m.normalized_histogram, '%')} | "
                f"RSI: {fmt_metric(m.rsi)} | RVOL: {fmt_metric(m.relative_volume, 'x')} | "
                f"Criteria: {'Pass' if m.momentum_pass else 'Fail'}")
            p.paragraph_format.space_after = Pt(5)
            daily_rows = [
                [d.strftime("%b %d, %Y"), fmt_price(float(row["Open"])),
                 fmt_price(float(row["Close"])), fmt_vol(float(row["Volume"])),
                 fmt_macd(float(row["MACD"])), fmt_macd(float(row["Signal"])),
                 fmt_macd(float(row["Histogram"])), fmt_metric(float(row["RSI"])),
                 fmt_metric(float(row["RelativeVolume"]), "x")]
                for d, row in m.daily.iterrows()
            ]
            make_table(doc, daily_headers, daily_rows, daily_widths, set(range(1, 9)))

    doc.add_paragraph()
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(6)
    p.paragraph_format.space_after = Pt(3)
    r = p.add_run("Sources and interpretation")
    r.bold = True
    r.font.color.rgb = NAVY
    p = doc.add_paragraph(
        "Listed securities: Nasdaq Trader symbol directory (nasdaqtrader.com). "
        "Historical daily OHLC and share volume: Yahoo Finance via yfinance. "
        "Prices use auto_adjust=False (Yahoo may still split-adjust older prices). "
        "The gain is based on closing-price movement "
        "(21 observations, 20 intervals), not total return. MACD = 12-session EMA minus "
        "26-session EMA; Signal = 9-session EMA of MACD; Histogram = MACD minus Signal. "
        "MACD uses up to 6 months of total historical price data; N/A means insufficient history. "
        "EMAs are recursive (adjust=False). RSI uses Wilder smoothing over 14 changes. "
        "Relative volume compares the latest session with the previous 20 sessions, excluding the latest. "
        "Normalized histogram is scaled by latest close; it is not a return or volatility adjustment. "
        "The technical score counts five independent momentum-condition flags and is not a forecast or validated investment ranking. "
        "Median daily dollar volume is the median of closing price multiplied by daily share volume across 21 sessions. "
        "The momentum rules are experimental, not backtested or predictive guarantees. "
        "Reverse-split screening uses the full "
        "available Yahoo Finance corporate-action history (new shares / old shares < 1). "
        "A clear result does not guarantee a stock never reverse-split: earlier events, "
        "predecessor symbols, and unavailable provider records may be missing. "
        "Missing records, corporate actions, and vendor differences may affect results. "
        "This is informational research, not investment advice."
    )
    for r in p.runs:
        r.font.size = Pt(8)
        r.font.color.rgb = GRAY

    path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(path)
    if not path.is_file() or path.stat().st_size == 0:
        raise OSError(f"The Word report could not be verified at {path}")



def offer_historical_backtest(handoff_path: Path | None, *,
                              no_prompt: bool, qualifying_count: int,
                              momentum_only: bool,
                              screener_report_path: Path | None = None) -> None:
    """Optionally run the installed historical backtester for THIS scan.

    Never prompt in automated mode. Declining, missing handoff data, zero
    qualifiers, or historical-analysis errors cannot invalidate a successful
    screener run or its original Word report. Discovery scans use Version 1.2
    score-based research; strict scans keep the original Version 1.1 engine.
    """
    if no_prompt or handoff_path is None or qualifying_count == 0:
        return
    while True:
        try:
            answer = input("Backtest qualifying stocks? [y/N]: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\nHistorical backtest skipped.")
            return
        if answer in ("", "n", "no"):
            print("Historical backtest skipped.")
            return
        if answer in ("y", "yes"):
            break
        print("Please enter Y or N.")

    print("\nStarting historical backtest for this scan...")
    try:
        # Import only after the user opts in; the original screener works
        # independently when the Backtesting Engine is unavailable.
        if momentum_only:
            # Preserve the existing Version 1.1 strict screening backtester.
            from Backtesting_Engine.screener_backtest import main as backtest_main
        else:
            # Discovery mode evaluates historical signal scores, not strict passes.
            from Backtesting_Engine.scored_screener_integration import main as backtest_main
        arguments = [str(handoff_path)]
        if screener_report_path is not None:
            arguments += ["--screener-report", str(screener_report_path)]
        status = backtest_main(arguments)
        if status != 0:
            print("WARNING: Historical backtest did not complete. "
                  "The original Word screening report is unaffected.", file=sys.stderr)
    except Exception as exc:
        print(f"WARNING: Historical backtest failed: {exc}. "
              "The original Word screening report is unaffected.", file=sys.stderr)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Screen Nasdaq stock gains with editable price/percentage filters; create a 21-session MACD Word report."
    )
    parser.add_argument("--output", type=str, default=None,
                        help="Optional .docx FILENAME only; saved inside the fixed Reports folder")
    parser.add_argument("--template", type=str, default=None,
                        help="Optional .docx FILENAME only; create an empty layout in the fixed Reports folder")
    parser.add_argument("--min-gain", type=float, default=None,
                        help="Minimum percentage gain (0 or higher; default prompt shows 10)")
    parser.add_argument("--min-price", type=float, default=None,
                        help="Minimum latest close in dollars (greater than 0; default prompt shows 1)")
    parser.add_argument("--max-price", type=float, default=None,
                        help="Maximum latest close in dollars (default prompt shows 10)")
    parser.add_argument("--no-prompt", action="store_true",
                        help="Skip interactive prompts; use provided filter flags or defaults")
    parser.add_argument("--research-mode", action="store_true",
                        help="Report all price/gain/split-qualified stocks without momentum filtering")
    parser.add_argument("--batch-size", type=int, default=50,
                        help="Tickers per Yahoo Finance request (default: 50)")
    parser.add_argument("--delay", type=float, default=1.25,
                        help="Pause in seconds between batches (default: 1.25)")
    parser.add_argument("--retries", type=int, default=2,
                        help="Retry count for empty/failed price batches (default: 2)")
    args = parser.parse_args()
    if args.batch_size < 1 or not math.isfinite(args.delay) or args.delay < 0 or args.retries < 0:
        parser.error("--batch-size >= 1, --delay finite and >= 0, and --retries >= 0 required")

    # --template is always noninteractive, including when executed via an IDE.
    if args.template is not None:
        args.no_prompt = True
    gain, min_price, max_price = get_filters(args)
    # Preserve strict --no-prompt defaults, but make interactive discovery the default.
    momentum_only = not args.research_mode
    if not args.no_prompt and momentum_only:
        while True:
            try:
                mode = input("Require momentum confirmation? [y/N]: ").strip().lower()
            except (EOFError, KeyboardInterrupt) as exc:
                raise RuntimeError("No interactive input available; use --no-prompt.") from exc
            if mode in ("", "y", "yes", "n", "no"):
                momentum_only = mode in ("y", "yes")
                break
            print("Please enter Y or N.")
    if args.template is not None:
        template_path = report_destination(args.template)
        build_document(template_path, [], None, 0, 0, gain, min_price, max_price, template=True, momentum_only=momentum_only)
        print(f"Report layout template written: {template_path}")
        return 0

    print("\n" + "=" * 52)
    print("SCREENING PARAMETERS")
    print("=" * 52)
    print(f"Exchange: Nasdaq | Trading sessions: {SESSION_COUNT}")
    print(f"Minimum 21-session gain: {gain:g}%")
    print(f"Latest close range: {fmt_price(min_price)} to {fmt_price(max_price)}")
    print("MACD / Signal / Histogram: standard 12, 26, 9")
    print("Momentum mode: " + ("Confirmation required" if momentum_only else "Research only"))
    print("Reverse-split filter: ALL available history; unverified histories excluded")
    print(f"Word report folder: {REPORTS_DIRECTORY}")
    cutoff = last_completed_calendar_date()
    print(f"Latest permitted completed-session date: {cutoff}")
    dates = get_session_dates(cutoff)
    print(f"Trading sessions: {dates[0]} through {dates[-1]} ({SESSION_COUNT} sessions)")
    securities = fetch_nasdaq_symbols()
    print(f"Nasdaq stock-type securities in directory: {len(securities):,}")
    scan_result = scan(
        securities, dates, args.batch_size, args.delay, args.retries,
        gain, min_price, max_price, momentum_only=momentum_only,
    )
    matches = scan_result.matches
    filename = args.output or f"Nasdaq_21_Session_Screen_{dates[-1]:%Y%m%d}.docx"
    output = report_destination(filename)
    build_document(output, matches, dates, scan_result.checked, scan_result.missing,
                   gain, min_price, max_price,
                   excluded_reverse=scan_result.excluded_reverse,
                   excluded_unverified=scan_result.excluded_unverified,
                   preliminary_matches=scan_result.initial_matches, momentum_only=momentum_only,
                   excluded_momentum=scan_result.excluded_momentum)
    no_latest_macd = sum(not math.isfinite(m.latest_macd) or not math.isfinite(m.latest_signal)
                         for m in matches)
    print(f"\nProvisional stocks passing price + gain: {scan_result.initial_matches:,}")
    print(f"Excluded by momentum criteria: {scan_result.excluded_momentum:,}")
    print(f"Excluded due to reverse split: {scan_result.excluded_reverse:,}")
    print(f"Excluded due to unverified split history: {scan_result.excluded_unverified:,}")
    print(f"Qualified stocks after all active filters: {len(matches):,}")
    # Version 1.2 Step 4: descriptive scores only. No change to candidate
    # membership, ordering, Word layout, or the Version 1.1 JSON contract.
    score_counts = {score: 0 for score in range(6)}
    unscored = 0
    for match in matches:
        score = match.technical_score.score
        if score is None:
            unscored += 1
        else:
            score_counts[score] += 1
    print("Technical scores (0-5): " + ", ".join(
        f"{score}/5={score_counts[score]}" for score in range(6)
    ) + f" | N/A={unscored}")
    print(f"Without complete 21-session history: {scan_result.missing:,} (disclosed in report)")
    if no_latest_macd:
        print(f"Qualifying stocks with no latest MACD/Signal: {no_latest_macd:,} (shown as N/A)")
    print(f"Word document: {output.resolve()}")
    # The JSON export is supplementary. A failure must not discard a valid
    # Word report or change the original screener's success status.
    handoff: Path | None = None
    try:
        handoff = save_screening_handoff(
            matches, dates[-1], gain, min_price, max_price, momentum_only
        )
    except OSError as exc:
        print(f"WARNING: JSON handoff could not be saved: {exc}", file=sys.stderr)
    else:
        print(f"Backtesting JSON handoff: {handoff.resolve()}")

    # Version 1.1 Step 6: optional backtest after BOTH original outputs.
    # --no-prompt never pauses for this step; Enter defaults to No.
    offer_historical_backtest(
        handoff, no_prompt=args.no_prompt,
        qualifying_count=len(matches), momentum_only=momentum_only,
        screener_report_path=output,
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (requests.RequestException, RuntimeError, ValueError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
