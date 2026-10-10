# Test plan (credit-safe)

Freya platform credits are limited (Kutay, 10 Oct). Simulations and chat turns spend them; everything below gate 3 is free.
Every thread follows these gates in order. A change only moves up a gate when the gate below it is green.

| Gate | What | Cost | Command |
|---|---|---|---|
| 0 | Unit tests | free | `python tests/logic/test_logic.py`, `python builder/parse/selftest.py` |
| 1 | Local engine sim: every scripted path asserts the expected close outcome, reason, promises, notes, transfers (PUB-01..13 and the variant cases in `test-briefs/cases-*.json`) | free | `python builder/generate/local_sim.py` (generator thread: make it assert, not just print) |
| 2 | Workflow lint + Freya dry run (schema check, stores nothing) | free | `python ci/lint_workflow.py out/<slot>.workflow.json --dry-run` |
| 3 | Chat smoke: 2 to 4 turns via `POST /api/v2/chat/message` to check the agent starts and speaks | small | only when gate 2 passes and the graph changed shape |
| 4 | Targeted sim: only the cases a change touches | 1 call per case | `python ci/sim.py <agent_id> --workflow <file> --brief A --only PUB-04,PUB-06 --why "<what changed>"` |
| 5 | Milestone sim: full brief, 1 rep | 10 (A) or 3 (B) calls | `python ci/sim.py ... --brief A --full --why "milestone ..."` |
| 6 | Robustness sim: full brief, `--reps 3`, then one `--style` at a time | 30+ calls | only on a candidate we might submit |

Rules:
- All simulations go through `ci/sim.py`. It refuses to run without a passing lint and dry run, refuses a full or multi-rep run without `--full`, and logs every run to `results/sim-ledger.csv`. `python ci/sim.py --ledger` shows the total spent so far.
- A failed simulated case is debugged from its transcript (`freya.get_call(call_id)`) and reproduced in gate 1 before re-simulating. Never re-run a sim to "see if it passes now".
- Model slowness (median slow turn > 10 s) is not our bug; wait and repeat later rather than burning reps.
- Variant briefs C/D/E need the stand-in bank behind a tunnel (`harness/README.md`); run them at gate 5 only once A and B are stable.
- The final builder's `--selftest` (in `build.py`) counts as gate 5: at most one full run per brief inside the 30-minute budget.

Rough budget until Sunday 17:00 UTC (adjust when we know the credit size): about 15 targeted runs, 6 milestone runs, 2 robustness rounds.
