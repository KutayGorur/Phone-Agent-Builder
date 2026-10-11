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
