# DBD-001 — Data dictionary
Proposed schema; not deployed. All dates are market dates unless explicitly UTC. DOUBLE preserves the existing Python floating-point model; NULL means unavailable where permitted. PK and FK declarations follow each table.
## schema_migration
Applied schema revision ledger

| Column | SQL type / nullability | Meaning |
|---|---|---|
| `version` | `INT UNSIGNED NOT NULL` | Migration sequence |
| `applied_utc` | `DATETIME(6) NOT NULL` | UTC application time |
| `script_sha256` | `CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL` | Exact migration bytes digest |

Primary key: `version`.

## research_run
Common identity and lifecycle for scan/backtest

| Column | SQL type / nullability | Meaning |
|---|---|---|
| `run_id` | `BIGINT UNSIGNED AUTO_INCREMENT NOT NULL` | Surrogate identifier |
| `run_uuid` | `CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL` | Application-generated UUID |
| `run_kind` | `ENUM('SCAN','BACKTEST') NOT NULL` | Execution type |
| `started_utc` | `DATETIME(6) NOT NULL` | UTC start |
| `finished_utc` | `DATETIME(6) NULL` | UTC finish |
| `status` | `ENUM('RUNNING','COMPLETED','FAILED','CANCELLED') NOT NULL` | Persisted execution state |
| `engine_revision` | `VARCHAR(255) NOT NULL` | Source commit or validated archive fingerprint |
| `environment_json` | `JSON NOT NULL` | Interpreter, dependency versions and execution settings |
| `error_text` | `TEXT NULL` | Failure explanation |

Primary key: `run_id`.
- `UNIQUE (run_uuid)`
- `KEY (run_kind, started_utc)`
- `CHECK (finished_utc IS NULL OR finished_utc >= started_utc)`
- `CHECK ((status = 'RUNNING' AND finished_utc IS NULL) OR (status <> 'RUNNING' AND finished_utc IS NOT NULL))`

## screening_run
Screening parameters, handoff identity and aggregate counters

| Column | SQL type / nullability | Meaning |
|---|---|---|
| `run_id` | `BIGINT UNSIGNED NOT NULL` | Originating research execution |
| `scan_id` | `VARCHAR(255) CHARACTER SET ascii COLLATE ascii_bin NOT NULL` | Legacy handoff identity |
| `scan_date` | `DATE NOT NULL` | Completed market session |
| `min_gain_pct` | `DOUBLE NOT NULL` | Minimum percentage gain |
| `min_price` | `DOUBLE NOT NULL` | Inclusive lower closing price |
| `max_price` | `DOUBLE NOT NULL` | Inclusive upper closing price |
| `momentum_required` | `TINYINT UNSIGNED NOT NULL` | 0 research; 1 strict |
| `batch_size` | `INT UNSIGNED NOT NULL` | Acquisition batch size |
| `batch_delay_seconds` | `DOUBLE NOT NULL` | Delay |
| `retries` | `INT UNSIGNED NOT NULL` | Retry count |
| `history_years` | `INT UNSIGNED NOT NULL` | Handoff historical period |
| `holding_sessions` | `INT UNSIGNED NOT NULL` | Handoff holding period |
| `round_trip_cost_pct` | `DOUBLE NOT NULL` | Handoff transaction cost |
| `checked` | `INT UNSIGNED NULL` | Baseline ScanResult counter |
| `missing` | `INT UNSIGNED NULL` | Baseline ScanResult counter |
| `initial_matches` | `INT UNSIGNED NULL` | Baseline ScanResult counter |
| `excluded_reverse` | `INT UNSIGNED NULL` | Baseline ScanResult counter |
| `excluded_unverified` | `INT UNSIGNED NULL` | Baseline ScanResult counter |
| `excluded_momentum` | `INT UNSIGNED NULL` | Baseline ScanResult counter |

