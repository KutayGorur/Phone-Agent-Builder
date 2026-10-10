# Task 04: real Brief D sim through a tunnel to the stand-in bank

Read `team/START-HERE.md` and `team/comms/PROTOCOL.md` first. Uses the sim slot; depends on task 01 (platform works).

## Goal
Show that a hidden, raw-material brief works end to end on the platform: build an agent from `test-briefs/brief-d.md` (a long memo, three products) with the real builder and simulate it against the stand-in bank.

## Context
The organisers' bank rejects unknown case ids, so variants need `harness/mock_bank.py` behind a public tunnel (cloudflared or ngrok). Full recipe in `harness/README.md` and `harness/HANDOFF.md` ("Next steps"). Case files: `test-briefs/cases-d.json` (11 customers), tool API `test-briefs/tools-d.openapi.json`. Generation for D already passes preflight and the local sim (D scenarios are in `local_sim.py`).

## Files you own
`team/comms/log-<agent>.md`; new helper scripts under `harness/` (new files only).

## Must not touch
`builder/generate/*`, `builder/parse/*` (report bugs to their owners).

## Steps
1. Free: `python builder/build.py --dry-run test-briefs/brief-d.md test-briefs/tools-d.openapi.json`, `python builder/generate/local_sim.py`, `python harness/preflight.py` as described in `harness/README.md`.
2. Real build (no self-test): `python3 builder/build.py test-briefs/brief-d.md test-briefs/tools-d.openapi.json`; note the agent id from `.freya-agents.json`.
3. Start `python harness/mock_bank.py`; start the tunnel (`cloudflared tunnel --url http://localhost:8787`; install cloudflared yourself, from the official source); `python harness/make_testset.py --server <tunnel url>`; set `FREYA_BANK_HOST=http://localhost:8787` as in the harness README.
4. Take the sim lock. One rep: `python3 tools/run_cases.py <agent_id> --cases test-briefs/cases-d.json --out results/d-rep1.json`, or through `ci/sim.py` if it supports `--cases` (read `ci/sim.py --help`; the ledger must still be written). Then `harness/report.py`.
5. For each failure classify: case-script wording problem (stand-in/scripts never ran on a real agent), mock bank difference, or builder bug. Reproduce builder bugs in `local_sim.py` and file them in the generator owner's inbox with the transcript.
6. Stop the tunnel and bank; release the lock.

## Done when
One D rep result logged with every failure classified; the tunnel recipe confirmed or corrected in a log note for `harness/README.md`.

## Freya budget
11 calls for one rep; no more than one extra targeted retry of at most 3 cases.
