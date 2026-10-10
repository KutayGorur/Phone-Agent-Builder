# Task 13: parser robustness on raw briefs (ACC-08 follow-up, H empty sections)

Read `team/comms/PROTOCOL.md` and `team/comms/accuracy-review-verdicts.md`. Uses a few LLM parser calls (not Freya sims). Effort: medium.

## Files you own
`builder/parse/*` (validate.py already has the ACC-08 reasons fix; extend it), `tests/parse/` (new).
## Must not touch
`builder/generate/*`, `build.py`, `local_sim.py`.

## Do
1. Reproduce: `python build.py --dry-run test-briefs/brief-h.md test-briefs/tools-h.openapi.json`; `out/brief-h.spec.json` has `parser.degraded=true` with the unhashable-dict error and empty closing/identity/calendar. Find which model field is malformed.
2. Validate nested shapes (reasons, bands, identity questions, outcomes) before any `set()`/dict walk; return path-specific errors so the repair loop can fix them; degrade one section, not the whole spec (`spec_parser.py:151`, `:252`).
3. Offline test with malformed fake model output per section; then rerun H and compare against `test-briefs/answer-key-h.md`.

## Done when
H parses with identity, closing and calendar populated; `python builder/parse/selftest.py` passes; unit tests cover malformed sections.
