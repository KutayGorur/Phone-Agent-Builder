# builder/logic

Spec-driven Python for Freya code nodes. Pure stdlib (`re`, `datetime`, `json`), no platform needed.

```python
from builder.logic import render_snippet, render_all, config_from_spec
code = render_snippet('check_promise_date', spec)            # str, goes into the code_exec `code` default
code = render_snippet('date_facts', spec, var_map={'days_late': 'p1_days_late'}, out_prefix='p1_')
```

`snippet_lib.py` is pasted verbatim into every snippet, so the tested code is the shipped code. A snippet
reads `vars`, sets every output (empty/`unknown` fallback first), never raises, contains no double braces.
Booleans are the strings `true`/`false`.

| snippet | reads (default var names) | writes |
|---|---|---|
| `date_facts` | `now`, `days_late` | `date_facts_status` (known/unknown), `today`, `today_weekday`, `today_is_business_day`, `next_business_day`, `band`, `deadline`, `deadline_weekday`, `persuasion_date`, `date_facts` (text block for prompts) |
| `check_promise_date` | `now`, `days_late` or `deadline`, `promise_date_input` (ISO or "next friday") | `promise_date_status` (ok / moved_to_next_business_day / after_deadline / in_past / invalid), `promise_date_final`, `promise_date_requested`, `promise_date_deadline` |
| `resolve_weekday` | `now`, `weekday_phrase` | `weekday_status` (ok/no_match), `weekday_date` |
| `check_callback` | `now`, `callback_date_input` (ISO/phrase), `callback_time_input` | `callback_status` (ok / bad_day / out_of_window / not_after_now / invalid_date / invalid_time / ambiguous_time), `callback_date`, `callback_time` (HH:MM), `callback_next_business_day` |
| `check_amount` | `amount_input`, `floor_amount`, `past_due` | `amount_status` (ok / below_floor / above_past_due / invalid), `amount_value` ("250.00") |
| `normalize_dob` | `now`, `dob_input` | `dob_status` (ok/invalid), `dob_value` (YYYY-MM-DD or ""), `dob_ambiguous` |

Spec fields used: `calendar.business_days/holidays` (+ optional `week_start`), `bands[*]`,
`third_party.callback.*`, `identity.questions[date_of_birth].numeric_date_order`.

Decisions to know about:
- Weeks run Monday to Sunday unless `calendar.week_start` is set. "next X" = X in the following week, "this X" = X in the current week (can be past), bare "X" = this week's if today or later, else next week's.
- Callback time with a colon or am/pm is taken as written (`10:00` is 10:00). A bare number like `3` is `ambiguous_time`.
- `callback.allowed_days` supports `today_or_next_business_day` (default), `today`, `next_business_day`, `any_business_day`. "Today" counts even if today is not a business day.
- Numeric DOB is read in the spec order (DMY default); an impossible reading (`03/15/1985`) is `invalid`, not guessed. `dob_ambiguous=true` means swapping day and month is also a valid date (the day_month_swapped hint).
- Missing spec sections do not crash; they are listed in `config_from_spec(spec)['warnings']`. Missing business days defaults to Mon-Fri.

Tests: `python tests/logic/test_logic.py` (Brief A values plus a Sun-Thu variant calendar).
