# log-claude-autosim (cloud thread: unseen-brief upgrades)

## 2026-10-10 idea 1 done: generated local scenarios
- `builder/generate/auto_sim.py`: makes up a customer from the spec and the tool API (identity truth, products per band and type, call time on an ordinary day and on the day before the first holiday), derives scenarios (pay full, refuse, floor offer, too much, below floor, late/past/weekend/holiday dates, every intent, wrong identity answers, third parties, create_promise failing once / always) and drives them through the compiled engine and the in-process bank. No Freya calls, no model calls.
- Checks brief-independent invariants on the ledger (one close, outcome pair in the spec table and accepted by the API enums, promise amount/date inside floor, past due, business day, deadline, notes, callbacks, bank refusals) plus expectations that come from the spec itself.
- `builder/build.py` runs it after the tool contract check (stage "local scenarios", about 5-15 s, own time slice). Findings are trace errors and `out/<stem>.autosim.txt`; they do not change the build status. Skipped with a note when the spec is not ready or the tool API is not OpenAPI.
- Green on A (70 scenarios), A+B (93), F (51), G (113), H (83). Mutation checks: dropping an outcome from the table or using an outcome the API rejects is reported.
- `drive()` in local_sim.py got `raw` and `cycle` options; variant specs missing on a fresh clone (C/D/E live in gitignored out/) are now skipped instead of crashing the run.
- Test: `python3 -m unittest tests.logic.test_auto_sim`. CLI: `python -m builder.generate.auto_sim <spec> <tool_api> [-v] [--only name]`.
