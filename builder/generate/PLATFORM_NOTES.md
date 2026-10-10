# Platform notes (Freya workflows), found by probing on 10 Oct 2026

Probe scripts are in `dev/` (`probe1.py` .. `probe3.py`, `run_probe.py`, `probe_tools.py`). Slots used: `gen-probe`, `gen-probe2`, `gen-probe3`.

## Variables and conditions
- **`is_set` is TRUE for an empty string.** `equals ''` is true for `''`, false for an unset variable. `not_equals ''` is true for an unset variable. So: initialise every control variable to `''` in an `init` code node and test with `equals` / `not_equals`, never `is_set`, if the code ever clears a variable.
- `equals`/`greater_than` on numbers written by code work (`n == '3'`, `n > 0`). `contains` works. `<node>.total_turns` / `<node>.current_turns` are usable in conditions.
- A list in a `pre_actions` node-level `response_mapping` (`data.products`) does NOT land in `vars` as a list. What exists is flattened keys named after the NODE (not the tool): `<node>_response.data.products.<i>.<field>` (all values strings). `data.ok` mapped fine (value `"true"`). Rebuild lists from these keys in code.
- Code writes `vars['x'] = <int/str>`; later nodes see them. JSON strings in `vars` are fine (use one `st` JSON string for dialogue state).
- A fixed `end_call` with `message_mode: custom` and `spoken_message: "... {{var}}"` resolves variables set by code.

## Hooks
- `pre_process_code` / `post_process_code` work on `pre_actions` tools too. In the hook `vars` is writable (`vars['pre_ran']='yes'` was visible later), `config['body']` can be rewritten, and keys added to `result['data']` are mapped by `response_mapping` (`data.state` -> variable).
- A baked body field typed `number` with default `"{{amt}}"` is sent as a STRING. Coerce in a pre hook: `config['body']['amount'] = float(config['body']['amount'])`. The bank then stored `510`.

## Code nodes
- Each code node hop costs roughly 0.5 to 1.3 s. Keep the number of hops per customer turn low (target: one engine hop).
- `import json, re, datetime` work. No `{{`/`}}` in code; `builder/logic` already enforces this.

## Chat route (`/api/v2/chat/message`)
- The first message is answered by the initial node's model prompt: **the opening `tts` line is NOT spoken** in chat. A scripted chat starts one turn "late". Use it for graph/engine debugging, use `run_cases.py` for real checks.
- Long turns (chains of many nodes) can return 504 although the server finishes the work. Read the call with `get_call(call_id)` afterwards.
- `route_evaluated` events list every branch with its result and the whole `variable_table`. Best debugging view.
- The platform clock is the real date (10 Oct 2026); the simulation `now` is 2026-10-14. Never let the platform anchor dates: extract words, resolve in code against `vars['now']`.

## Misc
- The mock bank's `/v1/practice/sessions` (body `{"case": "PUB-12"}`, header `x-team-key`) gives the call variables; `/v1/practice/ledger/<customer_id>` shows what was recorded. See `dev/probe3_run.py`.
- `.freya-agents.json` (slot -> workflow ids) is shared by all threads; use own slot names.

## Enum variables reject `''`
Code that writes `''` into a variable declared as an extraction enum gets `variable 'x' rejected by schema validation` (the call still goes on, the old value stays). Reset enum variables to a neutral enum value (`none`, `other`) instead.

## Freya call log (generator thread)
- 10 Oct, early: probes `gen-probe`, `gen-probe2`, `gen-probe3`: about 12 chat messages in total, 3 saved workflows.
- 10 Oct: `gen-a` v1 sim, 10 cases (identity tool pointed at a wrong URL, all failed); v2 sim, 10 cases (platform returned 503 / customers hung up at once); v2 sim, 2 cases (same). 3 sims, 22 calls.
- 10 Oct 13:3x-13:5x: platform returns 503 on `/chat/message` for every workflow including old probes; `dryRun` validation still works. No further sims until it recovers. Local engine tests (`local_sim.py`, in-process bank) pass for PUB-01, 02, 04..13.
