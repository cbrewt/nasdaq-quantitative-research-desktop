# Nasdaq Quantitative Research V2.0

## Data Interface Contract

Document reference: DIC-001
Approval date: November 25, 2026
Status: APPROVED
Implementation verification: PENDING
Development milestone: 02

### 1. Purpose

Establish the data integrity, interface compatibility,
traceability and reproducibility requirements for
the Version 2.0 desktop application.

This contract shall guide application integration,
research persistence and subsequent MySQL
database design.

### 2. Related technical documents

- AUDIT-001: Source code audit.
- ARCH-001: Approved desktop application architecture.
- QPC-001: Quantitative preservation contract.
- ADR-015: Validated integration baseline selection.
- ADR-016 through ADR-025: Architectural decisions.

The validated Version 1.2 source remains the
authoritative reference for existing application
interfaces and behavior.

### 3. Approved data preservation requirements

#### DIC-01 - JSON handoff compatibility

Preserve the existing JSON schema version 1
contract between the Stock Screener and the
Backtesting Engine.

Preserve existing field names, data types,
validation requirements and mode-selection
behavior.

Existing handoff fields include:

- schema_version
- scan_id
- scan_date
- qualifying_tickers
- screener_settings
- backtest_settings

An empty qualifying-ticker collection shall
remain a valid screening outcome.

Any future interface version changes require
documented compatibility considerations
and appropriate regression testing.

#### DIC-02 - Unique screening-run identity

Preserve a unique identity for each screening
execution.

Retain the existing scan_id for compatibility
and research traceability.

Multiple screening executions may occur
on the same trading date.

The completed trading date shall not serve
as the unique screening-run identifier.

Internal primary key selection shall be
determined during database design.

#### DIC-03 - Execution time and trading date

Distinguish the time at which a research
operation executes from the completed
trading date used by the research engine.

Preserve the relevant time zone and date
interpretation information.

Do not substitute an execution date for
the actual market observation date.

#### DIC-04 - Research parameter preservation

Preserve the exact research parameters
associated with each research execution.

Screening parameters include:

- Minimum percentage gain.
- Minimum closing price.
- Maximum closing price.
- Momentum confirmation requirement.

Historical simulation parameters include:

- Historical research period.
- Holding sessions.
- Estimated round-trip transaction cost.

Preserve other relevant acquisition and
engine settings required for reproducibility.

Previously saved research parameters shall
not be silently replaced by current defaults.

#### DIC-05 - Security and screening relationships

Maintain the relationship between each
security and its originating screening run.

A security may participate in multiple runs.

A screening run may contain multiple securities.

Relational persistence shall represent this
many-to-many relationship through an
appropriate associative structure.

Security identity and ticker history
requirements shall be evaluated during
database design.

#### DIC-06 - Missing-value preservation

Preserve the distinction between valid
numeric zero and unavailable research data.

Missing indicator values shall not be
silently converted to zero.

Unavailable technical scores shall remain
distinct from valid zero-point scores.

Preserve the meaning of undefined and
infinite statistical results.

Database representations shall preserve
these distinctions without information loss.

#### DIC-07 - Screening mode separation

Preserve Research Mode and Strict Momentum Mode
as distinct research workflows.

Maintain the screening mode associated with
each research execution and historical analysis.

Do not silently substitute strict historical
backtesting for score-based historical research,
or the reverse.

Preserve existing command-line compatibility.

#### DIC-08 - Historical signal association

Associate historical signals with their
originating backtest execution.

Preserve signal dates, relevant indicators
and available technical scores.

A historical signal shall remain traceable
to the research settings and data used
to produce it.

Preserve mode-specific signal interpretation.

#### DIC-09 - Simulated trade association

Associate completed simulated trades with
their originating historical signals.

Preserve existing trade attributes, including:

- Security identity.
- Signal date.
- Entry date and price.
- Exit date and price.
- Holding sessions.
- Gross return.
- Estimated transaction cost.
- Net return.

Preserve the distinction between completed,
incomplete and excluded trade opportunities.

Do not represent an incomplete trade
as a completed losing trade.

#### DIC-10 - Market data and reproducibility

Preserve relevant market data provenance
and calculation inputs required to reproduce
research results.

