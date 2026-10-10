# Handoff: builder/build.py and trace.py

**Done (committed, on main):** `builder/build.py`, `builder/trace.py`, `builder/__init__.py`, README section "Our builder".
Verified once end to end with stub parse/generate (brief-a, example agent created and exported, trace written).

**Not done / untested:**
- `--selftest` path (run_cases subprocess, fix loop) never run. `parse_results` regex expects run_cases' "N / M passed" line and `FAIL <id>` lines.
- Real `builder.parse.parse(brief_paths, tool_api_path)`, `builder.generate.generate(spec)` and optional `builder.fix.fix(spec, workflow, failed_ids)` are loaded by import if they exist; otherwise stubs run. Check their signatures match once those threads land.
- Parser/generator/fixer must call `builder.trace.model_call(model, purpose)` for every model call, or the trace will list none.

**Next steps:** run `python builder/build.py briefs/brief-a.md tools/openapi.json` again with the real stages; then try `--selftest --selftest-brief A`; check total time stays under 27 min.

**Gotchas:** last brief file names the Freya slot and `out/<stem>.workflow.json`; state is in `.freya-agents.json` (uncommitted, has a `brief-a` slot from my test run); fallback to `examples/base-agent.json` marks the trace `status=degraded`; Windows Git Bash heredocs with long scripts broke, use the Write tool.
