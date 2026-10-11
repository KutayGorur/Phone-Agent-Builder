# Mid-flight continuation, 2026-10-11 (codex-flight)

## Build status and model outages

- Read SPEC_CONTRACT, TEST_PLAN, RUNBOOK and BOARD before working; synced main from e3792fe through 993212d.
- Fix ae9a010: both dry-run and Freya-export paths return exit 2 for degraded builds, preserving diagnostic/fallback artifacts. Successful builds return 0; failures without an export return 1.
- Exhausted audit or repair model retries now mark the parser degraded and retain the backend failure reason, even if deterministic validation is clean. A recovered retry remains successful. This prevents a mid-build auth/usage-limit failure from silently skipping the audit.
- RUNBOOK now enables pipefail before piping to tee and explains that degraded status does not always mean the base workflow was used.
- Local gates: 269 logic tests; parser selftest; local_sim 0 FAIL (including the available C/D/E specs); build status tests (9 cases); four new model-failure/export regression tests. All passed. New tests use fake model/Freya calls and spend no credits.
- Main pushed with author Kutay <gorurkutay@gmail.com>. No PR created.

## Requested Freya retests: already completed by the concurrent thread

- Rebase picked up 993212d and avoided a duplicate paid run. See log-retest-0811.md.
- Brief A x1: 10/10; workflow 030a85bf-19a4-4ed9-8f62-a1ee93eeea97 v6; sim a3c99a16.
- A+B x1: 11/13; workflow d2fd658b-b7bb-47b8-b566-333db5526f05 v2; sim fb5058c9. PUB-05/PUB-08 are the known extra-note disagreements when Brief B is judged against A-only expectations.
- This matches/improves the previous A 29/30 and A+B 11/13 baselines, but a one-rep result does not establish 3/3 robustness on the current candidate.
- No generator or freya.py change in our commits relative to the tested main. No simulations, chats, new workflows or paid Freya calls from this continuation. Existing retest notes say 23 customer calls, not approximately 13: A has 10 and the combined A+B run has 13.

## Workspace cleanup

- Read-only list confirmed 17 workflows. DELETE /api/v2/workflow/{id} works; tested on inan-gen-a and verified absence after each deletion.
- Deleted only the five unambiguous authorized targets:
  - 8b4a94b5-30c5-477d-9943-23743cc97747 (inan-gen-a)
  - 068e29aa-ba6a-4b70-b074-e8b31cea6f65 (inan-gen-ab)
  - ea735359-d65b-43d1-8edd-b6407e80224a
  - e89f3cbf-05a2-44b9-9158-c0be4fb5590c
  - b8c2d0fb-7d28-4311-86cc-ebf8b0e18dd1
- Kutay subsequently authorized removal of old/duplicate tests. Verified old cloud Brief D cbf958f4-5d8e-4ac8-b732-003878c82ac9 and probes 18e6f55c-9994-46d1-bd4e-0b8d9ded691c, 2d4434f6-df00-4d4f-8da0-0daa2d956d2d, 21d3490c-06f2-44d8-a31a-2fcb7ae6bfda were unchanged version-1 workflows from the previous day, with no listed invoking-agent dependencies. Exported them locally before deleting.
- Remaining: 8, below the documented limit of 10. KEEP 030a85bf, d2fd658b and 51904896 intact. Those are also the three fresh-clone workflows; explicit KEEP takes precedence over the conflicting instruction to delete fresh-clone workflows. cbf9d8ac was a mismatched ID; the actual old cloud D was cbf958f4 above.
- Kutay then requested local backups. Six workflow exports are saved outside the repo at `C:/Users/gorur/OneDrive/Desktop/Build The Builder/freya-backups/2026-10-11/deleted-backups/`: the four exported before deletion plus cached exports for e89f3cbf and b8c2d0fb. The first three other deletions (inan-gen-a, inan-gen-ab, ea735359) have no recoverable export: workflow GET and version-history GET return 404, and local/ZIP searches found none. This limitation is explicit in the backup README/manifest. Backups may carry tool credentials and are not committed.
- Simulation UI "Unknown" is an orphaned assistant reference, not a new unknown assistant: API rows matching cases 01:23:09 and 00:59:45 have agentId=null while results remain present. The kept A run cases 08:57:36 retains its agentId. Preserved simulation index and sample historical details locally; no simulation deleted.

