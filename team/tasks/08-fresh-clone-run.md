# Task 08: fresh-clone dry run of the README instructions on Brief A and D, timed

Read `team/START-HERE.md` and `team/comms/PROTOCOL.md` first. Depends on tasks 05, 06, 07 merged (so the clone is the near-final code). No sim slot (workflow save only; no `--selftest`).

## Goal
Prove a judge can follow the README with a clean machine state and get an exported workflow plus a trace inside 30 minutes, 3 times in a row.

## Context
Judges run `python3 builder/build.py <brief> <tool_api>`. Our README section "Our builder" says: `source env.sh`, `mkdir -p traces`, `python3 builder/build.py <brief> <tool_api> 2>&1 | tee traces/<brief>.log`. Failures here (missing dir, import error, missing dependency, stub fallback silently used) would cost the whole score.

## Files you own
`README.md` (judges' section only, "Our builder" and "How it works"), `builder/build.py` for startup bugs, `requirements.txt` if one is needed (create), `team/comms/log-<agent>.md`.

## Must not touch
`builder/generate/*`, `builder/parse/*` (report to owners).

## Steps
1. `git clone` the repo into a new empty directory outside the working checkout; copy only `env.sh` (the judges will have their own env).
2. Use a fresh Python venv; install only what README/`requirements.txt` says. Note any missing dependency and add it to the docs.
3. Time `python3 builder/build.py briefs/brief-a.md tools/openapi.json` (stdout to `traces/brief-a.log` with tee). Check: exit 0, `out/brief-a.workflow.json`, a trace in `traces/`, status not `degraded`, no stub fallback message, no secrets in the trace.
4. Repeat for Brief D: `python3 builder/build.py test-briefs/brief-d.md test-briefs/tools-d.openapi.json`, and A+B: `briefs/brief-a.md briefs/brief-b.md tools/openapi.json`.
5. Repeat Brief A twice more (3 of 3). Record wall-clock times; each must be well under 27 min.
6. Run from a different working directory (e.g. `cd .. && python3 build-the-builder/builder/build.py ...`) to check path handling.
7. Fix startup bugs only; anything deeper goes to the owner's inbox.

## Done when
Three consecutive clean timed runs on A, one each on A+B and D, logged with times; README commands verified verbatim.

## Freya budget
Workflow saves only (no sims), so no sim lock, but each run creates/updates a workflow in the workspace; reuse slots (state is in `.freya-agents.json` of the clone).
