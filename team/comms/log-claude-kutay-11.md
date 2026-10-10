# Log claude-kutay-11 (task 11, spec compiler fixes)

## 2026-10-10T19:10Z
- ACC-05: `_date_tok` now returns explicit tokens (week_end, deadline, today, next_business_day, capped_next_business_day, midpoint, unknown + warning). F/G attempt 1 = capped_next_business_day, G attempt 3 = midpoint (bd 3). Engine support for the new tokens requested from task 10 (inbox).
- ACC-21: outcome roles chosen from structure; `when` only breaks ties and warns; two roles on one outcome warns. Tested with `when` removed and rows reversed on A, F, G.
- ACC-14: `create_promise_max_tries` 0 stays 0 (engine `or 2` still to fix, task 10). `ecfg.ignored_fields` + `build_E_warn` list unread spec fields; generate prints them (stderr) and keeps `LAST_WARNINGS`.
- ACC-11: failed transfer (tr_ok not true) goes to new `transfer_failed` node: promise outcome if cp_ok is true, else the spec's service-error close; close_call retried once on request failure. Documented in SPEC_CONTRACT.md (HANDOFF.md is not in my file list).
- ACC-15: tool URLs from `tools_server` (invalid -> default + warning).
- ACC-27: `confirmation.acknowledgement_scope` per_call|per_record (G's `after_recorded_say_after_each_record` maps to per_record) compiled into `E['ack_scope']`; engine side is task 10.
- Tests: tests/logic/test_compiler.py (14). Whole logic suite 83 OK, local_sim 54 pass / 8 fail (same 8 H failures as before).
