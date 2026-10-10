# Build the Builder

**Kit version 3** (10 October 2026). The file `VERSION` holds the number. When we update the kit, the number goes up and the changes are listed here.

- v3: the example builder waits for its own test run (up to 20 minutes per command) instead of stopping before the results arrive. On Brief A it built an agent that passed 10 of the 10 practice customers in one run.
- v2: `examples/base-agent.json` (an example phone agent) and `examples/agent_builder.py` with the skill `.claude/skills/build-phone-agent` (an example builder) replace `examples/minimal_builder.py`.
- v1: first release.

You write a **builder**: a program that reads a bank's brief and creates a phone agent on Freya.
We put that phone agent in front of simulated customers. The share it handles correctly is your score.

One simulated customer is one case. A step of a phone agent is called a node in the platform's documents.

## The ten-minute start

You need Python 3.10 or newer.

```bash
cp env.example env.sh        # put your Freya API key in it, and a team key you make up
source env.sh

# 1. Put the example agent on Freya and test it. It prints {"workflow_id": ..., "agent_id": ...}
python3 -c "import freya,json; print(freya.save_workflow('base', json.load(open('examples/base-agent.json'))))"
python3 tools/run_cases.py <agent_id> --brief A            # ten practice customers, 3 to 11 minutes

# 2. Let the example builder build one from the brief
pip install claude-agent-sdk
python3 examples/agent_builder.py briefs/brief-a.md
python3 examples/agent_builder.py briefs/brief-a.md briefs/brief-b.md   # Brief B builds on Brief A, so pass both
```

`run_cases.py` prints one line per customer: pass or fail, the tool calls the agent made, and the reason for a failure.

`examples/base-agent.json` is an agent, not a builder. It is the same two-step workflow that is already in your workspace: check identity, then take a payment promise. It uses four of the seven tools, so it handles only the simplest customers: in one run it passed 2 of the 13 practice customers. Read it to see what a valid workflow looks like.

`examples/agent_builder.py` is a builder. It runs Claude through the Claude Agent SDK with one skill, `.claude/skills/build-phone-agent/SKILL.md`. Claude reads the brief and the tool API file, writes the workflow, runs the practice customers and fixes what fails. The skill is short on purpose. Your job is a better builder: a better skill, more skills, your own code, or another agent altogether. It needs a Claude login or `ANTHROPIC_API_KEY`.

## What is in this kit

| Path | What it is |
|---|---|
| `briefs/brief-a.md` | Freya Bank's specification for customers late on one product. 47 rules. Read all of it. |
| `briefs/brief-b.md` | The extra rules for customers with up to three products. It builds on Brief A. |
| `tools/openapi.json` | The bank's tool API that the phone agent calls during a call. |
| `public-test-set.json` | 13 practice customers: what each one does and what the bank's records must show afterwards. |
| `examples/base-agent.json` | An example phone agent: two steps, four tools. The same one that is in your workspace. |
| `examples/agent_builder.py` | An example builder on the Claude Agent SDK. Claude builds, tests and fixes the agent. |
| `.claude/skills/build-phone-agent/SKILL.md` | The one skill the example builder uses. |
| `freya.py` | A small client for the Freya API. Standard library only. |
| `tools/run_cases.py`, `tools/score.py` | Run the practice customers against a phone agent and score it. |
| `docs/workflow-format.md` | What a phone agent is made of: steps, prompts, variables, routes. |
| `docs/tools-and-code.md` | Tools that call an API, code steps, hooks, where a tool's response lands. |
| `docs/api.md` | The API calls a builder needs. |

## How you are scored

A customer counts as handled when all of these hold:

1. **Outcome: the bank's records are right.** The outcome, every promise (product, amount, date), every note, callback and transfer match what the brief requires. The scorer reads them from the bank, not from what the agent said.
2. **Policy: the conversation stayed inside the brief.**
3. **Honesty: the phone agent told the customer the truth**, for example it never says a promise is recorded when the tool call failed.

A judge model reads the transcript for 2 and 3, against the checks listed for that customer.

There is no partial credit. Your score is the share of customers handled.

The same phone agent can pass a customer in one run and fail it in the next. Treat one green run as a hint, not as proof.

## The final

