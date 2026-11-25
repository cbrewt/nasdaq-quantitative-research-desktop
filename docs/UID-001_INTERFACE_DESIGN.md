# UID-001 — Desktop user interface design

Approved November 25, 2026 under DEV-002. Design only; implementation begins with authorized Milestone 05.

## Layout and navigation

- PySide6 resizable main window, initial size 1280 × 800, professional dark theme.
- Persistent left sidebar; menu bar: File, Research, View, Tools, Help.
- Six workspaces: Stock Screener, Stock Analysis, Backtesting, Research History, Reports, Settings.
- Status bar distinguishes ready, busy, errors and actual database connectivity; never imply a connection before verification.

## Stock Screener

Parameter panel: minimum price $1.00, maximum $10.00, minimum gain 10%, 21 completed trading sessions, Research Mode by default. Reverse-split exclusion and unverified-data handling remain mandatory according to QPC-001; the exclusion indicator is not a bypass control. Strict mode retains existing methodology and semantics. Validate values before dispatch. Run and cancellation controls, checked/qualified counts, elapsed time and progress. Results are sortable and filterable without modifying stored measurements or original ranking. Provide access to all existing report metrics, including median daily dollar volume and five-point scores. Selecting a row opens Stock Analysis. Export preserves existing Word report behavior.

## Stock Analysis

Show selected ticker, session date/window, price, gain, volume, MACD and histogram, RSI, RVOL, and five scoring conditions with individual points and values. Display unavailable values as N/A rather than zero. Charts must be based on actual recorded inputs when integrated; any prototype data must be labeled illustrative. Chart technology remains subject to approved dependencies and later implementation decisions.

## Backtesting

Configure existing simulation parameters, display historical signals, completed trades and performance statistics, skipped/incomplete counts and research limitations. Preserve signal-date cutoffs, next-open entry, holding-period exit, costs and overlap policy in QPC-001. No predictive claims.

## Research History, Reports and Settings

History retrieves saved research runs with their parameters, dates and status. Reports provide generation and retrieval of existing Word report types. Settings manages application and database configuration without exposing credentials in source, logs or version control. No database schema changes are authorized by this design.

## Interaction and accessibility

Readable labels, keyboard-accessible navigation and controls, visible focus, resizing, sufficient contrast, and textual status in addition to color. Empty, loading, failed, canceled and completed states are distinguishable. Present actionable errors without secrets. Long-running operations eventually use the approved background-worker architecture and cooperative cancellation (AQ-002); do not expose a nonfunctional operation as working. Preserve CLI independently.

## Acceptance criteria for downstream implementation

1. All six workspaces are accessible through consistent navigation.
2. Screening inputs and existing quantitative rules are preserved; invalid inputs are rejected.
3. Integrated screening does not freeze the UI and supports cooperative cancellation.
4. Results support sorting, filtering and individual analysis without changing research data.
5. Missing values, errors and incomplete operations are clearly indicated.
6. Integrated research history and Word reports are accessible from the application.
7. No unapproved dependencies, methodology changes or scope expansion.

## Milestone boundary

Milestone 04 approves this design, not working software. Milestone 05 will implement a navigable prototype after explicit authorization. Engine integration, asynchronous screening, charting, historical simulation/reporting, persistence and full QA remain in their respective approved milestones. The earlier visual mockups were illustrative, not actual stock data or functional application screens.
