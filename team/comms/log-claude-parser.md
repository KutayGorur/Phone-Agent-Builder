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