## PR 6 and Task 15

- PR 6 contains only a log and two traces. Scanned all three for secret patterns, copied them unchanged to main in f1ffc2d, pushed, then closed PR 6. Its application code is unchanged.
- Task 15's board row remains in-progress with last update 2026-10-10T23:25Z. Implementation is on main: 8d0540c (generated scenarios), 9d004c6 (enum guard), plus later hardening. log-claude-autosim.md describes both as done.
- Generated scenarios run inside build.py but findings are advisory, not a readiness failure. Enum repair leaves unresolved values visible through parser errors. Fresh C/D/E re-parses remain a validation follow-up; fresh clones skip their local_sim cases until generated specs exist. We did not edit another owner's board row.

## Preflight and fresh clone

- Real claude -p "ok" call succeeded on this Windows build machine. env.sh supplies Freya credentials only; no ANTHROPIC_API_KEY is configured there. Parser calls use the logged-in Claude CLI.
- Fresh clone of pushed main f1ffc2d, no env.sh copied and no Freya writes: 269 logic tests, parser selftest, nine build-status checks, four model-failure checks, local_sim 0 FAIL. C/D/E skipped because their generated specs are absent.
- Real-parser A dry run: exit 0, END status=ok, elapsed 73 seconds, 8 model calls, 70/70 generated scenarios; extraction, audit, repair and cross-check completed. Outputs and trace are in ignored out/codex-check/fresh-clone/.
- Real-parser A+B dry run: exit 2, END status=degraded, elapsed 70 seconds, 18 model calls (both parse attempts exhausted all three extraction groups and retries). CLI failures had zero API duration/usage and nonzero exit. This resembles earlier backend/usage-limit failures but the truncated CLI response does not establish the precise cause. No configured API fallback was used. This real run confirms the new nonzero failure handling; it does NOT establish a healthy A+B fresh build. Claude access is unreliable and needs resolution before final builds; a successful minimal preflight is insufficient assurance.
- Final briefs have not arrived. No final submission package/email was created. Use ci/prepare_submission.py with actual matching exports/traces after the final builds, then RUNBOOK 7a. Do not package the fresh-clone --dry-run outputs as Freya exports.
- Known pre-existing limitation from log-retest-0811.md: practice K's renamed routes are not mapped, so it degrades. Our nonzero exit now makes this condition actionable.

- Final inventory independently verified: eight workflows; kept A v6, A+B v2, D v2. Backed up local .freya-agents.json and remapped brief-a, brief-a-brief-b and brief-d slots to those kept IDs; removed slot entries pointing at deleted IDs. This prevents a later local practice build from recreating the deleted workflows. State remains gitignored.

## Platform stability tests requested by Kutay, 2026-10-11

Main was unchanged after ff190ad. Local gates remained green (269 logic tests, parser selftest, local_sim 0 FAIL). Exported the existing A v6 and A+B v2 workflows, checked the fixed experimental-5 agent model, and validated both graphs with Freya: zero errors/warnings. The linter only accepts generated graph JSON or the single-key workflow envelope, not the real export metadata envelope; lint inputs were copies of the exported graph without platform-added agent_config. The original exports and published workflows were unchanged. Graph digests: A eac9914265f9d99e, A+B 320dda49e8b3a2e4 (SHA-256 prefixes over canonical JSON of the lint input).

Took and published the shared sim lock before testing. All three runs went through ci/sim.py with --why, one simulation at a time, and are in the local results/sim-ledger.csv. No application code, Freya workflows or parser configuration changed.