Primary key: `run_id`.
- FK `run_id` → `research_run(run_id)`.
- `UNIQUE (scan_id)`
- `KEY (scan_date)`
- `CHECK (min_gain_pct >= 0 AND min_price > 0 AND max_price >= min_price)`
- `CHECK (momentum_required IN (0,1) AND batch_size > 0 AND batch_delay_seconds >= 0)`
- `CHECK (history_years > 0 AND holding_sessions > 0 AND round_trip_cost_pct BETWEEN 0 AND 100)`

## backtest_run
Actual simulation settings and originating scan

| Column | SQL type / nullability | Meaning |
|---|---|---|
| `run_id` | `BIGINT UNSIGNED NOT NULL` | Originating research execution |
| `source_scan_run_id` | `BIGINT UNSIGNED NULL` | Originating screening run; NULL for standalone legacy backtest |
| `history_years` | `INT UNSIGNED NULL` | Requested historical period; NULL for explicit date range |
| `evaluation_start` | `DATE NOT NULL` | First eligible evaluation date |
| `evaluation_end` | `DATE NOT NULL` | Last eligible evaluation date |
| `min_gain_pct` | `DOUBLE NOT NULL` | Effective gain threshold |
| `min_price` | `DOUBLE NOT NULL` | Effective minimum price |
| `max_price` | `DOUBLE NOT NULL` | Effective maximum price |
| `momentum_required` | `TINYINT UNSIGNED NOT NULL` | Effective historical engine mode |
| `holding_sessions` | `INT UNSIGNED NOT NULL` | Actual holding period |
| `round_trip_cost_pct` | `DOUBLE NOT NULL` | Actual transaction cost |
| `total_signals` | `INT UNSIGNED NULL` | Simulation signal count |
| `skipped_overlapping` | `INT UNSIGNED NULL` | Overlapping signals |
| `skipped_incomplete` | `INT UNSIGNED NULL` | Incomplete signals |

Primary key: `run_id`.
- FK `run_id` → `research_run(run_id)`.
- FK `source_scan_run_id` → `screening_run(run_id)`.
- `KEY (source_scan_run_id)`
- `CHECK (evaluation_end >= evaluation_start)`
- `CHECK (min_gain_pct >= 0 AND min_price > 0 AND max_price >= min_price AND momentum_required IN (0,1))`
- `CHECK (history_years > 0 AND holding_sessions > 0 AND round_trip_cost_pct BETWEEN 0 AND 100)`

## security
Internal identity; no assertion that ticker is permanent

| Column | SQL type / nullability | Meaning |
|---|---|---|
| `security_id` | `BIGINT UNSIGNED AUTO_INCREMENT NOT NULL` | Surrogate identifier |
| `identity_note` | `TEXT NULL` | Identity evidence or unresolved identity note |

Primary key: `security_id`.

## run_security
Run-specific universe membership, symbol/name and acquisition disposition

| Column | SQL type / nullability | Meaning |
|---|---|---|
| `run_id` | `BIGINT UNSIGNED NOT NULL` | Originating research execution |
| `security_id` | `BIGINT UNSIGNED NOT NULL` | Internal security identifier |
| `ticker` | `VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL` | Ticker as used by engine |
| `security_name` | `TEXT NULL` | Name as observed in source |
| `provider_symbol` | `VARCHAR(128) NULL` | Symbol requested from provider |
| `disposition` | `ENUM('UNKNOWN','QUALIFIED','REJECTED','MISSING','REVERSE_SPLIT','UNVERIFIED_SPLIT','MOMENTUM_EXCLUDED','ANALYZED','EXCLUDED') NOT NULL` | Observed outcome; UNKNOWN where not captured |
| `reason` | `TEXT NULL` | Observed explanation |
| `signal_count` | `INT UNSIGNED NULL` | Historical signals for symbol |