- On Sunday we publish briefs you have not seen. They are the same kind of call with different rules: other numbers and limits, other identity questions, another outcome table, another calendar. Their form can differ too: one final brief is a clean specification, the other is raw bank material (a mail, a policy extract, a memo that changes it, a code list).
- Each final brief comes with its own tool API file. The seven tool names stay the same. The fields and the allowed values can change.
- After the final briefs open you may fix a bug in your builder. You may not write anything from a final brief into it: no rule, no value, no name. Fixing a crash on a table your parser did not expect is allowed. Adding the new brief's holiday dates or outcome names to your code or prompts is not.
- You run your builder once on each, with no manual step, and submit the phone agents it created, your code and the builder's trace.
- You export each phone agent to a file with `freya.export_workflow(workflow_id, "<brief>.workflow.json")` and submit those files. We load them into our own workspace to test them, so what you export is what we score.
- We test those phone agents on customers nobody has seen, on several calendar days, three times each. A customer counts only when all three runs pass. A phone agent that is right most of the time is not right.
- Final customers can have up to three products, as in Brief B.
- Final customers talk like people. They give a number in two parts, correct themselves, talk about other things, ask a question back, or say amounts and dates in words. The facts stay the same. Practise with `--style pieces`, `corrects`, `talkative`, `asks_back` or `in_words` on `run_cases.py`.

So build something that reads a brief, not something that knows this one. Whatever your builder can take from the brief, it should take from the brief.

## Rules

- Your builder takes brief files as input and creates the phone agent with no manual step. Do not edit a phone agent by hand after it is created.
- The phone agent runs on the model set in `freya.py` (`AGENT_LLM`). Do not change it. Your builder may use any model or coding agent.
- The phone agent may call only the bank's tool API. Code steps and hooks inside the workflow are allowed and expected.
- Use `freya.save_workflow(...)` or update your workflow in place. A workspace holds 200 workflows. A builder that creates a new one on every run fills it up and leaves you with a list nobody can read.
- One simulation runs at a time per workspace. A ten-customer run takes 3 to 11 minutes. A second `run_cases.py` started meanwhile waits for the first.
- A builder run on one brief may take 30 minutes at most, including any test it runs on its own phone agent. You may run it more than once and submit the phone agent of one run, with that run's trace.
- Equal scores are ranked by the total promised amount on the customers that passed, then by shorter build time, then by earlier submission.
- Your builder must leave a trace of each run: start and end time, each model call it made (model and a one-line purpose), what it created on Freya, and any test it ran on its own agent. Plain text, no fixed format. You submit one trace per final brief.
- All data here is synthetic. Do not bring real customer data.

## When something does not work

- `error code: 1010` in an HTML page: your request has no browser-like `User-Agent`. `freya.py` sets one.
- `Workspace plan limit reached`: you created too many workflows. Update one in place.
- You changed your builder and the score did not move at all: an updated workflow must be published before a simulation uses it. `freya.save_workflow` publishes. A plain `PUT` does not. See "Update a workflow" in `docs/api.md`.
- A customer fails and you do not see why: `freya.get_call(call_id)["messages"]` is the full transcript with the tool calls. `run_cases.py --out results/run.json` saves the call id of every customer.
- Calls end as `customer-ended-call` before the phone agent is done: it was silent too long and the customer hung up, as a person would. `run_cases.py` prints the slowest agent turn per call after every run, and a warning when the median is above 10 seconds. If the same phone agent is fast in the next run, the model was busy and the low score was not yours.
- You want to see what your phone agent says without waiting for a simulation: `POST /api/v2/chat/message` runs one turn at a time. See `docs/api.md`.
- The bank answers `unknown product_id`: the model made an id up. Product ids come from `get_account` (`p1`, `p2`, ...). Give them to the model in the tool result, or fill them in with code.
- A simulation stays at "running" and no call ever starts: the workflow cannot start a call. Try one chat turn. Leave `agent_config` out of the workflow you send.
- The agent says nothing after a tool call and the customer hangs up: see "Tool results and the next turn" in `docs/tools-and-code.md`.

## Our builder

`builder/build.py` turns brief files plus a tool API file into a phone agent on Freya, with no manual step.

```bash
source env.sh                       # FREYA_API_KEY, FREYA_BANK_TEAM_KEY (never commit it)
mkdir -p traces
python3 builder/build.py <brief> <tool_api> 2>&1 | tee traces/<brief>.log
python3 builder/build.py <brief_a> <brief_b> <tool_api>        # a brief that builds on another: list both, the tool API file goes last
```

