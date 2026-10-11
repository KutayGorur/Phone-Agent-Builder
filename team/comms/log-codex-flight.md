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
