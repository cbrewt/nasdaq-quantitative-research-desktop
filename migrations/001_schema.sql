-- DBD-001 PROPOSAL ONLY. Do not execute until approved.
-- Run with an administrator in a fresh dedicated database; no --force.
CREATE DATABASE `nasdaq_quant_research_v2` CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
USE `nasdaq_quant_research_v2`;
SET SESSION time_zone = '+00:00';

CREATE TABLE `schema_migration` (
  `version` INT UNSIGNED NOT NULL,
  `applied_utc` DATETIME(6) NOT NULL,
  `script_sha256` CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  PRIMARY KEY (version)
) ENGINE=InnoDB;

CREATE TABLE `research_run` (
  `run_id` BIGINT UNSIGNED AUTO_INCREMENT NOT NULL,
  `run_uuid` CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  `run_kind` ENUM('SCAN','BACKTEST') NOT NULL,
  `started_utc` DATETIME(6) NOT NULL,
  `finished_utc` DATETIME(6) NULL,
  `status` ENUM('RUNNING','COMPLETED','FAILED','CANCELLED') NOT NULL,
  `engine_revision` VARCHAR(255) NOT NULL,
  `environment_json` JSON NOT NULL,
  `error_text` TEXT NULL,
  PRIMARY KEY (run_id),
  UNIQUE (run_uuid),
  KEY (run_kind, started_utc),
  CHECK (finished_utc IS NULL OR finished_utc >= started_utc),
  CHECK ((status = 'RUNNING' AND finished_utc IS NULL) OR (status <> 'RUNNING' AND finished_utc IS NOT NULL))
) ENGINE=InnoDB;

CREATE TABLE `screening_run` (
  `run_id` BIGINT UNSIGNED NOT NULL,
  `scan_id` VARCHAR(255) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  `scan_date` DATE NOT NULL,
  `min_gain_pct` DOUBLE NOT NULL,
  `min_price` DOUBLE NOT NULL,
  `max_price` DOUBLE NOT NULL,
  `momentum_required` TINYINT UNSIGNED NOT NULL,
  `batch_size` INT UNSIGNED NOT NULL,
  `batch_delay_seconds` DOUBLE NOT NULL,
  `retries` INT UNSIGNED NOT NULL,
  `history_years` INT UNSIGNED NOT NULL,
  `holding_sessions` INT UNSIGNED NOT NULL,
  `round_trip_cost_pct` DOUBLE NOT NULL,
  `checked` INT UNSIGNED NULL,
  `missing` INT UNSIGNED NULL,
  `initial_matches` INT UNSIGNED NULL,
  `excluded_reverse` INT UNSIGNED NULL,
  `excluded_unverified` INT UNSIGNED NULL,
  `excluded_momentum` INT UNSIGNED NULL,
  PRIMARY KEY (run_id),
  FOREIGN KEY (run_id) REFERENCES `research_run` (run_id),
  UNIQUE (scan_id),
  KEY (scan_date),
  CHECK (min_gain_pct >= 0 AND min_price > 0 AND max_price >= min_price),
  CHECK (momentum_required IN (0,1) AND batch_size > 0 AND batch_delay_seconds >= 0),
  CHECK (history_years > 0 AND holding_sessions > 0 AND round_trip_cost_pct BETWEEN 0 AND 100)
) ENGINE=InnoDB;

CREATE TABLE `backtest_run` (
  `run_id` BIGINT UNSIGNED NOT NULL,
  `source_scan_run_id` BIGINT UNSIGNED NULL,
  `history_years` INT UNSIGNED NULL,
  `evaluation_start` DATE NOT NULL,
  `evaluation_end` DATE NOT NULL,
  `min_gain_pct` DOUBLE NOT NULL,
  `min_price` DOUBLE NOT NULL,
  `max_price` DOUBLE NOT NULL,
  `momentum_required` TINYINT UNSIGNED NOT NULL,
  `holding_sessions` INT UNSIGNED NOT NULL,
  `round_trip_cost_pct` DOUBLE NOT NULL,
  `total_signals` INT UNSIGNED NULL,
  `skipped_overlapping` INT UNSIGNED NULL,
  `skipped_incomplete` INT UNSIGNED NULL,
  PRIMARY KEY (run_id),
  FOREIGN KEY (run_id) REFERENCES `research_run` (run_id),
  FOREIGN KEY (source_scan_run_id) REFERENCES `screening_run` (run_id),
  KEY (source_scan_run_id),
  CHECK (evaluation_end >= evaluation_start),
  CHECK (min_gain_pct >= 0 AND min_price > 0 AND max_price >= min_price AND momentum_required IN (0,1)),
  CHECK (history_years > 0 AND holding_sessions > 0 AND round_trip_cost_pct BETWEEN 0 AND 100)
) ENGINE=InnoDB;

