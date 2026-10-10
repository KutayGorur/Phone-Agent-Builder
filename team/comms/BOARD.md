# Task board

Status values: free / claimed / in-progress / blocked / done. Times are UTC. Edit only your own row (plus a free row you claim). Commit and push to main right away.

"Sim" = uses the Freya sim slot (take the lock in SIM-LOCK.md). "Gen" = edits `builder/generate/` (one owner at a time; do these in order 06, 07, then 05 may run in parallel because it only owns `local_sim.py`).

| Task | File | Sim | Gen | Depends on | Owner | Status | Claimed at | Branch | Last update |
|---|---|---|---|---|---|---|---|---|---|
| 01 smoke check + PUB-04/06/10 retry | tasks/01-smoke-and-retry.md | yes | fixes only | none | | free | | | |
| 02 Brief A x3, A+B x3, styles, hard scripts | tasks/02-robustness-runs.md | yes | fixes only | 01 | | free | | | |
| 03 real build.py --selftest + trace review | tasks/03-selftest-and-trace.md | yes | no | 01 (agent must run) | | free | | | |
| 04 real Brief D sim via tunnel + mock bank | tasks/04-brief-d-real-sim.md | yes | fixes only | 01 | | free | | | |
| 05 wire briefs F/G/H into local_sim.py | tasks/05-local-sim-fgh.md | no | `local_sim.py` only | none | claude-kutay | claimed | 2026-10-10T16:10Z | task/05-local-sim-fgh | 2026-10-10T16:10Z |
| 06 spec gaps A42, A47, A35, A26, transfer-after-promise, B9/B10 | tasks/06-spec-gaps.md | no | yes (ecfg, engine_lib, parse) | none | claude-inan | done (PR #1, awaiting merge) | 2026-10-10T16:54Z | task/06-spec-gaps | 2026-10-10T16:57Z |
| 07 guard against repeating last line after engine failure | tasks/07-engine-failure-guard.md | no | yes (engine_lib, generate.py) | after 06 | claude-inan | done (PR #2 on top of #1, awaiting merge) | 2026-10-10T16:57Z | task/07-engine-failure-guard | 2026-10-10T16:59Z |
| 08 fresh-clone dry run on A and D, timed | tasks/08-fresh-clone-run.md | no (workflow save only) | no | 05, 06, 07 merged | | free | | | |
| 09 Sunday run-book + submission | tasks/09-sunday-runbook.md | no | no | all | | free | | | |

Merge order for generator work: 06 -> 07 -> (01/02/03/04 fixes, small PRs). Anyone needing a generator change outside their task puts a request in the owner's inbox.
