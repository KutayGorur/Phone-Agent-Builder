# Task 09: Sunday run-book for the hidden briefs and submission

Read `team/START-HERE.md` and `team/comms/PROTOCOL.md` first. Depends on all other tasks (write the draft early, finalise after they merge). No Freya calls until the procedure is executed on Sunday.

## Goal
A step-by-step `team/RUNBOOK.md` for Sunday (window 17:00 to 20:00 UTC) so any team member or agent can run the hidden briefs and submit without improvising.

## Context
Judges run `python3 builder/build.py <brief> <tool_api>` on hidden raw-material briefs, 30-minute cap, 3 of 3 runs; submission is the export, the commit of the builder and the trace. Read the hackathon page https://www.freyavoice.ai/hackathon and the kit README for the exact submission mechanics and fill the exact steps into the run-book (do not guess; if the submission form is not documented, list what Kutay must confirm). Hidden briefs are unseen, so the run-book must say: copy the briefs to a scratch folder, never hardcode, and what to do if the parser output looks wrong.

## Files you own
`team/RUNBOOK.md`, `team/comms/log-<agent>.md`.

## Must not touch
Code.

## Content of RUNBOOK.md
1. Freeze: Sunday 12:00 UTC stop feature work; tag the commit (`git tag submit-candidate`); the working tree must be clean; tests green (`local_sim.py`, `test_logic.py`, parser selftest).
2. Pre-flight at 16:30 UTC: env.sh present, keys valid, Freya platform healthy (a single cheap check), parser LLM login valid, free disk, clean `out/` and `traces/`.
3. When the hidden briefs arrive: save them unmodified, read them once for obvious format surprises (a new section type, a new language, renamed codes) and inspect `out/<brief>.spec.json` after the first parse against the brief text for the five riskiest facts (calendar, bands/floors, identity questions, outcome table, queues).
4. Run order and timing: run the build 3 times (or as the rules require), `tee` into `traces/`, check each trace has start/end, model calls, Freya resources, status not degraded; time each run.
5. Decision rules: when to accept the spec, when to rerun the parser, when to add a `--spec-file` hand correction (only if the rules allow it; check the hackathon page), when to submit a degraded result.
6. Credit rules: at most one smoke sim on the hidden brief before submission, via `ci/sim.py --why`; skip if credits are short.
7. Submission checklist: export file name, commit hash pushed, trace files included, required form fields, who clicks submit, submission screenshot saved.
8. Contacts and fallback: where to find people (inbox/board), what to do if the platform is down at 19:00.

## Done when
RUNBOOK.md is complete with every submission mechanic verified against the official page, reviewed by Kutay via inbox.
