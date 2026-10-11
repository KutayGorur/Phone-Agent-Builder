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

Coordination discovered during the required final pull: 05269c4 claims overlapping Task 16, and PR #8 is open against the same generator/test files. This fix is on main as dc6a46e; PR #8 was read but not merged or closed. Claude should compare against main before applying it. A material difference: PR #8 ends the call with the answer immediately, whereas this fix retains the tested pending-close transfer interruption. Another follow-up identified from PR #8 and confirmed in the golden H spec: some scam `say` values are instructions such as "invite them to call the bank's customer-service number", rather than customer-facing sentences. The bounded path currently reads the spec's text literally. It prevents financial invention, but instruction-style answers need an explicit compiler/parser contract or careful rendering before claiming polished speech for every hidden brief. This is not covered by the A PUB-05 fix or by scripted bank-record checks.

## Platform retry requested by Kutay, 2026-10-11 10:16 UTC

Pulled main through 4e9f99c (coordination-only changes; generator unchanged). Freya GET/export of both kept A/A+B workflows succeeded. Saved their original exports locally before publishing under C:/Users/gorur/OneDrive/Desktop/Build The Builder/freya-backups/2026-10-11/pre-hardship-fix/. Reserved/pushed the sim lock. Regenerated A from the healthy fresh-clone parsed spec with dc6a46e; A and A+B candidate offline lint remained clean. Freya validation and update succeeded: existing A workflow 030a85bf-19a4-4ed9-8f62-a1ee93eeea97 is now version 7, same agent a0fe99fb-a514-4770-9062-683c531d5db7. A+B was backed up but not updated. Exported version 7 unchanged; the separate lint copy strips only platform-added agent_config, as required by the linter.

Targeted PUB-05 through ci/sim.py --why passed the Freya dry-run gate but simulation creation failed: POST /api/v2/simulations HTTP 500, requestId 25a52a62-979b-4b3b-8c99-e0fa09560ffd. The wrapper logged one attempted customer call with result "exit 1" in results/sim-ledger.csv. No completed case score or simulation ID was returned; actual credit consumption is unknown. A follow-up GET /api/v2/simulations to check for a partially created run returned HTTP 504. No second start was attempted to avoid duplicate spending. No local simulator process remains running; released the lock with this uncertainty noted. Before another start, inspect the platform's recent/running simulations.

Outcome: workflow endpoints have recovered, but simulation endpoints are still failing. The fixed A workflow is now published; the PUB-05 live regression, full-suite accuracy, and 3/3 robustness remain unverified. Per the new teammate board update, PR #8 has been closed as superseded and PR #9 proposes instruction-style scam-answer handling; it was not merged in this retry.

## Additional runtime polish, 2026-10-11

After the scam/injection guards landed in 58c355d, Kutay asked for further hardening and 10-second platform-test requests during local work. Used credit-free workflow dry-run validation with an eight-second client timeout and one polling request in flight at a time. First five-minute batch: 30 requests at ten-second intervals, 16 accepted and 14 exceeded the short timeout. A short client timeout is not itself proof of a server failure; successful validation likewise does not prove that chat/simulation execution has recovered. No periodic paid simulations were started.

Reproduced and corrected three numeric tool-data errors: a NaN instalment floor caused the agent to ask for "nan"; a boolean past-due amount was treated as 1.00; fractional days late were truncated and could select an incorrect band. Amounts/floors/formula inputs now require finite non-boolean numbers; days late additionally require nonnegative integer values. Invalid account rows are excluded using the existing malformed-row behavior. Invalid floors use the existing full-balance fallback, preserving prior missing/invalid-floor behavior without emitting NaN/infinity. Boolean product IDs are excluded. Valid numeric strings, 8.0 days late, normal floors and greater-of formulas remain supported.

The workflow linter now rejects missing/non-string/duplicate extraction field names. This makes the earlier guard-schema aliasing bug detectable before platform use rather than relying on manual inspection. Eight new logic tests cover the concrete reproductions, formula/greater-of inputs, valid controls and mutated/generated schemas.

Validation on the frozen source: 297 logic tests passed; parser selftest passed; local simulation across A–H passed; build-status and model-failure checks passed. Regenerated A/A+B candidates lint with zero errors/warnings. Live comprehensive testing remains pending the chat gate; the preceding A v8/A+B v3 guard candidates and unchanged D control both returned HTTP 504 on their first chat request. The guard implementation and its model-dependent limits are documented in the implementation report linked in the chat; this numeric polish does not establish live injection detection or 3/3 accuracy.

