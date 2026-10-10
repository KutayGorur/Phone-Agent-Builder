"""Render code-node snippets (strings for the code_exec `code` default) from a spec.

    code = render_snippet('check_promise_date', spec)
    all_code = render_all(spec)

Each snippet is: library source + a JSON config blob + a small entry block that reads
`vars`, writes `vars`, and never raises. The result contains no double braces.

Input variable names can be remapped (var_map) and every output name can be prefixed
(out_prefix), e.g. for one run per product: out_prefix='p1_', var_map=dict(days_late='p1_days_late').
"""
import json
import os

from .config import config_from_spec

_HERE = os.path.dirname(os.path.abspath(__file__))

# name -> (default input var names, output var names with fallback values, entry code)
SNIPPETS = {}


def _register(name, inputs, outputs, entry):
    SNIPPETS[name] = {'inputs': inputs, 'outputs': outputs, 'entry': entry}


_register(
    'date_facts',
    ['now', 'days_late'],
    {'date_facts_status': 'unknown', 'today': '', 'today_weekday': '', 'today_is_business_day': '',
     'next_business_day': '', 'band': '', 'deadline': '', 'deadline_weekday': '',
     'persuasion_date': '', 'date_facts': ''},
    '''
    today, now_min = parse_now(_get('now'))
    if today is None:
        return
    band = band_for(_get('days_late'), CFG)
    deadline = deadline_for(today, band, CFG)
    nb = next_bd(today, CFG)
    pd = persuasion_date(today, CFG)
    _set('today', today.isoformat())
    _set('today_weekday', WD_NAMES[today.weekday()])
    _set('today_is_business_day', 'true' if is_bd(today, CFG) else 'false')
    _set('next_business_day', nb.isoformat() if nb else '')
    _set('band', band['name'] if band else '')
    _set('deadline', deadline.isoformat() if deadline else '')
    _set('deadline_weekday', WD_NAMES[deadline.weekday()] if deadline else '')
    _set('persuasion_date', pd.isoformat() if pd else '')
    _set('date_facts', build_date_facts(today, now_min, band, deadline, CFG))
    _set('date_facts_status', 'known')
''')

_register(
    'resolve_weekday',
    ['now', 'weekday_phrase'],
    {'weekday_status': 'unknown', 'weekday_date': ''},
    '''
    today, now_min = parse_now(_get('now'))
    if today is None:
        return
    st, d = resolve_phrase(_get('weekday_phrase'), today, CFG)
    if st == 'ok':
        _set('weekday_date', d.isoformat())
        _set('weekday_status', 'ok')
    else:
        _set('weekday_status', 'no_match')
''')

_register(
    'check_promise_date',
    ['now', 'days_late', 'deadline', 'promise_date_input'],
    {'promise_date_status': 'unknown', 'promise_date_final': '', 'promise_date_requested': '',
     'promise_date_deadline': ''},
    '''
    today, now_min = parse_now(_get('now'))
    if today is None:
        return
    deadline = parse_iso(_get('deadline'))
    if deadline is None:
        deadline = deadline_for(today, band_for(_get('days_late'), CFG), CFG)
    _set('promise_date_deadline', deadline.isoformat() if deadline else '')
    st, d = read_date(_get('promise_date_input'), today, CFG)
    if st != 'ok':
        _set('promise_date_status', 'invalid')
        return
    _set('promise_date_requested', d.isoformat())
    st, final = check_promise_date(d, today, deadline, CFG)
    _set('promise_date_final', final.isoformat() if final else '')
    _set('promise_date_status', st)
''')

_register(
    'check_callback',
    ['now', 'callback_date_input', 'callback_time_input'],
    {'callback_status': 'unknown', 'callback_date': '', 'callback_time': '',
     'callback_next_business_day': ''},
    '''
    today, now_min = parse_now(_get('now'))
    if today is None:
        return
    nb = next_bd(today, CFG)
    _set('callback_next_business_day', nb.isoformat() if nb else '')
    st, d, mins = check_callback(_get('callback_date_input'), _get('callback_time_input'), today, now_min, CFG)
    _set('callback_date', d.isoformat() if d else '')
    _set('callback_time', fmt_time(mins) if mins is not None else '')
    _set('callback_status', st)
''')

_register(
    'check_amount',
    ['amount_input', 'floor_amount', 'past_due'],
    {'amount_status': 'unknown', 'amount_value': ''},
    '''
    st, val = check_amount(_get('amount_input'), _get('floor_amount'), _get('past_due'))
    _set('amount_value', val if val else '')
    _set('amount_status', st)
''')

_register(
    'normalize_dob',
    ['now', 'dob_input'],
    {'dob_status': 'unknown', 'dob_value': '', 'dob_ambiguous': ''},
    '''
    today, now_min = parse_now(_get('now'))
    st, val, amb = normalize_dob(_get('dob_input'), CFG, today)
    _set('dob_value', val)
    _set('dob_ambiguous', 'true' if amb else 'false')
    _set('dob_status', st)
''')


def _lib_source():
    with open(os.path.join(_HERE, 'snippet_lib.py'), 'r', encoding='utf-8') as f:
        return f.read()


def _indent(block):
    return block.strip('\n')


def render_snippet(name, spec, var_map=None, out_prefix='', cfg=None):
    """Return the Python source (str) of one code-node snippet for this spec."""
    if name not in SNIPPETS:
        raise KeyError('unknown snippet %r; choose from %s' % (name, sorted(SNIPPETS)))
    meta = SNIPPETS[name]
    cfg = cfg if cfg is not None else config_from_spec(spec)
    var_map = dict(var_map or {})
    for k in var_map:
        if k not in meta['inputs']:
            raise KeyError('snippet %r has no input %r (inputs: %s)' % (name, k, meta['inputs']))
    blob = {'cfg': cfg, 'in': var_map, 'pfx': out_prefix}
    blob_text = json.dumps(blob, indent=1, sort_keys=True)
    if "'''" in blob_text or '\\' in blob_text:
        raise ValueError('config contains characters that cannot be embedded safely')
    lines = [
        _lib_source().rstrip('\n'),
        '',
        '',
        '# ---------------------------------------------------------------- injected from spec',
        'import json',
        "BLOB = json.loads(r'''" + blob_text + "''')",
        "CFG = BLOB['cfg']",
        "IN = BLOB['in']",
        "PFX = BLOB['pfx']",
        "OUT_DEFAULTS = json.loads(r'''" + json.dumps(meta['outputs'], indent=1, sort_keys=True) + "''')",
        '',
        '',
        'def _get(key):',
        '    return vars.get(IN.get(key, key))',
        '',
        '',
        'def _set(key, value):',
        '    vars[PFX + key] = value',
        '',
        '',
        'def _run():',
        _indent(meta['entry']),
        '',
        '',
        'for _k in OUT_DEFAULTS:',
        '    _set(_k, OUT_DEFAULTS[_k])',
        'try:',
        '    _run()',
        'except Exception:',
        '    pass',
        '',
    ]
    code = '\n'.join(lines)
    if '{{' in code or '}}' in code:
        raise ValueError('rendered snippet %r contains a double brace' % name)
    return code


def render_all(spec, var_maps=None, out_prefix=''):
    """{snippet name: code} for every snippet."""
    var_maps = var_maps or {}
    return dict((n, render_snippet(n, spec, var_maps.get(n), out_prefix)) for n in SNIPPETS)


def run_snippet(code, variables):
    """Execute a rendered snippet the way the platform does: a `vars` dict in, mutated in place."""
    ns = {'vars': variables}
    exec(compile(code, '<snippet>', 'exec'), ns)
    return variables