CREATE TABLE `security` (
  `security_id` BIGINT UNSIGNED AUTO_INCREMENT NOT NULL,
  `identity_note` TEXT NULL,
  PRIMARY KEY (security_id)
) ENGINE=InnoDB;

CREATE TABLE `run_security` (
  `run_id` BIGINT UNSIGNED NOT NULL,
  `security_id` BIGINT UNSIGNED NOT NULL,
  `ticker` VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  `security_name` TEXT NULL,
  `provider_symbol` VARCHAR(128) NULL,
  `disposition` ENUM('UNKNOWN','QUALIFIED','REJECTED','MISSING','REVERSE_SPLIT','UNVERIFIED_SPLIT','MOMENTUM_EXCLUDED','ANALYZED','EXCLUDED') NOT NULL,
  `reason` TEXT NULL,
  `signal_count` INT UNSIGNED NULL,
  PRIMARY KEY (run_id, security_id),
  FOREIGN KEY (run_id) REFERENCES `research_run` (run_id),
  FOREIGN KEY (security_id) REFERENCES `security` (security_id),
  UNIQUE (run_id, ticker),
  KEY (security_id, run_id),
  KEY (ticker, run_id)
) ENGINE=InnoDB;

CREATE TABLE `input_artifact` (
  `artifact_id` BIGINT UNSIGNED AUTO_INCREMENT NOT NULL,
  `run_id` BIGINT UNSIGNED NOT NULL,
  `security_id` BIGINT UNSIGNED NULL,
  `role` VARCHAR(64) NOT NULL,
  `sequence_no` INT UNSIGNED NOT NULL,
  `provider` VARCHAR(255) NOT NULL,
  `captured_utc` DATETIME(6) NOT NULL,
  `request_json` JSON NOT NULL,
  `format_name` VARCHAR(64) NOT NULL,
  `sha256` CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  `payload` LONGBLOB NOT NULL,
  PRIMARY KEY (artifact_id),
  FOREIGN KEY (run_id) REFERENCES `research_run` (run_id),
  FOREIGN KEY (run_id, security_id) REFERENCES `run_security` (run_id, security_id),
  UNIQUE (run_id, sequence_no),
  KEY (run_id, role),
  KEY (sha256)
) ENGINE=InnoDB;

CREATE TABLE `trading_session` (
  `run_id` BIGINT UNSIGNED NOT NULL,
  `session_date` DATE NOT NULL,
  `session_no` INT UNSIGNED NOT NULL,
  PRIMARY KEY (run_id, session_date),
  FOREIGN KEY (run_id) REFERENCES `research_run` (run_id),
  UNIQUE (run_id, session_no)
) ENGINE=InnoDB;

CREATE TABLE `daily_observation` (
  `run_id` BIGINT UNSIGNED NOT NULL,
  `security_id` BIGINT UNSIGNED NOT NULL,
  `series_kind` ENUM('ENGINE_INPUT','SCREEN_DISPLAY') NOT NULL,
  `session_date` DATE NOT NULL,
  `open_price` DOUBLE NULL,
  `high_price` DOUBLE NULL,
  `low_price` DOUBLE NULL,
  `close_price` DOUBLE NULL,
  `volume` DOUBLE NULL,
  `macd` DOUBLE NULL,
  `signal_line` DOUBLE NULL,
  `histogram` DOUBLE NULL,
  `normalized_histogram` DOUBLE NULL,
  `rsi` DOUBLE NULL,
  `relative_volume` DOUBLE NULL,
  `rising_days` INT UNSIGNED NULL,
  PRIMARY KEY (run_id, security_id, series_kind, session_date),
  FOREIGN KEY (run_id, security_id) REFERENCES `run_security` (run_id, security_id),
  CHECK (open_price IS NULL OR open_price > 0),
  CHECK (close_price IS NULL OR close_price > 0),
  CHECK (volume IS NULL OR volume >= 0)
) ENGINE=InnoDB;

