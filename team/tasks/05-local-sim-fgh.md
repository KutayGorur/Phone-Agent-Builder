# Task 05: wire briefs F, G, H into the local sim (free)

Read `team/START-HERE.md` and `team/comms/PROTOCOL.md` first. No Freya calls. Touches `builder/generate/local_sim.py` only, so it can run in parallel with 06/07 (rebase before merging).

## Goal
`python builder/generate/local_sim.py` also covers briefs F, G and H, each asserting the expected close outcome, reason, promises, notes and transfers, like the existing 41 scenarios for A to E.

## Context
`test-briefs/` has `brief-f/g/h.md`, `tools-f/g/h.openapi.json`, `cases-f/g/h.json`; H is raw mail/policy extracts with a later memo and a renamed code list, with amendment key `answer-key-h.md`. The local sim feeds scripted extractions into an in-process stand-in bank and the real scorer. Look at how C, D and E are wired in `local_sim.py` and replicate. To get specs, run the parser (needs the LLM; one parse per brief): `python builder/build.py --dry-run test-briefs/brief-f.md test-briefs/tools-f.openapi.json` writes `out/<stem>.spec.json`. Check the spec against the brief by eye (and against `answer-key-h.md` for H); parser errors are findings, not things to hide.

## Files you own
`builder/generate/local_sim.py`; new files `test-briefs/scripts-f/g/h` style fixtures if needed; `team/comms/log-<agent>.md`.

## Must not touch
`engine_lib.py`, `ecfg.py`, `generate.py`, `builder/parse/` (file bugs in the owner's inbox: tasks 06/07 owner for generator, or Kutay for parser).

## Steps
1. Read `local_sim.py` structure; run it to confirm 41 green.
2. Generate specs for F, G, H; save copies under `builder/specs/` as `brief-f.spec.json` etc. only if reviewed and correct.
3. Add scenarios per case in `cases-f/g/h.json` (one per customer family at least), asserting the expected records.
4. For each failing scenario decide: spec parse error (parser), generator/engine bug (inbox to generator owner with a minimal repro), or wrong script (fix script).
5. Update the "Local sim" note in `README.md` section "Overfitting" if the scenario count changes (that line is shared: edit only that sentence, small PR).

## Done when
All F/G/H scenarios exist; those that fail are filed as bugs with repro commands; the count of scenarios is reported in your log.
