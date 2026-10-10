"""Spec-driven date, amount and DOB logic for Freya code nodes.

This file is BOTH imported by the local unit tests AND pasted verbatim into every
rendered code snippet (see render.py), so the tested code is the shipped code.

Sandbox rules it obeys: only `re` and `datetime` are imported, no double braces
anywhere, no f-strings, nothing raises at import time. Every function takes the
config dict `cfg` explicitly (built by config.config_from_spec).
"""
import re
import datetime

WD_NAMES = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
WD_ALIASES = {
    'mon': 0, 'monday': 0, 'tue': 1, 'tues': 1, 'tuesday': 1,
    'wed': 2, 'weds': 2, 'wednesday': 2, 'thu': 3, 'thur': 3, 'thurs': 3, 'thursday': 3,
    'fri': 4, 'friday': 4, 'sat': 5, 'saturday': 5, 'sun': 6, 'sunday': 6,
}
MONTH_ALIASES = {
    'jan': 1, 'january': 1, 'feb': 2, 'february': 2, 'mar': 3, 'march': 3,
    'apr': 4, 'april': 4, 'may': 5, 'jun': 6, 'june': 6, 'jul': 7, 'july': 7,
    'aug': 8, 'august': 8, 'sep': 9, 'sept': 9, 'september': 9,
    'oct': 10, 'october': 10, 'nov': 11, 'november': 11, 'dec': 12, 'december': 12,
}
_SCAN_LIMIT = 4000


# ---------------------------------------------------------------- parsing

def parse_now(s):
    """'2026-10-14T11:00' -> (date, minutes_since_midnight or None). (None, None) if unreadable."""
    try:
        m = re.match(r'^\s*(\d{4})-(\d{1,2})-(\d{1,2})(?:[T ]+(\d{1,2}):(\d{2}))?', str(s))
        if not m:
            return None, None
        d = datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        mins = None
        if m.group(4) is not None:
            mins = int(m.group(4)) * 60 + int(m.group(5))
        return d, mins
    except Exception:
        return None, None


def parse_iso(s):
    """Strict YYYY-MM-DD -> date or None."""
    try:
        m = re.match(r'^\s*(\d{4})-(\d{2})-(\d{2})\s*$', str(s))
        if not m:
            return None
        return datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except Exception:
        return None