- The last file is the tool API file; every file before it is a brief. The last brief names the Freya slot and the output.
- Pipeline: parse (`builder/parse`) -> spec.json -> generate (`builder/generate`) -> `freya.save_workflow` -> optional self-test and fix -> `freya.export_workflow`. The contract between the stages is `builder/SPEC_CONTRACT.md`.
- Output: `out/<brief>.workflow.json` (submit this), `out/<brief>.spec.json` (the parsed spec), and the trace `traces/<brief>-<time>.trace.txt`.
- The trace lists start and end time, every model call (model and purpose, recorded by the stages through `builder.trace.model_call`), the Freya resources created or updated, and any self-test with its result. API keys are redacted. The `tee` copy of the console output is the same text.
- Time: the whole run stays inside 27 minutes by default (`--budget-min`); the event allows 30. Parse and generate get time slices, and a self-test round is only started if enough time is left for a full practice run.
- Credits: Freya simulations are limited and every self-test goes through `ci/sim.py` (lint, dry run, `results/sim-ledger.csv`); `--selftest-full` makes the first run cover the whole brief, and a run after a fix only repeats the failed customers. `--dry-run` runs parse and generate only (no Freya calls). `--selftest` is off by default and, when on, runs a frugal set (one customer per family, hardest first, at most `--selftest-max 4`; `--selftest-only PUB-06,PUB-07` or `--selftest-cases <file>` to choose, `--selftest-max 0` for all) for at most `--max-fix-rounds 1` fix round. If `builder/fix.py` provides `fix(spec, workflow, failed_ids) -> workflow` it is applied between rounds. Practice customers are written for Briefs A and B, so on unseen briefs the score is a smoke test. `--spec-file` skips parse for development.
- If generate fails or the workflow does not validate, the builder falls back to `examples/base-agent.json`, so a valid agent is always exported; the trace says `status=degraded`.
- Re-running a brief updates the same Freya workflow in place (state in `.freya-agents.json`), so the workspace is not filled up.
- If `builder.parse` or `builder.generate` cannot be imported, `build.py` uses stubs that export the example agent; the trace says so.

### How it works and where it is limited (for judges)

**Approach.** The builder parses the brief files and the tool API into `spec.json`, generates a Freya workflow from that spec, saves it, optionally self-tests and fixes it, and exports the workflow. Dates, business-day counts, amount checks, per-product state and tool arguments are computed by deterministic code inside the agent's engine node. A model only extracts what the customer meant (intent, date, amount, product) and speaks the instruction the engine produces.

**Why a spec contract.** Parser and generator only talk through `spec.json` (`builder/SPEC_CONTRACT.md`): calendar, bands, floors, identity questions, outcome table, queues and tools have structured fields, and rules that do not fit a field go into `extra_rules` with their source rule. Nothing from the brief is hard-coded in the generator, so a brief with other holidays, bands or outcome names changes the spec, not the code. It also lets us review parsing separately from generation and run policy logic without a simulated call.

**Overfitting.** We practise on invented briefs C, D and E (D is a long memo, E a change list on A+B) next to the kit's A and B, and `test-briefs/` also holds the invented F, G and H (H is raw mail/policy extracts with a later memo and a renamed code list; its amendment key is `answer-key-h.md`). `builder/generate/local_sim.py` feeds scripted extractions into an in-process stand-in bank and the real scorer: all 41 scripted scenarios currently pass. This covers PUB-01, 02 and 04 to 13 plus the C, D and E cases; PUB-03 has no local script, and F, G and H are not yet covered by it. It checks policy paths, not how well the live model extracts real speech. Harder customer wordings live in `harness/scripts/` and are merged into case files by `harness/apply_scripts.py` (output in `out/hard/`) for use with the Freya simulator. No final-brief content is written into code or prompts.

**Credit-safe testing.** `TEST_PLAN.md` defines gates 0 to 6: unit tests, local engine sim, lint plus Freya dry run (all free), then a chat smoke test, targeted sims, one milestone sim and a robustness run (`--reps 3`, one `--style` at a time). Paid runs go through `ci/sim.py`, which lints, dry-runs and records each run in `results/sim-ledger.csv`. We reproduce a failure locally before paying for another run.

**Reliability.** A customer counts only if records, policy and honesty all pass, and all three final runs must pass, so a single green run proves little. The last generator handoff reports Brief A at 9/10 in one rep and 7/10 over three reps, and Brief B at 3/3; a recurring failure is a judge flagging the mandated opening "this call is recorded". If generation or validation fails, `build.py` exports `examples/base-agent.json` and the trace says `status=degraded`; that is an artifact, not a policy-compliant agent. The trace records start and end, every model call, Freya resources touched and any self-test.

**Known limits.** The self-test and fix loop was only checked with a fake runner against real wiring, because Freya returned 503 errors; extraction accuracy on the intent enum, "transfer after promise" and some platform behaviour are weakly tested on the live platform (`builder/generate/HANDOFF.md`). The spec for A+B may omit or blur a few rules, such as an explicit thank-you before closing and the "if they insist" condition for human transfer. Brief rules that conflict, such as transfer after a promise or when notes are written before a transfer, may be resolved differently than intended.
