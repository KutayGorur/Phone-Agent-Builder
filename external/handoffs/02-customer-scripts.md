# Task: write difficult customer scripts (paste this whole message)

You help a hackathon team that tests phone agents for a fictional bank (Freya Bank). A simulated customer follows a short text "script". You write harder scripts. No repo access; use only the attached files. **No Freya API key, nothing from hidden briefs.**

**Attach before sending:** `public-test-set.json` (13 practice cases PUB-01..13), `briefs/brief-a.md`, `briefs/brief-b.md`. Optional second pass: `test-briefs/cases-c.json`, `cases-d.json`, `cases-e.json` (ids TC-*, TD-*, TE-*).

## What a case is
Each case has `variables`, `identity` (the true answers), `products`, a `script` (one or two sentences: what the customer says and does), `expected` (what the bank's records must show) and `checks`. Only `script` and `checks` are yours to rewrite. **Facts and `expected` must not change** (same outcome, promises, notes, callbacks, transfers). Only the customer's behaviour changes.

## Make each case harder (one or two ways per case, vary them)
- gives a number in two parts ("four four... seven one") or a date in words ("the fourteenth of March, eighty-eight")
- corrects himself after the read-back, then returns to the original
- talks about something else for a turn, asks a question back ("which product exactly?", "can you repeat?")
- says amounts and dates in words ("three hundred and twenty", "the Friday after next")
- answers a different question than the one asked
- hesitates, says "hmm, maybe", then agrees; says "yes, but" (not a clear yes) before a clear yes
- asks for a discount or a plan and accepts being told no
- anything that stays possible within `expected`; never make the customer do something that would change the outcome

## Output format (exact)
One JSON array in a single code block, to be saved as `external/<agent>/scripts/scripts-pub.json` (or `-c`, `-d`, `-e`). One object per case:
```
{"id":"PUB-01","style_tags":["pieces","talkative"],"script":"<new script, 1 to 3 sentences, third person like the originals>","extra_checks":["<one added check line per style>"]}
```
Keep the original `id`. Do not copy `expected`. Each script under 60 words. Do not contradict `identity` or `products`. After the array, add a 5-line note on which styles were hardest to keep consistent with `expected`.
