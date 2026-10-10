# Task 10: engine state and parsing fixes (ACC-01,02,03,04,06,09,10,13,19,20,22,23,24,26,27)

Read `team/comms/PROTOCOL.md` and `team/comms/accuracy-review-verdicts.md` first (it has the repro for each ACC). No Freya calls. Effort: medium (one owner, sequential).

## Files you own
`builder/generate/engine_lib.py`, new `tests/logic/test_engine_state.py`.
## Must not touch
`ecfg.py`, `generate.py`, `build.py`, `builder/parse/*`, `local_sim.py`.

## Do, in this order (commit + push after each group)
1. Parsing helpers (`free_date`, `free_amount`, `free_time`): ACC-22 explicit d/m/y before `digitize`, "N days/weeks from now/today"; ACC-13 comma decimals, negatives, ranges and pence ask for clarification instead of picking a number; ACC-23 explicit 24h time ("07:00") is rejected or re-asked, not moved to 19:00.
2. Product scope: ACC-20 apply an offer to `x_product` when it names a product; ACC-02 matcher must require a unique match (ask when ambiguous, no silent first match); ACC-03 "all" correction updates every selected product.
3. Proposal state: keep a pending amount/date per product in `st`, merge only supplied fields (ACC-01, ACC-04 per-product amount with date, ACC-09 hardship + volunteered offer, ACC-10 callback day kept across turns).
4. Termination and speech: ACC-19 notes for agreed-but-unrecorded products on a stop; ACC-24 answer `x_q` before create/close; ACC-06 never offer an amount/date pair already rejected (needs Task 11 date tokens for G, but the history check is independent); ACC-27 per-record acknowledgement only when the spec field from Task 11 asks for it (skip until that lands); ACC-26 do not invent ids or zero amounts for missing account fields.

## Done when
Each ACC has a test in `tests/logic/test_engine_state.py` using the probe pattern (`engine_code(build_E(spec))`, set vars, assert bank-visible output); `python tests/logic/test_logic.py` and `python -m builder.generate.local_sim` stay at least as green as before (H has 8 known failures from Task 13).
