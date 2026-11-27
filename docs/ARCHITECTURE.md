# Nasdaq Quantitative Research V2.0

> Historical design/checkpoint record. For current implementation, QA scope and outstanding release gates as of November 27, 2026, see [release notes](RELEASE_NOTES.md). Original requirements and historical evidence below are retained.

## Approved Desktop Application Architecture

Document reference: ARCH-001
Approval date: November 25, 2026
Status: APPROVED
Implementation status: NOT IMPLEMENTED
Development milestone: 02

### 1. Architecture objective

Develop a professional Windows desktop application
while preserving the quantitative integrity of
the validated Version 1.2 research engine.

The application shall employ a modular, layered
monolithic architecture.

Unnecessary frameworks, microservices and distributed
application components shall not be introduced.

### 2. Approved technology stack

- Windows 11 Pro
- Python 3.14.2
- PySide6 6.12.0
- MySQL
- MySQL Connector/Python 26.10.0
- Visual Studio Code
- Git
- pandas 2.3.3
- numpy 2.3.5
- yfinance 1.7.0
- python-docx 1.2.0
- requests 2.32.5

Additional dependencies require user approval.

### 3. Architectural layers

#### Layer 1 - Presentation

Responsibilities:

- Desktop application windows and navigation.
- User input and screening parameter controls.
- Sortable and filterable research results.
- Technical indicator visualization.
- Historical simulation presentation.
- Research history and report management.
- Command-line compatibility.

The presentation layer shall not implement
quantitative research formulas or SQL queries.

#### Layer 2 - Application

Responsibilities:

- Research request validation.
- Screening workflow coordination.
- Historical backtesting coordination.
- Progress and cancellation coordination.
- Research persistence coordination.
- Report generation coordination.
- Workflow-level exception handling.

The application layer shall expose defined interfaces
for presentation and infrastructure components.

#### Layer 3 - Quantitative Domain

Responsibilities:

- Stock qualification rules.
- Technical indicator calculations.
- Five-point technical scoring.
- Liquidity calculations.
- Historical signal generation.
- Trade simulation.
- Statistical performance calculations.

The quantitative domain shall remain independent
of PySide6, MySQL and presentation-layer objects.

Quantitative methodologies shall be preserved
in accordance with QPC-001.

#### Layer 4 - Infrastructure

Responsibilities:

- Nasdaq security directory acquisition.
- Yahoo Finance market data acquisition.
- MySQL database connections and repositories.
- JSON handoff serialization.
- Word report generation.
- Filesystem operations.
- Application logging.

Infrastructure components shall implement
application-owned interface contracts.

### 4. Dependency direction

Presentation depends on application services.

Application services depend on quantitative domain
components and application-owned interfaces.

Infrastructure implements application-owned
interfaces and may use domain data structures.

The quantitative domain shall not depend on
presentation or infrastructure implementations.

Application bootstrap code shall assemble the
required services and infrastructure components.

Circular dependencies shall be avoided.

### 5. Approved target project structure

    Nasdaq_Quant_Research_Desktop/
        .git/
        .venv/
        src/
            nasdaq_research/
                __init__.py
                __main__.py
                bootstrap.py
                presentation/
                cli/
                application/
                domain/
                infrastructure/
                    market_data/
                    database/
                    reporting/
                    serialization/
                config/
        tests/
            unit/
            integration/
            regression/
            fixtures/
        docs/
        migrations/
        .gitignore
        README.md
        ROADMAP.md
        DECISIONS.md
        MILESTONES.md
        requirements.txt
        requirements-lock.txt

This is the approved target organization.

Directories and modules shall be created
incrementally within their scheduled milestones.

Protected baseline archives shall remain outside
the Version 2.0 development directory.

### 6. Application service boundaries

Proposed service responsibilities approved
under the architecture:

- ScreeningService: coordinate stock screening.
- BacktestingService: coordinate historical research.
- ResearchHistoryService: retrieve saved research.
- ReportService: coordinate report generation.

Supporting interface contracts:

- MarketDataProvider
- SecurityDirectoryProvider
- ResearchRepository
- ProgressReporter
- CancellationToken

Python standard-library interfaces, protocols
and data classes may be used.

An additional dependency-injection framework
shall not be introduced.

### 7. Quantitative engine integration

Reuse the validated Version 1.2 research engine
through controlled adaptation rather than rewriting
its established quantitative methodologies.

Preserve existing:

- Shared Analytics calculations.
- Screening qualification rules.
- Historical signal generation.
- Trade simulation.
- Performance statistics.
- JSON handoff compatibility.
- Command-line behavior.

Separate the existing primary screener's
presentation, acquisition and reporting concerns.

The historical backup screener shall remain
preserved but shall not become an active
Version 2.0 component.

The empty research_snapshot.py module shall not
be treated as implemented functionality.

All adaptations shall occur in independent
Version 2.0 working copies.

### 8. Background processing

Use PySide6 QObject workers, QThread and Qt signals
for long-running research operations.

The main GUI thread shall remain responsive.

GUI widgets shall be updated from the GUI thread.

Cancellation shall be cooperative and shall not
forcibly terminate a running research thread.

Operation states:

- Ready
- Running
- Cancelling
- Cancelled
- Completed
- Failed

