# Nasdaq Quantitative Research V2.0 — User guide

Release candidate | November 27, 2026

## Start and connect

Double-click the desktop shortcut, or from the project directory run `.\.venv\Scripts\python.exe .\launch_desktop.py`. The six workspaces are listed in the left sidebar. In Settings, leave local MySQL port at 3306 unless your installation differs; click Connect to research database and enter the application password. It is held in memory only. Confirm MySQL connected. Never use the administrator account for routine application operation.

## Stock Screener

1. Enter minimum and maximum closing price (defaults $1 and $10) and minimum gain (10%). The window is 21 completed sessions, representing 20 close-to-close intervals. Reverse-split exclusion is mandatory; unverified split histories are excluded.
2. Choose Research Mode for broad discovery with five-point scoring, or Strict Mode for the preserved momentum gate. Preview sample results is fictional and not live research.
3. Click Run live screener. Observe progress, checked and qualified counts and exclusions. Cancel cooperatively if needed; an in-flight provider request may take time to return. Do not treat a canceled scan as completed.
4. Sort by clicking a column heading; use Filter ticker to narrow the display. Horizontal scrolling exposes additional columns. Sorting/filtering does not change research measurements.
5. Select a live result and click Analyze selected stock (or double-click the row).

## Stock Analysis

The five conditions each contribute one point: MACD > 0; histogram > 0; at least three consecutive histogram increases; RSI 50–70 inclusive; RVOL > 1.0. Unavailable scores differ from zero. MACD uses 12/26/9 periods, RSI 14 and RVOL compares against the prior 20 sessions. Median daily dollar volume summarizes Close × Volume over the observation window. These are descriptive characteristics, not forecasts.

Scroll inside the analysis panel to view closing price, trading volume, MACD and signal, histogram, RSI and RVOL. Missing values appear as gaps. Charts use the completed live scan; sample rows and saved-history rows do not reconstruct charts. Price labels show two decimals; volume uses K/M; zero and RVOL 1.0 reference lines are labeled.

## Backtesting

Complete a live scan first. Open Backtesting; the simulation uses its original candidates and settings. Defaults: two years, five holding sessions, 0.50% round-trip cost. Click Run historical simulation and wait for completion. Historical cancellation is not implemented. Entry is the next session open and exit is the final holding-session close. Same-ticker overlapping trades are excluded. Future observations must not enter signal calculations. Current candidate selection is not a historical point-in-time universe; results are subject to selection/survivorship bias and simplified costs. Trade-level statistics are not portfolio returns.

## Research History and Reports

With MySQL connected, completed live scans may save automatically. Refresh saved scans, select a run and click View selected scan or View saved simulations. The latter shows linked simulation and report counts and archived input chunk counts. Save current live scan, Save latest simulation and Save latest screening report are available as appropriate; read the status before repeating a save. Duplicate prevention does not delete older records. Reports: click Generate screening Word report or Open reports folder. Historical simulations generate integrated reports. Local output is under `%USERPROFILE%\Nasdaq_Quant_Research_V2_Reports`; retain the folder in backups. If database persistence fails, check the status and preserve local reports.

## Troubleshooting

- Database disconnected: confirm MySQL80 is running, port and application password; error 1045 is authentication failure. Do not reset privileges casually.
- No current result: return to Stock Screener, select a completed live result and click Analyze selected stock.
- Calendar mismatch: inspect identified ticker(s); do not fill missing prices or bypass the checks. Verified pre-listing absences are handled via CAL-001.
- Provider failures: retry only when appropriate; do not interpret incomplete data as zero. No historical cancellation control is provided.
- Replay status: the interface reports capture availability, not individual offline verification. Runs 13/14 and 15/16 were independently replay-tested; older output-only records cannot be replayed.

See [release notes](RELEASE_NOTES.md) and [backup and recovery](BACKUP_RECOVERY.md).