CREATE TABLE `screening_result` (
  `run_id` BIGINT UNSIGNED NOT NULL,
  `security_id` BIGINT UNSIGNED NOT NULL,
  `gain_pct` DOUBLE NOT NULL,
  `avg_open` DOUBLE NOT NULL,
  `avg_close` DOUBLE NOT NULL,
  `avg_volume` DOUBLE NOT NULL,
  `first_close` DOUBLE NOT NULL,
  `last_close` DOUBLE NOT NULL,
  `median_dollar_volume` DOUBLE NULL,
  `scan_rank` INT UNSIGNED NOT NULL,
  `report_rank` INT UNSIGNED NOT NULL,
  `technical_score` TINYINT UNSIGNED NULL,
  `macd_positive` TINYINT UNSIGNED NULL,
  `histogram_positive` TINYINT UNSIGNED NULL,
  `histogram_rising_three` TINYINT UNSIGNED NULL,
  `rsi_50_to_70` TINYINT UNSIGNED NULL,
  `relative_volume_above_one` TINYINT UNSIGNED NULL,
  PRIMARY KEY (run_id, security_id),
  FOREIGN KEY (run_id, security_id) REFERENCES `run_security` (run_id, security_id),
  FOREIGN KEY (run_id) REFERENCES `screening_run` (run_id),
  UNIQUE (run_id, scan_rank),
  UNIQUE (run_id, report_rank),
  CHECK (macd_positive IN (0,1)),
  CHECK (histogram_positive IN (0,1)),
  CHECK (histogram_rising_three IN (0,1)),
  CHECK (rsi_50_to_70 IN (0,1)),
  CHECK (relative_volume_above_one IN (0,1)),
  CHECK ((technical_score IS NULL AND (macd_positive IS NULL OR histogram_positive IS NULL OR histogram_rising_three IS NULL OR rsi_50_to_70 IS NULL OR relative_volume_above_one IS NULL)) OR (technical_score IS NOT NULL AND macd_positive IS NOT NULL AND histogram_positive IS NOT NULL AND histogram_rising_three IS NOT NULL AND rsi_50_to_70 IS NOT NULL AND relative_volume_above_one IS NOT NULL AND technical_score = macd_positive + histogram_positive + histogram_rising_three + rsi_50_to_70 + relative_volume_above_one))
) ENGINE=InnoDB;

CREATE TABLE `historical_signal` (
  `run_id` BIGINT UNSIGNED NOT NULL,
  `security_id` BIGINT UNSIGNED NOT NULL,
  `signal_date` DATE NOT NULL,
  `first_close` DOUBLE NULL,
  `last_close` DOUBLE NULL,
  `gain_pct` DOUBLE NULL,
  `macd` DOUBLE NULL,
  `histogram` DOUBLE NULL,
  `rsi` DOUBLE NULL,
  `relative_volume` DOUBLE NULL,
  `rising_days` INT UNSIGNED NULL,
  `technical_score` TINYINT UNSIGNED NULL,
  `macd_positive` TINYINT UNSIGNED NULL,
  `histogram_positive` TINYINT UNSIGNED NULL,
  `histogram_rising_three` TINYINT UNSIGNED NULL,
  `rsi_50_to_70` TINYINT UNSIGNED NULL,
  `relative_volume_above_one` TINYINT UNSIGNED NULL,
  `trade_disposition` ENUM('UNKNOWN','COMPLETED','OVERLAPPING','INCOMPLETE') NOT NULL,
  PRIMARY KEY (run_id, security_id, signal_date),
  FOREIGN KEY (run_id, security_id) REFERENCES `run_security` (run_id, security_id),
  FOREIGN KEY (run_id) REFERENCES `backtest_run` (run_id),
  FOREIGN KEY (run_id, signal_date) REFERENCES `trading_session` (run_id, session_date),
  CHECK (macd_positive IN (0,1)),
  CHECK (histogram_positive IN (0,1)),
  CHECK (histogram_rising_three IN (0,1)),
  CHECK (rsi_50_to_70 IN (0,1)),
  CHECK (relative_volume_above_one IN (0,1)),
  CHECK ((technical_score IS NULL AND (macd_positive IS NULL OR histogram_positive IS NULL OR histogram_rising_three IS NULL OR rsi_50_to_70 IS NULL OR relative_volume_above_one IS NULL)) OR (technical_score IS NOT NULL AND macd_positive IS NOT NULL AND histogram_positive IS NOT NULL AND histogram_rising_three IS NOT NULL AND rsi_50_to_70 IS NOT NULL AND relative_volume_above_one IS NOT NULL AND technical_score = macd_positive + histogram_positive + histogram_rising_three + rsi_50_to_70 + relative_volume_above_one)),
  KEY (run_id, signal_date)
) ENGINE=InnoDB;

