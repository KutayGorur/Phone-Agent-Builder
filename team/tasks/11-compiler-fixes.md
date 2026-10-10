# Task 11: spec compiler fixes (ACC-05,11,14,15,21,27)

Read `team/comms/PROTOCOL.md` and `team/comms/accuracy-review-verdicts.md`. No Freya calls. Effort: medium.

## Files you own
`builder/generate/ecfg.py`, `builder/generate/generate.py`, `builder/SPEC_CONTRACT.md`, new `tests/logic/test_compiler.py`.
## Must not touch
`engine_lib.py` (Task 10; if you need an engine change, put a request in its owner's inbox), `build.py`, `builder/parse/*`, `local_sim.py`.

## Do
1. ACC-05: replace `_date_tok` keyword guessing with explicit tokens (`next_business_day`, `deadline`, `capped_next_business_day`, `midpoint`, `week_end`, `today`); unknown text must not silently become deadline/week. Check against `out/brief-g.spec.json` and F: attempts 1 and 3 must compile to their real meaning.
2. ACC-21: choose outcome roles (promise, paid, no-promise, transfer) from structure (reasons empty/not, `intents.sp_already_paid.close`, `pers.on_exhausted`) and refuse to map two roles to one outcome without a warning; test with `when` removed and rows reordered.
3. ACC-14: `create_promise_max_tries` 0 must not become 2 (use `is None` check); add a capability warning list for spec fields the generator ignores.
4. ACC-11: `do_close` result handling and transfer failure: decide a fail-safe, document in HANDOFF.md; do not invent outcome codes.
5. ACC-15 (low): build tool URLs from `spec['tools_server']` when present.
6. ACC-27: add spec contract field for acknowledgement scope (`per_record|per_call`), compile it into E, tell Task 10 owner via inbox.

## Done when
Tests in `tests/logic/test_compiler.py`; `tests/logic/test_logic.py` and `local_sim` no worse than before.