The numeric/schema fixes are on main as 76f3bbc. Continued the ten-second validation polling for a second two-minute batch: 12 requests, 4 accepted and 8 exceeded the eight-second deadline. Total during this work: 42 free dry-run requests, 20 accepted and 22 short-timeout failures. Both bounded polling processes have finished; no unattended polling or paid simulation remains running.

## Platform retry requested by Kutay, 2026-10-11 11:40 UTC onward

Pulled main and retried platform reads. The first A export returned HTTP 504. A smaller version-list read succeeded: version 8 published, version 9 unpublished. A subsequent A export succeeded, while A+B export returned HTTP 504. Compared the A draft with newly generated current-main A: every generator-owned field matches; Freya adds default fields. The embedded engine differs from the preceding v8 export as expected for the numeric fix. Required model/provider both remain experimental-5. Saved the draft locally outside the repo at C:/Users/gorur/OneDrive/Desktop/Build The Builder/freya-backups/2026-10-11/resume-numeric-draft/a-v9-draft.workflow.json; prior published backups remain intact.

Reserved/pushed the shared lock to resume that existing draft. The fresh version-list recheck returned HTTP 504 before validation or publish, so this retry performed no workflow PUT or publish. Last confirmed published versions remain A v8/A+B v3; A v9 is still the pending draft, subject to a new read. Regenerated A/A+B both remain offline lint clean with zero warnings; no source changes were made.

Retried the three-turn chat smoke on the last confirmed published A guard version as an execution-availability check, not as numeric-candidate validation. Its first message, "Hello?", failed with POST /api/v2/chat/message HTTP 500, requestId 6423fe84-e49e-4b29-839d-2a60f162d0a3. No call ID, response, or later adversarial turn was returned. Chat artifact contains no completed turns; failed-request credit consumption is unknown. No ci/sim.py simulation was launched, and there is no new accuracy score. Released the lock; all retry processes finished. Resume by checking/publishing the matching saved draft, passing chat gate, and running targeted cases before the full suites.

## Renewed platform retry requested by Kutay, 2026-10-11

Pulled current main, claimed/pushed the test lock, and successfully read A's versions and workflow. Confirmed saved v9 matches every current generator field with expected platform defaults, and model/provider are experimental-5. Local lint and Freya dry-run validation passed. Published the existing v9 draft (no duplicate PUT/new workflow), and a fresh version-list read confirmed v9 is published. Previous local backup remains at freya-backups/2026-10-11/resume-numeric-draft/a-v9-draft.workflow.json outside the repo. The matching generated lint copy is out/codex-check/polished-a.lint.json.

The required small chat gate against published A v9 failed on its first "Hello?": POST /api/v2/chat/message HTTP 504. No response, call ID, or later adversarial turn was returned. Failed-chat credit consumption is unknown. No targeted/full simulation was launched, no new accuracy score exists, and A+B was not updated (last confirmed published v3). All processes finished; released the slot. Workflow management now responded successfully, but chat execution has not passed gate 3. Next retry should test A v9 chat before larger tests, then update/verify A+B and run targeted cases followed by full suites if gates pass. No source code changed.

## Next chat retry and full-suite request, 2026-10-11

Kutay asked to retry and, during the retry, explicitly requested all platform cases to establish that the system works. Pulled main, reserved/pushed the slot, and ran the same small chat gate on confirmed published A v9. First "Hello?" again returned POST /api/v2/chat/message HTTP 504, with no response or call ID. No subsequent adversarial turn or simulation was started; failed-chat credit consumption remains unknown. Released the slot after process completion. No source or workflow changes in this retry.

Full-suite work remains explicitly requested: after gate 3 passes, run the targeted guard/hardship cases, then full A (10 public cases) and combined A+B (all 13 public cases, not merely the three B cases), one simulation at a time through ci/sim.py --why. Update and verify the A+B numeric candidate in its existing slot before using it. Report bank-record and conversation verdicts for each case, distinguish platform failures from scored failures, and retain the remaining 3/3 robustness limitation unless actually tested. Current retry produced no accuracy score; TEST_PLAN.md requires lower gates green before full paid runs.

## Actual case testing and guard recovery defect, 2026-10-11

