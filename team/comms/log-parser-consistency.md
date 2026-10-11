# log-parser-consistency (cloud thread "Parser consistency", 2026-10-11 overnight)

No Freya calls. The `claude` login works in the cloud container (one parse ~2 min; the cross-check second extraction ~30 s).

## Built (all on main, each with tests; gates green: logic tests, parser selftest, local_sim 0 FAIL, build-status test)
- **Parse twice** (`builder/parse/consistency.py`, `spec_parser.cross_check`, `build.cross_check_parse`): after the first parse, a child process re-runs the three
  extraction calls, compiles both specs and compares 12 critical facts. A disagreement is settled by (1) the safer value (holidays union, business days
  intersection, larger identity limit, outcome reasons union), (2) one model re-ask that must name a brief unit and quote its words (a quote not in that unit
  is ignored; options alternate position), (3) the first parse. Every write is re-compiled and undone unless it gives exactly the chosen value and moves no
  other fact. Disagreements go to the trace (`parse cross-check: ...`) and `spec.parser.consistency`. Skipped with less than 12 min left or when the parser is
  swapped (tests). Live check on Brief E: the second parse agreed on all facts. Cost: ~30-90 s of model time, inside the budget.
- Shape guard (`generate/sanitize.py`, `build.shape_guard`): wrong-typed sections are coerced or dropped before anything reads the spec (the I/J/K crash).
- Engine: while an offer is pending a question never names the floor again (PUB-06); `local_sim.drive(..., said=[])` captures spoken instructions.
- extra_rules that repeat a generated line or an earlier extra rule (>75% word overlap) leave the system prompt (listed as compiler warnings).
- Tricky-brief findings: B2 per-product amount field, B3 floor rounding and greater-of, B4 reason on every outcome, B5 callback "next N working days",
  B6 calendar-day deadlines, B8 identity schemes (digits, spoken digits and years, letters-and-digits, accent folding) + idea 5a, B9 spoken amounts and
  article grammar. Contract additions are at the end of `builder/SPEC_CONTRACT.md`.
- B7 (renamed routes/params, units in brief K): not adapted. README says the seven tool names stay the same and brief H says the parameter names are unchanged,
  so a real adapter was judged not worth the risk. Done instead: generated local scenarios skip with a note when the API lacks the standard routes (K no longer
  reports 95 failures); `tool_contract_problems` still labels such a build degraded.

## Open / ideas
- Idea 4 (non-English phrase table), idea 7 (end-of-call self-check of extra rules) not started.
- `auto_sim.floor_of` mirrors the engine's floor logic (same rounding rule); an independent oracle would catch shared mistakes.
- A build that drops a malformed section is degraded; check the trace line `shape guard:` when a final brief builds degraded.
