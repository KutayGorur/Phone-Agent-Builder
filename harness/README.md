# Our own test material and tools

Purpose: test the builder on briefs it was not tuned on (the final uses unseen briefs).

## The variant briefs (`test-briefs/`)

| Brief | Form | What differs from Briefs A and B |
|---|---|---|
| `brief-c.md` | clean specification, one product | Nordhaven Bank. Three bands (8th / 5th / 3rd business day, 1 / 2 / 3 attempts). Calendar Monday to Saturday with Saturday holidays. Identity: date of birth then postcode, month-first numeric dates, two wrong answers end the check, extra hint `year_two_digits`. Callback 09:00 to 16:30, two asks. Floor is `minimum_due` for every type. Renamed outcomes (`settled`, `handover`, `no_contact`, ...), reasons (`care`, `disputed`, `callback_set`, ...), queues and product fields (`amount_overdue`, `days_overdue`). Different closing sentence. |
| `brief-d.md` | raw bank material: a mail, a policy extract, an amending memo, a code list | Alpenbank. Up to three products. The memo overrides the extract (bands, callback window, holiday list, first persuasion attempt, "speaking" no longer counts). Overdraft floor is computed (25 percent). Identity: account opening year then date of birth, day-first dates. Coded outcomes (`PTP`, `NOREACH`, ...), queues (`Q_RESTR`) and fields (`arrears`, `days_past_due`). Notes apply to every product without a promise. |
| `brief-e.md` | change list on top of A and B (like Brief B) | Two products, postcode instead of phone digits, four wrong answers, callback from 09:00 to 18:00, different holidays, a third (severe) band, different texts. Tool API differs only in the identity field. |

Each has `tools-<x>.openapi.json` (derived from `tools/openapi.json`) and `cases-<x>.json` (same format as `public-test-set.json`,
8 / 11 / 9 customers, every date computed from the variant's calendar).
`python harness/make_testset.py` regenerates all six files; edit the cases there, not in the JSON.

## Can run_cases.py run them?

`tools/run_cases.py --cases test-briefs/cases-c.json --brief C` builds the customers (personas) from any case file, so the
simulation side works. The bank side does not: the organisers' mock answers `unknown practice case` for any id that is not its own
(checked with a call, also with the full customer in the request body), and the phone agent calls the tool URL inside the workflow.

So there is a stand-in, `harness/mock_bank.py`: same endpoints and ledger shape, reads our case files, checks enums from the variant's
tool API file, supports `faults` and per-case `max_wrong`. The phone agent runs on Freya's cloud, so it needs a public URL (tunnel).
The steps are in the docstring of `mock_bank.py`. `python harness/mock_bank.py --selftest` replays every expected ledger through the
server and the real `tools/score.py` (all 28 pass), which proves the case files and the scorer agree.
Not tested here: a real simulation against the stand-in (it needs the Freya key and a tunnel, and one simulation slot).

Caveat: the stand-in is our reading of the mock from `score.py` and `openapi.json`. Details the real mock does something else with (duplicate promises, exact error texts) can differ.

## Report (`harness/report.py`)

```bash
python tools/run_cases.py <agent_id> --cases test-briefs/cases-c.json --out results/c-rep1.json   # repeat for rep2, rep3 (or use --reps 3)
python harness/report.py results/ --family --md results/c-report.md
```

Counts every run in every file. Prints the mean pass rate, the strict score (a customer counts only when all runs pass, as in the final),
flaky and never-passing customers, a table per customer, and the failure reasons with counts and one call id each.
`results/` is gitignored in this repo, so the outputs stay local.

## Pre-flight before any simulation (Freya credits are limited)

The one procedure is the gate table in `TEST_PLAN.md`. This is where the harness tools fit in:

1. Gate 0/1, free: `python harness/mock_bank.py --selftest` (case files and scorer agree), then the local engine sim. The engine can call the tools through the in-process bank: `from harness.mock_bank import Bank; bank = Bank(api_dict, cases); cid = bank.new_session("TC-01")["variables"]["customer_id"]; status, result = bank.tool("verify_identity", {"customer_id": cid, ...})`, then `score_ledger(case, bank.ledger(cid))` from `tools/score.py`.
2. Free, before lint: `python harness/preflight.py <workflow.json> <tools.openapi.json>` checks the workflow against the brief's tool API file (URLs, body fields, enum values, stale names from another brief, enum values never mentioned). Exit code 1 on errors. Try it on `examples/base-agent.json` against `tools/openapi.json` (0 errors) and against `test-briefs/tools-c.openapi.json` (flags stale names).
3. Gate 2, free: `python ci/lint_workflow.py out/<slot>.workflow.json --dry-run`.
4. Gate 4 to 6, spends credits, only through `python ci/sim.py <agent_id> --workflow <file> --brief X --only <ids> --why "<reason>"`. Variant briefs C/D/E need the stand-in bank behind a tunnel (above), at gate 5 and only once A and B are stable.
