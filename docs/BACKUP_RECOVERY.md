# Backup and recovery — V2.0

November 27, 2026 | Local Windows deployment

## Preserve the baseline

Never overwrite the original V1.2 source or its final and validated source ZIP archives. Keep V2 backups separately, outside Git. The application account is not an administrator. Store SQL dumps and reports securely; they contain research data. Do not upload credentials or SQL dumps unnecessarily.

## Source backup

Close the desktop application and ensure `git status --short` is empty. Create a new timestamped directory outside the repository. Use `git archive --format=zip --output=<absolute path> HEAD` to capture tracked files, and `git bundle create <absolute path> --all` to preserve Git history. Verify ZIP integrity (Python `zipfile.testzip()`), bundle (`git bundle verify`), and SHA-256 (`Get-FileHash`). Keep requirements files; the virtual environment is not included. Back up local reports, verification utilities and evidence separately after reviewing them for credentials. A Git archive alone is not a full operational backup.

## Database backup

Use matching MySQL 8.0 utilities in `C:\Program Files\MySQL\MySQL Server 8.0\bin`. Close the app and avoid concurrent writers/DDL. In PowerShell, set `$bin` to that directory and `$backupFile` to a fresh absolute SQL filename outside Git:

```powershell
& "$bin\mysqldump.exe" --host=127.0.0.1 --port=3306 --user=root --password --single-transaction --no-tablespaces --set-gtid-purged=OFF --routines --triggers --events --result-file="$backupFile" nasdaq_quant_research_v2
if ($LASTEXITCODE -ne 0) { throw "Backup failed" }
Get-Item -LiteralPath $backupFile
Get-FileHash -LiteralPath $backupFile -Algorithm SHA256
```

Confirm a nonempty file and retain the hash separately. Password is entered at the prompt, never on the command line. The dump does not preserve MySQL accounts/grants; preserve approved DBD-001 account setup and grant inventory separately (without secrets).

## Isolated recovery

Use a fresh unique `nasdaq_recovery_test_YYYYMMDD_HHMMSS` schema, never the production schema. Verify the backup hash. With administrator privileges, create the new schema with utf8mb4 and restore using the mysql client `SOURCE` command (forward slashes in the absolute filename), selecting only the isolated schema. Check exit status and review errors. Before relying on a dump, inspect for database-selection or cross-schema statements; do not restore untrusted SQL. Compare original and recovered table inventories, definitions, constraints and row counts/checksums while source is quiescent. Use `CHECKSUM TABLE source.table, recovery.table EXTENDED` for every table; NULL or differing checksums fail the test. Check foreign keys for orphan rows, including composite keys. Never point the production application to a recovery schema or delete original research to test restoration.

## Verified evidence and remaining release work

Milestone 3 initial schema recovery and synthetic constraint rejection passed. Milestone 11 populated backup and isolated restoration passed: 14 matching extended table checksums; 19 source foreign keys had zero orphan rows. Application account grants and non-mutating DML permission probes passed. Retain the recovery database and backup. The final release backup must be refreshed after later runs (17 and 18), then checked independently; final backup filenames and hashes have not yet been supplied. Do not mark release closure until evidence is recorded and user acceptance received.

## Rebuild and troubleshooting

Restore source into a separate directory, provision Python 3.14.2 and an isolated `.venv`, install approved requirements from the lock inventory, validate dependencies and tests; never overwrite the protected V1.2 baseline. Restore MySQL using the approved schema/account configuration and verified backup. Recreate the Windows shortcut using `.venv\Scripts\pythonw.exe`, argument `launch_desktop.py` (absolute path, quoted), and project root as working directory. Test startup and history retrieval before use. Full environment recreation on a new machine has not been verified in this project.
