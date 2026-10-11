"""Turn spec.json into the flat config dict the snippet library runs on.

Nothing here is brief-specific: every value is read from the spec. Missing sections
leave their keys as None (or the documented default) and add a line to
cfg['warnings'] so the generator can see what was not configured.
"""
import re

_DAY_INDEX = {'mon': 0, 'tue': 1, 'wed': 2, 'thu': 3, 'fri': 4, 'sat': 5, 'sun': 6}


def _day_index(name):
    return _DAY_INDEX.get(str(name).strip().lower()[:3])


def _hhmm(s):
    m = re.match(r'^\s*(\d{1,2}):(\d{2})\s*$', str(s)) if s is not None else None
    return int(m.group(1)) * 60 + int(m.group(2)) if m else None


def _num(v):
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)) and v >= 0:
        return int(v)
    if isinstance(v, str) and v.strip().isdigit():
        return int(v.strip())
    return None


def read_deadline(dl):
    """A band deadline object -> (business days after today, calendar days after today, roll). Business days win when both
    are given. Calendar-day deadlines that land on a closed day roll back (default) or forward, as the spec says."""
    if isinstance(dl, (int, float)) and not isinstance(dl, bool):
        return _num(dl), None, None
    if not isinstance(dl, dict):
        return None, None, None
    bd = next((_num(dl[k]) for k in ('business_days_after_today', 'working_days_after_today', 'business_days', 'working_days') if _num(dl.get(k)) is not None), None)
    cd = next((_num(dl[k]) for k in ('calendar_days_after_today', 'calendar_days', 'days_after_today', 'days') if _num(dl.get(k)) is not None), None)
    roll = None
    for k in ('if_non_business_day', 'if_non_working_day', 'non_business_day', 'on_non_business_day', 'roll', 'rolled', 'roll_direction', 'if_closed'):
        v = dl.get(k)
        if isinstance(v, str):
            t = v.lower()
            roll = 'forward' if re.search(r'forward|next|after|later|following', t) and not re.search(r'back|before|previous|earlier|prior', t) else 'back'
            break
    return bd, (None if bd is not None else cd), (roll or 'back')


def config_from_spec(spec):
    spec = spec or {}
    warnings = []

    cal = spec.get('calendar') or {}
    days = [_day_index(d) for d in (cal.get('business_days') or [])]
    days = sorted(set(d for d in days if d is not None))
    if not days:
        warnings.append('calendar.business_days missing: defaulted to Mon-Fri')
        days = [0, 1, 2, 3, 4]
    holidays = sorted(set(str(h) for h in (cal.get('holidays') or [])))
    week_start = _day_index(cal.get('week_start')) if cal.get('week_start') else None
    if week_start is None:
        week_start = 0

    bands = []
    for b in spec.get('bands') or []:
        dl = b.get('deadline') or {}
        bd, cd, roll = read_deadline(dl)
        bands.append({
            'name': b.get('name'),
            'min': b.get('days_late_min'),
            'max': b.get('days_late_max'),
            'deadline_bd': bd,
            'deadline_cd': cd,
            'deadline_roll': roll,
            'attempts': b.get('persuasion_attempts'),
        })
    if not bands:
        warnings.append('bands missing: no deadline can be computed')

    cb = (spec.get('third_party') or {}).get('callback') or {}
    if not cb:
        warnings.append('third_party.callback missing: callback window unchecked')

    order = None
    for q in (spec.get('identity') or {}).get('questions') or []:
        if q.get('field') == 'date_of_birth' or q.get('numeric_date_order'):
            order = q.get('numeric_date_order')
            if order:
                break
    order = str(order).upper() if order else 'DMY'

    amounts = spec.get('amounts') or {}

    return {
        'bd': days,
        'holidays': holidays,
        'week_start': week_start,
        'bands': bands,
        'cb_days': cb.get('allowed_days'),
        'cb_start': _hhmm(cb.get('window_start')),
        'cb_end': _hhmm(cb.get('window_end')),
        'cb_inclusive': cb.get('inclusive') is not False,
        'cb_after_now': cb.get('must_be_after_now') is not False,
        'dob_order': order,
        'floor_field_by_product': amounts.get('floor_field_by_product'),
        'warnings': warnings,
    }
