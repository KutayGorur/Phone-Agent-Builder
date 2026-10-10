# Verdicts on external/handoffs/PHONE-AGENT-ACCURACY-REVIEW.md (27 claims)

Checked 2026-10-10 against current main. Evidence is from my own in-memory probes of the generated engine (`engine_code(build_E(spec))`, hand-set extraction variables, no Freya, no live model) plus source reading. As the handoff says, probes bypass the extractor, so "confirmed" means the engine behaves that way given those variables, not that a live call fails at that rate. Line numbers are in `builder/generate/engine_lib.py` unless noted.

Tally: 24 confirmed, 2 partly true (ACC-12, ACC-18), 1 wrong (ACC-25). ACC-17 and ACC-08 had a small fixable part, now fixed (marked FIXED).

| ID | Verdict | Evidence | Action |
|---|---|---|---|
| ACC-01 | Confirmed | Offer 150 then date "tomorrow" reads back 500 on 15 Oct (`offer` :675 falls back to `def_amt`). Date-only edit at read-back gives 500 on 16 Oct. Amount-only edit drops the date and re-asks it (`turn_confirm` :972). | Task 10 |
| ACC-02 | Confirmed | `target_products(st,'car loan')` returns p1 (personal loan), matcher :746 accepts the shared word "loan". | Task 10 |
| ACC-03 | Confirmed | "all" + Friday at read-back: p1 moves to 16 Oct, p2 stays 15 Oct. | Task 10 |
| ACC-04 | Confirmed | `x_product=all, x_amount=150, x_date=tomorrow` reads back 500 and 500. Scope ambiguity caveat is valid. | Task 10 |
| ACC-05 | Confirmed | `ecfg.py:55` `_date_tok` maps any "deadline" text to deadline. G built `pers` = deadline, deadline, deadline although attempt 1 is "next business day after today, capped at deadline" and attempt 3 is a midpoint. | Task 11 |
| ACC-06 | Confirmed | G, 10 days late: offers 100 on 26 Jan for attempt 1 and again for attempt 2, no history check in `refusal` (:626). Depends partly on ACC-05. | Task 10 (history) after 11 |
| ACC-07 | Confirmed | `out/brief-h.spec.json` has `parser.degraded=true`; generated H graph has `init` -> `get_account` (no identity questions) and all four outcome mappings null; F spec carries 2 `unresolved_errors`. `build.py` never reads `spec["parser"]`; dry run sets status ok (:150). | Task 12 |
| ACC-08 | Confirmed, **FIXED** | `validate.py` built `set(reasons)` before type checks and raised TypeError. Now reports a path-specific error for dict/str/nested reasons (3 mutations tested). This is the same exception class as H's saved degrade, but I did not re-run the parser, so H's cause is not proven. | Fixed; follow-up in Task 13 |
| ACC-09 | Confirmed | Hardship + 150 tomorrow clears the offer; declining support then closes `no_promise/hardship` with no promise. | Task 10 |
| ACC-10 | Confirmed | "tomorrow" then "three pm" schedules 2026-10-14 15:00 (today), not the 15th. | Task 10 |
| ACC-11 | Confirmed | `tr_ok=false` after a transfer request still closes `transferred/restructuring` (`transferred` :1186 ignores result). Note/close failure gaps are source-only. Expected outcome on failure is not in the briefs, so needs a decision. | Task 11 (close) / 10 (transfer) |
| ACC-12 | Partly true | After last successful `create_promise` the route is `fin` immediately (`created` :1019), so no post-record turn exists. No brief requires a listening phase; platform barge-in not testable here. | No task; policy question, noted for Kutay |
| ACC-13 | Confirmed | `free_amount` (:246): "150,50" -> 15050, "-150" -> 150, "150 to 200" -> 150, "and fifty pence" dropped. | Task 10 |
| ACC-14 | Confirmed | `ecfg.py:213` `create_promise_max_tries or 2` turns a 0 into 2; other listed gaps are source-backed (presence limit, max_wrong_answers_total, no-repeat unused). Coverage check absent. | Task 11 |
| ACC-15 | Confirmed (low) | `generate.py:17` hardcodes `BASE`; `tools_server` ignored. F/G/H keep the same server so no current failure. | Task 11, low priority |
| ACC-16 | Confirmed (low) | `build.py:36-44` `_run_limited` clamps wait to >=1s and `shutdown(wait=False)` cannot stop a running worker. | Task 12 |
| ACC-17 | Partly fixed | (7) **FIXED**: `tools/score.py` now fails a ledger with more than one `close_call` or an unsuccessful one. Other points hold: parser selftest uses a fake model; `local_sim` skips cases without scripts. The claim that G/H are not wired is stale: `local_sim.py` has `g` and `h` scenario sets; H currently fails 8 cases (same before and after my change, caused by the degraded H spec). | Rest in Tasks 10/12 acceptance tests |
| ACC-18 | Partly true | Single-intent extraction and generic `agree` are real, but this is extraction-risk, not an engine bug, and `x_q` handling exists (:857-866). Historical results are not current-source evidence. | Folded into ACC-24 work in Task 10 |
| ACC-19 | Confirmed | Stop twice at joint read-back closes `no_promise/refused`; both products stay `agreed`, notes empty, note queue empty. | Task 10 |
| ACC-20 | Confirmed | After refusing, "car loan, 250, tomorrow" is agreed on p1 (personal loan); p2 left open. | Task 10 |
| ACC-21 | Confirmed | With `when` removed and rows swapped, validation returns no errors/warnings, `build_E` gives `r_promise: paid`, and a recorded promise closes as `paid`. `ecfg.py:147-178`. | Task 11 |
| ACC-22 | Confirmed | `free_date`: "23/11/2026" -> 23 Oct, "11/06/2026" -> 11 Nov, "two days from now" -> today, "one week from today" -> today. ISO, "23.10.2026", "in two days" work. | Task 10 |
| ACC-23 | Confirmed | Third party "tomorrow" + "07:00" schedules 2026-10-15 19:00 silently. "7 am" correctly re-asks. | Task 10 |
| ACC-24 | Confirmed | `agree` + `x_q=yes` at read-back routes straight to `create` with no answer spoken. | Task 10 |
| ACC-25 | **Wrong** | Executing the generated `fin_unclear`, `fin_wrong_number`, `fin_deceased` code gives "…Thank you for your time. Goodbye." in all three (`ecfg.py:189` goodbye, appended to each `*_say`). Deceased text is "I am sorry for your loss. Thank you for your time. Goodbye." The handoff's claimed omissions do not exist on current main. | None |
| ACC-26 | Confirmed | Product with only id+type: speech says "0.00 past due and 0 days late" and "credit card ending is"; missing product_id becomes invented `p1`. Frequency on live data unknown. | Task 10 (low) |
| ACC-27 | Confirmed | G, two charge cards: first `create_promise` success routes straight to the second create with no speech; sentence appears once in the closing. Applies only to G's per-record rule. | Task 11 (spec field) + 10 |

## Not actioned and why
- ACC-12: needs a policy decision (is a post-record turn required?), not a code fix.
- ACC-25: refuted.
- Handoff proposals to build a general proposal-state framework are broader than needed; Task 10 should add a small per-product pending-proposal dict inside the existing `st` state, not a new framework.

## Additional finding from the task 05 thread
Parser produced empty closing/identity/calendar sections for `test-briefs/brief-h.md` (likely the ACC-08 exception class). Covered by Task 13.
