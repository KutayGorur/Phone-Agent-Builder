# Task 07: guard against the agent repeating its last line when the engine code node fails

Read `team/START-HERE.md` and `team/comms/PROTOCOL.md` first. No Freya calls to build it (one targeted sim to verify is optional, ask for the lock). GENERATOR OWNER: edits `builder/generate/engine_lib.py` and `generate.py`; do after task 06 or have the same agent do both.

## Goal
When the engine code node fails on the platform (sandbox errors such as "Failed to reach snekbox" or "Sandbox did not return a parseable result"), the agent must not repeat its last line forever and must end the call in a defined, honest way.

## Context
Observed in `builder/generate/HANDOFF.md`: a failed code node leaves the stale route `say` and the old `instruction`, so the speaking node repeats the previous sentence. API nodes already re-enter only while their result var is `pending`. `PLATFORM_NOTES.md` explains variables, routes, code nodes and hooks, and what a failed code node leaves behind.

## Files you own
`builder/generate/engine_lib.py`, `builder/generate/generate.py`, `builder/generate/PLATFORM_NOTES.md`.

## Must not touch
`ecfg.py` and `builder/parse/` (task 06), `local_sim.py` (task 05).

## Steps
1. Read how `engine` writes `instruction` and `route`; find how a failed run is visible to the next node (probe in `PLATFORM_NOTES.md`, or design so it does not need to be visible: e.g. the engine clears `route`/`instruction` to a sentinel at start and the transitions treat the sentinel as failure).
2. Implement: a turn counter or sentinel so that a second consecutive engine failure routes to a neutral close (outcome from the spec's "technical failure" or the safest unresolved outcome defined in the spec's outcome table, e.g. callback/no-promise), after saying a short apology line. Spec-driven, no hardcoded outcome names.
3. Local sim: simulate a failing engine (raise inside the run) in a scenario and assert the call ends with the fallback outcome (coordinate with task 05 for the harness hook, or add a small test in `tests/`).
4. `python ci/lint_workflow.py out/gen-a.workflow.json --dry-run` and `preflight.py` must pass.
5. Optional verification on the platform needs a sandbox outage that cannot be forced; rely on the local test plus lint. Do not spend credits on it.

## Done when
Local test shows no repeated line and a defined close on repeated engine failure; lint/preflight green; PLATFORM_NOTES updated; PR merged.