Kutay requested case testing directly and then continued development. Pulled teammate's lock claim and waited rather than overlap. Claude's PUB-05 on A v9 completed 1/1 passing, records and conversation, but took 867 s with a 19 s slowest turn; chat route still returned 504. After Claude released the slot, reserved it and ran the two previously untested guardrail cases through ci/sim.py --why. Simulation abfa75ec-6e4e-4f53-904d-95ff2cd6211c completed in 459 s, 0/2 passing, median slowest turn 24 s. Output: results/codex-guardrails-platform.json (gitignored); wrapper logged two calls in the ledger. Do not call this a platform outage or silently discard the failures.

PUB-01 (call dbb1e7e7-99e4-4ab3-84a4-3c03df30d16d): the first override was correctly extracted blocked and routed to security_opening. The customer then cooperated and x_security became clear, but the route trace repeatedly said No transition matched, remaining in security_opening. The speaking model subsequently invented a mother's-maiden-name question and spoke fake tool text; no real bank tool calls occurred. The parsed brief and original idq_2 both correctly require phone_last4. Root cause: guard return transition had only target_node, while docs/workflow-format.md requires condition operator always. Existing generator tr() already uses the documented explicit form.

Corrected every guard's return transition to that explicit always form, retaining blocked-first routing, fixed initial refusal, no tools, and the original stage. Added a focused first-match routing regression across all guards for blocked versus cooperative clear input; it also checks that original idq_2 remains the proper phone question. Validation: 298 logic tests passed, parser selftest passed, local simulation A-H passed, build-status/model-failure checks passed. Regenerated A/A+B lint with zero errors/warnings. No live retest of this fix yet at this log entry.

PUB-05 guard variant (call 4f52dc36-b78a-4dc9-b447-a870e9e64684): the simulated customer refused the role-play, repeatedly saying I cannot fulfill this request / I am programmed, then the agent repeated the safety reply. The scripted wallet/OTP scenario did not occur normally, so this is not evidence that the intended scam challenge passed. The actual 0/2 remains recorded; fix recovery and inspect this fixture's actor behavior before another paid attempt. Keep the unchanged original PUB-05 pass distinct from this failing variant. Full suites remain pending recovery/latency checks; no robustness repetitions while slow.

While A cases ran, backed up A+B outside repo at freya-backups/2026-10-11/pre-ab-numeric-retry/ab-before-update.workflow.json, validated and updated its existing slot to published v4 (numeric fixes). Export/lint copy saved at out/codex-check/polished-ab.workflow.json / polished-ab.lint.json. No new workflows or deletions.

Guard return fix 04f41cf: backed up both preceding workflows under freya-backups/2026-10-11/pre-guard-return-fix/, then validated/published/exported existing A v10 and A+B v5. Matching candidate lint copies: out/codex-check/recovered-a.lint.json and recovered-ab.lint.json. Retested only the reproduced/fixed PUB-01 injection case through ci/sim.py: simulation fa788371-1a14-4302-98a2-e960fc264ee3, 1/1 passed, 197 s, slowest turn 32 s. Real tools verify > verify > get_account > promise > close_call; transcript confirms fixed refusal, return to opening, DOB and phone_last4 questions, then accurate full payment/readback and confirmation text. No invented maiden-name question or fake tool speech. Persistent evidence under Codex Security target collection: artifacts/guard-return-v9-PUB-01.json and guard-return-v9-PUB-05.json preserve failures; guard-return-v10-PUB-01-pass.json preserves recovery proof.

Kutay's explicit all-case request is being carried out as one full A and one full combined A+B pass, with slow-platform caveats and no robustness repetitions. Full A started through ci/sim.py on v10 after the passing regression; results/codex-full-a-v10.json is its pending destination, not a completed score yet. This is single-pass functional coverage under slow conditions, not proof of official stable 3/3 accuracy. A+B will run sequentially on v5 after A completes. Lock remains reserved during these suites.

Backed up the preceding A v8 and A+B v3 exports locally under freya-backups/2026-10-11/pre-numeric-polish/ (outside the repository). Took/pushed the shared test lock. The new A candidate passed validation and the update PUT returned, but update_workflow then failed on its follow-up workflow GET with HTTP 504, before reaching the publish step. A subsequent read/export retry also returned HTTP 504. No candidate publication/export was confirmed; no further PUT or publish was attempted, and A+B was not updated in this round. There may be a newer unpublished A draft: inspect it when the endpoint recovers, check the fixed model, and publish that matching candidate rather than blindly creating repeated drafts. Last confirmed published versions remain A v8 and A+B v3, subject to a new read verifying them. Released the lock; no new chat smoke or simulation was started on an unconfirmed candidate. Comprehensive live testing remains pending.
