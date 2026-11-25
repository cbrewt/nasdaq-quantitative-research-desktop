# DBD-001 | MySQL database design — review proposal

Nasdaq Quantitative Research V2.0 Desktop • Milestone 03 • 2026-11-25

**Status: PROPOSED. Do not execute the SQL or verifier yet.** DEV-002 is approved; the schema itself is not. This package consolidates design and review into one deliverable. No server or local project files were modified.

## Decisions for approval

1. Dedicated database `nasdaq_quant_research_v2`, InnoDB, utf8mb4, MySQL 8.0.16 or later with enforced CHECK constraints. Server version, actual host/port, privileges and settings must be verified locally before installation. The earlier MySQL client version alone is not server evidence.
2. Common `research_run` identity (surrogate BIGINT plus UUID), scan and backtest subtype tables. Retain legacy scan_id independently of market date. A standalone configured backtest may have no originating scan. Integrated backtests must link to the originating scan and inherit its mode/settings under the current engine rules.
3. Internal security identity plus run-specific symbol/name/provider mapping. Do not infer identity continuity from a ticker alone. Reuse an identity only with defensible evidence; otherwise assign a separate identity. Search history by observed ticker without claiming continuity. No external security master dependency.
4. Preserve the actual relevant provider inputs, including the complete security universe, reference calendar, historical warmup, rejected candidates' inputs, split history and observed acquisition failures. Store versioned lossless input artifacts in MySQL LONGBLOB columns with SHA-256, alongside queryable normalized observations. Capture both pre-validation and engine-boundary data where necessary; keep invalid/duplicate/unsorted observations in artifacts rather than forcing them into a clean relational series. No pickle or executable deserialization. A proposed serialization approach is UTF-8 JSON with explicit dtype/index/timezone/order metadata and tagged IEEE-754 float values (hex or exact binary representation), distinct missing kinds and integer values. Round-trip tests must confirm exact engine input semantics; this codec is not implemented here. Split large captures into ordered bounded chunks with per-chunk and manifest digests; record request and chunk information in request_json. Verify provider licensing/retention terms before retaining live provider data; no redistribution implied.
5. Preserve existing Python floating-point calculations with DOUBLE (rather than rounding prices or indicators to fixed decimal scales). Store unavailable values as NULL, preserve condition flags as nullable 0/1, and represent profit-factor infinity explicitly. Use UTC DATETIME(6) for execution times, DATE for trading sessions, and preserve source timezone and adjustment settings in capture metadata. SQL is not a second quantitative engine.
6. Persist reports as exact bytes with digest and run linkage; integrated reports link to backtest run whose source_scan_run_id identifies screening run. Files can be exported to an approved report directory. No portfolio/trading execution features.

## Table groups and normalization

- Run identity: research_run, screening_run, backtest_run. One run may have one matching subtype; one scan may have many backtests. Subtype exclusivity, source scan completion and mode consistency are application transaction invariants.
- Research inputs: security, run_security, input_artifact, trading_session, daily_observation. Each run has many securities; each security can participate in many runs. The composite run/security key prevents cross-run result associations. Input artifacts may be run-wide (security_id NULL) or security-specific. Observations are keyed by run/security/series/date, not globally by ticker/date, so later data revisions cannot overwrite prior research. Display and engine input series are separate; the calendar can include fewer dates than the indicator warmup data, so daily_observation deliberately does not reference trading_session.
- Results: screening_result, historical_signal, simulated_trade, performance_summary. A candidate has one summary per run/security; a historical signal has at most one completed trade, enforced by the shared composite primary key. Stats are keyed by backtest run and score group (ALL, 0–5, NA). Unavailable score is not zero. Empty score groups can have counts of zero and null statistics; no synthetic losing trades.
- Administration: schema_migration and research_report. Migration ledger records version, UTC and script digest. Reports belong to a specific run.

Each relation has an explicit primary key and dependent facts describe that key. Repeated research settings and summary values are deliberate immutable execution snapshots, not independently editable security or global parameter properties. Derived rows are materialized research outputs for audit and query efficiency; repository must validate their consistency with source snapshots. No comma-separated lists of securities, polymorphic foreign keys, or EAV indicator model. The schema is a proposed normalized relational core with controlled historical snapshots and opaque input artifacts, not a claim of formally proven BCNF for all domain rules. See DATA_DICTIONARY.md for every field, PK, FK, check and explicit index; ERD.svg shows parent-to-child FK paths. Default FK behavior is RESTRICT/NO ACTION. FK-supporting indexes are created by MySQL where needed. Additional explicit indexes support run history, ticker searches, ranking and trade date queries. Verify plans using EXPLAIN with representative volumes in later QA.

## Source mapping and required adaptations

Based on the validated source ZIP (SHA-256 71ec91441fe26f35e34534b5e758c01a4b8aacf2e75938aa156a4f78ef457909) and Milestone 02 DIC/QPC/ARCH documents. Source checksum and ZIP integrity independently checked in this session.

