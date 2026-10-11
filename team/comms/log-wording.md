# Wording lint log (idea 5b)

2026-10-11 Claude (cloud thread "Agent wording check"). Tool: `ci/wording_lint.py`, offline, no Freya or model calls.

    python3 ci/wording_lint.py out/gen-a.workflow.json --spec builder/specs/brief-a.spec.json --brief briefs/brief-a.md [--brief ...]

It reads every line the agent can say: opening/fixed tts, node task messages, the system prompt, and the strings inside the engine config (tp.*, idv.*, *_say, create_failed, after_recorded and so on). Rules: W1 forbidden/budget phrase, W2 debt or product wording before verification, W3 terms outside the brief (discount, waiver, plan, "cancel it now"), W4 failure line claiming success, W5 repeated lines, W6 missing opening disclosure or a brief "say exactly" sentence missing from the workflow. Exit 1 on ERROR. Proven on a mutated workflow (budget question, waiver, "recorded" in the failure node, debt word in the security question): all four caught.

## Results (workflows generated locally from builder/specs/*.spec.json with builder.generate)
| Brief | Errors | Warns | Notes |
|---|---|---|---|
| A | 0 | 1 | system prompt says the AI answer twice (two phrasings) |
| A+B | 0 | 1 | same |
| F | 0 | 2 | scam answer and "twice not wanting to talk" each stated twice in the system prompt; opening says "recorded" (the brief dictates it) |
| G | 0 | 1 | AI answer twice |
| H | 0 | 1 | real-clock rule stated twice |

Info only: "Thank you for your time." / "Goodbye." appear in 6 places and "I am transferring you now." in 3 (all fixed closings on different paths, never both in one call).

## Findings and suggested phrase changes (builder/ is owned by the Parser consistency thread, not edited here)
1. Duplicate instructions in the system prompt (W5 warn, all five briefs). They come from `extra_rules` repeating a rule the compiler already writes (AI answer, scam answer, real-clock rule, "twice not wanting to talk"). Harmless but each costs tokens and F shows two wordings of the same rule. Suggest: in the prompt assembly, drop an `extra_rule` whose normalised words overlap >75% with a generated line.
2. A says "we are recording this call" while F/G/H say "this call is recorded" (copied from the brief). PUB-10's judge matched "recorded" in the opening. For F/G/H the brief's wording is explicit, so keep it; for any brief that only says "recorded" in rule text, prefer "recording this call".
3. Thin evidence: no failing phrase was found in the generated lines, so no change is urgent. Remaining judge risk is in model-written lines (answers to questions via `reask`/`facts()`), which an offline lint cannot see; PUB-06's "names the floor again" is that kind (see inbox-claude-kutay.md). Suggest a transcript-side check later: after any sim, run the same regexes over the agent turns in the call transcript.

## Transcript mode (2026-10-11, same thread)
    python3 ci/wording_lint.py <call.json | folder of call.json> --calls --brief briefs/brief-a.md

Reads agent turns from a saved Freya call (`freya.get_call(call_id)["messages"]`, role `assistant`) and applies W1 (budget or forbidden question), W2 (debt wording before `get_account`), W3, W4 (says recorded/all set before `create_promise` ran), W5 (same sentence twice) and T1 (the same amount named twice in a floor-type offer, the PUB-06 pattern). Tool names are detected from any non-text field of a message, so key names need not match exactly. Tested on a synthetic PUB-06-shaped call (all four planted problems found); not yet run on a real call.

**Real calls not checked: the data is not in the cloud container.** `results/` and `sim-ledger.csv` are gitignored and live on Kutay's PC / the shared folder; the container has neither, and fetching calls would need Freya keys (instruction was no Freya calls). To run it on the PC: for each `call_id` in `results/*.json` (`final[].call_id`), save `freya.get_call(id)` to `results/calls/<id>.json` (a read, no simulation credit), then `python3 ci/wording_lint.py results/calls --calls --brief briefs/brief-a.md`.

### Risky agent lines already reported in the logs (root cause where known)
| Call | Line / behaviour | Root cause | Status |
|---|---|---|---|
| f6b23525-b078-483d-9483-cb2826c7ee44 and 1876d421-33bb-447b-91f7-580de9a78f64 (PUB-06) | after the floor offer the customer asks "How much can you do instead?" and the agent names the floor again; a judge counts a second offer (T1 pattern) | `reask()` answers from `facts()`, which includes the floor figure even while an attempt is pending (engine_lib.py ~560, ~1027) | open. Suggested wording: while an offer is pending, answer "that is the amount I mentioned" and repeat only the question "Can you do that?" |
| 8bc9c1cb-... (PUB-10) | opening "the call is recorded" matched the judge's "not before a successful call" check | fixed opening text | fixed ("we are recording this call"); F/G/H still use the brief's "recorded" |
| e8a46af7-a3a5-4d68-8d86-497a2e11edf0 (A+B PUB-12) | joint "Can you pay all of these today?" counted as one attempt per product | judge reading, agent lines identical to a passing call | not changed |
These three are the only wording-related judge failures in the logs; none is a W2/W3/W4 hit.