Primary key: `run_id, security_id`.
- FK `run_id` → `research_run(run_id)`.
- FK `security_id` → `security(security_id)`.
- `UNIQUE (run_id, ticker)`
- `KEY (security_id, run_id)`
- `KEY (ticker, run_id)`

## input_artifact
Immutable run-specific captured inputs including failed acquisition evidence

| Column | SQL type / nullability | Meaning |
|---|---|---|
| `artifact_id` | `BIGINT UNSIGNED AUTO_INCREMENT NOT NULL` | Surrogate identifier |
| `run_id` | `BIGINT UNSIGNED NOT NULL` | Originating research execution |
| `security_id` | `BIGINT UNSIGNED NULL` | Optional per-security association |
| `role` | `VARCHAR(64) NOT NULL` | Universe, calendar, screening history, backtest history, split history, handoff or error |
| `sequence_no` | `INT UNSIGNED NOT NULL` | Capture order within run |
| `provider` | `VARCHAR(255) NOT NULL` | Source identity |
| `captured_utc` | `DATETIME(6) NOT NULL` | UTC capture time |
| `request_json` | `JSON NOT NULL` | Actual request options, dates, adjustment flags, timezone |
| `format_name` | `VARCHAR(64) NOT NULL` | Versioned lossless serialization format |
| `sha256` | `CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL` | Digest of payload bytes |
| `payload` | `LONGBLOB NOT NULL` | Actual source/engine-boundary bytes or explicit failure record |

Primary key: `artifact_id`.
- FK `run_id` → `research_run(run_id)`.
- FK `run_id, security_id` → `run_security(run_id, security_id)`.
- `UNIQUE (run_id, sequence_no)`
- `KEY (run_id, role)`
- `KEY (sha256)`

## trading_session
Ordered reference calendar used by each research run

| Column | SQL type / nullability | Meaning |
|---|---|---|
| `run_id` | `BIGINT UNSIGNED NOT NULL` | Originating research execution |
| `session_date` | `DATE NOT NULL` | Market date |
| `session_no` | `INT UNSIGNED NOT NULL` | Chronological ordinal |

Primary key: `run_id, session_date`.
- FK `run_id` → `research_run(run_id)`.
- `UNIQUE (run_id, session_no)`

## daily_observation
Queryable validated inputs or displayed daily analytics; exact input retained separately

| Column | SQL type / nullability | Meaning |
|---|---|---|
| `run_id` | `BIGINT UNSIGNED NOT NULL` | Originating research execution |
| `security_id` | `BIGINT UNSIGNED NOT NULL` | Internal security identifier |
| `series_kind` | `ENUM('ENGINE_INPUT','SCREEN_DISPLAY') NOT NULL` | Distinguishes input history and report window |
| `session_date` | `DATE NOT NULL` | Market date |
| `open_price` | `DOUBLE NULL` | Observed or calculated open price |
| `high_price` | `DOUBLE NULL` | Observed or calculated high price |
| `low_price` | `DOUBLE NULL` | Observed or calculated low price |
| `close_price` | `DOUBLE NULL` | Observed or calculated close price |
| `volume` | `DOUBLE NULL` | Observed or calculated volume |
| `macd` | `DOUBLE NULL` | Observed or calculated macd |
| `signal_line` | `DOUBLE NULL` | Observed or calculated signal line |
| `histogram` | `DOUBLE NULL` | Observed or calculated histogram |
| `normalized_histogram` | `DOUBLE NULL` | Observed or calculated normalized histogram |
| `rsi` | `DOUBLE NULL` | Observed or calculated rsi |
| `relative_volume` | `DOUBLE NULL` | Observed or calculated relative volume |
| `rising_days` | `INT UNSIGNED NULL` | Consecutive histogram increases |

Primary key: `run_id, security_id, series_kind, session_date`.
- FK `run_id, security_id` → `run_security(run_id, security_id)`.
- `CHECK (open_price IS NULL OR open_price > 0)`
- `CHECK (close_price IS NULL OR close_price > 0)`
- `CHECK (volume IS NULL OR volume >= 0)`