External network operations may need to finish
or time out before cancellation completes.

Detailed background processing implementation
belongs to Development Milestone 07.

### 9. MySQL persistence architecture

Use the Repository Pattern and explicit
parameterized SQL with MySQL Connector/Python.

Do not introduce an ORM framework.

Database requirements:

- Dedicated research database.
- Dedicated least-privilege application account.
- Credentials stored outside source code and Git.
- Explicit transaction commit and rollback.
- Appropriate relational integrity constraints.
- Numbered, version-controlled schema migrations.
- Database connections confined to their owning
  worker or operation.
- Database backup and recovery procedures.

The physical schema requires separate user approval
during Development Milestone 03.

### 10. Research reproducibility

Preserve the information needed to associate
research results with their original inputs:

- Unique research-run identity.
- Execution timestamp.
- Completed trading date.
- Research parameters.
- Quantitative engine revision.
- Relevant original market data.
- Security universe and reference trading calendar.
- Relevant corporate-action information.
- Source data provenance.
- Research calculations and outputs.
- Associated reports.

Preserving only the displayed twenty-one trading
sessions is insufficient for reproducing indicators
requiring longer warmup histories.

Data requirements are governed by DIC-001.

The physical storage and retention design shall be
reviewed during the database design milestone.

### 11. Configuration and operational paths

Centralize application configuration and path
management.

Separate generated files, reports, operational
configuration and credentials from source code.

Do not commit database credentials or generated
research data to the source repository.

### 12. Failure isolation

Invalid research requests shall be rejected before
execution.

Missing market data shall follow established
quantitative exclusion rules.

A screening run with no qualifying securities
shall remain a valid completed operation.

A secondary workflow failure shall not invalidate
successful primary research results.

Database persistence failures shall be reported
accurately, with available research results
preserved in memory where practical.

Report generation failures shall not discard
successful research results.

Cancellation shall be represented explicitly.

Unexpected exceptions shall be logged and
communicated through meaningful user messages.

### 13. Testing architecture

Preserve the existing thirty-four offline
regression and integration tests.

Extend testing to include:

- Unit testing.
- Application service integration testing.
- Deterministic quantitative regression testing.
- Database integrity testing.
- Graphical interface testing.
- Error-handling verification.
- Performance testing.
- Security verification.
- Database backup and recovery testing.
- Windows deployment verification.

Compare Version 1.2 and Version 2.0 using
identical fixed market data and research settings.

Verify equivalent:

- Qualifying security sets.
- Technical indicator calculations.
- Technical scores and missing-score behavior.
- Liquidity measurements and ranking.
- Historical signal dates.
- Simulated trade dates and returns.
- Statistical performance calculations.

Numerical comparison tolerances shall be
documented and justified.

### 14. Architectural qualifications

The following qualifications were explicitly
included in the user's architecture approval.

AQ-001 - Application launch and imports

The src-based package structure requires an
explicit application launch and import-resolution
strategy without unapproved dependencies.

AQ-002 - Thread-safe cancellation

Cancellation must use a thread-safe mechanism
accessible while a research worker is busy.

A queued Qt cancellation signal alone may
be insufficient.

AQ-003 - Research input preservation

Reproducibility requires preserving the actual
relevant calculation inputs rather than merely
provider names, dates and research parameters.

### 15. Approved architectural decisions

- ADR-016: Modular layered monolithic architecture.
- ADR-017: Python source package organization.
- ADR-018: Quantitative engine preservation.
- ADR-019: Shared application services.
- ADR-020: External provider interfaces.
- ADR-021: MySQL repository architecture.
- ADR-022: Qt background processing.
- ADR-023: Research identity and reproducibility.
- ADR-024: Centralized configuration and paths.
- ADR-025: Failure isolation and testing.

### 16. Implementation roadmap

Milestone 03: MySQL database design.
Milestone 04: User interface design.
Milestone 05: Desktop application prototype.
Milestone 06: Quantitative research engine integration.
Milestone 07: Background processing.
Milestone 08: Technical analysis visualization.
Milestone 09: Historical simulation and reporting.
Milestone 10: Database integration.
Milestone 11: Quality assurance and testing.
Milestone 12: Windows deployment and formal acceptance.

No implementation shall be advanced ahead of
its authorized development milestone.

### 17. Formal architectural approval

Approval date: November 25, 2026

The user formally approved:

- ARCH-001.
- ADR-016 through ADR-025.
- QPC-001.
- DIC-001.
- All three architectural qualifications.

Architecture approval does not constitute
approval of a physical database schema,
production user interface or quantitative
methodology change.

### 18. Outstanding limitations

The approved architecture has not yet been
implemented or tested.

MySQL connectivity remains unverified.

Physical database design and production
user interface design remain pending.

Comprehensive quantitative equivalence
and live market data testing remain pending.

The existing historical research methodology
retains present-day candidate selection bias.

### 19. Baseline protection and scope control

The original Version 1.2 application and both
protected archives shall remain unchanged.

All implementation work shall occur within
the independent Version 2.0 development project.

Additional dependencies, quantitative methodology
changes and project scope expansion require
explicit user approval.

The approved twelve-milestone roadmap and
its definitive endpoint remain unchanged.
