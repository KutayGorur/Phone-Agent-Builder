# Sunday run-book (hidden briefs open 17:00 UTC, submissions close 20:00 UTC)

Source of truth for rules: `README.md` ("The final", "Rules", "Our builder") and https://www.freyavoice.ai/hackathon.
What the README says about submitting: export each phone agent to `<brief>.workflow.json`, submit those files, the builder code, and one trace per final brief. The exact submission form is NOT documented in the kit; Kutay must confirm it on the hackathon page (see "To confirm" at the end).

Judges run: `python3 builder/build.py <brief> <tool_api>`, no manual step, at most 30 minutes per brief (our default budget is 27, `--budget-min`).

## 1. Freeze (Sunday 12:00 UTC)
- Stop feature work. Only crash fixes after the briefs open, and nothing from a final brief goes into code or prompts (no rule, value, name, date).
- Working tree clean on main, pushed. Gates green:
  ```bash
  python tests/logic/test_logic.py && for f in tests/logic/test_*.py; do python $f; done
  python builder/parse/selftest.py
  python builder/generate/local_sim.py          # expect 0 FAIL lines
  ```
- Tag: `git tag submit-candidate && git push origin submit-candidate`.
- Never commit `env.sh`, `apikey.txt`, `.freya-agents.json` secrets (the file only holds workflow ids).

