# Sim slot lock

Free. codex-flight released the slot after completed PUB-06 targeted regressions, 2026-10-11. No simulations running from this continuation.

Fix f2d3eeb: existing A v11 and A+B v6 each passed PUB-06 1/1, records + conversation. A slowest turn 9.3 s; combined about 25 s. Latency recovery is not sustained: three-rep/style rounds deferred per TEST_PLAN, with no automatic repeats.

Previous unchanged rerun finished A v10 7/10 (PUB-04/06/08 early customer hangups, no tools) and combined v5 11/13 raw (only required B notes conflicting with A-only fixtures). PUB-07/PUB-09 passed in the rerun, but earlier traces show missing identity tool dispatch plus no matched transition; platform slowness alone is unproven. See team/comms/kutay-codex-release.md.