def fmt_time(mins):
    return '%02d:%02d' % (mins // 60, mins % 60)


def parse_hhmm(s):
    """'10:00' -> minutes, or None (used for config values)."""
    try:
        m = re.match(r'^\s*(\d{1,2}):(\d{2})\s*$', str(s))
        if not m:
            return None
        return int(m.group(1)) * 60 + int(m.group(2))
    except Exception:
        return None


# ---------------------------------------------------------------- calendar

def is_bd(d, cfg):
    return d.weekday() in cfg['bd'] and d.isoformat() not in cfg['holidays']


def next_bd(d, cfg, include_self=False):
    """First business day after d (or d itself when include_self). None if there is none."""
    cur = d if include_self else d + datetime.timedelta(days=1)
    for _ in range(_SCAN_LIMIT):
        if is_bd(cur, cfg):
            return cur
        cur = cur + datetime.timedelta(days=1)
    return None


def add_bd(d, n, cfg):
    """The n-th business day after d (n >= 1). None if n is not a positive integer or no calendar."""
    try:
        n = int(n)
    except Exception:
        return None
    if n < 1:
        return None
    cur = d
    for _ in range(n):
        cur = next_bd(cur, cfg)
        if cur is None:
            return None
    return cur


def band_for(days_late, cfg):
    """The band dict whose [min, max] holds days_late, else None."""
    try:
        n = int(float(str(days_late).strip()))
    except Exception:
        return None
    for b in cfg['bands']:
        lo_ok = b.get('min') is None or n >= b['min']
        hi_ok = b.get('max') is None or n <= b['max']
        if lo_ok and hi_ok:
            return b
    return None


def deadline_for(today, band, cfg):
    if band is None or band.get('deadline_bd') is None:
        return None
    return add_bd(today, band['deadline_bd'], cfg)


def week_start(d, cfg):
    return d - datetime.timedelta(days=(d.weekday() - cfg['week_start']) % 7)


def weekday_in_week(d, weekday, cfg, weeks_ahead=0):
    start = week_start(d, cfg) + datetime.timedelta(days=7 * weeks_ahead)
    return start + datetime.timedelta(days=(weekday - cfg['week_start']) % 7)


def last_bd_of_week(d, cfg, weeks_ahead=0):
    start = week_start(d, cfg) + datetime.timedelta(days=7 * weeks_ahead)
    for i in range(6, -1, -1):
        day = start + datetime.timedelta(days=i)
        if is_bd(day, cfg):
            return day
    return None


def persuasion_date(today, cfg):
    """Last business day of this week; if that is today (or already past), last business day of next week."""
    for k in range(0, 60):
        last = last_bd_of_week(today, cfg, k)
        if last is not None and last > today:
            return last
    return None


def resolve_phrase(text, today, cfg):
    """'next friday' / 'this monday' / 'friday' / 'today' / 'tomorrow' -> (status, date).

    next X = X in the following calendar week; this X = X in the current week
    (may be before today: the promise check then reports in_past); bare X = this
    week's X if it is today or later, else next week's.
    """
    try:
        t = str(text).strip().lower()
        words = re.findall(r'[a-z]+', t)
        wd = None
        for w in words:
            if w in WD_ALIASES:
                wd = WD_ALIASES[w]
        if wd is None:
            if 'tomorrow' in words:
                return 'ok', today + datetime.timedelta(days=1)
            if 'today' in words:
                return 'ok', today
            return 'no_match', None
        if 'next' in words:
            return 'ok', weekday_in_week(today, wd, cfg, 1)
        if 'this' in words:
            return 'ok', weekday_in_week(today, wd, cfg, 0)
        this_week = weekday_in_week(today, wd, cfg, 0)
        if this_week >= today:
            return 'ok', this_week
        return 'ok', weekday_in_week(today, wd, cfg, 1)
    except Exception:
        return 'no_match', None


def read_date(text, today, cfg):
    """ISO date or weekday phrase -> (status, date); status 'ok' or 'invalid'."""
    d = parse_iso(text)
    if d is not None:
        return 'ok', d
    st, d = resolve_phrase(text, today, cfg)
    if st == 'ok':
        return 'ok', d
    return 'invalid', None


# ---------------------------------------------------------------- promise date

def check_promise_date(d, today, deadline, cfg):
    """Returns (status, final_date_or_None).

    in_past               d < today
    after_deadline        d > deadline  -> final = deadline (offer it; refusal is a flat refusal)
    moved_to_next_business_day  weekend/holiday on or before the deadline -> next business day
    ok                    d accepted as is
    """
    if d < today:
        return 'in_past', None
    if deadline is not None and d > deadline:
        return 'after_deadline', deadline
    if not is_bd(d, cfg):
        n = next_bd(d, cfg)
        if n is None:
            return 'invalid', None
        if deadline is not None and n > deadline:
            return 'after_deadline', deadline
        return 'moved_to_next_business_day', n
    return 'ok', d


# ---------------------------------------------------------------- callback

def parse_time(s):
    """Spoken/typed time -> (minutes, status). status ok | ambiguous | invalid.

    With a colon or am/pm the time is taken as written (10:00 = 10:00, 3pm = 15:00).
    A bare number such as '3' or '930' is ambiguous (am or pm).
    """
    try:
        t = str(s).strip().lower().replace('.', '')
        t = t.replace("o'clock", '').replace('oclock', '').replace('hrs', '').replace('hours', '')
        t = re.sub(r'^\s*at\s+', '', t).strip()
        if t in ('noon', 'midday'):
            return 720, 'ok'
        if t == 'midnight':
            return 0, 'ok'
        m = re.match(r'^(\d{1,2})(?:(:|h)?(\d{2}))?\s*(am|pm)?$', t)
        if not m:
            return None, 'invalid'
        hour = int(m.group(1))
        minute = int(m.group(3)) if m.group(3) is not None else 0
        sep = m.group(2)
        ampm = m.group(4)
        if minute > 59 or hour > 24:
            return None, 'invalid'
        if ampm:
            if hour < 1 or hour > 12:
                return None, 'invalid'
            if ampm == 'am':
                hour = 0 if hour == 12 else hour
            else:
                hour = 12 if hour == 12 else hour + 12
            return hour * 60 + minute, 'ok'
        if hour > 23:
            return None, 'invalid'
        if sep is None and hour <= 12 and not t.startswith('0'):
            return hour * 60 + minute, 'ambiguous'
        return hour * 60 + minute, 'ok'
    except Exception:
        return None, 'invalid'


def check_callback(date_text, time_text, today, now_min, cfg):
    """Returns (status, date_or_None, minutes_or_None).

    status: ok | invalid_date | invalid_time | ambiguous_time | bad_day |
            out_of_window | not_after_now
    """
    st, d = read_date(date_text, today, cfg)
    if st != 'ok':
        return 'invalid_date', None, None
    mins, tst = parse_time(time_text)
    if tst == 'invalid':
        return 'invalid_time', d, None
    if tst == 'ambiguous':
        return 'ambiguous_time', d, mins
    days = cfg.get('cb_days') or 'today_or_next_business_day'
    if days == 'today':
        day_ok = d == today
    elif days == 'next_business_day':
        day_ok = d == next_bd(today, cfg)
    elif days == 'any_business_day':
        day_ok = d >= today and is_bd(d, cfg)
    else:
        day_ok = d == today or d == next_bd(today, cfg)
    if not day_ok:
        return 'bad_day', d, mins
    lo = cfg.get('cb_start')
    hi = cfg.get('cb_end')
    if lo is not None and hi is not None:
        if cfg.get('cb_inclusive', True):
            in_window = lo <= mins <= hi
        else:
            in_window = lo < mins < hi
        if not in_window:
            return 'out_of_window', d, mins
    if cfg.get('cb_after_now', True) and d == today and now_min is not None and mins <= now_min:
        return 'not_after_now', d, mins
    return 'ok', d, mins


# ---------------------------------------------------------------- amounts

def parse_cents(x):
    """12, 12.5, '$1,200.50', '1.200,50', '300' -> integer cents, or None."""
    try:
        if isinstance(x, bool):
            return None
        if isinstance(x, (int, float)):
            return int(round(float(x) * 100))
        s = re.sub(r'[^0-9.,-]', '', str(x))
        if s in ('', '-', '.', ','):
            return None
        if ',' in s and '.' in s:
            if s.rfind(',') > s.rfind('.'):
                s = s.replace('.', '').replace(',', '.')
            else:
                s = s.replace(',', '')
        elif ',' in s:
            tail = s.split(',')[-1]
            if len(tail) == 2 and s.count(',') == 1:
                s = s.replace(',', '.')
            else:
                s = s.replace(',', '')
        return int(round(float(s) * 100))
    except Exception:
        return None


def fmt_cents(c):
    sign = '-' if c < 0 else ''
    c = abs(c)
    return '%s%d.%02d' % (sign, c // 100, c % 100)


def check_amount(amount, floor, past_due):
    """floor <= amount <= past_due. Returns (status, normalized_amount_or_None).

    status: ok | below_floor | above_past_due | invalid
    """
    a = parse_cents(amount)
    if a is None or a <= 0:
        return 'invalid', None
    f = parse_cents(floor)
    p = parse_cents(past_due)
    if f is not None and a < f:
        return 'below_floor', fmt_cents(a)
    if p is not None and a > p:
        return 'above_past_due', fmt_cents(a)
    return 'ok', fmt_cents(a)


# ---------------------------------------------------------------- date of birth

def _expand_year(y, today):
    if y >= 100:
        return y
    cur = today.year % 100 if today is not None else 26
    return 1900 + y if y > cur else 2000 + y


def _build_dob(day, month, year, today):
    try:
        d = datetime.date(year, month, day)
    except Exception:
        return None
    if d.year < 1900:
        return None
    if today is not None and d > today:
        return None
    return d


def normalize_dob(raw, cfg, today):
    """Any spoken/typed date of birth -> (status, 'YYYY-MM-DD' or '', ambiguous_bool).

    Numeric dates are read in cfg['dob_order'] (default DMY). Month words remove the
    ambiguity. ambiguous is True when a numeric date has day and month both <= 12 and
    different, i.e. swapping them would also be a valid date.
    """
    try:
        s = str(raw).strip().lower()
        order = cfg.get('dob_order') or 'DMY'
        # year first: 1985-03-15, 1985/3/15
        m = re.match(r'^(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})$', s)
        if m:
            d = _build_dob(int(m.group(3)), int(m.group(2)), int(m.group(1)), today)
            if d is None:
                return 'invalid', '', False
            return 'ok', d.isoformat(), False
        nums = None
        m = re.match(r'^(\d{8})$', s)
        if m:
            g = m.group(1)
            if g[:2] in ('19', '20'):
                d = _build_dob(int(g[6:8]), int(g[4:6]), int(g[0:4]), today)
                if d is not None:
                    return 'ok', d.isoformat(), False
            nums = (int(g[0:2]), int(g[2:4]), int(g[4:8]))
        if nums is None:
            m = re.match(r'^(\d{1,2})[\s./-]+(\d{1,2})[\s./-]+(\d{2}|\d{4})$', s)
            if m:
                nums = (int(m.group(1)), int(m.group(2)), int(m.group(3)))
        if nums is not None:
            if order == 'MDY':
                month, day = nums[0], nums[1]
            else:
                day, month = nums[0], nums[1]
            year = _expand_year(nums[2], today)
            d = _build_dob(day, month, year, today)
            if d is None:
                return 'invalid', '', False
            amb = day <= 12 and month <= 12 and day != month
            return 'ok', d.isoformat(), amb
        # month as a word: 15 March 1985, March 15th, 1985, 15th of March 85
        s = re.sub(r'(\d)(st|nd|rd|th)\b', r'\1', s)
        tokens = re.findall(r'[a-z]+|\d+', s)
        month = None
        numbers = []
        for tok in tokens:
            if tok.isdigit():
                numbers.append(tok)
            elif tok in MONTH_ALIASES and month is None:
                month = MONTH_ALIASES[tok]
        if month is None or len(numbers) != 2:
            return 'invalid', '', False
        a, b = numbers[0], numbers[1]
        if len(a) == 4 and len(b) <= 2:
            year, day = int(a), int(b)
        else:
            day, year = int(a), _expand_year(int(b), today)
        d = _build_dob(day, month, year, today)
        if d is None:
            return 'invalid', '', False
        return 'ok', d.isoformat(), False
    except Exception:
        return 'invalid', '', False


# ---------------------------------------------------------------- date facts text

def day_label(d, cfg):
    tag = '' if is_bd(d, cfg) else ' (not a business day)'
    return '%s %s%s' % (WD_NAMES[d.weekday()], d.isoformat(), tag)


def build_date_facts(today, now_min, band, deadline, cfg):
    lines = []
    when = day_label(today, cfg)
    if now_min is not None:
        when = when + ', time %s' % fmt_time(now_min)
    lines.append('Today is %s.' % when)
    if band is not None:
        lines.append('Band: %s.' % band['name'])
    if deadline is not None:
        lines.append('Latest promise date (deadline): %s.' % day_label(deadline, cfg))
    nb = next_bd(today, cfg)
    if nb is not None:
        lines.append('Next business day: %s.' % day_label(nb, cfg))
    pd = persuasion_date(today, cfg)
    if pd is not None:
        lines.append('Last business day of this week (of next week if that is today or past): %s.' % day_label(pd, cfg))
    for k, name in ((0, 'This week'), (1, 'Next week')):
        start = week_start(today, cfg) + datetime.timedelta(days=7 * k)
        parts = []
        for i in range(7):
            parts.append(day_label(start + datetime.timedelta(days=i), cfg))
        lines.append('%s: %s.' % (name, '; '.join(parts)))
    if cfg['holidays']:
        lines.append('Holidays: %s.' % ', '.join(cfg['holidays']))
    return '\n'.join(lines)
