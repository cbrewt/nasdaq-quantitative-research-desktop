# Milestone 06 screening integration

Validated V1.2 modules are vendored byte-for-byte inside infrastructure/validated_v12 (inactive backup excluded). Compatibility adapter exposes existing engine; application service delegates screening, strict/research selection and ranking. This is a transitional legacy boundary; reporting and persistence are not called by the GUI. Existing original CLI and archives are untouched.

Run launch_desktop.py and select Run live screener. Full Nasdaq scan uses baseline defaults, terminal progress, synchronous operation; UI may be unresponsive until completion. Cancellation and worker processing are Milestone 07. Sample preview remains explicitly fictional. No database writes or report generation. Results are in memory; later milestones must persist actual calculation inputs. Live data availability depends on providers.
