# Task: write new practice bank briefs

You are helping a hackathon team. We build a program that reads a bank's brief and builds a phone agent. We practise on invented briefs so our builder is not tuned to the real ones. You have no repo access; use only the attached files.

**Files already in this project folder (read them from disk, paths as written):** `briefs/brief-a.md`, `briefs/brief-b.md` (the base briefs), `test-briefs/brief-d.md` (a long memo-style variant) and `test-briefs/brief-e.md` (a short change list on top of A+B), `test-briefs/cases-e.json` (case format), `test-briefs/tools-e.openapi.json` (tool API format).

## Rules
- Fictional bank, synthetic data. **No Freya API key, no real data, nothing copied from any hidden or official final brief.** Invent every number and date yourself.
- Keep the structure of a call (opening, identity, debt, promise, close) but vary: bands and deadlines, floors, number of persuasion attempts, callback window, holiday list, number of security questions and their fields, wrong-answer limit, sentences the agent must say, outcome/reason table.
- The seven tools stay: `verify_identity`, `get_account`, `create_promise`, `add_note`, `schedule_callback`, `transfer_to_agent`, `close_call`. Change only what the tool API allows: enum values (verify field names, product types, note reasons, queue names, outcome codes) and the names of product fields in `get_account` (e.g. `arrears` instead of `past_due`). Do not add or remove tools or parameters.
- Use dates between autumn 2026 and spring 2027 and a `now` per case. Weekday names must be correct. For every expected promise or callback date, show the business-day arithmetic in a `checks` line.

## Produce 3 briefs (F, G, H)
- **F**: clean specification, about 40 numbered rules, one product, different numbers, at least 6 distinct outcome codes.
- **G**: change list on top of A+B (like E), up to 3 products, new holidays, new security fields.
- **H**: **messy raw material**, not a spec: an internal mail from a collections manager, a policy extract with irrelevant paragraphs, a later memo that amends or reverses two earlier points, and a code list that renames outcomes and reasons. The reader must reconcile them. Put an "answer key of amendments" in a separate file, not in the brief.

## Output format (exact; one code block per file, labelled with its path)
For each X in f, g, h:
- `briefs/brief-x.md`
- `briefs/tools-x.openapi.json`: same structure as `tools-e.openapi.json`, only enums and field names changed
- `briefs/cases-x.json`: JSON array of 6 to 8 cases in exactly the format of `cases-e.json` (`id` like `TF-01`, `brief`, `family`, `level`, `title`, `variables`, `identity`, `products`, `script`, `expected` {outcome, reason, promises, notes, callbacks, transfers}, `checks`, `bank` {`max_wrong`}). Use the outcome and reason codes of your tool API. Cover: happy path, third party, wrong identity answers, hardship, vague or holiday dates, amount floor, multi-product partial promise, tool failure, restructuring transfer.
- `briefs/README-x.md`: five lines: what is varied, which rules are the traps.

Keep every file compact. If the answer is too long for one message, send F first and wait for me to say "continue" for G and H.

## Where to write
Write every output file under `output/` in this folder (never overwrite the input files). In task 1 the output paths above are relative to `output/`, e.g. `output/briefs/brief-f.md`. If you cannot write files, give each file in a code block labelled with its path.
