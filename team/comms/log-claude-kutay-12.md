# Log claude-kutay-12 (task 12)
## 2026-10-10T18:55Z
- build.py: `readiness_problems(spec)` (parser.degraded, unresolved_errors, empty identity questions / closing outcomes / calendar) -> trace status `degraded`, exit code stays 0 (fallback export still happens).
- ACC-16: parse runs in a child process killed at the slice end; `_run_limited` uses daemon threads; a watchdog timer ends the process (status `timeout`, exit 3) 15 s before 30 min; `os._exit` at the end of main.
- tests/test_build_status.py (offline, fake parse): passes. Dry run on A spec -> ok; on out/brief-h.spec.json -> degraded.
- Child parse model_call lines still go to the same trace file, but the parent's model_calls counter no longer counts them.