## 2. Pre-flight (16:30 UTC)
```bash
source env.sh                      # FREYA_API_KEY, FREYA_API_URL, FREYA_BANK_TEAM_KEY
python -c "import freya; print(freya.workspace_id())"     # key valid
python ci/lint_workflow.py out/gen-a.workflow.json --dry-run   # regenerate first if out/ is empty: python -m builder.generate.generate builder/specs/brief-a.spec.json out/gen-a.workflow.json
claude --version                   # parser LLM login (or ANTHROPIC_API_KEY) works; the parse/audit calls fail silently otherwise
df -h .                            # free disk
```
- Clean `out/` and `traces/` of old files so the submitted ones are unambiguous (move, don't delete, anything you want to keep).
- Check `team/comms/SIM-LOCK.md` is empty and nobody else runs a sim on the workspace.
- One cheap platform check if wanted: `python ci/sim.py <agent_id> --workflow out/gen-a.workflow.json --brief A --only PUB-01 --why "sunday preflight"` (1 call).

## 3. When the briefs arrive
1. Save the briefs and tool API files unmodified into a scratch folder outside the repo, e.g. `~/final/` (nothing from them is ever committed).
2. Read each once for format surprises (new section type, other language, renamed codes). Note them in `team/comms/log-<agent>.md` without copying values into code.
3. If one final brief builds on another (like Brief B on A), list both files, tool API last: `python3 builder/build.py ~/final/briefA.md ~/final/briefB.md ~/final/tools.json`. Multi-file builds write `out/<stem1>-<stem2>.workflow.json` (stems joined with `-`, sanitized, max 60 chars) and use that name as the Freya slot; traces go to `traces/<stem1>-<stem2>-<time>.trace.txt`.

## 4. Build (per brief)
```bash
source env.sh && mkdir -p traces
python3 builder/build.py ~/final/<brief> ~/final/<tool_api> 2>&1 | tee traces/<brief>.log
```
- Wall time target under 27 min; typically under a minute for parse+generate+save (fresh clone, Brief A: 44 s).
- Add `--selftest` only if credits allow; it is a smoke test on the practice customers (A/B cases), not meaningful for unseen briefs. Default is off.
- Check after each run:
  - last trace line `[END] status=ok` (not `degraded`, not stub). `status=degraded` means the workflow fell back to `examples/base-agent.json`.
  - `out/<stem>.workflow.json` exists and `out/<stem>.spec.json` was written.
  - the trace lists start/end time, every model call, the Freya resources, no keys: `grep -n "fak_\|FREYA_BANK_TEAM_KEY" traces/*.trace.txt` must be empty.
  - the "audit" model call did not fail (a skipped audit is silent).
- Inspect `out/<stem>.spec.json` against the brief text for the five riskiest facts: calendar (working days, holidays), bands/floors and attempt counts, identity questions and wrong-answer limit, outcome/reason table, queues. Compare the compiler warnings printed during generate ("spec field ... is not read").

## 5. Decision rules
- Spec matches the brief on the five facts: accept.
- A fact is wrong or a section is empty: rerun the parser once (non-deterministic). If still wrong, only a generic parser fix is allowed (e.g. crash on an unexpected table); do not write the brief's values anywhere. Hand-editing the spec with `--spec-file` breaks "no manual step", so use it only for diagnosis, never for the submitted run.
- Two runs may differ; submit the workflow and trace of ONE run (the README allows several runs, submit one run's agent with that run's trace).
- Build fails or degrades twice: submit the degraded export anyway with its trace rather than nothing, and say so in the notes.

## 6. Credits
- Freya credits are limited and show no balance. Max one smoke sim per hidden brief, through `ci/sim.py ... --why "..."`, only after lint and dry run pass. Skip if credits look short. Variant briefs need the mock bank behind a tunnel, so a sim on unseen briefs is only possible when the brief uses the practice case ids; otherwise skip sims.
- Take the sim lock first (`team/comms/SIM-LOCK.md`); one simulation per workspace at a time.

## 7. Submission checklist
- [ ] `out/<stem>.workflow.json` per final brief (file exported by the builder; do not edit by hand)
- [ ] matching trace `traces/<stem>-<time>.trace.txt` per brief
- [ ] builder code at the commit the run used: `git rev-parse HEAD`, pushed to origin (https://github.com/KutayGorur/Phone-Agent-Builder); tag `submit-candidate`
- [ ] working tree clean; no final-brief content in the repo (`git grep` for distinctive strings from the final briefs must be empty)
- [ ] screenshot or copy of the submission confirmation saved to `team/comms/`
- [ ] who clicks submit: Kutay (account owner)

## 7a. Submission (verified 2026-10-10 against https://www.freyavoice.ai/hackathon)
- Delivery: email. "Before 20:00 UTC, send the form below to the address in your kit email." The address is not on the page; find it in the kit email (Kutay).
- Form fields: `team`, `repo`, `commit`, `run_command`, `workflows` (one path per brief), `traces` (one path per brief). Example paths on the page: `submission/hidden-1.workflow.json`, `traces/hidden-1.log` (examples, not a naming rule).
- Run command: `python3 builder/build.py {brief_path} {tool_api_path}`, example `... 2>&1 | tee traces/hidden-1.log`.
- "Submit one phone agent per brief, with the trace of the run that made it. Do not edit a phone agent after the run."
- "Export each phone agent to a file with `freya.export_workflow` and commit the files." Top ten teams: "we clone the repository at that commit", so the commit must include the exports and traces and be pushed.
- Trace: plain text, no required format; start/end time, every model call (model + one-line reason), what was created on Freya (workflow ID, agent ID, steps, tools), any self-test with result. "Remove API keys before you commit." Coding agent session logs are optional.
- Limits: 30 min per brief including self-tests; up to 10 workflows per workspace (the README says 200; keep the workspace tidy anyway).
- Gap to note: our builder writes `out/<stem>.workflow.json` and `traces/<stem>-<time>.trace.txt`; copy/commit them to the paths you list in the form.

## 8. Fallbacks and contacts
- Platform down at 19:00 (errors from `freya.workspace_id()`, or sandbox "Failed to reach snekbox" in sims): a build does not need sims, so run the build anyway; export is a plain GET. Do not burn credits retrying sims.
- Parser LLM down: the builder falls back and the trace says so; rerun once after a few minutes.
- Deadline math: start the final builds by 18:30 so two reruns still fit before 20:00. Submit by 19:30, not 19:59.
- Coordination: `team/comms/BOARD.md`, `SIM-LOCK.md`, inbox files in `team/comms/`.

## To confirm with Kutay before Sunday
1. Submission mechanism: DONE, see 7a. Still needed: the email address from the kit email.
2. Whether the final briefs come as files, and the exact tool API file names.
3. That the judges' machine has `claude` CLI or `ANTHROPIC_API_KEY` for the parser (our parser needs it; see the Brief A fresh-clone note in `log-claude-inan.md`).

## Verified on 2026-10-10 (claude-prep)
- Real `--selftest` on Brief A, our slot: 472 s wall clock, `[END] status=ok model_calls=4` (count now correct), trace has START/STAGE/MODEL/FREYA/SELFTEST/END, no `fak_` key and no bank key in the trace. Self-test result 3/4: PUB-12 (a Brief B case) failed against the Brief A-only agent, which is expected; the default pick does not filter by brief, so pass `--selftest-brief A` (or `--selftest-only`) when self-testing a single brief. Trace timestamps are local time, not UTC.
- Fresh clone of main, multi-file dry run (`build.py --dry-run briefs/brief-a.md briefs/brief-b.md tools/openapi.json`): wrote `out/brief-a-brief-b.workflow.json`, `.spec.json`, `.source.txt` and a trace named `brief-a-brief-b-<time>.trace.txt`. That run ended `status=degraded` because every `claude` CLI call failed after ~3 s with cost 0 (the machine's Claude usage limit, not a builder bug). So: the parser needs a working `claude` login or API key at run time; check this in pre-flight with a real call, not just `claude --version`.
- Freya judge can hang: a sim stayed 'running' for 45+ min on one call whose transcript was fine. Cancel with `POST /api/v2/simulations/<id>/cancel` (`freya.api("POST", f"/api/v2/simulations/{sid}/cancel", {})`). `/stop` does not exist. Builds do not depend on sims.
- Cloudflared is installed on Kutay's machine, but starting a public tunnel was blocked by the session's permission mode, so Brief D has not been simulated against the stand-in bank.

## Fresh-clone dry run, cloud (2026-10-10, no PC, no Freya calls)
- Cloud container, `claude` CLI 2.1.296 logged in (real `claude -p` call works), no `ANTHROPIC_API_KEY`: so a build needs only a working `claude` login or API key, nothing on Kutay's PC. Python 3.13, no pip installs needed.
- Logic tests (5 + 56) OK, parser selftest OK. `build.py --dry-run` ends `status=ok`: Brief A 26 s, A+B 52 s, C 46 s, D 114 s, E 85 s.
- `local_sim.py` crashes on a fresh clone (StopIteration) until `out/brief-c|d|e.spec.json` exist (they are gitignored, only f/g/h specs are committed). Generate first: `for x in c d e; do python3 builder/build.py --dry-run test-briefs/brief-$x.md test-briefs/tools-$x.openapi.json; done`. Needs `FREYA_API_KEY` set to any value for dry run to start? Not required in the run above.
- After that, local_sim shows 2 FAILs on freshly parsed specs: D TD-03 (second promise 480 vs expected 120, overdraft floor) and E TE-04 (leftover steps after close). Likely parser variance on C/D/E; reported to the builder owner, not fixed here.
