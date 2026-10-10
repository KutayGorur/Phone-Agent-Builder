# builder/logic handoff

**Done (pushed, commit abb77ef):** snippet_lib.py (pure logic), config.py (spec -> cfg), render.py (6 snippets), README.md (snippet inputs/outputs), tests/logic/test_logic.py (56 tests, all pass: `python tests/logic/test_logic.py`).

**In progress:** nothing.

**Next steps:**
- Generator wires snippets into `code` nodes (`render_snippet(name, spec, var_map, out_prefix)`), using output var names from README.md.
- Run one rendered snippet on the real platform to confirm the sandbox accepts it (only `re`, `datetime`, `json` used; not yet verified on Freya).
- Brief B: per-product runs via `var_map` + `out_prefix`; check `bands` deadlines with its spec; add any new snippets needed.
- Decide whether `calendar.week_start` (optional, read by config.py) goes into SPEC_CONTRACT.md (kickoff thread owns it).

**Gotchas:** weeks are Mon-Sun by default; bare callback times like "3" give `ambiguous_time`; impossible numeric DOB readings are `invalid`, never guessed; missing spec sections only add `cfg['warnings']`; missing business_days defaults to Mon-Fri.
