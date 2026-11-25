# Nasdaq Quantitative Research V2.0

## Architectural Decision Record

Established: November 24, 2026

## Purpose

Maintain a permanent, version-controlled record of
significant architectural, technical, and project
governance decisions.

Each significant decision shall document its rationale,
approval status, and relevant technical consequences.

## ADR-001 - Application Version Designation

Status: APPROVED

Decision:
Designate the desktop application as Version 2.0.

Rationale:
Distinguish desktop development from the completed
Version 1.2 command-line application.

## ADR-002 - Version 1.2 Baseline Protection

Status: APPROVED

Decision:
Treat Version 1.2 as an immutable baseline.

Rationale:
Preserve a completed, tested, and accepted
quantitative research application.

Consequences:
Original source files and verified backup archives
must not be modified, overwritten, or deleted.

Baseline archive:
Nasdaq_Quant_Research_V1_2_Final.zip

SHA-256:
f0d8cfd042d2374ef64370ec6aff495bcf3123d8ab28d015d80e62b16a0a15b4

## ADR-003 - Operating System

Status: APPROVED

Decision:
Use Windows 11 Pro as the target operating system.

Rationale:
Align development and deployment with the user's
existing desktop environment.

## ADR-004 - Programming Language

Status: APPROVED

Decision:
Use Python for application development.

Initial development version: Python 3.14.2

Rationale:
Preserve compatibility with the existing research
engine and minimize unnecessary code conversion.

## ADR-005 - Desktop Framework

Status: APPROVED

Decision:
Use PySide6 (Qt) for the desktop presentation layer.

Initial package version: 6.12.0

Rationale:
Provide professional desktop widgets, model-based
tables, event processing, and extensible interfaces.

Verification:
Basic graphical execution successfully tested.

## ADR-006 - Research Database

Status: APPROVED

Decision:
Use MySQL as the local research database.

Rationale:
Provide relational data integrity, structured research
history, and compatibility with existing expertise.

Consequences:
A dedicated database and restricted application
account shall be established.

Database schema approval is required before
implementation.

Database connectivity remains pending verification.

## ADR-007 - Database Connectivity

Status: APPROVED

Decision:
Use MySQL Connector/Python.

Initial package version: 26.10.0

Rationale:
Provide Python-to-MySQL database connectivity.

Verification:
Package installation and import verified.
Server connectivity remains unverified.

## ADR-008 - Development Environment

Status: APPROVED

Decision:
Use Visual Studio Code as the development environment.

Rationale:
Maintain compatibility with the existing development
workflow and Python tooling.

## ADR-009 - Version Control

Status: APPROVED

Decision:
Use Git for independent Version 2.0 version control.

Implementation:
Local repository with main as the initial branch.

No remote repository has been configured.

## ADR-010 - Development Directory Isolation

Status: IMPLEMENTED

Decision:
Establish Version 2.0 in a separate local directory
outside the existing OneDrive project directory.

Directory:
C:\Users\wrpur\Projects\Nasdaq_Quant_Research_Desktop

Rationale:
Protect Version 1.2 and reduce synchronization risks
associated with development environments.

## ADR-011 - Python Environment Isolation

Status: IMPLEMENTED

Decision:
Use a dedicated Python virtual environment (.venv).

Rationale:
Prevent Version 2.0 dependency installation from
interfering with the global Python environment
or existing applications.

Verification:
Virtual environment isolation confirmed.

## ADR-012 - Dependency Version Management

Status: IMPLEMENTED

Decision:
Pin the seven approved direct dependency versions.

Maintain requirements.txt and requirements-lock.txt.

Rationale:
Improve reproducibility and reduce dependency-related
regression risks.

Limitation:
Matching direct dependency versions does not establish
complete quantitative equivalence with Version 1.2.

Regression testing remains required.

## ADR-013 - Fixed Development Roadmap

Status: APPROVED

Decision:
Follow the approved twelve-step development roadmap.

Rationale:
Maintain controlled scope, measurable acceptance
criteria, and a definitive project endpoint.

Consequences:
User authorization is required before advancing to
the next major development milestone.

Step 12 constitutes the definitive project endpoint.

## ADR-014 - Quantitative Research Integrity

Status: APPROVED

Decision:
Preserve existing screening, scoring, and historical
simulation methodologies.

Rationale:
Maintain the integrity of the original quantitative
research application.

Consequences:
Methodology changes require explicit user approval.

Equivalent results must be verified using identical
inputs and market data.

## Pending Architectural Decisions

