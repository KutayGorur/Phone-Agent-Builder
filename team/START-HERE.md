# START HERE (onboarding for a teammate's AI coding agent)

You are joining a hackathon team mid-flight. This file is self-contained. Read it fully, then open `team/comms/PROTOCOL.md` and `team/comms/BOARD.md`, pick a free task in `team/tasks/`, claim it, and work.

## 1. Goal and rules

Hackathon: "Build the Builder" (Freya Voice). We write a **builder**: `python3 builder/build.py <brief files...> <tool_api.json>` reads a bank's brief and creates a debt-collection phone agent (a Freya workflow) with no manual step. Judges run the builder on hidden briefs; the produced agent talks to simulated customers (1 customer = 1 case). Score = share of cases handled.

A case counts only if all hold: (1) the bank's records are right (outcome, promises: product/amount/date, notes, callbacks, transfers; read from the bank, not the transcript); (2) the conversation stayed inside the brief (policy judge); (3) honesty. Read `README.md` ("How you are scored", "Our builder"), `briefs/brief-a.md` and `briefs/brief-b.md` first.

Rules to respect (never break):
- Deadline: Sunday 2026-10-11, submission window 17:00 to 20:00 UTC. Today is Saturday 10 Oct.
- Judges run `python3 builder/build.py <brief> <tool_api>` (briefs first, tool API file last) on hidden briefs. The run must finish within 30 minutes (we budget 27, `--budget-min`) and must pass **3 of 3** runs. Hidden briefs are "raw material" (memos, mail extracts, change lists), not clean specs.
- **No hardcoding of hidden briefs.** Nothing from a specific brief may live in generator code or prompts; brief content flows only through `spec.json` (`builder/SPEC_CONTRACT.md`). We practise on invented briefs C to H for this reason.
- Submission = exported workflow + git commit of the builder + the trace the builder writes (`traces/*.trace.txt`, mandatory; every model call must be recorded via `builder.trace.model_call`).
- Never commit `env.sh`, `apikey.txt`, `.env` (gitignored). Never print keys into logs, traces or comms files.

## 2. Architecture

```
brief(s) + tool API --parse--> spec.json --generate--> workflow.json --save--> Freya --(optional selftest/fix)--> export
   builder/parse/        builder/SPEC_CONTRACT.md     builder/generate/        builder/build.py + builder/trace.py
```

Design principle: the model never decides policy. Per customer turn, model extraction fills a few variables (intent, date, amount, product); ONE engine code node (`builder/generate/engine_lib.py` plus `builder/logic/snippet_lib.py`) updates a JSON call state and writes `instruction` + `route`; a speaking node says the instruction; API nodes make the bank calls with values baked by code. Dates, business days, amount checks and per-product state are deterministic code.

File map:

| Path | What | Notes |
|---|---|---|
| `builder/build.py`, `builder/trace.py` | entry point, time budget, fallback to `examples/base-agent.json` (trace says `status=degraded`), trace writer | flags: `--dry-run` (no Freya), `--spec-file`, `--selftest`, `--selftest-full`, `--selftest-max`, `--selftest-only`, `--budget-min`, `--max-fix-rounds` |
| `builder/parse/` | brief + tool API -> spec.json (LLM via the `claude` CLI or ANTHROPIC_API_KEY) | `HANDOFF.md`, `selftest.py` |
| `builder/SPEC_CONTRACT.md`, `builder/specs/` | the spec shape; golden specs for A and A+B | change only with notice in comms |
| `builder/logic/`, `tests/logic/` | calendar, bands, promise-date checks, DOB normalising | `python tests/logic/test_logic.py` |
| `builder/generate/` | `ecfg.py` (spec -> engine config), `engine_lib.py` (engine code), `generate.py` (node graph), `local_sim.py` (free scripted sim), `PLATFORM_NOTES.md` (Freya quirks, READ), `HANDOFF.md` (design, READ) | |
| `ci/sim.py`, `ci/lint_workflow.py` | the only way to run paid sims; lint + dry run | |
| `harness/` | `mock_bank.py` (stand-in bank), `apply_scripts.py` + `scripts/` (harder customer wordings), `preflight.py`, `report.py`, `make_testset.py` | `harness/README.md`, `harness/HANDOFF.md` |
| `test-briefs/` | invented briefs C to H, tool APIs, case files | H has an answer key `answer-key-h.md` |
| `tools/run_cases.py`, `tools/score.py`, `freya.py` | kit runner, scorer, Freya client | |
| `TEST_PLAN.md` | credit gates 0 to 6 (follow them) | |
| `results/sim-ledger.csv` | every paid sim, appended by `ci/sim.py` | `results/` is gitignored, so the ledger is local per machine |
| `team/` | this onboarding, tasks, comms | |

## 3. Setup

Python 3.10+. Git Bash on Windows works; write long scripts as files, not shell heredocs (they break). `python3` may be `python`.
```bash
git clone https://github.com/KutayGorur/Phone-Agent-Builder.git   # private: Kutay must add you first
cd Phone-Agent-Builder   # work in the folder that has README.md and builder/
cp env.example env.sh
```
`env.sh` is NOT in git. Edit it:
- `FREYA_API_KEY=` your own key from your Freya workspace (API keys page). Your workspace is separate from Kutay's, so you have your own sim slot and credits.
- `FREYA_API_URL=https://staging-app.freyavoice.ai`
- `FREYA_BANK_TEAM_KEY=` use the same value Kutay uses (ask Kutay privately; never via git or comms files).
Then `source env.sh`. Never commit it.