## screening_result
Qualified candidate summary and two ordering conventions

| Column | SQL type / nullability | Meaning |
|---|---|---|
| `run_id` | `BIGINT UNSIGNED NOT NULL` | Originating research execution |
| `security_id` | `BIGINT UNSIGNED NOT NULL` | Internal security identifier |
| `gain_pct` | `DOUBLE NOT NULL` | Baseline Match gain_pct |
| `avg_open` | `DOUBLE NOT NULL` | Baseline Match avg_open |
| `avg_close` | `DOUBLE NOT NULL` | Baseline Match avg_close |
| `avg_volume` | `DOUBLE NOT NULL` | Baseline Match avg_volume |
| `first_close` | `DOUBLE NOT NULL` | Baseline Match first_close |
| `last_close` | `DOUBLE NOT NULL` | Baseline Match last_close |
| `median_dollar_volume` | `DOUBLE NULL` | Median close times volume |
| `scan_rank` | `INT UNSIGNED NOT NULL` | Original scan order |
| `report_rank` | `INT UNSIGNED NOT NULL` | Original report order |
| `technical_score` | `TINYINT UNSIGNED NULL` | 0–5 or NULL for unavailable/not computed |
| `macd_positive` | `TINYINT UNSIGNED NULL` | Condition 0 false, 1 true, NULL unavailable/not computed |
| `histogram_positive` | `TINYINT UNSIGNED NULL` | Condition 0 false, 1 true, NULL unavailable/not computed |
| `histogram_rising_three` | `TINYINT UNSIGNED NULL` | Condition 0 false, 1 true, NULL unavailable/not computed |
| `rsi_50_to_70` | `TINYINT UNSIGNED NULL` | Condition 0 false, 1 true, NULL unavailable/not computed |
| `relative_volume_above_one` | `TINYINT UNSIGNED NULL` | Condition 0 false, 1 true, NULL unavailable/not computed |

Primary key: `run_id, security_id`.
- FK `run_id, security_id` → `run_security(run_id, security_id)`.
- FK `run_id` → `screening_run(run_id)`.
- `UNIQUE (run_id, scan_rank)`
- `UNIQUE (run_id, report_rank)`
- `CHECK (macd_positive IN (0,1))`
- `CHECK (histogram_positive IN (0,1))`
- `CHECK (histogram_rising_three IN (0,1))`
- `CHECK (rsi_50_to_70 IN (0,1))`
- `CHECK (relative_volume_above_one IN (0,1))`
- `CHECK ((technical_score IS NULL AND (macd_positive IS NULL OR histogram_positive IS NULL OR histogram_rising_three IS NULL OR rsi_50_to_70 IS NULL OR relative_volume_above_one IS NULL)) OR (technical_score IS NOT NULL AND macd_positive IS NOT NULL AND histogram_positive IS NOT NULL AND histogram_rising_three IS NOT NULL AND rsi_50_to_70 IS NOT NULL AND relative_volume_above_one IS NOT NULL AND technical_score = macd_positive + histogram_positive + histogram_rising_three + rsi_50_to_70 + relative_volume_above_one))`

## historical_signal
Signal-date metrics and optional score; strict score not fabricated