| Run | Calls | Result | Simulation | Duration | Median worst turn per call |
|---|---:|---|---|---:|---:|
| Targeted A: PUB-04 dates, PUB-06 amounts, PUB-10 failed-tool retry | 3 | 3/3 | 0ee1117e-03d9-45c8-a416-07fc35b82791 | 116 s | 17 s |
| Full A, one repetition | 10 | 9/10 | a53768f1-2aa4-4cf2-ad15-0bd36135bf8a | 170 s | 9 s |
| B-only on kept A+B agent, one repetition | 3 | 3/3 | 3444b8a0-0cbf-4fc4-aca2-6c2efc6cb74e | 75 s | 13 s |

Total: 16 customer calls, 15 passes including repeated targeted cases. The full A/B suites passed 12 of 13 distinct customers. All bank-record checks passed; the only failure was the conversation/policy check for A PUB-05. This is a drop from the immediately preceding A 10/10 result on the SAME workflow version, evidence of speech variance. B passed all three B-specific cases; this B-only result is not a retest of all 13 cases against the combined workflow. Three repetitions were not attempted: a real policy violation already exists, and targeted/B latency was above TEST_PLAN's slow-turn threshold. Paused 45 seconds after the initial slow run before the single A milestone. No failed A case was re-simulated.

### Confirmed remaining problem: free-form reply resumes repayment after hardship

Failed call: c4a6b975-356b-4a51-85a2-b8aa94d398b6, in the full-A simulation above.

1. Customer states job loss, inability to pay anything, and asks for a discount.
2. Agent gives sympathy and offers support. Customer explicitly declines transfer and repeats the discount question.
3. Agent says it cannot offer discounts, then volunteers the full 780.00 on Friday 16 October and asks whether that works.
4. Customer refuses. Agent finally closes no_promise / hardship. No promise was recorded, so ledger checks pass, but the spoken proposal breaches hardship/no-persuasion policy. The judge calls it a payment plan; irrespective of that label, the transcript confirms an unsolicited repayment proposal after hardship.

The actual extractor classified the decline-plus-discount question as x_intent=sp_restructuring with x_q=yes. The hard_pending state nevertheless handled it as declining support and selected no_promise/hardship correctly. The engine's next state had nopers=hardship, product status=noted, and defer=fin. Its instruction explicitly said "Answer it, then ask nothing further", "Never invent figures, dates or reasons", and "never offer a discount, waiver or payment plan". The speech model added a full-amount Friday proposal despite that instruction. This is not a false judge failure and not a ledger outcome bug.

Gate-1 diagnosis: saved the real transcript and replayed the actual published code_exec code with the actual prior variable snapshot plus the captured extraction (sp_restructuring, question=yes). Replay selected route=ask, close=no_promise/hardship, defer=fin; the instruction contained the no-offer/no-followup constraints and no Friday 16 October proposal. Assertions passed. This reproduces the vulnerable instruction path locally, but does not reproduce stochastic speech with a deterministic engine test. Existing local_sim cannot detect this violation because it supplies extractions and checks the ledger instead of running the speech model.

Proposed generic fix for the generator owner: keep post-hardship/terminal question replies under deterministic speech control. For unsupported questions, use the brief's fixed unknown-question answer through TTS, then the existing closing, without another free-form conversational turn. For supported questions, use bounded answer templates chosen from the spec rather than offering unrestricted financial facts and asking the model to compose a reply. Preserve legitimate AI/scam/account questions required by the brief. Strengthening the negative prompt alone is not a reliable fix: the exact prohibition was already present in this failed call. Do not change the fixed agent model, record a false promise, or relabel the correct hardship close to mask the conversation failure.

Acceptance checks: unsupported discount request after declining support; no-transfer plus a question in one sentence; a repeated question; a supported balance question after hardship; a volunteered valid payment offer after hardship (which the brief allows) must remain distinct from the agent proposing one. Verify no renewed amount/date offers, no forbidden terms offered, correct hardship closing, and no extra follow-up question. Add meaningful offline state/graph checks for the deterministic reply path, then only target PUB-05 through ci/sim.py after local gates pass. A failed unchanged case must not be re-run merely to seek a green sample. Robustness remains unproven until an appropriate 3/3 run on a fixed candidate.

