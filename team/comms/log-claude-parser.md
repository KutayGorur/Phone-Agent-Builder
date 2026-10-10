# log claude-parser (task 13)

## 2026-10-10T18:55Z
- Claimed row 13. Saved H degrade ("unhashable dict") was not reproducible from saved debug files; only `set(reasons)` (already fixed, ACC-08) and `d not in WEEKDAYS`-style checks could raise it.
- validate.py: new `shape_errors()` (path-specific, runs first); the four check groups run independently and a crash in one becomes one error. spec_parser.py: `_quarantine()` nulls a section still malformed after repair, moves its rules to extra_rules, keeps the rest.
- tests/parse/test_malformed.py (15 malformed shapes + one-section degrade) and builder/parse/selftest.py pass.
- Next: one real H parse.