| Column | SQL type / nullability | Meaning |
|---|---|---|
| `run_id` | `BIGINT UNSIGNED NOT NULL` | Originating research execution |
| `security_id` | `BIGINT UNSIGNED NOT NULL` | Internal security identifier |
| `signal_date` | `DATE NOT NULL` | Signal session |
| `first_close` | `DOUBLE NULL` | HistoricalSignal first_close |
| `last_close` | `DOUBLE NULL` | HistoricalSignal last_close |
| `gain_pct` | `DOUBLE NULL` | HistoricalSignal gain_pct |
| `macd` | `DOUBLE NULL` | HistoricalSignal macd |
| `histogram` | `DOUBLE NULL` | HistoricalSignal histogram |
| `rsi` | `DOUBLE NULL` | HistoricalSignal rsi |
| `relative_volume` | `DOUBLE NULL` | HistoricalSignal relative_volume |
| `rising_days` | `INT UNSIGNED NULL` | Consecutive increases |
| `technical_score` | `TINYINT UNSIGNED NULL` | 0–5 or NULL for unavailable/not computed |
| `macd_positive` | `TINYINT UNSIGNED NULL` | Condition 0 false, 1 true, NULL unavailable/not computed |
| `histogram_positive` | `TINYINT UNSIGNED NULL` | Condition 0 false, 1 true, NULL unavailable/not computed |
| `histogram_rising_three` | `TINYINT UNSIGNED NULL` | Condition 0 false, 1 true, NULL unavailable/not computed |
| `rsi_50_to_70` | `TINYINT UNSIGNED NULL` | Condition 0 false, 1 true, NULL unavailable/not computed |
| `relative_volume_above_one` | `TINYINT UNSIGNED NULL` | Condition 0 false, 1 true, NULL unavailable/not computed |
| `trade_disposition` | `ENUM('UNKNOWN','COMPLETED','OVERLAPPING','INCOMPLETE') NOT NULL` | Simulation disposition when captured |

Primary key: `run_id, security_id, signal_date`.
- FK `run_id, security_id` → `run_security(run_id, security_id)`.
- FK `run_id` → `backtest_run(run_id)`.
- FK `run_id, signal_date` → `trading_session(run_id, session_date)`.
- `CHECK (macd_positive IN (0,1))`
- `CHECK (histogram_positive IN (0,1))`
- `CHECK (histogram_rising_three IN (0,1))`
- `CHECK (rsi_50_to_70 IN (0,1))`
- `CHECK (relative_volume_above_one IN (0,1))`
- `CHECK ((technical_score IS NULL AND (macd_positive IS NULL OR histogram_positive IS NULL OR histogram_rising_three IS NULL OR rsi_50_to_70 IS NULL OR relative_volume_above_one IS NULL)) OR (technical_score IS NOT NULL AND macd_positive IS NOT NULL AND histogram_positive IS NOT NULL AND histogram_rising_three IS NOT NULL AND rsi_50_to_70 IS NOT NULL AND relative_volume_above_one IS NOT NULL AND technical_score = macd_positive + histogram_positive + histogram_rising_three + rsi_50_to_70 + relative_volume_above_one))`
- `KEY (run_id, signal_date)`

## simulated_trade
At most one completed trade per originating signal

| Column | SQL type / nullability | Meaning |
|---|---|---|
| `run_id` | `BIGINT UNSIGNED NOT NULL` | Originating research execution |
| `security_id` | `BIGINT UNSIGNED NOT NULL` | Internal security identifier |
| `signal_date` | `DATE NOT NULL` | Originating signal |
| `entry_date` | `DATE NOT NULL` | Entry session |
| `exit_date` | `DATE NOT NULL` | Exit session |
| `holding_sessions` | `INT UNSIGNED NOT NULL` | Simulated duration |
| `entry_price` | `DOUBLE NOT NULL` | Baseline SimulatedTrade entry_price |
| `exit_price` | `DOUBLE NOT NULL` | Baseline SimulatedTrade exit_price |
| `gross_return_pct` | `DOUBLE NOT NULL` | Baseline SimulatedTrade gross_return_pct |
| `round_trip_cost_pct` | `DOUBLE NOT NULL` | Baseline SimulatedTrade round_trip_cost_pct |
| `net_return_pct` | `DOUBLE NOT NULL` | Baseline SimulatedTrade net_return_pct |

