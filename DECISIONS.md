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