# Sim slot lock

Free. codex-flight released the slot after combined-policy three-rep verification, 2026-10-11. All simulations terminal; API active list empty.

CURRENT READINESS: NOT FULLY VERIFIED. Combined v6 strict 11/13 customers passing 3/3 (37/39 calls), using separately labeled tests/fixtures/public-test-set-ab.json. PUB-05 hardship and PUB-08 paid required notes passed 3/3. PUB-01 sandbox result parse error and PUB-02 late callback after timeout/retry each failed once. Exact evidence: team/comms/log-codex-flight.md. Original official fixtures/scorer unchanged; original combined raw score remains 11/13 for a different reason (B-required notes versus A expectations).

Three reps: 55d6cbfa-8d77-48e8-9b2e-5eed3a6ff935 (12/13), 21903ee5-2ac9-4be6-9ce7-d619fbab6c4a (13/13), d6e18c3b-2af5-445c-abec-ef3f6d5b4fba (12/13). Results results/codex-ab-policy-three-rep-v6.json. Targeted note cases first passed 2/2 (0f4cf3a7). 41 paid calls logged via ci/sim.py --why.

No generator, parser or published workflow changes; A v11 / combined v6 remain candidates and required experimental-5 retained. Local gates: 32 test files, parser selftest and local_sim passed. Earlier A recovery covered all ten cases once, 10/10. No blanket opening stalls in the latest runs, but late writes and sandbox-result parsing prevent claiming full stability. No styles, workflow cleanup, new handoff, submission or retry automation. No test process or simulation remains running.
