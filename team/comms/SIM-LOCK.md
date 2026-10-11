# Sim slot lock

Free. codex-flight released the slot after current A v11 verification-interruption checks, 2026-10-11. No test processes or simulations remain running from this continuation.

PUB-07/PUB-09 passed 2/2 (simulation daf908af), then PUB-04/PUB-08 passed 2/2 (07faf0da), records + conversation, no hang-ups. One call at a time; four paid calls total. Worst replies reached 15.5 s and 11.1 s, so broad 3-rep/style rounds remain deferred under TEST_PLAN.

Primary developer fixes: ae88bc2 counts unanswered silence; df6e6f0 returns non-zero for scored failures and rejects empty selections. Baseline local gates and eight new reporting regressions passed. Earlier interrupted calls show ~60.3 s unanswered silence; identity-dispatch root cause remains unproven. Current candidates stay A v11 / combined v6, with PUB-06 previously targeted 1/1 each. Latest state: team/comms/log-codex-flight.md.
