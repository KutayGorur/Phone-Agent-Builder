# Kutay + Codex release work — 11 October 2026

## PUB-06: fix, rather than ship the known speech failure

Commit f2d3eeb keeps an existing persuasion offer's reask on fixed TTS instead of free-form generation. It preserves the pending amount/date and offer history, answers supported AI/scam/balance/deadline questions once, and keeps customer changes, acceptance/readback and human transfer working. There is no graph-shape change. All 27 logic test suites, parser selftest and local_sim passed before publication.

A v11 targeted PUB-06 passed 1/1 records + conversation, simulation 8d92726b-3cba-4853-bfbe-739d6076a877, call 6590b585-1afb-4f96-9259-9a32f04fcba0, 83 s total / 9.3 s slowest turn. Transcript exercises too_much -> "You tell me. How much is the minimum payment" -> bounded response -> agreement -> readback -> real promise -> close. Minimum offer is not repeated in the reask and no fee rationale is invented. Extraction classified that question as balance, so the reply gives existing balance facts; this passed the judge but does not demonstrate perfect question classification.

Existing A slot 030a85bf-19a4-4ed9-8f62-a1ee93eeea97 now v11; combined slot d2fd658b-b7bb-47b8-b566-333db5526f05 now v6. Combined PUB-06 targeted test passed 1/1 records + conversation: simulation b01f4a79-6b32-4846-b669-c79f6188b78a, call e9458848-9c41-4070-a53d-3131fe0c9710, 156 s total / 25.0 s slowest turn. The platform latency gate is not sustained; no milestone, three-rep or style round followed. Both pre-update workflows and four old copies were exported outside the repository to ../../freya-backups/2026-10-11/pre-pub06-and-spare-cleanup/ (relative to repo). No workflows were deleted during this work.

## Rerun review and hang-ups: do not call them merely platform slowness

The prior unchanged rerun completed: A v10 7/10, A+B v5 11/13 raw. Combined failures again were only Brief-B-required hardship/paid notes conflicting with A-only expected records. All 13 combined conversation verdicts passed, and B's three cases passed. A's failures moved to PUB-04/06/08, all customer-ended before any tool calls. PUB-07 and PUB-09 passed on A and combined in the rerun. These are single passes, not three-repetition evidence.

Detailed earlier PUB-07/PUB-09 traces show a concrete identity dispatch interruption:
- PUB-07 call f4504870-0e1e-439e-9c14-6a93f16784ad: full DOB at 27.806 s, x_stance=other / x_security=clear at 51.329 s, then No transition matched in idq_1 at 51.333 s. No verify_identity tool ran. Customer ended at about 88 s.
- PUB-09 call 84dcfbfa-1e3a-4e05-9b92-f76fabbe9cc1: full DOB at 38.183 s, same clear/other extraction at 61.599 s, No transition matched at 61.603 s. No verify_identity tool ran. Customer ended at about 99 s.

The identity state was empty because the model did not invoke the tool; existing transitions only cover passed, locked, declined or human. Clear security classification did not block the call. About 23.5 seconds were spent on extraction/routing, but the logs do not explain why tool invocation or a spoken retry never followed. Therefore slowness is a contributor candidate, not an established sole cause. No evidence of a downstream date-policy or restructuring error. Do not weaken verification or force a passed state.

Follow-up if this recurs under normal latency: capture platform inference/tool-dispatch errors; consider an explicit bounded recovery path for missing identity dispatch, or extraction plus deterministic API dispatch. Preserve multipart answers, swapped-date hints, wrong-answer limits, declines/human interruption, and injection guards. This larger identity redesign has not been applied during release verification.

## Three repetitions and styles

Run only after the current candidate's targeted tests and milestone pass, and median slowest-turn latency is at most 10 s. Prior unchanged medians: A 12.6 s and combined 22.6 s. One targeted A call at 9.3 s is promising but does not establish whole-suite recovery.

Keep one simulation at a time and use ci/sim.py --why for every run. Full A is 10 cases; B-only is 3 cases on the combined agent. Retain raw combined fixture failures; do not relabel 11/13 as 13/13. Run a full A milestone first; if passing and fast, A --full --reps 3, then B --brief B --full --reps 3; then talkative, asks_back and in_words separately, checking results/latency before the next style. No automatic repeats or --rerun-if-slow. Stop broad paid runs if latency stays above the gate or a concrete failure needs diagnosis.

## Items Kutay deferred

Kutay asked to skip team name / kit submission address / build-machine designation questions, and corrected the UI-cleanup interpretation. Focus remains on the builder and testing. Workspace currently has 8 workflows against limit 10; no cleanup was executed. Four old workflow exports are backed up if cleanup is later requested. Submission and final builds are pending, not marked complete.

Final briefs open 17:00 UTC (20:00 Istanbul), close 20:00 UTC (23:00 Istanbul). Select one build machine and preserve its local .freya-agents.json. Do not run the same hidden brief on a second machine. Use actual hidden input files only when released; no hand-edited specs or workflow exports. Follow team/RUNBOOK.md 7a and ci/prepare_submission.py after builds, with matching traces and a pushed commit containing the exports. Kit email recipient and team name remain unknown; no email or submission was sent. A direct web recheck of the hackathon page failed; rely on the previously verified runbook until it can be rechecked.

## Current checkpoint

PUB-06 fix complete and live verified on both candidates; main source f2d3eeb. Results: results/codex-pub06-a-v11.json and results/codex-pub06-ab-v6.json. Two paid customer calls were spent during this assigned work, both through ci/sim.py and the shared lock. The earlier 23-call unchanged rerun is separately logged. Sim slot released after both targeted simulations completed. No tests are running from this continuation.

Real Claude readiness check on this Windows machine returned exit 0 and ok. Machine designation for final builds is still deliberately deferred, rather than implied by that readiness check.


