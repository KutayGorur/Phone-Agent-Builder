# Bites — İnan + Claude, Sunday 11 October 2026

Our half of the split. Kutay + Codex hold everything that touches Freya or the generator: the sim slot, the PUB-06 decision, the PUB-07/09 hang-ups, style and 3-rep runs, the workspace cap, the submission email address, the final builds and the submit click. We do not run simulations and do not edit `builder/generate/`.

Times are UTC. Hidden briefs open 17:00, submission closes 20:00. Only crash fixes after 17:00; nothing from a hidden brief goes into code or prompts.

A new session: read this file, do the first bite that is not `done`, update its status line here.

## Bite 1 — README judges' section — done and pushed
Rewrote "Reliability" and "Known limits" and the local-scenario count in `README.md` with the 11 October numbers from `platform-case-review.md`.

## Bite 2 — parser fallback model — done and pushed (Kutay said yes)
`builder/parse/llm.py` `complete()` falls back between backends (API key, `claude` CLI) but not between models. If the default model is refused or at its limit on both, the build ends `status=degraded` with the example agent. Change: after both backends fail on the default model, try once more on a smaller model, and write the fallback into the trace. Add a unit test next to `tests/test_model_failure_status.py`; check with `python3 builder/build.py briefs/brief-a.md tools/openapi.json --dry-run`.
Done: `FALLBACK_MODEL` (`claude-sonnet-5-5`, env `PARSER_FALLBACK_MODEL`, empty turns it off) in `llm.py`, `tests/test_model_fallback.py`. All tests, parser selftest and local sim pass. Live check: a dry-run build of Brief A with a nonexistent `PARSER_MODEL` fell back on every call and ended `status=ok` in 85 s.

## Bite 3 — pre-flight on this machine — at 16:30 — early pass at 14:19 partly done, dry-run build still open
Early pass 14:19 UTC: `git pull --rebase` already up to date at `c7cd24d`; all test files pass; parser selftest clean on A and A+B; `local_sim.py` 0 FAIL; `env.sh` exists, ignored, not tracked. Not done: the `--dry-run` build of Brief A (the real Claude login check) and deleting its trace. Repeat the whole bite at 16:30.
This machine is the backup build machine. Check: `git pull --rebase origin main`; all tests pass; `python3 builder/generate/local_sim.py` has 0 FAIL; `env.sh` exists and is not tracked; a `--dry-run` build of Brief A ends `status=ok` (proves the Claude login with a real call); delete the trace that dry run writes. Report the result to İnan.

## Bite 4 — cross-check the hidden briefs — at 17:00, needs the brief files from İnan
İnan puts the hidden briefs and tool API file in `~/final/` (outside the repo). Run `python3 builder/build.py ~/final/<brief> ~/final/<tool_api> --dry-run` per brief: no Freya calls, no new workflows. Compare `out/<stem>.spec.json` with Kutay's parsed spec on five facts: calendar and holidays, bands and floors, identity questions, outcome table, queues. Report differences to İnan in words; do not paste brief text into the repo or comms. Do not run a real build here unless Kutay's machine cannot: two machines building the same brief create two workflows, and the workspace has 8 of 10.

## Bite 5 — check the submission commit — after Kutay's builds
After Kutay pushes: `git pull`, then `python3 ci/prepare_submission.py <stems>` (dry run). Check every trace ends `[END] status=ok` and not `degraded`, no keys in `submission/`, each workflow file has `workflow_id`, no hidden-brief text anywhere outside `submission/`, the commit in the form fields is pushed.

## Bite 6 — PR #9 — İnan by hand
Closing was denied on this machine. PR #9 is superseded by `58c355d`; close it on GitHub with that note.

## Not doing today
Live tests of briefs C to H (tunnel blocked) and the scam-guard test fixture.
