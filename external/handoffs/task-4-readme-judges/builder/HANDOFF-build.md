# Handoff: builder/build.py and trace.py

**Done (committed, on main):** `builder/build.py`, `builder/trace.py`, `builder/__init__.py`, README section "Our builder".
Verified once end to end with stub parse/generate (brief-a, example agent created and exported, trace written).

**Not done / untested:**
- `--selftest` path (run_cases subprocess, fix loop) never run. `parse_results` regex expects run_cases' "N / M passed" line and `FAIL <id>` lines.
- Real `builder.parse.parse(brief_paths, tool_api_path)`, `builder.generate.generate(spec)` and optional `builder.fix.fix(spec, workflow, failed_ids)` are loaded by import if they exist; otherwise stubs run. Check their signatures match once those threads land.
- Parser/generator/fixer must call `builder.trace.model_call(model, purpose)` for every model call, or the trace will list none.

**Next steps:** run `python builder/build.py briefs/brief-a.md tools/openapi.json` again with the real stages; then try `--selftest --selftest-brief A`; check total time stays under 27 min.

**Gotchas:** last brief file names the Freya slot and `out/<stem>.workflow.json`; state is in `.freya-agents.json` (uncommitted, has a `brief-a` slot from my test run); fallback to `examples/base-agent.json` marks the trace `status=degraded`; Windows Git Bash heredocs with long scripts broke, use the Write tool.

## Update (resumed 10 Oct, credit rules)
- Real parse/generate are wired (imported from builder.parse / builder.generate). `--spec-file` skips parse, `--dry-run` makes no Freya calls.
- Self-test is frugal: off by default; when on, 4 customers (one per family), 1 fix round. Plumbing verified with a fake run_cases (`--run-cases-cmd`), no real simulation was run.
- Still not run: a real `--selftest` against Freya or the mock bank (needs tunnel, see harness/README.md).
- Self-test now goes through ci/sim.py (lint, dry run, ledger). Round 0 = frugal set (or --selftest-full = the one full run); later rounds rerun only failed ids.