CREATE TABLE `simulated_trade` (
  `run_id` BIGINT UNSIGNED NOT NULL,
  `security_id` BIGINT UNSIGNED NOT NULL,
  `signal_date` DATE NOT NULL,
  `entry_date` DATE NOT NULL,
  `exit_date` DATE NOT NULL,
  `holding_sessions` INT UNSIGNED NOT NULL,
  `entry_price` DOUBLE NOT NULL,
  `exit_price` DOUBLE NOT NULL,
  `gross_return_pct` DOUBLE NOT NULL,
  `round_trip_cost_pct` DOUBLE NOT NULL,
  `net_return_pct` DOUBLE NOT NULL,
  PRIMARY KEY (run_id, security_id, signal_date),
  FOREIGN KEY (run_id, security_id, signal_date) REFERENCES `historical_signal` (run_id, security_id, signal_date),
  FOREIGN KEY (run_id, entry_date) REFERENCES `trading_session` (run_id, session_date),
  FOREIGN KEY (run_id, exit_date) REFERENCES `trading_session` (run_id, session_date),
  CHECK (entry_date > signal_date AND exit_date >= entry_date AND holding_sessions > 0),
  CHECK (entry_price > 0 AND exit_price > 0 AND round_trip_cost_pct BETWEEN 0 AND 100),
  KEY (run_id, exit_date)
) ENGINE=InnoDB;

CREATE TABLE `performance_summary` (
  `run_id` BIGINT UNSIGNED NOT NULL,
  `score_group` ENUM('ALL','0','1','2','3','4','5','NA') NOT NULL,
  `signal_count` INT UNSIGNED NULL,
  `total_trades` INT UNSIGNED NOT NULL,
  `winning_trades` INT UNSIGNED NOT NULL,
  `losing_trades` INT UNSIGNED NOT NULL,
  `breakeven_trades` INT UNSIGNED NOT NULL,
  `win_rate_pct` DOUBLE NULL,
  `average_gross_return_pct` DOUBLE NULL,
  `average_net_return_pct` DOUBLE NULL,
  `average_winning_return_pct` DOUBLE NULL,
  `average_losing_return_pct` DOUBLE NULL,
  `expectancy_pct` DOUBLE NULL,
  `profit_factor` DOUBLE NULL,
  `best_trade_pct` DOUBLE NULL,
  `worst_trade_pct` DOUBLE NULL,
  `average_transaction_cost_pct` DOUBLE NULL,
  `profit_factor_state` ENUM('FINITE','INFINITE','UNDEFINED') NOT NULL,
  PRIMARY KEY (run_id, score_group),
  FOREIGN KEY (run_id) REFERENCES `backtest_run` (run_id),
  CHECK (total_trades = winning_trades + losing_trades + breakeven_trades),
  CHECK ((profit_factor_state = 'FINITE' AND profit_factor IS NOT NULL AND profit_factor >= 0) OR (profit_factor_state <> 'FINITE' AND profit_factor IS NULL))
) ENGINE=InnoDB;

CREATE TABLE `research_report` (
  `report_id` BIGINT UNSIGNED AUTO_INCREMENT NOT NULL,
  `run_id` BIGINT UNSIGNED NOT NULL,
  `report_kind` VARCHAR(64) NOT NULL,
  `generated_utc` DATETIME(6) NOT NULL,
  `filename` VARCHAR(255) NOT NULL,
  `sha256` CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  `payload` LONGBLOB NOT NULL,
  PRIMARY KEY (report_id),
  FOREIGN KEY (run_id) REFERENCES `research_run` (run_id),
  KEY (run_id, generated_utc)
) ENGINE=InnoDB;