Parser LLM: be logged in to the `claude` CLI, or `export ANTHROPIC_API_KEY=...`. Check with `python builder/parse/selftest.py` (see `builder/parse/HANDOFF.md`).

Free sanity checks (no credits), run first:
```bash
python tests/logic/test_logic.py
python builder/parse/selftest.py
python builder/generate/local_sim.py          # 41 scenarios, must stay green
python builder/build.py --dry-run briefs/brief-a.md tools/openapi.json
```

## 4. Current status (10 Oct ~15:00 UTC)

- Pipeline wired end to end. In Kutay's workspace `gen-a` (agent 44fa9bd3-fe31-4542-9542-fa396fe997c6, v9) and `gen-ab` (bc15d11e-..., v3) are deployed from `out/gen-a.workflow.json` and `out/gen-ab.workflow.json`. `out/` is gitignored: regenerate with `python -m builder.generate.generate <spec> <out>` (specs in `builder/specs/`). Your clone creates its own slots in your workspace on first build or save.
- Results: Brief A 9/10 (1 rep), 7/10 strict over 3 reps; Brief B 3/3 (1 rep, twice). Local sim 41/41.
- Known failures: PUB-10 judge flags the mandated opening "this call is recorded" (judge noise); PUB-06 "minimum offered once" (fix written, local-green, NOT verified on Freya); PUB-04 `x_q` fix (question asked together with an answer) not re-verified; Freya sandbox flakes ("Failed to reach snekbox", "Sandbox did not return a parseable result") at the last runs wasted 4 calls.
- Never run on the platform: `build.py --selftest`, variants C/D/E/F/G/H, `--style` runs, 3-rep Brief B. Spec gaps: A42, A47, A35, A26, transfer-after-promise, B9/B10 notes timing.
- Read `builder/generate/HANDOFF.md` and `PLATFORM_NOTES.md` before touching the generator.

## 5. Freya credit rules (hard)

Credits are limited. Sims and chat turns spend them. Follow `TEST_PLAN.md` gates in order; a change moves up only when the gate below is green.
- Every paid sim goes through `python ci/sim.py <agent_id> --workflow <file> --brief A --only PUB-04,PUB-06 --why "<what changed>"`. It refuses without lint + dry run, and a full or multi-rep run needs `--full`. Always pass `--why`.
- Ledger: `results/sim-ledger.csv`; `python ci/sim.py --ledger` shows spend. Also note spend in your log.
- **One simulation per workspace at a time.** Take the slot lock in `team/comms/SIM-LOCK.md` before any sim (see PROTOCOL.md), even when you think you are alone.
- Before re-running a failed case, read its transcript (`freya.get_call(call_id)` or `builder/generate/dev/showcall.py`), reproduce it in `local_sim.py` (free), then re-sim. Never re-run "to see if it passes now".
- Slow model (median agent turn > 10 s) or sandbox errors are platform problems: wait, do not burn reps.
- Team budget until Sunday: about 15 targeted runs, 6 milestone runs, 2 robustness rounds.

## 6. Platform gotchas

- Chat route (`/api/v2/chat/message`) does not speak the opening tts; use real sims for end-to-end checks.
- `is_set` is true for `''`; lists from `response_mapping` are unusable (rebuild from flattened `<node>_response.data.products.<i>.<field>`); baked numbers are strings; code hops cost about 1 s each. More in `PLATFORM_NOTES.md`.
- Never edit an agent by hand in the UI; do not touch `AGENT_LLM`.
- `.freya-agents.json` is local state (slot -> agent id), uncommitted.
- The organisers' bank rejects unknown case ids; `harness/mock_bank.py` stands in for variant briefs C to H (needs a tunnel, `harness/README.md`).
- Root-level `public-test-set.json` may be an older copy; use the one in the repo.
- Shared checkout rule: no branch switching in a checkout someone else is using; `git add` only your paths; `git pull --rebase origin main` before push.

## 7. Collaboration protocol (summary; full text in `team/comms/PROTOCOL.md`)

1. `git pull --rebase origin main`; read `team/comms/BOARD.md` and your inbox.
2. Claim a task by editing its BOARD row; commit and push to main immediately. If the push conflicts, re-pull and choose another task.
3. Work on branch `task/NN-name`; merge to main through a PR. BOARD, SIM-LOCK, log and inbox edits go straight to main.
4. Heartbeat on the board at least hourly; release the task if you stop.
5. Tasks that edit `builder/generate/` (05, 06, 07, and any fix coming out of 01, 02, 03, 04) are sequential or single-owner; see the table in BOARD.md.
6. Commit only your own paths (`git add <paths>`, never `git add -A`); use your own git name and email.
7. Task 09 (Sunday run-book) is the final procedure. Stop feature work Sunday 12:00 UTC unless the board says otherwise.
