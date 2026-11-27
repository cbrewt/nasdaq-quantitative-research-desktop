# Milestone 06 screening integration

> Historical design/checkpoint record. For current implementation, QA scope and outstanding release gates as of November 27, 2026, see [release notes](RELEASE_NOTES.md). Original requirements and historical evidence below are retained.

Validated V1.2 modules are vendored byte-for-byte inside infrastructure/validated_v12 (inactive backup excluded). Compatibility adapter exposes existing engine; application service delegates screening, strict/research selection and ranking. This is a transitional legacy boundary; reporting and persistence are not called by the GUI. Existing original CLI and archives are untouched.

Run launch_desktop.py and select Run live screener. Full Nasdaq scan uses baseline defaults, terminal progress, synchronous operation; UI may be unresponsive until completion. Cancellation and worker processing are Milestone 07. Sample preview remains explicitly fictional. No database writes or report generation. Results are in memory; later milestones must persist actual calculation inputs. Live data availability depends on providers.

## Final verification

Live desktop scan on November 25, 2026: 3431 checked, 86 qualified; CTKB live analysis displayed score 5/5. Display formatting only: prices, gains, RSI and RVOL to two decimals; MACD and histogram to six (scientific notation for tiny nonzero values); volume with separators. Underlying calculations and numeric sort role unchanged. Original offline suites, fixed-input adapter comparison and display tests passed. Protected archives verified; vendored active source compared allowing line-ending conversion. Initial installer import issue worked around by preloading dependencies; root cause unresolved. Full independent data replay, asynchronous processing and persistence remain later milestones. Formal Milestone 06 acceptance pending.
