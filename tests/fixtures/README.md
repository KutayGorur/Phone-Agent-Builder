# Combined Brief A+B practice expectations

`public-test-set-ab.json` is an explicitly separate practice fixture for an agent built from both briefs. It preserves all 13 original customers, identities, scripts, conversation checks, promises, outcomes, callbacks and transfers.

Only two expected note lists differ from `public-test-set.json`:

- PUB-05: expect `p1 / hardship`.
- PUB-08: expect `p1 / paid`.

Brief B rules 8-9 require notes for every product without a promise, including hardship and already-paid cases, even when only one product is returned. The original Brief A fixture expects no notes for these cases and remains authoritative for the A-only agent. Do not remove required notes from the combined agent to satisfy A-only expectations. Original raw scores remain unchanged; results against this file must be labeled combined-brief expectations.

Run through the credit guard, for example:

```bash
python ci/sim.py <combined-agent-id> --workflow <combined-workflow.json> --cases tests/fixtures/public-test-set-ab.json --full --why "combined-brief expectations" -- --out results/combined-policy.json
```

This does not change the official test set or scorer and cannot establish the hidden-case or official submission score.
