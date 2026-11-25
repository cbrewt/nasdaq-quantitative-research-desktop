# Nasdaq Quantitative Research V2.0

## Source Code Audit

Document reference: AUDIT-001
Date: November 25, 2026
Development milestone: 02

### 1. Audit objective

Establish an accurate understanding of the validated
Version 1.2 research engine before integrating it
into the Version 2.0 desktop application.

### 2. Audited baseline

Archive:
Nasdaq_Quant_Research_V1_2_Validated_Source.zip

SHA-256:
71ec91441fe26f35e34534b5e758c01a4b8aacf2e75938aa156a4f78ef457909

Archive size: 83543 bytes
Python source files: 29
Source lines: 6551

ZIP integrity: PASS
Archive checksum: PASS
Python AST parsing: 29 of 29 files passed

Line counts include blank lines, comments,
and documentation strings.

### 3. Source inventory

#### Backtesting_Engine - 21 files

| File | Lines | Responsibility |
|---|---:|---|
| __init__.py | 0 | Package initialization |
| backtest_analysis.py | 74 | Integrated simulation and analysis |
| backtest_config.py | 178 | Backtest configuration |
| config_storage.py | 108 | Configuration persistence |
| configured_backtest.py | 124 | Configured execution |
| evaluation_engine.py | 127 | Historical signal evaluation |
| historical_data.py | 188 | Historical data validation |
| integrated_report.py | 209 | Integrated Word reporting |
| market_data_provider.py | 126 | Historical data retrieval |
| multi_stock_backtest.py | 296 | Multiple-stock backtesting |
| multi_trade_simulator.py | 188 | Multiple-trade simulation |
| performance_report.py | 426 | Performance reporting |
| performance_statistics.py | 185 | Statistical calculations |
| research_snapshot.py | 0 | Empty placeholder |
| scored_backtest.py | 304 | Score-based historical research |
| scored_integrated_report.py | 156 | Scored integrated reporting |
| scored_screener_integration.py | 135 | Research Mode integration |
| screener_backtest.py | 184 | Strict Mode integration |
| screener_handoff.py | 214 | JSON handoff validation |
| signal_engine.py | 154 | Historical signal generation |
| trade_simulator.py | 168 | Individual trade simulation |

#### Shared_Analytics - 4 files

| File | Lines | Responsibility |
|---|---:|---|
| __init__.py | 0 | Package initialization |
| indicators.py | 246 | Technical indicator calculations |
| screening_rules.py | 41 | Momentum qualification |
| technical_scoring.py | 71 | Five-condition technical scoring |

#### Stock_Screener - 2 files

| File | Lines | Responsibility |
|---|---:|---|
| Nasdaq_21_Session_Screener.py | 1174 | Primary screening application |
| Nasdaq_21_Session_Screener_BACKUP.py | 1002 | Historical backup implementation |

#### tests - 2 files

| File | Lines | Responsibility |
|---|---:|---|
| Step6_Scored_Backtest_Tests.py | 221 | Quantitative regression testing |
| Step7_Integration_Tests.py | 252 | Integration and reporting testing |

### 4. External dependencies

Direct third-party dependencies identified:

- pandas
- numpy
- yfinance
- requests
- python-docx

All five are included in the approved Version 2.0
development environment.

PySide6 and MySQL Connector/Python are approved
Version 2.0 dependencies.

No additional dependencies are authorized by this audit.

### 5. Dependency and coupling findings

D01 - Command-line coupling

The primary screener combines user interaction,
research execution and output generation.

Separate presentation from application services.

D02 - Market data acquisition

Screening and backtesting use external market data
retrieval with different validation requirements.

Introduce provider interfaces while preserving
existing acquisition behavior.

D03 - Blocking operations

Screening includes synchronous downloads, retries,
delays and corporate-action verification.

Use background processing for desktop execution.

D04 - File-based research handoff

The screener and backtesting engine exchange
research parameters using JSON schema version 1.

Preserve this compatibility contract.

D05 - Report generation coupling

