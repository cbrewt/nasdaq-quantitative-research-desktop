# Milestone 03 — Database implementation and verification

Accepted November 25, 2026. DBD-001 approved; original design proposal retained as historical reference.

Database: `nasdaq_quant_research_v2`; recovery: `nasdaq_quant_research_v2_restore_test`; application account: `nasdaq_research_app@127.0.0.1`.

Migration 001 SHA-256: d1140e86b3419ed7b7c1be2b025f7f18d1a85038310394d2ab7750b49ce03309

Initial backup authentication failed (1045); recovery-only script subsequently passed. No reinstall or database deletion.

Backup filename: `initial_schema_resume_20261125T154900929702Z.sql` (stored outside Git in user home backup directory). SHA-256: `46942f8f4cbb70d125e57aa4d0ec06000610b94526b2361050b7f68fdec178b6`.

Original installation report SHA-256: `38fa5fd0dab249e631417ef8775b4333a3448080bf9df59f1efd4b052d24fb0e`. Recovery report SHA-256: `cbeca0fd306e33c0c6d46dff875b437b7f09675480f92adcb22fd5aac26f0f06`.

## Verification evidence (selected PASS lines from local reports)

```text
PASS: approved SQL inventory and SHA-256
PASS: mysql and mysqldump clients located
PASS: MySQL server supports enforced CHECK constraints: 8.0.44
PASS: both target database names unused
PASS: dedicated account name unused
PASS: nasdaq_quant_research_v2: exact table inventory and InnoDB
PASS: nasdaq_quant_research_v2: columns, PKs, exact FK mappings, explicit indexes and enforced CHECK counts
PASS: empty qualifying scan supported
PASS: rejected duplicate scan_id (1062)
PASS: rejected invalid price range (3819)
PASS: rejected invalid transaction cost (3819)
PASS: rejected invalid evaluation dates (3819)
PASS: rejected orphan security (1452)
PASS: rejected inconsistent score (3819)
PASS: valid zero score preserved
PASS: unavailable score preserved
PASS: rejected cross-run trade link (1452)
PASS: rejected invalid trade dates (3819)
PASS: rejected duplicate completed trade (1062)
PASS: infinity state preserved
PASS: binary input digest round trip
PASS: report byte round trip
PASS: synthetic records rolled back
PASS: migration ledger verified
PASS: application account connection and SELECT
PASS: application INSERT and rollback
PASS: rejected application DELETE (1142)
PASS: rejected application migration modification (1142)
PASS: rejected application DDL (1142)
PASS: original installer, approved schema and prior test evidence verified
PASS: MySQL clients located
PASS: nasdaq_quant_research_v2: exact table inventory and InnoDB
PASS: nasdaq_quant_research_v2: columns, PKs, exact FK mappings, explicit indexes and enforced CHECK counts
PASS: existing migration ledger matches
PASS: restore database name is unused
PASS: initial database contains only migration ledger
PASS: nasdaq_quant_research_v2_restore_test: exact table inventory and InnoDB
PASS: nasdaq_quant_research_v2_restore_test: columns, PKs, exact FK mappings, explicit indexes and enforced CHECK counts
PASS: restored migration ledger identical
PASS: restore row count: schema_migration
PASS: restore table definition: schema_migration
PASS: restore row count: research_run
PASS: restore table definition: research_run
PASS: restore row count: screening_run
PASS: restore table definition: screening_run
PASS: restore row count: backtest_run
PASS: restore table definition: backtest_run
PASS: restore row count: security
PASS: restore table definition: security
PASS: restore row count: run_security
PASS: restore table definition: run_security
PASS: restore row count: input_artifact
PASS: restore table definition: input_artifact
PASS: restore row count: trading_session
PASS: restore table definition: trading_session
PASS: restore row count: daily_observation
PASS: restore table definition: daily_observation
PASS: restore row count: screening_result
PASS: restore table definition: screening_result
PASS: restore row count: historical_signal
PASS: restore table definition: historical_signal
PASS: restore row count: simulated_trade
PASS: restore table definition: simulated_trade
PASS: restore row count: performance_summary
PASS: restore table definition: performance_summary
PASS: restore row count: research_report
PASS: restore table definition: research_report
SUCCESS: DBD-001 BACKUP AND RESTORE VERIFIED
```

## Remaining work

Repository-level cross-table invariants, populated backup/recovery, quantitative replay, storage growth and retention validation remain pending. Restore-test database retained. Installer and recovery utilities and complete logs retained in the local packages directory. No passwords stored in this record.
