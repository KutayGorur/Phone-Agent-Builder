# Task 03: real `build.py --selftest` and trace review

Read `team/START-HERE.md` and `team/comms/PROTOCOL.md` first. Uses the sim slot; start when task 01 shows the platform works.

## Goal
Run the real submission command with the self-test on, once, and confirm the trace and the time budget meet the rules.

## Context
The self-test/fix loop was only checked with a fake runner. The ledger may show an interrupted 4-case self-test on slot `brief-a` (see `results/sim-ledger.csv` for rows with a `why` mentioning selftest); check it first: if the ledger on your machine is empty, ask Kutay (inbox) whether that run finished before spending. The judges' trace requirement: start/end time, every model call (model + purpose), Freya resources touched, self-test result; keys redacted. `build.py` details: README section "Our builder" and `builder/HANDOFF-build.md`.

## Files you own
`builder/build.py`, `builder/trace.py`, `team/comms/log-<agent>.md`.

## Must not touch
`builder/generate/*`, `builder/parse/*` (message their owners if a stage fails to call `builder.trace.model_call`).

## Steps
1. Free: `python builder/build.py --dry-run briefs/brief-a.md tools/openapi.json`; read the trace in `traces/` and check every model call appears.
2. Check the ledger for the interrupted self-test; note the finding in your log.
3. Take the sim lock. Run `source env.sh; mkdir -p traces; python3 builder/build.py --selftest briefs/brief-a.md tools/openapi.json 2>&1 | tee traces/brief-a.log` (default frugal set, max 4 customers, 1 fix round). Time it.
4. Review: total time under 27 min, trace complete with the self-test result, `status` not degraded, exported `out/brief-a.workflow.json` exists, no secrets in trace (grep for `fak_` and the bank key).
5. Fix plumbing bugs in `build.py`/`trace.py` (regex of `parse_results`, `FAIL <id>` lines, run_cases output). Do not add a fix loop that edits generator files.
6. Release the lock.

## Done when
One real self-test completes (or its failure cause is documented) and the trace passes the checklist in step 4.

## Freya budget
One self-test: at most 4 sim calls plus at most 4 for the fix round. No full runs.