Word reporting is embedded in the primary screener,
with additional dedicated backtesting report modules.

Separate report generation from research execution.

D06 - Filesystem coupling

Several components derive operational paths from
their source file locations.

Centralize application path configuration.

D07 - Existing testability

The scored backtester accepts an optional price
loader, supporting deterministic testing.

Preserve and extend dependency injection.

### 6. Quantitative audit findings

Preserve the existing implementation of:

- Twenty-one-session price and gain screening.
- Inclusive price boundaries.
- Reverse-split exclusion and verification.
- Completed-session cutoff behavior.
- MACD, signal line and histogram calculations.
- RSI and relative volume calculations.
- Indicator warmup and missing-data behavior.
- Five-condition technical scoring.
- Research Mode and Strict Momentum Mode.
- Median daily dollar volume and ranking.
- Historical signal generation.
- Trade entry, exit and holding-period rules.
- Transaction costs and trade overlap restrictions.
- Statistical performance calculations.

An unavailable technical score must remain distinct
from a valid score of zero.

The existing observation window contains twenty-one
closing prices and twenty close-to-close intervals.

Quantitative preservation requirements are governed
by the approved QPC-001 contract.

### 7. Data flow and interface findings

The current screening application produces structured
Python research results and Word reports.

A versioned JSON handoff connects screening results
to the optional historical backtesting workflow.

Important existing data structures include:

- Security
- Match
- ScanResult
- TechnicalScore
- ScreenerSettings
- BacktestSettings
- ScreenerHandoff
- HistoricalSignal
- ScoredSignal
- SimulatedTrade
- MultipleTradeResult
- PerformanceStatistics
- ScorePerformance
- ScoredBacktestResult

Screening-run identity must remain distinct from
the completed trading date.

The existing JSON handoff preserves research requests
but does not preserve all original market observations.

No MySQL persistence implementation exists in the
validated source.

Data preservation requirements are governed by
the approved DIC-001 contract.

### 8. Research integrity limitations

Q01 - Refactoring may introduce quantitative regressions.

Q02 - Historical research is conditioned on stocks
qualifying in the present-day screening results.

Q03 - External corporate-action records may be incomplete.

Q04 - Historical market data may subsequently be revised.

Q05 - Indicator warmup histories may differ between
research workflows.

Q06 - Missing scores must not be converted to zero.

Q07 - Transaction costs use simplified assumptions.

Q08 - Individual-trade statistics are not portfolio
investment returns.

Q09 - Presentation ranking must not be confused with
stock qualification.

Preserve the existing methodology and disclose these
limitations. Methodology changes require explicit
user approval.

### 9. Integration recommendations

- Preserve the Shared Analytics quantitative foundation.
- Reuse existing historical signal and simulation logic.
- Separate the primary screener's responsibilities.
- Preserve existing command-line behavior.
- Exclude the historical backup screener from active
  Version 2.0 integration.
- Do not treat the empty research_snapshot module
  as implemented functionality.
- Introduce application-owned provider and repository
  interfaces.
- Preserve the existing regression tests.
- Compare both application versions using identical
  deterministic market data.

These recommendations align with the approved
ARCH-001 architecture and ADR-016 through ADR-025.

### 10. Verification evidence and limitations

The validated source archive was independently
checked for its SHA-256 fingerprint and ZIP integrity.

All 29 Python files were statically parsed.

Development Milestone 01 established the following
offline regression test results:

- Step 6: 16 of 16 passed.
- Step 7: 18 of 18 passed.
- Combined: 34 of 34 passed.

These results are historical verification evidence.
No new application execution is claimed by this audit.

Static inspection does not establish complete runtime
correctness or comprehensive quantitative equivalence.

Live market data verification, MySQL connectivity
and Version 2.0 implementation testing remain pending.

### 11. Baseline protection

The original Version 1.2 application and both
protected archives shall remain unchanged.

All Version 2.0 implementation work shall occur
within the independent development project.

No quantitative methodology changes, additional
dependencies or application scope expansion are
authorized by this document.
