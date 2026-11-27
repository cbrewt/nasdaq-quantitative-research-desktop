# V2.0 release notes and QA record

November 27, 2026 | Release acceptance pending | Source branding commit 868afe5

## Delivered functionality

Windows 11 Pro desktop application with six workspaces; original V1.2 engine preserved inside `infrastructure/validated_v12`; Research and Strict modes; sortable/filterable results; six technical charts; background screening with cooperative cancellation; historical simulation and Word reporting; MySQL research history and input capture. CAL-001 intentionally extends calendar handling for verified pre-listing absence only. Migration 001 remains unchanged.

## Verification evidence

| Check | Result |
|---|---|
| Automated QA | 53 tests in nine suites, all passed; 28.184 s |
| Baseline protection | Both protected archives unchanged; 28 active Python sources matched after line-ending normalization |
| Research Mode runs 13/14 | 297 chunks, 79 matches, 7,910 signals, 2,026 trades; offline replay passed |
| Strict Mode runs 15/16 | 94 chunks, six matches, 32 signals, 17 trades; offline replay passed |
| Independent baseline comparison | Strict screening passed; controlled historical comparison passed for four common-calendar stocks |
| Populated recovery | 14 table checksums matched; 19 foreign keys zero orphans |
| Security | Effective dedicated account; SELECT and authorized UPDATE planning allowed; protected UPDATE, DELETE and migration INSERT denied |
| Windows | Six charts visually verified; shortcut startup, database connection and history retrieval passed; final branding verified |

QA revision 875bd60; subsequent branding-only commit 868afe5 passed syntax and Windows visual checks. Step 10 and Step 11 accepted November 27. Step 12 formal acceptance and final backup evidence remain pending.

## Known limitations and test boundaries

- STAK and LSE historical baseline comparison is blocked by original calendar policy; both passed V2 offline replay. Controlled equivalence does not prove universal equivalence. Earlier runs lacking complete inputs are not replayable. Capture stores engine-boundary provider values, not raw Yahoo HTTP traffic. The UI banner does not certify individual replay.
- Current candidate selection and survivorship bias, no point-in-time Nasdaq universe, possible historical data revisions or incomplete corporate actions, indicator warmup and simplified costs; no portfolio capital model or predictive guarantee.
- Historical cancellation and saved-history chart reconstruction are not implemented. Screening cancellation is cooperative. Local report paths may require horizontal scrolling; older duplicate report records were retained.
- Observed performance accepted; no formal live workload benchmark. Qt offscreen font directory warning did not affect observed Windows rendering. The earlier installer dependency-preload workaround has unresolved root cause.
- Milestone 11 DDL restrictions verified via grants; active invalid-write constraint tests not repeated on populated production data (initial Milestone 3 synthetic rejection tests passed). Backup comparison covered table inventory and extended checksums, not an exhaustive schema/object comparison at this stage.
- Local deployment depends on existing Python environment and MySQL service; no redistributable installer. Final backups must be kept outside Git.

Historical design and checkpoint documents retain their original context; this release record supersedes their earlier pending implementation statuses, not approved quantitative or architectural requirements.
