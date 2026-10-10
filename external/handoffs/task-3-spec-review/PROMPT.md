# Task: review a parsed spec against two bank briefs

A program parsed two bank briefs into a JSON spec; a generator turns the spec into a phone agent. You check whether the spec matches the briefs. No repo access; use only the attached files. **No Freya API key; use nothing outside the attachments.**

**Files already in this project folder (read them from disk, paths as written):** `briefs/brief-a.md` (47 numbered rules), `briefs/brief-b.md` (11 rules that replace or extend A for up to 3 products), `builder/specs/brief-ab.spec.json` (the parsed spec for A+B together), `builder/SPEC_CONTRACT.md` (what each spec field means).

## Do
1. Read `SPEC_CONTRACT.md` first, so you know what each field means.
2. Go through Brief A rules 1-47 and Brief B rules 1-11 (B replaces A where it says so, e.g. B 10 vs A 41, B 4 vs A 28/30). For each rule decide: covered correctly, missing, wrong (value, order or wording differs), or not expressible in the contract.
3. Check exactly: holidays, bands and deadlines, persuasion attempts, floors, callback window, wrong-answer limit, outcome/reason table, sentences to say, queue names, note reasons.
4. Check interactions: precedence (e.g. A 32 over 30 and 41), per-product counting, transfers adding no notes, closing priority with several products.

## Output format (exact), to be saved as `review.md`
```
## Summary
<3 lines: verdict, number wrong, number missing>

## Findings
| # | Rule (A12 / B8 ...) | Status (wrong / missing / unclear) | Spec path (JSON pointer) | Brief says | Spec says | Suggested fix |

## Covered correctly
<comma-separated rule numbers>

## Not expressible
<rule number + one line each>
```
List only real discrepancies you can quote from the files. Write "cannot tell" instead of guessing. Do not rewrite the spec.

## Where to write
Write every output file under `output/` in this folder (never overwrite the input files). In task 1 the output paths above are relative to `output/`, e.g. `output/briefs/brief-f.md`. If you cannot write files, give each file in a code block labelled with its path.
