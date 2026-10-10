# Task 02: Brief A x3, A+B x3, style runs, hard scripts

Read `team/START-HERE.md` and `team/comms/PROTOCOL.md` first. Uses the sim slot for hours; depends on task 01 being `done` (agent must work).

## Goal
Measure the 3/3 robustness of the generated agent on Brief A and A+B, and find failures that appear only with other customer styles or harder wordings.

## Context
The judges need 3 of 3 runs; a single green run proves little. Last numbers: A 7/10 strict over 3 reps (platform slow), B 3/3 once. `--style` options: `pieces|corrects|talkative|asks_back|in_words`. Harder wordings live in `harness/scripts/`; `harness/apply_scripts.py` merges them into case files in `out/hard/`. See `TEST_PLAN.md` gates 5 and 6, `harness/README.md`.

## Files you own
`team/comms/log-<agent>.md`; new customer scripts under `harness/scripts/` (new files only).

## Must not touch
`builder/generate/*` (report bugs to the generator owner's inbox, or send a small PR with transcript evidence), `builder/parse/`.

## Steps
1. Agent for A: regenerate and save `gen-a` (see task 01 step 1-2). Take the sim lock.
2. Milestone (gate 5): `python ci/sim.py <agent_id> --workflow out/gen-a.workflow.json --brief A --full --why "milestone A 1 rep"`.
3. If at least 9/10: robustness (gate 6): `--brief A --full --reps 3 --why "robustness A"`. Then ONE style at a time: `--style pieces`, then `corrects`, etc., only if the previous was clean enough to be informative.
4. Brief A+B: build/save `gen-ab` from `builder/specs/brief-ab.spec.json`, `--brief B` milestone then `--reps 3`.
5. Hard scripts: `python harness/apply_scripts.py` (read its usage), then run the produced case file with `run_cases.py --cases out/hard/<file>` through the same discipline (only after the basic runs are green).
6. After every failure: transcript, classify (judge noise / platform / extraction / engine), reproduce locally, report. Never re-run to see if it passes.
7. Write results with `python harness/report.py results/` into your log.

## Done when
A 3 reps and B 3 reps results plus at least two style runs and the hard-script run are logged, each failure classified with the case id and a proposed fix filed in the relevant inbox.

## Freya budget
Gate 6 allows 30+ calls for A x3 and 9 for B x3; styles about 10 each. Stop and ask Kutay (inbox) before exceeding 80 calls in total. Use the lock for the whole time you run; release between batches.
