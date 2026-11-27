# Milestone 07 — Background processing

> Historical design/checkpoint record. For current implementation, QA scope and outstanding release gates as of November 27, 2026, see [release notes](RELEASE_NOTES.md). Original requirements and historical evidence below are retained.

QObject worker in QThread; GUI updates via signals; thread-safe Event cancellation at safe boundaries before/after each baseline batch and during interbatch delay. In-flight provider calls and split checks cannot be interrupted immediately. No partial results published after cancellation. Close requests cancel and defer closing until worker completes. The existing CLI and vendored engine remain unchanged. Screening uses original 50-symbol batches, retry settings and 1.25-second delay between batches; aggregates counters and applies original global ordering/ranking. Windows interaction tests and formal acceptance pending.