| Existing source structure | Proposed destination |
|---|---|
| Security, Match, ScanResult in primary screener | security, run_security, screening_result, daily_observation, screening_run |
| ScreenerHandoff and ScreenerSettings/BacktestSettings in screener_handoff.py | screening_run, backtest_run, input_artifact (exact JSON v1) |
| HistoricalSignal, ScoredSignal, TechnicalScore | historical_signal and screening_result (five nullable flags) |
| SimulatedTrade, MultipleTradeResult | simulated_trade, backtest_run accounting |
| PerformanceStatistics, ScorePerformance | performance_summary |
| ScoredBacktestResult, MultiStockBacktestResult | backtest_run, run_security, historical_signal, performance_summary |
| Existing Word report modules | research_report |

Source scan() exposes aggregate exclusions, not all individual rejection reasons. UNKNOWN is required until capture instrumentation exists; never infer missing dispositions. Strict backtest public result does not expose all historical signals; capture them at generation without changing rules. Preserve exact raw market inputs separately from validated rows. Legacy JSON importer accepts some identifiers longer than proposed indexed strings: keep exact payload and reject/explicitly handle unsupported persistence lengths rather than truncate; generated local IDs are short. Standalone CLI remains preserved. Strict historical score may be not computed, distinct by mode; do not fabricate it. The persistence adapter, not this DDL, must enforce these semantics.

## Transaction and integrity boundaries

Persist a run and its complete inputs/results in an explicit InnoDB transaction, or stage a RUNNING record and finalize all children and COMPLETED state atomically. Failed/cancelled runs can record the parent status without falsely completed subtype data. Reject incomplete inputs when claiming reproducibility. Secondary operations (backtest, report) use separate transactions; primary screening remains available if they fail. Never mark a failed save as saved. Cross-row and cross-table invariants (mode, subtype, date ordering, calendar adjacency, holding period, nonoverlap, count reconciliation, score flags versus actual indicators, report/run identity, immutable completed inputs, digest matching) must be verified by the repository and tests; CHECK constraints alone do not enforce them. Application uses strict SQL mode, UTC connection settings, parameterized SQL and explicit rollback. DDL is not transactional across statements; do not rely on rollback for schema creation.

## Security, migrations and recovery

- Local server access only by default; use dedicated application account restricted to localhost/appropriate loopback host. Provision using separate administrator account; no password in script, Git, command-line argument or logs. Prompt for password or use an approved OS-backed credential strategy; choose during implementation. App account receives only required SELECT, INSERT and narrowly scoped UPDATE grants; no CREATE/DROP/ALTER/GRANT, no DELETE by default. Migration and backup accounts separate as necessary. Do not grant global privileges. Verify grants using SHOW GRANTS and negative tests.
- Apply numbered migration 001 only to a newly created dedicated database, using a reviewed installer that refuses any existing database (including partial creation), uses no --force and stops on errors. Do not run the proposed SQL directly at this stage. Record migration version and script SHA-256 after complete DDL and structural validation. Subsequent migrations require a verified backup and controlled forward changes. If a creation fails, inspect the partial schema; never automatically drop an existing database. No unrelated database touched.
- Back up dedicated schema and data with mysqldump (InnoDB consistent snapshot, --single-transaction, --quick, --hex-blob; no concurrent DDL). Keep backup outside source, restricted access, digest and retention schedule. Restore to a separately named test database, not production or unrelated schemas. Verify table/row counts, artifact/report digests and deterministic replay. Recommend daily backups on research days and before migrations, with 7 daily and 4 weekly copies as a proposed starting policy; adjust after measuring database growth and checking data retention rights. No scheduled automation created.
- MySQL packet and disk limits need validation with realistic captures; use bounded chunks and measure storage before retention is finalized. No new library is requested.

## Verification plan and acceptance gate

The enclosed SQL, data dictionary and FK diagram were generated from one schema definition. Static checks verified PK/FK column presence, referenced primary keys and matching FK types; Python verifier compiles. No MySQL server execution or connectivity is claimed. The read-only verifier checks table/column/PK inventories and FK counts after installation; it is not a full constraint test. During Phase 2, provide a consolidated installer and test harness covering exact FK/index/check metadata and enforced rejection of invalid inputs, duplicate identifiers, orphan references, cross-run trade links, invalid scores, invalid date/cost, missing versus zero and infinity, zero qualifying results, rollback, separate report/backtest failure, permissions, migration ledger and backup/restore. Use isolated test schema/transaction fixtures; never use production research data. Quantitative replay and actual persistence integration remain scheduled for Milestones 6/10/11. Document actual outcomes before Milestone 03 acceptance.

## References

- Validated Python archive and approved Milestone 02 documents, including DIC-001, QPC-001, ARCH-001, ADR-015 through ADR-025.
- MySQL 8.0 manual: https://dev.mysql.com/doc/refman/8.0/en/create-table-foreign-keys.html ; https://dev.mysql.com/doc/refman/8.0/en/create-table.html ; https://dev.mysql.com/doc/refman/8.0/en/implicit-commit.html

## Approval

Review this proposal, ERD.svg, DATA_DICTIONARY.md and 001_schema_proposed.sql. Approval authorizes preparation of Phase 2 only within this database design milestone and explicitly approved schema. DEV-002 will be documented alongside the design. No database deployment, credentials or new dependencies are required during review. Milestone 04 remains unauthorized until separate acceptance and authorization.
