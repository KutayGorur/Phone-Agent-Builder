# Task 12: honest build status and hard time limit (ACC-07, ACC-16)

Read `team/comms/PROTOCOL.md` and `team/comms/accuracy-review-verdicts.md`. No Freya calls. Effort: low.

## Files you own
`builder/build.py`, `tests/test_build_status.py` (new).
## Must not touch
anything under `builder/generate/`, `builder/parse/`, `local_sim.py`.

## Do
1. ACC-07: after parsing, read `spec['parser']` (`degraded`, `unresolved_errors`) and a minimum-content check (non-empty identity questions, closing outcomes, calendar). Write them into the trace and make the final trace status say `degraded` when they fail. Do not export a degraded spec as `ok`. Keep the existing fallback behaviour so something valid is always exported, but label it.
2. ACC-16: replace `_run_limited` thread abandonment with a monotonic deadline passed down; run parse in a subprocess that is killed at the slice end (or at least terminate on timeout), and make sure the interpreter exits at the 30-minute limit.
3. Offline test with a fake parse that sleeps and a fake degraded spec; assert exit code, trace status and elapsed time.

## Done when
`python build.py --dry-run` on A still gives `ok`; on `out/brief-h.spec.json` gives `degraded`.