Local artifacts (gitignored): results/codex-platform-targeted.json, results/codex-platform-a.json, results/codex-platform-b.json, results/codex-platform-pub05-call.json, results/codex-platform-pub05-replay.json; runner logs and original workflow exports under out/codex-check/. Raw transcripts/exports are not committed because they can contain platform/tool configuration. The narrative above is the shareable handoff. The Claude parser access risk from the fresh-clone test also remains open.

## Teammate checklist closeout at Kutay's request, 2026-10-11

- The pasted teammate note predates this continuation. Cleanup was completed with nine old/test workflows deleted and the three explicitly kept development workflows preserved; last successful verified inventory is eight. Backups and the three unavailable originals are documented above. Two spare slots remain; if three hidden briefs are delivered, one further unused workflow needs backup/removal when the platform is available. Do not delete the active fresh-clone A/A+B/D workflows merely because the older note calls them disposable.
- The requested A and combined A+B live check already landed in 3da67e2/993212d: A 10/10, combined A+B 11/13. Together those runs are 23 calls (10 + 13), not 13. Runtime generator unchanged since those runs. Subsequent authorized tests are documented above and found an actual hardship speech violation; no unchanged failing case was re-run to seek a green score.
- PR 6 is confirmed CLOSED, with all three log/trace files already on main.
- Task 15 board status corrected to done at Kutay's explicit request, using implementation commits 8d0540c/9d004c6 and green local tests as evidence; owner retained and fresh-variant follow-up noted. No feature code changed.
- The degraded exit-0 issue is fixed by ae9a010: degraded builds return 2, and exhausted audit/repair calls mark degraded. Both offline tests and the real failed A+B fresh-clone run verified this. Provider access itself remains unreliable.
- New live inventory verification failed twice with HTTP 504 (workspaces and workflows endpoints). No new sim or deletion launched during the outage. Prior count is explicitly the last successful inventory, not a claim of a new successful read. Sim lock remains free.

## PUB-05 speech fix, 2026-10-11

Kutay authorized continuing development after the confirmed live failure. The generator now uses the existing fixed-TTS node for questions during hardship handling and before terminal closure. A small question-kind extraction selects brief-defined AI/scam/unknown answers or bounded account-balance/deadline facts. Unsupported discount/waiver/plan questions receive the brief's unknown answer; a free-form speech task no longer gets the chance to invent a renewed repayment proposal on these paths. The extracted kind is reset each turn. Initial hardship and corrected readbacks accompanied by questions also retain their exact fixed wording.

This preserves the existing no_promise/hardship outcome, deferred close, and transfer interruption. A customer-volunteered valid payment offer after hardship still reaches confirmation and requires agreement before recording. Ordinary negotiation question handling remains as before.

Eight new regression tests cover the actual failed extraction (declined support misclassified as restructuring plus a discount question), repeated and supported questions, stale question kinds, transfer interruption, volunteered offers, paid closure, and the fixed-TTS graph/extraction wiring. Existing close/correction tests now verify the fixed reply and the corrected promise date after subsequent agreement.

Validation: all 277 logic tests passed; parser selftest passed; scripted local simulations across A–H passed; build-status and model-failure checks passed. Newly generated A and A+B candidate graphs have zero offline lint errors or warnings. The logic-suite log is gitignored at out/codex-check/terminal-question-unit.log.

Live verification is blocked by Freya: a fresh GET of the kept A workflow returned HTTP 504. No workflow update, deletion, or paid simulation was performed for this fix. Existing live versions therefore still contain the earlier speech bug. When Freya recovers, export/back up the active A workflow, publish a candidate generated by this commit to the existing A slot, pass the Freya dry run, and target PUB-05 through ci/sim.py with the sim lock and a --why reason. Inspect both conversation and record checks before widening the run. Three-repetition robustness and the unreliable Claude parser access remain open; local success does not establish live 3/3 accuracy.
