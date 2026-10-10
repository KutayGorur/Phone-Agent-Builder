# Parser handoff (builder/parse/, builder/specs/)

## Done
- Golden specs `builder/specs/brief-a.spec.json` and `brief-ab.spec.json` (hand-checked, on main). `rule_coverage` in them maps every brief unit to spec paths.
- `parse(brief_paths, tool_api_path) -> dict` in `builder/parse/spec_parser.py` (exported from `builder.parse`). Steps:
  1. `units.py` splits the briefs into addressable units (rules, sub-clauses `9.4`, lettered/bullet items `p12.a`, tables `t1`, paragraphs `p3`; ids get a file tag like `a:39` when several files are given).
  2. `tools_api.py` builds the `tools` block from the OpenAPI file (never from a model).
  3. Three parallel model calls (sections groups g1/g2/g3, `prompts.py`), then `validate.py` (coverage of every unit, tool-API enums, bands, grounding of dates/numbers), one audit call, one or two repair calls.
  4. Output has extra additive keys: `tools_server`, `rule_coverage`, `parser` (models, seconds, warnings, open_questions).
  5. If no model works, `parse` returns a degraded spec: every brief unit as an `extra_rules` sentence (`parser.degraded: true`).
- `llm.py`: stdlib only. Uses `ANTHROPIC_API_KEY` (HTTPS) if set, else the `claude` CLI (`claude -p`, tools off, long prompt via stdin). Every call goes through `trace.model_call(model, purpose)`. Model: env `PARSER_MODEL` (default `claude-opus-5-5`), `PARSER_AUDIT_MODEL`, budget `PARSER_BUDGET_S` (default 480 s).
- `python builder/parse/selftest.py`: offline plumbing test with a fake model returning the golden spec (passes for A and A+B).
- CLI: `python -m builder.parse.spec_parser <brief...> <tools.openapi.json> --out out/x.spec.json`. Debug output of each model call goes to `out/parse/`. `PARSER_REPLAY_DIR=dir` dumps prompts and reads `<slug>.answer.txt` instead of calling a model.

## Real-model results (claude login worked after Kutay logged in)
- Brief D (raw: mail + policy + overriding memo + code list): 3.5 min, memo overrides applied (bands, holidays, callback window, attempt 1 date, "speaking" no longer accepted), codes used as outcomes because tools-d enums are code-style. Checked by eye, looked right. After this run I changed the prompt to forbid `effective_from` fields and made prose coverage values non-fatal; D was re-run into `out/d.spec.json` but not re-inspected.
- Brief A: matches the golden in meta, call_variables, opening, third_party, identity, debt_statement, calendar, bands, persuasion, confirmation, multi_product; small wording diffs in dates, amounts, intents, closing (the worked example in the prompt is brief A itself, so this is not a generalisation test).
- Brief E (A+B+E change list): all overrides applied (3 bands, new holidays, postcode field, 4 wrong answers, 09:00 window, new sentences, max_products 2). 90 s.
- Brief C was started, result in `out/c.spec.json`, not inspected.

## Next steps
1. Inspect `out/c.spec.json` and the re-run `out/d.spec.json` (check `parser.unresolved_errors`, `open_questions`).
2. Feed the three specs to the generator and see what it misses; adjust spec fields with the integration lead if the generator needs different shapes (Contract changes go through the planning thread).
3. Optional: dedupe near-duplicate `extra_rules` (D had 55, many repeats); wrong `source` ids occasionally (e.g. D "6.6" for a rule from 8.2).
4. Open question for the lead: memo effective dates are ignored (final state assumed), noted only in `open_questions`.
5. If time is short at the final run, set `PARSER_AUDIT_MODEL` to a faster model; a full parse takes 1.5 to 4 min.

## Gotchas
- `python` here is MSYS Python without pip: keep everything stdlib. A shell `claude -p` only works if `claude auth status` says loggedIn.
- Windows command lines are limited to ~32k chars: never pass the system prompt as a CLI argument (it goes via stdin).
- Do not edit `builder/SPEC_CONTRACT.md` from here.
