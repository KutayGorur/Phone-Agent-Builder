# log-fixverify (agent claude-fixverify, task 14)

Verdicts: team/comms/fix-verification-verdicts.md. Tests for these fixes: tests/logic/test_fix_verify.py. Baseline before work: all suites green, local_sim 62/62.

- 2026-10-10 verdicts written, BOARD row 14 claimed.
- fix 1 (R1, R2, R4): pending amount/date kept across which-account/which-one questions; unknown product names ask instead of guessing, ordinals and ids resolve; compound amount alternatives ask again with brief-safe wording and keep the date. Suites green, local_sim 62/62.
- fix 2 (R3): an agree that carries a date or amount is a change; the question wrapper no longer erases it. Green, 62/62.
- fix 3 (R5, R6): refused counter-offers join the rejected-pair history; a hardship customer's volunteered offer goes through the scope-aware path and hardship stops persuasion on the remaining products (noted with the hardship decline reason). Green, 62/62.
- fix 4 (R7): speech after a record (G per-record) and the deferred close both honour a new request (transfer first; corrections return the unrecorded products to the read-back); the closing answer no longer carries the negotiation question. Transfer + question stays unanswered by design. Green, 62/62.
- fix 5 (R8): engine sets a durable promise_recorded flag when a record succeeds; the transfer_failed node and the sandbox-failure promise guard use it (or the just-answered cp_ok), not only the latest cp_ok. Green, 62/62.