- Detailed application module architecture.
- Research engine integration interfaces.
- MySQL database schema.
- Database credential storage implementation.
- Database migration procedures.
- Desktop interface layouts.
- Background processing implementation.
- Technical chart implementation.
- Windows application packaging.

These decisions require review and approval during
their respective development milestones.

## Decision Record Governance

New architectural decisions shall be documented using
sequential ADR identifiers.

Previous decisions shall be retained for historical
traceability. Superseded decisions shall be identified
rather than silently removed.

No unapproved dependency, feature, or quantitative
methodology change shall be introduced.
## ADR-015 - Validated Integration Baseline Selection

Date: November 24, 2026

Status: APPROVED AND VALIDATED

Context:

Final baseline protection verification identified
three Python source files that differed from their
counterparts in the original Version 1.2 archive.

Of the 29 Python source files examined, 26 were
byte-identical. No files were missing or additional.

The three differences were investigated individually.

Identified differences:

1. Backtesting_Engine/integrated_report.py

   Added repeating Word table column headings
   for multipage reports.

2. Backtesting_Engine/scored_integrated_report.py

   Added a page break before the Limitations
   and Interpretation section.

3. tests/Step7_Integration_Tests.py

   Added an eighteenth integration test verifying
   the repeating Word table header property.

No quantitative methodology changes were identified
in the reviewed source differences.

Decision:

Preserve the original Version 1.2 archive and the
enhanced working source revision.

Adopt the separately validated source revision as
the Version 2.0 quantitative research integration
baseline.

Original protected archive:

Nasdaq_Quant_Research_V1_2_Final.zip

SHA-256:
f0d8cfd042d2374ef64370ec6aff495bcf3123d8ab28d015d80e62b16a0a15b4

Validated integration baseline archive:

Nasdaq_Quant_Research_V1_2_Validated_Source.zip

SHA-256:
71ec91441fe26f35e34534b5e758c01a4b8aacf2e75938aa156a4f78ef457909

Archive size: 83543 bytes
Python source files: 29

Verification evidence:

- All 29 source files copied to an isolated workspace.
- All 29 individual source checksums verified.
- Step 6 offline regression tests: 16 of 16 passed.
- Step 7 offline integration tests: 18 of 18 passed.
- Combined automated tests: 34 of 34 passed.
- Reported test failures and errors: zero.
- Validated ZIP archive integrity: passed.
- Validated archive source inventory: passed.
- Original archive checksum preservation: passed.

Test environment:

Python 3.14.2
Version 2.0 isolated virtual environment.

Rationale:

Preserve legitimate report presentation enhancements
while maintaining an immutable original backup and
a reproducible source integration baseline.

Consequences:

Both archives shall remain protected and unchanged.

Version 2.0 integration shall use a separate working
copy of the validated source archive.

Neither protected Version 1.2 source state shall
be modified during Version 2.0 development.

Limitations:

The date on which the three source changes were
originally introduced has not been established.

The successful offline tests do not independently
establish comprehensive quantitative equivalence,
live market data functionality, or MySQL connectivity.

These matters remain subject to the approved
Version 2.0 development roadmap.

The validated archive contains Python source files
only and does not replace the original comprehensive
Version 1.2 backup.

Relationship to previous decisions:

ADR-002 remains in force.

ADR-015 supplements the original baseline protection
decision without superseding its requirements.


## ADR-016 - Modular Layered Monolithic Architecture

Date: November 25, 2026

Status: APPROVED
Implementation: PENDING

Decision:

Adopt a modular, layered monolithic architecture
consisting of presentation, application,
quantitative domain and infrastructure layers.

Rationale:

Separate responsibilities while minimizing
unnecessary implementation complexity.

Consequences:

Presentation shall not implement quantitative
formulas or SQL queries.

The quantitative domain shall remain independent
of presentation and infrastructure implementations.

Reference: ARCH-001.


## ADR-017 - Python Source Package Organization

Date: November 25, 2026

Status: APPROVED
Implementation: PENDING

Decision:

Adopt a src-based Python package structure using
nasdaq_research as the primary application package.

Maintain separate source, test, documentation
and database migration directories.

Rationale:

Improve maintainability, import organization
and independent component testing.

Consequences:

Establish an explicit application launch and
import-resolution strategy without introducing
unapproved dependencies.

Create application modules incrementally within
their authorized development milestones.

References: ARCH-001 and AQ-001.


## ADR-018 - Quantitative Engine Preservation

Date: November 25, 2026

Status: APPROVED
Implementation: PENDING

Decision:

Reuse the validated Version 1.2 research engine
through controlled adaptation rather than rewriting
established quantitative methodologies.

Adopt all sixteen QPC-001 preservation requirements.

Rationale:

Protect mathematical integrity and maintain
consistent quantitative research behavior.

Consequences:

Preserve existing indicator calculations,
screening rules, technical scoring, simulation
and statistical performance methodologies.

Compare Version 1.2 and Version 2.0 using
identical deterministic market data.

Quantitative methodology changes require
explicit user approval.

References: ADR-015, ARCH-001 and QPC-001.


## ADR-019 - Shared Application Services

Date: November 25, 2026

Status: APPROVED
Implementation: PENDING

Decision:

Establish shared application services accessible
to both graphical and command-line interfaces.

Rationale:

Avoid duplicate research implementations and
preserve command-line functionality.

Consequences:

Application services shall coordinate screening,
historical simulation, research history and
report generation.

Presentation components shall interact with
research services through defined interfaces.

Reference: ARCH-001.


## ADR-020 - External Provider Interfaces

Date: November 25, 2026

Status: APPROVED
Implementation: PENDING

Decision:

Separate external market data and security
directory acquisition from quantitative
calculations through defined provider interfaces.

Rationale:

Improve component testability and isolate
external service dependencies.

Consequences:

Preserve existing market data acquisition,
validation and exclusion behavior.

Support deterministic test data substitution.

Do not silently change market data sources
or quantitative methodology.

References: ARCH-001, QPC-001 and DIC-001.


## ADR-021 - MySQL Repository Architecture

Date: November 25, 2026

Status: APPROVED
Implementation: PENDING

Decision:

Use the Repository Pattern with explicit,
parameterized SQL and MySQL Connector/Python.

Do not introduce an ORM framework.

Rationale:

Provide direct control over relational integrity,
SQL execution, database transactions and indexes.

Consequences:

Database access shall remain within
the infrastructure layer.

Use a dedicated research database, restricted
database privileges, external credential storage
and version-controlled schema migrations.

Physical database schema approval remains
a separate requirement of Milestone 03.

References: ARCH-001 and DIC-001.


## ADR-022 - Qt Background Processing

Date: November 25, 2026

Status: APPROVED
Implementation: PENDING

Decision:

Use PySide6 QObject workers, QThread and Qt
signals for long-running research operations.

Rationale:

Maintain graphical interface responsiveness
during screening and historical analysis.

Consequences:

Use cooperative cancellation and thread-safe
communication between workers and the GUI.

Cancellation must remain accessible while
a worker is busy.

A queued Qt cancellation signal alone may
be insufficient.

Do not forcibly terminate active research threads.

References: ARCH-001 and AQ-002.


## ADR-023 - Research Identity and Reproducibility

Date: November 25, 2026

Status: APPROVED
Implementation: PENDING

Decision:

Preserve unique research-run identities,
research parameters, relevant original source
inputs and quantitative engine revisions.

Adopt all twelve DIC-001 requirements.

Rationale:

Support research traceability, data integrity
and historical reproducibility.

Consequences:

Distinguish execution timestamps from
completed trading dates.

Associate research results, historical signals,
simulated trades and reports with their
originating research executions.

Preserve the actual relevant calculation inputs,
not merely provider names, dates and parameters.

Physical storage and retention requirements
remain subject to database design review.

References: ARCH-001, DIC-001 and AQ-003.


## ADR-024 - Centralized Configuration and Paths

Date: November 25, 2026

Status: APPROVED
Implementation: PENDING

Decision:

Centralize application configuration and
operational path management.

Rationale:

Reduce filesystem coupling and protect
credentials and operational data.

Consequences:

Separate generated research files, reports,
configuration and credentials from source code.

Database credentials shall not be committed
to Git or embedded within application source.

Protected Version 1.2 archives shall remain
outside the active development directory.

Reference: ARCH-001.


## ADR-025 - Failure Isolation and Testing

Date: November 25, 2026

Status: APPROVED
Implementation: PENDING

Decision:

Preserve successful primary research results
when secondary workflow operations fail.

Require systematic automated verification
throughout the approved development roadmap.

Rationale:

Protect research integrity and prevent
secondary failures from discarding valid results.

Consequences:

Report database persistence and report-generation
failures accurately.

Represent cancellation explicitly.

Preserve the existing thirty-four offline tests
and extend coverage through unit, integration,
regression, database, GUI, security, performance,
backup and deployment testing.

Comprehensive quantitative equivalence requires
separate implementation verification.

References: ARCH-001, QPC-001 and DIC-001.
