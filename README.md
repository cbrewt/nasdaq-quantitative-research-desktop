# Nasdaq Quantitative Research V2.0

## Desktop Edition

### Project Status

- Version: 2.0
- Status: Release acceptance pending
- Development commencement: November 24, 2026
- Development milestone: Step 12 of 12 (11 formally accepted)

## Project Objective

Develop a professional Windows desktop application for the
Nasdaq Quantitative Research Version 1.2 stock screener
while preserving the integrity of the existing quantitative
research engine.

## Approved Technology Stack

| Component | Technology |
|---|---|
| Operating System | Windows 11 Pro (64-bit) |
| Programming Language | Python 3.14.2 |
| Desktop Framework | PySide6 6.12.0 |
| Research Database | MySQL |
| Database Connector | MySQL Connector/Python 26.10.0 |
| Development Environment | Visual Studio Code |
| Version Control | Git |

## Baseline Protection

Version 1.2 is a completed and protected application.

The original Version 1.2 source files and verified backup
archives must never be modified, overwritten, or deleted
during Version 2.0 development.

All desktop application development shall occur within
this independent project directory.

## Quantitative Research Integrity

- Preserve existing screening criteria.
- Preserve the five-point technical scoring methodology.
- Preserve existing historical simulation methodologies.
- Prevent look-ahead bias.
- Maintain transparent and reproducible calculations.
- Verify equivalent results against Version 1.2.
- Require explicit approval for methodology changes.

## Architectural Principles

- Modular application architecture.
- Separation of presentation and research logic.
- Independent database access layer.
- Secure database credential management.
- Input validation and exception handling.
- Background processing for long-running operations.
- Automated testing and regression verification.

## Dependency Management

The Python virtual environment is stored in .venv.

Direct application dependencies are documented in
requirements.txt.

The installed application dependency inventory is
documented in requirements-lock.txt.

## Development Methodology

Development follows a fixed twelve-step roadmap.

Each development milestone requires measurable acceptance
criteria, supporting verification evidence, and user
authorization before advancing to the next major step.

Step 12 constitutes the definitive project endpoint.

## Project Documentation

- README.md
- ROADMAP.md
- DECISIONS.md

## Current Development Status

As of November 27, 2026: Milestones 1–11 formally accepted. Windows desktop deployment and release branding verified. Final documentation, source/database backups and formal Step 12 acceptance remain pending. See [release notes](docs/RELEASE_NOTES.md) for verification scope and limitations. Earlier design/checkpoint documents are historical records, not current status.

## Launch and operate

Double-click the Windows desktop shortcut **Nasdaq Quantitative Research V2.0** or run from the project root in PowerShell:

```powershell
.\.venv\Scripts\python.exe .\launch_desktop.py
```

In Settings, connect to the dedicated local MySQL database with the application account password. See [User guide](docs/USER_GUIDE.md), [Backup and recovery](docs/BACKUP_RECOVERY.md), [Architecture](docs/ARCHITECTURE.md), and [Quantitative contract](docs/QUANTITATIVE_CONTRACT.md).

## Distribution

Local Windows deployment using the existing virtual environment; not a standalone redistributable executable. Keep credentials, local reports, SQL backups and development packages outside Git. Preserve the original V1.2 application independently.
