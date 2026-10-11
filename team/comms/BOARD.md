# Task board

Status values: free / claimed / in-progress / blocked / done. Times are UTC. Edit only your own row (plus a free row you claim). Commit and push to main right away.

"Sim" = uses the Freya sim slot (take the lock in SIM-LOCK.md). "Gen" = edits `builder/generate/` (one owner at a time; do these in order 06, 07, then 05 may run in parallel because it only owns `local_sim.py`).

| Task | File | Sim | Gen | Depends on | Owner | Status | Claimed at | Branch | Last update |
|---|---|---|---|---|---|---|---|---|---|
| 01 smoke check + PUB-04/06/10 retry | tasks/01-smoke-and-retry.md | yes | fixes only | none | claude-inan | done (PR #3 merged) | 2026-10-10T17:33Z | task/01-opening-wording | 2026-10-10T17:41Z |
| 02 Brief A x3, A+B x3, styles, hard scripts | tasks/02-robustness-runs.md | yes | fixes only | 01 | claude-inan | done (PR #4 merged) | 2026-10-10T17:48Z | task/02-identity-in-parts | 2026-10-10T18:46Z |
| 03 real build.py --selftest + trace review | tasks/03-selftest-and-trace.md | yes | no | 01 (agent must run) | | claude-prep | done | 2026-10-10T20:50Z | main | 2026-10-10T20:50Z |
| 04 real Brief D sim via tunnel + mock bank | tasks/04-brief-d-real-sim.md | yes | fixes only | 01 | | claude-prep | blocked: tunnel start denied | 2026-10-10T20:50Z | main | 2026-10-10T20:50Z |
| 05 wire briefs F/G/H into local_sim.py | tasks/05-local-sim-fgh.md | no | `local_sim.py` only | none | claude-kutay | done | 2026-10-10T16:10Z | main | 2026-10-10T16:30Z |
| 06 spec gaps A42, A47, A35, A26, transfer-after-promise, B9/B10 | tasks/06-spec-gaps.md | no | yes (ecfg, engine_lib, parse) | none | claude-inan | done (PR #1 merged) | 2026-10-10T16:54Z | task/06-spec-gaps | 2026-10-10T17:41Z |
| 07 guard against repeating last line after engine failure | tasks/07-engine-failure-guard.md | no | yes (engine_lib, generate.py) | after 06 | claude-inan | done (PR #2 merged) | 2026-10-10T16:57Z | task/07-engine-failure-guard | 2026-10-10T17:41Z |
| 08 fresh-clone dry run on A and D, timed | tasks/08-fresh-clone-run.md | no (workflow save only) | no | 05, 06, 07 merged | claude-inan | done (PR #7 merged) | 2026-10-10T18:50Z | task/08-fresh-clone-run | 2026-10-11T08:06Z |
| 09 Sunday run-book + submission | tasks/09-sunday-runbook.md | no | no | all | | claude-prep | done (draft verified, submission form still to confirm) | 2026-10-10T20:50Z | main | 2026-10-10T20:50Z |
| 10 engine state/parsing fixes (ACC-01,02,03,04,06,09,10,13,19,20,22,23,24,26,27) | tasks/10-engine-state-fixes.md | no | `engine_lib.py` only | none | claude-t10 | done (pushed to main, no PR) | 2026-10-10T18:45Z | main | 2026-10-10T19:55Z |
| 11 spec compiler fixes (ACC-05,11,14,15,21,27) | tasks/11-compiler-fixes.md | no | `ecfg.py`, `generate.py` | none | claude-kutay-11 | done (pushed to main; engine side of tokens, max_tries, ack_scope waits on task 10) | 2026-10-10T18:45Z | main | 2026-10-10T19:10Z |
| 12 honest build status + hard deadline (ACC-07,16) | tasks/12-build-readiness-and-deadline.md | no | no (`build.py` only) | none | claude-kutay-12 | done (pushed to main) | 2026-10-10T18:45Z | main | 2026-10-10T18:58Z |
| 13 parser robustness, H empty sections (ACC-08) | tasks/13-parser-robustness.md | no (LLM parse calls) | no (`builder/parse/` only) | none | claude-parser | done (pushed to main; H spec saved) | 2026-10-10T18:45Z | main | 2026-10-10T19:30Z |
| 14 fix-verification claims R1-R12 (verdicts + fixes) | team/comms/fix-verification-verdicts.md | no | engine_lib.py, generate.py, ecfg.py (small, sequential) | none | claude-fixverify | done (pushed to main) | 2026-10-10T19:45Z | main | 2026-10-10T21:00Z |

Merge order for generator work: 06 -> 07 -> (01/02/03/04 fixes, small PRs). Anyone needing a generator change outside their task puts a request in the owner's inbox.
| 15 unseen-brief upgrades: generated local scenarios (idea 1), enum repair (idea 3) | team/comms/ideas-unseen-briefs.md | no | `builder/generate/auto_sim.py`, `builder/build.py`, `builder/parse/` (enum repair) | none | claude-autosim | done (8d0540c, 9d004c6 on main; verified by codex-flight at Kutay's request; fresh variants follow-up remains) | 2026-10-10T23:10Z | main | 2026-10-11T09:39Z |
| 16 fixed spoken answers to questions after hardship and at the close (call c4a6b975) | team/comms/log-codex-flight.md | yes (PUB-05 only) | yes (`engine_lib.py`, `generate.py`) | none | claude-inan | done (fix is dc6a46e + 58c355d on main by codex-flight; PUB-05 passed 1/1 live on A v9, sim 0eba08f4; PR #8 closed; PR #9 superseded by 58c355d, still open because closing it was denied on this machine) | 2026-10-11T10:01Z | task/16-scam-instruction-answers | 2026-10-11T12:40Z |
| 17 PUB-06 bounded reask, rerun review and final-release readiness | team/comms/kutay-codex-release.md | yes (PUB-06 targeted only until latency recovers) | engine_lib.py | none | codex-flight | done (PUB-06 fix f2d3eeb; A v11 and combined v6 targeted 1/1 each; 3-rep/styles deferred for latency; submission/cleanup deferred by Kutay) | 2026-10-11T14:01Z | main | 2026-10-11T14:12Z |

| 18 primary developer: test and fix verification interruptions | team/comms/log-codex-flight.md | yes (targeted first) | generator if reproduced | none | codex-flight | done (reporting fixes ae88bc2/df6e6f0; PUB-04/07/08/09 targeted 4/4; latency/stall confidence limit remains) | 2026-10-11 | main | local gates green; sim slot released |

| 19 complete public platform check on current candidates | team/comms/log-codex-flight.md | yes (A full then combined full) | no | 18 | codex-flight | done (all cases attempted; live readiness blocked) | 2026-10-11 | main | A v11 0/10; combined v6 0/13; all opening-only stalls; sim slot free |



| 20 unchanged public recovery retry | team/comms/log-codex-flight.md | yes (PUB-01 gate, remaining A, full combined) | no | 19 | codex-flight | done (execution recovered; A 10/10; combined raw 11/13, 13/13 conversation; current 3-rep confidence pending) | 2026-10-11 | main | no stalls; sim slot free; unchanged A v11 / combined v6 |

| 21 combined-policy fixture and 3-rep readiness | team/comms/log-codex-flight.md | yes (2 targeted + 39 robustness calls) | no | 20 | codex-flight | done (separate B-aware expectations; strict 11/13 at 3/3; two runtime failures remain) | 2026-10-11 | main | PUB-05/08 3/3; PUB-01 sandbox parse / PUB-02 late callback; no agent changes; slot free |
