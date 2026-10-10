# Gap analysis (read-only review, 2026-10-10, main at 64fc8a7)

Scope: angles NOT in `accuracy-review-verdicts.md` (ACC-01..27 are not repeated). Nothing was changed or run on Freya. Evidence is from reading code, existing traces/ledger, and two tiny local probes (noted). Ranked by expected impact on the final score. "Size" = rough fix effort.

Context that matters: the Sunday run is on Kutay's own Windows machine (Python 3.14.7, Git Bash, `claude` CLI login, output piped through `tee`), with limited model usage.

## Ranked findings

### 1. The newest generator has never been verified live; the last four live runs were 0/3 (credit cost only)
- Evidence: `results/sim-ledger.csv`. Green runs: 14:03 A 9/10, 14:13 B 3/3, 14:26 A 3 reps 7/10. Then 14:32, 14:39, 14:49 all 0/3 (PUB-04/06/10) and 14:53 0/1. Those were blamed on a sandbox outage and nothing has been run live since, while Task 10 groups 1 to 4 and parser changes landed after that (`git log`: 0513d43, fccef02). START-HERE §4 also says `--selftest`, variants C..H, `--style` runs and 3-rep B were never run on the platform.
- Impact: highest. 24 verdict fixes are local-sim green only; a regression in the engine would hit every customer, and "3 of 3 runs" is unforgiving (A was 7/10 strict before these changes).
- Fix: no code. Spend credits in this order before Sunday: one A milestone and one B milestone on the final commit, then one `--style` pass (`pieces`, `corrects`, `in_words`). Tag the last commit that scores well as the fallback submission.

### 2. Parse has no fallback model, and failures produce either a broken agent or no output at all
- Evidence:
  - `builder/parse/llm.py:101-103` picks API or CLI only by whether `ANTHROPIC_API_KEY` is set; there is no switch to the other backend or to another model when a call fails. A set but unusable key kills the parse even if the CLI works.
  - `traces/brief-g-20261010-191105.trace.txt`: both audit attempts failed instantly with `claude CLI failed (1)` and `total_cost_usd: 0`, the signature of a usage or rate limit. Kutay says usage is limited.
  - `spec_parser.py` `_degraded` (all calls fail) gives a spec with no identity, closing or calendar. `build.py:237-243` then exports it, labelled degraded. That agent skips verification and fails everything.
  - `build.py:212-214`: if the parse subprocess times out (`left()*0.35`, about 9.5 min) or raises, there is no fallback. The outer `except` runs, nothing is exported, exit code 1. A degraded spec at least yields a file, so this is worse.
- Impact: one rate-limit hiccup or a slow Opus call turns a possible pass into 0 on that brief.
- Fix (S to M): on CLI/API failure retry once on the other backend and then on a smaller model (`claude-sonnet-5-5`); catch the parse timeout and fall back to the degraded spec.

### 3. The 27-minute budget is almost unused, and an unready spec is shipped without trying again
- Evidence: parse takes 62 to 185 s in every trace (A 26 s, D 139 s, F 100 s, H 185 s). The 21:43 H run ended `spec not ready ... 2 unresolved parser error(s)` (trace line 24), yet `build.py:221-225` only flags it and proceeds. `readiness_problems()` is computed once, never used to re-parse.
- Evidence of non-determinism: H gave a degraded spec at 19:11 and a different failure at 21:43 for the same input; the parse is a single sample.
- Impact: high on the "raw material" brief, which is the kind most likely to trip the parser.
- Fix (S to M): loop parse up to 2 or 3 times while `readiness_problems(spec)` is non-empty or unresolved errors remain, keep the spec with the fewest problems, and stop at about 50% of the budget. Optionally run 2 samples in parallel and diff the critical sections (identity, outcomes, calendar, bands).

### 4. Request field names and response paths of the bank tools are hard-coded; the tool API is not used to build calls
- Evidence: `generate.py:324-429` fixes the request bodies (`product_id`, `amount`, `date`, `reason`, `queue`, `outcome`, `field`, `answer`, `time`) and the response paths (`data.ok`, `data.state`; `hint == 'day_month_swapped'` at `generate.py:181`). `spec["tools"]` is parsed (`tools_api.py`) but `generate.py`/`ecfg.py` never read it (only `tools_server` for the URL). README: "The seven tool names stay the same. The fields and the allowed values can change."
- I compared the request and response property names of `tools/openapi.json` with all six invented variants (C..H): identical. Only enums and a few response names (`days_late` vs `overdue_days`, via the spec) differ. So a renamed request field or a new required field has never been exercised.
- Impact: if the hidden API renames or adds a request field (for example a required `channel`, or `promise_date`), every bank call returns 400 and every customer fails. Probability moderate-low, severity total.
- Fix: S to catch it (at build time diff the tool block against the names the generator emits, trace it, and degrade loudly), M to generate the bodies from the tool block.

### 5. Windows encoding: one non-cp1252 character in the trace can crash the build or force a degraded parse
- Evidence (my probe): with `PYTHONIOENCODING=cp1252`, `Trace.note('lira ₺ and ş')` raises `UnicodeEncodeError`. `trace.py:_line` writes the file first, then `print`s, so the exception escapes after the write. `grep` shows no `reconfigure`, `PYTHONUTF8` or `PYTHONIOENCODING` anywhere in the builder or run-book. When output is piped (`| tee`) Python on Windows uses the locale code page. Parse notes include model error text and validation text quoting the brief (for example "≥", "→"), and in the parse child process `_note` runs inside the `try` that returns `_degraded(...)`.
- Related: `units.py:load_briefs` does `read_text(encoding="utf-8")`. A mail saved with a BOM, a cp1252 file, or a .docx/.pdf raises and the whole build exports nothing; a BOM also breaks the first rule's number match.
- Impact: low probability, total loss when it hits, and the fix is tiny.
- Fix (S): `sys.stdout.reconfigure(errors="replace")` in `build.py` and in `_CHILD`; read briefs with `utf-8-sig` and `errors="replace"`, and fail with a clear trace line for binary formats. Put `PYTHONUTF8=1` in the Sunday run-book.

