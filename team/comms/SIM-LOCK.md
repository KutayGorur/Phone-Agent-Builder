# Sim slot lock

RESERVED by codex-flight for Kutay's requested recovery retry, 2026-10-11. Start with A v11 PUB-01, concurrency 1; continue remaining public cases only if execution recovers. Existing workflows and fixtures unchanged. Every simulation via ci/sim.py --why.

CURRENT LIVE READINESS: BLOCKED. A v11 full 0/10 (6221a0ae); combined v6 full 0/13 (48238249). All 23 calls stopped after opening + first customer reply, with no extraction/routing/tool events and ~60 s unanswered silence. Every transcript inspected; no bank tools. Detailed results/state: team/comms/log-codex-flight.md.

No source/workflow changes or retries during these runs. Required experimental-5 model retained. Shared runtime/model availability problem is suspected; exact cause unconfirmed. Local gates remain green. After recovery, start with one actual PUB-01 call before spending on broad suites. No retry automation or simulation is running.