Relevant information includes:

- Market data provider identity.
- Acquisition timestamps.
- Security universe used.
- Reference trading calendar.
- Relevant price and volume observations.
- Corporate-action information used.
- Data acquisition and adjustment settings.
- Indicator warmup history.
- Quantitative engine revision.
- Research parameters.

Preserve the actual relevant source inputs,
not merely instructions for downloading them again.

A subsequent data download may contain
revised historical observations.

Distinguish rerunning a research request
from reproducing its original results.

Physical storage, retention and data
representation shall be evaluated during
the database design milestone.

#### DIC-11 - Report association

Associate generated reports with their
originating research-run identity.

Preserve report type, generation information
and relevant research references.

Do not rely solely on filenames, trading
dates or matching ticker collections to
establish unique report ownership.

Report-generation behavior shall remain
compatible with the approved research workflows.

#### DIC-12 - Secondary failure isolation

Prevent secondary workflow failures from
invalidating successful primary research results.

Historical simulation failure shall not
discard successful screening results.

Report generation failure shall not
discard successful research calculations.

Database persistence failure shall be
reported accurately.

Available research results shall be preserved
in memory where practical.

A cancelled or partially completed operation
shall not be represented as successfully
completed and persisted.

### 4. Existing application interfaces

Important existing data structures include:

- Security.
- Match.
- ScanResult.
- TechnicalScore.
- ScreenerSettings.
- BacktestSettings.
- ScreenerHandoff.
- HistoricalSignal.
- ScoredSignal.
- SimulatedTrade.
- MultipleTradeResult.
- PerformanceStatistics.
- ScorePerformance.
- ScoredBacktestResult.

These structures provide the starting point
for Version 2.0 application integration.

Controlled adaptations shall preserve
existing quantitative semantics.

### 5. Approved application service boundaries

Application services shall coordinate
research workflows without exposing
database implementation details to
the presentation or quantitative layers.

The approved architecture identifies:

- ScreeningService.
- BacktestingService.
- ResearchHistoryService.
- ReportService.
- MarketDataProvider.
- SecurityDirectoryProvider.
- ResearchRepository.
- ProgressReporter.
- CancellationToken.

Final method signatures and implementation
details shall be established during their
authorized development milestones.

### 6. Preliminary relational design considerations

Conceptual research entities include:

- Screening Run.
- Security.
- Screening Result.
- Daily Observation.
- Backtest Run.
- Historical Signal.
- Simulated Trade.
- Performance Statistics.
- Report.

These entities are preliminary design inputs,
not approved physical database tables.

Development Milestone 03 shall address:

- Entity definitions and functional dependencies.
- Relational normalization.
- Primary and foreign keys.
- Cardinality and optionality.
- Data types and numerical precision.
- Uniqueness and integrity constraints.
- Indexes and query requirements.
- Market data provenance and revision identity.
- Research persistence transaction boundaries.
- Backup and recovery requirements.

No physical database schema is approved
or implemented by this document.

### 7. Data interface verification requirements

Subsequent testing shall verify:

- Existing JSON handoff compatibility.
- Unique research-run identification.
- Preservation of research parameters.
- Correct security-to-run relationships.
- Missing-value preservation.
- Correct screening mode identification.
- Historical signal and trade associations.
- Research input reproducibility.
- Report-to-run associations.
- Database transaction consistency.
- Secondary workflow failure isolation.

Research results shall be compared using
identical deterministic inputs where applicable.

### 8. Verification status and limitations

All twelve data preservation requirements
were formally approved on November 25, 2026.

The validated Version 1.2 application provides
file-based research persistence.

It does not provide the proposed MySQL
research repository implementation.

The existing JSON handoff preserves research
requests but does not independently preserve
all original market data inputs.

The approved Version 2.0 data architecture
has not yet been implemented or tested.

Complete reproducibility, database integrity
and interface compatibility remain subject
to subsequent verification.

### 9. Change control and baseline protection

Changes to this approved contract require
documented review and user approval.

No additional dependencies, quantitative
methodology changes or scope expansion
are authorized by this document.

The original Version 1.2 application and
both protected archives shall remain unchanged.

Database implementation shall not commence
before approval of the physical database schema.