### 6. Brief precedence depends on the order of the command-line arguments
- Evidence: `prompts.py:15` "Later material overrides earlier material", `units.py` docstring "File order is precedence order". The README's raw-material brief is several items (mail, policy extract, memo that changes it, code list). If the files are passed alphabetically or in any order with the policy after the memo, the printed extract overrides the memo. The in-file rule ("memo, supersedes, effective") is also in the prompt, but the file-order rule is stated first and is absolute.
- Impact: medium on the raw-material brief; wrong calendar or limits.
- Fix (S): change the prompt so explicit supersede wording and dates beat file order, and pass file order only as a tiebreak. Add one local test with H's files reversed.

### 7. Generator warnings and ignored spec fields are invisible; there is no build-time check that the engine actually runs
- Evidence: `ecfg.py:319-324` returns warnings ("guessed roles, ignored spec fields"), `generate.py` stores them in `LAST_WARNINGS`, and `build.py` never reads that list (grep: no match). `ignored_fields` lists brief rules the parser captured in fields the generator does not implement (`_TOP_CONSUMED`/`CONSUMED`, `ecfg.py:331+`). Self-test is off by default, so the generated engine is never executed before export. `local_sim` covers invented briefs only when someone writes scripts.
- Impact: a rule lost or a role guessed wrongly on a hidden brief is silent, in the trace and in the result.
- Fix (S for the trace and status; M for a build-time smoke): write `LAST_WARNINGS` into the trace and, for ignored non-trivial fields, append them to the system-prompt rules (they already exist as extra_rules text). For the smoke, run `engine_code(E)` through the existing local sim machinery with a few synthetic extraction turns (free) and mark the build degraded if it raises.

### 8. Trace and submission hygiene
- `END ... model_calls=0` in every trace (for example brief-h 21:43: six `[MODEL]` lines but `model_calls=0`) because parse runs in a child process with its own counter (`build.py` `_CHILD`). A judge reading the trace sees a contradiction with the "every model call" requirement.
- `traces/` and `.freya-agents.json` and `.personas.json` are untracked and not in `.gitignore`; the submission needs the trace of the submitted run committed next to the code. Risk of committing the wrong run's trace, or of `git add -A` picking up local state.
- Fix (S): count `[MODEL]` lines when writing END, or have the child report its count; add a Sunday run-book line for which trace and workflow file belong to which brief.

### 9. Workflow slot and output name come from the last file name only
- Evidence: `build.py:179` `stem = Path(briefs[-1]).stem`; slot, `out/<stem>.workflow.json` and the state key use it. Two final briefs whose last file has the same stem (for example both `memo.txt`, or `brief.md` in two folders) overwrite each other's workflow and export. `save_workflow` (`freya.py:35-42`) also trusts `.freya-agents.json`: if it holds an id from another workspace or key (teammates use separate workspaces, see START-HERE §3), the update raises and the build ends with nothing exported.
- Impact: low probability, bad outcome; also racy if two builds run at once (read-modify-write of the state file).
- Fix (S): slot = stems of all briefs plus a short content hash; on a 404 from update, recreate and overwrite the state entry.

### 10. Fragile JSON extraction from model answers costs a retry, and two failures drop a section group
- Evidence: 21:43 H trace: `Extra data: line 1 column 12286` on the intents/closing group, a retry of 53 s. `llm.extract_json` slices from the first `{` to the last `}`, so trailing text containing a brace breaks it. If the retry also fails, the group stays null and is left to repair.
- Fix (S): use `json.JSONDecoder().raw_decode` from the first `{`, and try fenced blocks first.

### 11. Spoken text is English-only and currency-less
- Evidence: fixed phrases in `generate.py` ("I am sorry, I did not catch that. Could you say it again, please?", "Say thank you in two words", "And the rest?", "I am sorry, I could not connect you."), and the amount handling in `engine_lib.py` (`£$€` only recognised when parsing a negative sign). `meta.language` is only a system-prompt prefix.
- Impact: only if a hidden brief is non-English or uses another currency format; the README describes "other numbers, limits, questions, calendar", so likely English.
- Fix (M): leave as is, but note it in the judge section.

## Checked and fine (no action)
- Kit files unchanged: `freya.py`, `tools/run_cases.py`, `tools/openapi.json`, `VERSION`, `public-test-set.json` are byte-identical to the v3 zip, so `AGENT_LLM` is untouched. `tools/score.py` differs from the zip (check it is intentional, it is not part of the build).
- Time cap: builds take 1 to 3 min, far below 30 min; the tie-break on build time is not a concern. Watchdog and `os._exit` exist.
- Engine code (67 KB) parses under Python 3.8 and 3.10 grammar (`ast.parse(feature_version=...)`), so a different sandbox version is not a syntax risk. No `match`/walrus.
- Paths with spaces work (all runs here are in a path with spaces); subprocesses use `sys.executable`, not `python3`.
- More than 3 products: no hard-coded cap found in `generate.py`/`ecfg.py`.
- Workspace cap: re-runs update in place; fine unless finding 9 hits.

## Not verified here
- Whether a judge-run machine other than Kutay's has the `claude` CLI and the `--tools ""` and `--no-session-persistence` flags (CLI-version dependent, `llm.py:51-53`).
- Anything on Freya itself.

Nothing in this file has been fixed. Fixes wait for Kutay's approval.
