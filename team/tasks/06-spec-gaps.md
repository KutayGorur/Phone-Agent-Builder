# Task 06: spec gaps (A42, A47, A35, A26, transfer-after-promise, B9/B10 notes timing)

Read `team/START-HERE.md` and `team/comms/PROTOCOL.md` first. No Freya calls. GENERATOR OWNER: edits `builder/generate/ecfg.py`, `engine_lib.py`, `builder/parse/` and `builder/specs/`. Only one agent at a time may hold tasks 06 and 07 (suggest the same agent does both, 06 first).

## Goal
Resolve the known spec ambiguities so the spec and engine implement what the briefs say, driven by the spec (never hardcoded to Brief A).

## Context
Rules referenced as A<n> / B<n> are numbered rules in `briefs/brief-a.md` and `briefs/brief-b.md`. Gaps listed in `builder/generate/HANDOFF.md` and the README "Known limits":
- A42, A47, A35, A26: read each rule, check what `builder/specs/brief-a.spec.json` and the engine do, fix any divergence.
- Transfer after a promise: when a customer has already made a promise and then asks for a human, the briefs may conflict (post-record turn is "not built" per the handoff). Decide from the brief text what the records must show; if the brief is genuinely ambiguous, pick the safer reading, write it in `builder/generate/HANDOFF.md`, and say so in your log.
- B9/B10: timing of notes relative to transfer/promise creation in Brief B.
- Also the README notes that the A+B spec may omit an explicit thank-you before closing and the "if they insist" condition for human transfer.

## Files you own
`builder/generate/ecfg.py`, `builder/generate/engine_lib.py`, `builder/parse/*`, `builder/specs/*`, `builder/SPEC_CONTRACT.md` (announce contract changes in every inbox), `tests/logic/*`.

## Must not touch
`builder/generate/local_sim.py` (task 05 owns it; add scenarios by inbox request or a tiny separate PR after 05 merges), `builder/build.py`.

## Steps
1. For each item: quote the brief rule, show current behaviour (spec field + engine path), decide, change the spec field/parser prompt and engine reading it. Keep it general: a new contract field is fine, a Brief-A-specific constant is not.
2. Add a local_sim scenario per fix (coordinate with task 05) and keep `python builder/generate/local_sim.py` and `python tests/logic/test_logic.py` green.
3. Re-run parser selftest `python builder/parse/selftest.py` (uses the LLM; a few calls).
4. Document decisions in `builder/generate/HANDOFF.md` (append section).

## Done when
Each item has a decision, a test, and a note; all free gates green; PR merged.
