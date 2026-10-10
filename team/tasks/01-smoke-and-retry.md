# Task 01: sandbox smoke check, then PUB-04/06/10 retry

Read `team/START-HERE.md` and `team/comms/PROTOCOL.md` first. Uses the sim slot.

## Goal
Find out whether the Freya code sandbox works again, then verify on the platform the two fixes that are only local-green (PUB-06 short re-ask, PUB-04 `x_q`) and re-check PUB-10.

## Context
`gen-a` v9 was deployed with the fixes but the last runs hit sandbox errors ("Failed to reach snekbox", "Name or service not known"), so 4 calls were wasted. PUB-10 usually fails only because the judge flags the mandated opening "this call is recorded" (judge noise; do not change wording unless a transcript shows a real problem). See `builder/generate/HANDOFF.md` (Status sections) and `PLATFORM_NOTES.md`.

## Files you own
`team/comms/log-<agent>.md`. You may not edit `builder/generate/*` except a small fix with a failing transcript as evidence (then coordinate with the owner of tasks 06/07 via inbox; PR separately).

## Must not touch
`builder/parse/`, `builder/build.py`, `briefs/`, `tests/`.

## Steps
1. Free gates: `python builder/generate/local_sim.py` green. Regenerate: `python -m builder.generate.generate builder/specs/brief-a.spec.json out/gen-a.workflow.json`; `python ci/lint_workflow.py out/gen-a.workflow.json --dry-run`.
2. Save to your own slot and get the agent id: `python3 -c "import freya,json; print(freya.save_workflow('gen-a', json.load(open('out/gen-a.workflow.json'))))"`.
3. Take the sim lock. Smoke: one case, `python ci/sim.py <agent_id> --workflow out/gen-a.workflow.json --brief A --only PUB-01 --why "sandbox smoke check"`. If the transcript shows sandbox errors, release the lock, wait 15 minutes, retry once. If still failing, mark blocked and tell Kutay in the inbox.
4. If the smoke passes: `--only PUB-04,PUB-06,PUB-10 --why "verify short re-ask, x_q fix, opening wording"`.
5. For each failure read the transcript, decide if it is judge noise, platform, or a real bug. Real bug: reproduce in `local_sim.py` (add a scenario), fix, regenerate, re-sim only that case.
6. Release the lock after each sim.

## Done when
PUB-04 and PUB-06 pass on the platform (or a root cause is written in your log with the transcript evidence), PUB-10 result is explained, results are in your log with ledger total.

## Freya budget
Max 1 smoke + 3 cases + at most 2 single-case retries (about 6 calls).
