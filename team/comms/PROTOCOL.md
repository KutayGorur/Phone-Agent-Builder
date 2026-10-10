# Collaboration protocol

Agent names: pick a short unique name (e.g. `agent-kutay`, `agent-mate`). Use it everywhere below as `<agent>`.

## Claiming a task
1. `git pull --rebase origin main`.
2. In `team/comms/BOARD.md` set your row: owner = `<agent>`, status = `claimed`, claimed-at = UTC now, branch = `task/NN-name`.
3. Commit (only BOARD.md) and push to main immediately.
4. If the push is rejected: `git pull --rebase origin main`; if the row was taken, pick another free task. Never overwrite someone else's row.
5. Create your branch `task/NN-name` and set status `in-progress`.

## While working
- Heartbeat: update "last update" on your row (and one line in your log) at least every hour. A row with no update for 2 hours may be marked `free` by anyone, with a note in the old owner's inbox.
- Work on `task/NN-name`, open a PR to main when done; BOARD, SIM-LOCK, logs and inboxes are edited directly on main.
- Commit only your own paths. `git add <paths>`; never `git add -A`. Do not rewrite shared history.
- Files outside your task's "owns" list: do not edit. Ask the owner via their inbox.
- When blocked: status `blocked`, say why in your log and inbox the person/agent who can unblock.
- When finished: status `done` with the PR link in your log; release by leaving the row `done`. If you stop early, set status back to `free` and write handoff notes in your log.

## Sim slot lock (Freya allows one simulation per workspace at a time)
- `team/comms/SIM-LOCK.md` holds at most one active line: `<agent> | task NN | started <UTC> | expected <minutes> min`.
- Before any `ci/sim.py` or `run_cases.py` call: pull, check the file is empty (no active line), write your line, commit, push to main. If the push conflicts or someone else's line is there, wait and re-check; do not sim.
- After the sim ends (success or fail), clear your line, commit, push. A line older than 60 minutes is stale: ask the owner via inbox, then clear it.
- Agents with different Freya workspaces/keys still log their spend but use their own lock line prefixed with the workspace name.

## Logs and messages
- One log per agent: `team/comms/log-<agent>.md`. Append notes, decisions, results, handoffs, ledger totals. Only you edit your log; never edit another agent's log.
- To message another agent or Kutay: append to `team/comms/inbox-<agent>.md` (create if missing) with `## <UTC> from <you>` and the text. Append only; never edit or delete earlier text. Read your own inbox at each pull.
- Never put API keys, the bank team key or other secrets in any comms file.

## Branches and PRs
- Recommended: each agent works on `task/NN-name` and merges via PR; keeps PRs small. Run `python builder/generate/local_sim.py` and `python tests/logic/test_logic.py` before opening a PR that touches `builder/`.
- The merge order for generator code is in BOARD.md.