Primary key: `run_id, security_id, signal_date`.
- FK `run_id, security_id, signal_date` → `historical_signal(run_id, security_id, signal_date)`.
- FK `run_id, entry_date` → `trading_session(run_id, session_date)`.
- FK `run_id, exit_date` → `trading_session(run_id, session_date)`.
- `CHECK (entry_date > signal_date AND exit_date >= entry_date AND holding_sessions > 0)`
- `CHECK (entry_price > 0 AND exit_price > 0 AND round_trip_cost_pct BETWEEN 0 AND 100)`
- `KEY (run_id, exit_date)`

## performance_summary
Overall or score-group statistics; explicit infinity and undefined state

| Column | SQL type / nullability | Meaning |
|---|---|---|
| `run_id` | `BIGINT UNSIGNED NOT NULL` | Originating research execution |
| `score_group` | `ENUM('ALL','0','1','2','3','4','5','NA') NOT NULL` | ALL overall; NA unavailable score |
| `signal_count` | `INT UNSIGNED NULL` | Signals in group |
| `total_trades` | `INT UNSIGNED NOT NULL` | Completed trade accounting |
| `winning_trades` | `INT UNSIGNED NOT NULL` | Completed trade accounting |
| `losing_trades` | `INT UNSIGNED NOT NULL` | Completed trade accounting |
| `breakeven_trades` | `INT UNSIGNED NOT NULL` | Completed trade accounting |
| `win_rate_pct` | `DOUBLE NULL` | Baseline PerformanceStatistics win_rate_pct |
| `average_gross_return_pct` | `DOUBLE NULL` | Baseline PerformanceStatistics average_gross_return_pct |
| `average_net_return_pct` | `DOUBLE NULL` | Baseline PerformanceStatistics average_net_return_pct |
| `average_winning_return_pct` | `DOUBLE NULL` | Baseline PerformanceStatistics average_winning_return_pct |
| `average_losing_return_pct` | `DOUBLE NULL` | Baseline PerformanceStatistics average_losing_return_pct |
| `expectancy_pct` | `DOUBLE NULL` | Baseline PerformanceStatistics expectancy_pct |
| `profit_factor` | `DOUBLE NULL` | Baseline PerformanceStatistics profit_factor |
| `best_trade_pct` | `DOUBLE NULL` | Baseline PerformanceStatistics best_trade_pct |
| `worst_trade_pct` | `DOUBLE NULL` | Baseline PerformanceStatistics worst_trade_pct |
| `average_transaction_cost_pct` | `DOUBLE NULL` | Baseline PerformanceStatistics average_transaction_cost_pct |
| `profit_factor_state` | `ENUM('FINITE','INFINITE','UNDEFINED') NOT NULL` | Explicit nonfinite semantics |

Primary key: `run_id, score_group`.
- FK `run_id` → `backtest_run(run_id)`.
- `CHECK (total_trades = winning_trades + losing_trades + breakeven_trades)`
- `CHECK ((profit_factor_state = 'FINITE' AND profit_factor IS NOT NULL AND profit_factor >= 0) OR (profit_factor_state <> 'FINITE' AND profit_factor IS NULL))`

## research_report
Report bytes linked to originating run; independent generation lifecycle

| Column | SQL type / nullability | Meaning |
|---|---|---|
| `report_id` | `BIGINT UNSIGNED AUTO_INCREMENT NOT NULL` | Surrogate identifier |
| `run_id` | `BIGINT UNSIGNED NOT NULL` | Originating research execution |
| `report_kind` | `VARCHAR(64) NOT NULL` | Screening, performance or integrated |
| `generated_utc` | `DATETIME(6) NOT NULL` | UTC creation time |
| `filename` | `VARCHAR(255) NOT NULL` | Display filename |
| `sha256` | `CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL` | Report content digest |
| `payload` | `LONGBLOB NOT NULL` | Exact generated Word document |

Primary key: `report_id`.
- FK `run_id` → `research_run(run_id)`.
- `KEY (run_id, generated_utc)`
