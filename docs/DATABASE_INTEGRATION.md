# Milestone 10 — screening persistence checkpoint

Uses existing restricted account, parameterized transactional inserts, session-only password and background DB operations. Saves qualified screening outputs and display observations; does not capture raw provider inputs, rejected universe, historical simulations or report payloads yet. Not a replayable snapshot. Milestone 10 not complete.

## Historical persistence checkpoint
Research Mode historical signals, completed trades, aggregate and score-group statistics and Word report payloads are stored transactionally. Noncompleted signal disposition remains UNKNOWN; aggregate skip counts preserved. Strict-mode complete signals and raw inputs remain outstanding. Reports retained locally on failure.

### Report responsiveness correction
Standalone report generation uses a Qt worker; report saving remains on the database worker. Both workspaces show save status. Selected-run simulation retrieval also displays the standalone screening report count. Historical pre-export still uses the GUI thread; Windows responsiveness and populated-data recovery require verification.

### Historical report background processing and duplicate guard
Historical pre-export now runs in the historical worker. Report storage retains the first stored report for each run and kind; subsequent local exports remain on disk. Existing report records are not removed. Cooperating writers use a connection-scoped MySQL named lock and READ COMMITTED transactions. Strict-mode complete signals and original input capture remain outstanding; no existing run is replayable.
