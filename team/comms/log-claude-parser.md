# log claude-parser (task 13)

## 2026-10-10T18:55Z
- Claimed row 13. Saved H degrade ("unhashable dict") was not reproducible from saved debug files; only `set(reasons)` (already fixed, ACC-08) and `d not in WEEKDAYS`-style checks could raise it.
- validate.py: new `shape_errors()` (path-specific, runs first); the four check groups run independently and a crash in one becomes one error. spec_parser.py: `_quarantine()` nulls a section still malformed after repair, moves its rules to extra_rules, keeps the rest.
- tests/parse/test_malformed.py (15 malformed shapes + one-section degrade) and builder/parse/selftest.py pass.
- Next: one real H parse.

## 2026-10-10T19:30Z
- Real H parse (build.py --dry-run, 185s): not degraded; identity (membership_year then postal_code), calendar (3 holidays), bands (1-8: 7 days/1 attempt; 9-55: 4 days/2), closing (6 outcomes, note reasons, REFER/NO_ANSWER reasons) all populated and matching answer-key-h.md. Callback 09:45-16:45.
- Remaining 2 errors were `rule_coverage -> open_questions[0]`: validate now accepts open_questions as context. Revalidated offline: 0 errors.
- Saved builder/specs/brief-h.spec.json (also out/brief-h.spec.json). TASK 05: you can finish H from it (local_sim h scenario).
- Cause of the original degrade not reproduced (model output varies); every nested-shape path now gives an error or a one-section fallback instead of an exception.

## 2026-10-10T19:50Z follow-up from task 05 (TH-04, TH-06)
- Parser did not drop intent actions. H's hardship uses on_accept/on_decline like A and G, but on_decline had `note_remaining_products` (an invented key) and no outcome; persuasion.on_exhausted had `note_reason` and no outcome, so ecfg took r_nopromise from the text of "when" and picked PAID_CLAIM.
- Generic fix: spec_parser.normalize_intents (runs after extract and after each repair) maps invented note keys to `note: {reason}` and, for a note-only branch, fills `base: {outcome, reason}` from the single closing outcome that lists the reason. validate.shape_errors now flags on_accept/on_decline/close_verified/close_unverified with no readable outcome/reason/note.
- H spec updated offline (no re-parse). local_sim: 61/62; TH-04 passes.
- TH-06 is a script bug in local_sim.py (task 05's file): step 2 `agree` accepts the loan offer, then the later `refuse` steps never reach a close. With script [offer card tomorrow, refuse, refuse, agree] the engine closes COMMIT + NO_AGREEMENT note on p2 and passes.
