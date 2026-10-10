"""Generated local scenarios for any spec: no Freya calls, no model calls, no hand-written customer scripts.

    python -m builder.generate.auto_sim <spec.json> <tool_api.json> [-v] [--only substring]

A customer (identity answers, products, call time) is made up from the spec and the tool API. Scenarios derived from the
spec (pay in full, refuse, partial offers, bad dates, every intent, wrong identity answers, third parties, a failing
create_promise) are driven through the generated engine and the in-process stand-in bank, and the bank's ledger is
checked against brief-independent invariants:

- exactly one close_call, last, accepted by the tool API's enums; the outcome/reason pair is in the spec's outcome table
- every promise: known product, amount between the product's floor and its past-due amount, a business day that is not
  before today and not after the product's deadline, one promise per product
- notes only where the spec allows them, never for a product that has a promise
- callbacks inside the spec's day and time window
- no tool call that the bank refused (bad enum value, unknown product), apart from injected 500s
- the outcome agrees with the ledger (promise outcome only with a promise, transfer outcome only after a transfer)
- scenario expectations that follow from the spec itself (wrong answers end as the spec's failed-verification close, ...)

Findings go to the trace as compiler gaps; nothing here changes the workflow.
"""
import datetime as dt
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'tools'))

from builder.generate.ecfg import build_E
from builder.logic import snippet_lib as sl

BUILTIN = ('agree', 'refuse', 'too_much', 'offer', 'evasive', 'question', 'none')
START = dt.date(2026, 10, 14)


def I(i, **k):
    return dict(x_intent=(i if i in BUILTIN else 'sp_' + i), **k)


def TP(ev, d='', t=''):
    return dict(tp_event=ev, tp_date=d, tp_time=t)


def _tools(spec):
    t = spec.get('tools') or {}
    t = t.get('tools') if isinstance(t.get('tools'), dict) else t
    return {k: v for k, v in t.items() if isinstance(v, dict)}


def _date_text(d):
    return '%s %d %s' % (sl.WD_NAMES[d.weekday()], d.day, d.strftime('%B'))


def _hhmm(mins):
    return '%d:%02d' % (mins // 60, mins % 60)


def _nows(cal):
    """Two call times: an ordinary business day, and the business day before the first holiday (if the calendar has one)."""
    def bd_from(d):
        return sl.next_bd(d, cal, include_self=True) or d
    a = bd_from(START)
    out = [a]
    hol = sorted(h for h in cal.get('holidays') or [] if h >= a.isoformat())
    if hol:
        try:
            h = dt.date.fromisoformat(hol[0])
            b = h - dt.timedelta(days=1)
            while not sl.is_bd(b, cal):
                b -= dt.timedelta(days=1)
            if b > a:
                out.append(b)
        except ValueError:
            pass
    return out


def _types(spec, E, tools):
    items = (((tools.get('get_account') or {}).get('response_fields') or {}).get('products') or {}).get('items') or {}
    ts = list((items.get('type') or {}).get('enum') or [])
    for src in (E.get('floor_field') or {}, E.get('pn') or {}, E.get('formula') or {}):
        for t in src:
            if t not in ts:
                ts.append(t)
    return ts or ['product'], items


def _identity(spec):
    qs = (spec.get('identity') or {}).get('questions') or []
    truth, wrong = {}, {}
    for i, q in enumerate(qs):
        f = q.get('field')
        if not f:
            continue
        fmt = '%s %s' % (q.get('format') or '', f)
        if 'YYYY-MM-DD' in fmt or 'date' in fmt.lower() or 'birth' in fmt.lower():
            truth[f] = '1980-03-14'
            wrong[f] = ['21 August 1992', '2 January 1975', '30 November 1969', '9 May 1958', '17 June 1949', '1 April 1941']
        else:
            truth[f] = '4821'
            wrong[f] = ['1111', '2222', '3333', '5555', '6666', '7777']
    return qs, truth, wrong


def make_product(E, items, ptype, days, pd=1000.0, nth=1):
    raw = {'product_id': 'p%d' % nth, 'type': ptype}
    for k, v in items.items():
        if k in raw:
            continue
        raw[k] = '1234' if v.get('type') == 'string' else (100 if v.get('type') == 'integer' else 100.0)
    raw[E['f_pd']] = pd
    raw[E['f_days']] = days
    ff = (E.get('floor_field') or {}).get(ptype)
    if ff:
        raw[ff] = round(pd / 4, 2)
    raw.pop('product_id')
    return raw


def floor_of(E, raw):
    ff = (E.get('floor_field') or {}).get(raw.get('type'))
    v = None
    if ff and raw.get(ff) not in (None, ''):
        v = float(raw[ff])
    fm = (E.get('formula') or {}).get(raw.get('type'))
    if v is None and isinstance(fm, dict):
        try:
            v = round(float(raw.get(fm.get('field') or E['f_pd'])) * float(fm.get('percent_of_field')) / 100.0 + 0.004999, 2)
        except Exception:
            v = None
    pd = float(raw[E['f_pd']])
    return pd if (v is None or v <= 0 or v > pd) else v


def deadline_of(E, raw, today):
    cal = E['cal']
    band = sl.band_for(raw[E['f_days']], cal)
    bands = cal.get('bands') or []
    if band is None and bands:
        band = bands[-1] if (bands[-1].get('max') is not None and int(raw[E['f_days']]) > bands[-1]['max']) else bands[0]
    return sl.deadline_for(today, band, cal) if band else None


# ---------------------------------------------------------------- invariants

def _pair_ok(closing, outcome, reason):
    outs = closing.get('outcomes') or []
    if not outs:
        return True
    for o in outs:
        if o.get('outcome') == outcome:
            rs = o.get('reasons') or []
            return (reason in rs) if rs else not reason
    return False


def invariants(spec, E, case, led):
    bad = []
    cal, now = E['cal'], case['variables']['now']
    today = dt.date.fromisoformat(now[:10])
    prods = {'p%d' % (i + 1): p for i, p in enumerate(case['products'])}
    calls = led.get('calls') or []
    closes = [c for c in calls if c['tool'] == 'close_call']
    if len(closes) != 1 or calls[-1]['tool'] != 'close_call':
        bad.append('close_call called %d times, or not last' % len(closes))
    elif led.get('outcome') is None:
        bad.append('close_call refused by the tool API: %s' % (closes[0].get('result') or {}).get('error'))
    for c in calls:
        r = c.get('result') or {}
        if r.get('ok') is False and c.get('status') != 500 and c['tool'] != 'verify_identity':
            bad.append('bank refused %s: %s' % (c['tool'], r.get('error')))
    oc, rs = led.get('outcome'), led.get('reason')
    if oc is not None and not _pair_ok(spec.get('closing') or {}, oc, rs):
        bad.append('closed with (%s, %s), not in the spec outcome table' % (oc, rs))
    seen = set()
    for p in led.get('promises') or []:
        raw = prods.get(p['product_id'])
        if raw is None:
            bad.append('promise for unknown product %s' % p['product_id']); continue
        if p['product_id'] in seen:
            bad.append('two promises for %s' % p['product_id'])
        seen.add(p['product_id'])
        fl, pd = floor_of(E, raw), float(raw[E['f_pd']])
        if not (fl - 0.005 <= p['amount'] <= pd + 0.005):
            bad.append('promise amount %s outside floor %s..past due %s' % (p['amount'], fl, pd))
        try:
            d = dt.date.fromisoformat(p['date'])
        except ValueError:
            bad.append('promise date %r is not a date' % p['date']); continue
        dead = deadline_of(E, raw, today)
        if d < today:
            bad.append('promise date %s is before today' % d)
        if not sl.is_bd(d, cal):
            bad.append('promise date %s is not a business day' % d)
        if dead and d > dead:
            bad.append('promise date %s is after the deadline %s' % (d, dead))
    noted = {}
    for n in led.get('notes') or []:
        noted.setdefault(n.get('product_id'), []).append(n['reason'])
        if not E['use_notes']:
            bad.append('note %s although the spec has no note tool' % n['reason'])
        elif E['note_reasons'] and n['reason'] not in E['note_reasons']:
            bad.append('note reason %s is not one of the spec note reasons %s' % (n['reason'], E['note_reasons']))
        if n.get('product_id') in seen and not case.get('faults'):
            bad.append('note on %s, which has a promise' % n.get('product_id'))
    mx = (E['tp'].get('max_bad'))
    for cb in led.get('callbacks') or []:
        try:
            d = dt.date.fromisoformat(cb['date'])
            mins, st = sl.parse_time(cb['time'])
        except Exception:
            bad.append('callback %s is not a date and time' % cb); continue
        stt, _, _ = sl.check_callback(cb['date'], cb['time'], today, int(now[11:13]) * 60 + int(now[14:16]), cal)
        if stt != 'ok':
            bad.append('callback %s %s is not allowed by the spec window (%s)' % (cb['date'], cb['time'], stt))
    out = E['out']
    if led.get('promises') and oc in (out.get('r_nopromise'), out.get('r_paid')) and oc != out.get('r_promise'):
        bad.append('a promise is on record but the call closed %s' % oc)
    if oc is not None and oc == out.get('r_promise') and not led.get('promises'):
        bad.append('closed %s without any promise on record' % oc)
    if oc is not None and oc == out.get('r_transfer') and out.get('r_transfer') not in (out.get('r_promise'), out.get('r_nopromise')) \
            and not led.get('transfers'):
        bad.append('closed %s without a transfer' % oc)
    return bad


# ---------------------------------------------------------------- scenarios

def scenarios(spec, E, tools, api_ok=True):
    """-> list of dicts: name, steps ('identity' / 'tp' also), products (raw dicts), now, faults, expect(E, led) -> [problems]."""
    cal = E['cal']
    qs, truth, wrong = _identity(spec)
    types, items = _types(spec, E, tools)
    bands = cal.get('bands') or [{'min': 1, 'max': 30}]
    multi = bool((spec.get('meta') or {}).get('multi_product')) and (int((spec.get('meta') or {}).get('max_products') or 2) > 1)
    nows = _nows(cal)
    out, ox = [], E['out']
    note_ok = lambda *a: []

    def band_days(b):
        lo, hi = b.get('min'), b.get('max')
        lo = 1 if lo is None else lo
        return lo if hi is None else (lo + hi) // 2

    def eq(oc, rs=None, transfers=None, label=''):
        def f(E_, led, case):
            p = []
            if (led.get('outcome'), led.get('reason')) != (oc, rs or None):
                p.append('%s closed (%s, %s), the spec says (%s, %s)' % (label, led.get('outcome'), led.get('reason'), oc, rs))
            if transfers is not None and sorted(t['queue'] for t in led.get('transfers') or []) != sorted(transfers):
                p.append('%s transfers %s, expected %s' % (label, led.get('transfers'), transfers))
            return p
        return f

    def no_promise(E_, led, case):
        return ['promise recorded although the customer only refused'] if led.get('promises') else []

    def promised(E_, led, case):
        return [] if led.get('promises') else ['no promise recorded although the customer agreed to a valid offer']

    def add(name, prods, now, steps, expect=None, faults=None):
        out.append({'name': name, 'products': prods, 'now': now, 'steps': steps, 'expect': expect, 'faults': faults or []})

    def customer_scen(tag, prods, now, full):
        today = now
        raws = prods
        dls = [d for d in (deadline_of(E, r, today) for r in raws) if d]
        dl = min(dls) if dls else None
        fl = min(floor_of(E, r) for r in raws)
        pd = max(float(r[E['f_pd']]) for r in raws)
        single = len(raws) == 1
        add(tag + 'pay_full', raws, now, [I('agree')], promised if single else None)
        add(tag + 'refuse_all', raws, now, [I('refuse')], (lambda E_, led, case: no_promise(E_, led, case) + (
            eq(E['exhausted']['outcome'], E['exhausted']['reason'], label='refusal')(E_, led, case) if single and E['exhausted'].get('outcome') else [])))
        if dl:
            add(tag + 'floor_offer', raws, now, [I('refuse'), I('offer', x_amount=str(int(fl)) if fl == int(fl) else str(fl), x_date=_date_text(dl)), I('agree')])
        if not full:
            return
        add(tag + 'too_much', raws, now, [I('too_much'), I('agree')])
        add(tag + 'evasive', raws, now, [I('evasive'), I('question'), I('agree')])
        if fl > 1:
            add(tag + 'below_floor', raws, now, [I('offer', x_amount=str(int(fl // 2)), x_date=_date_text(dl) if dl else 'tomorrow'), I('agree')])
        if dl:
            late = sl.add_bd(dl, 3, cal)
            if late:
                add(tag + 'after_deadline', raws, now, [I('offer', x_date=_date_text(late)), I('agree')])
            add(tag + 'deadline_refused', raws, now, [I('offer', x_date=_date_text(late or dl)), I('refuse')])
        good = _date_text(sl.next_bd(now, cal) if dl is None or sl.next_bd(now, cal) <= dl else dl)   # the day the customer settles on
        add(tag + 'yesterday', raws, now, [I('offer', x_date=_date_text(now - dt.timedelta(days=1))), I('offer', x_date=good), I('agree')])
        sat = now + dt.timedelta(days=(5 - now.weekday()) % 7 or 7)
        add(tag + 'weekend', raws, now, [I('offer', x_date=_date_text(sat)), I('offer', x_date=good), I('agree')])
        for h in cal.get('holidays') or []:
            try:
                hd = dt.date.fromisoformat(h)
            except ValueError:
                continue
            if now < hd and (dl is None or hd <= dl) and sl.is_bd(hd, {**cal, 'holidays': []}):
                add(tag + 'holiday', raws, now, [I('offer', x_date=_date_text(hd)), I('offer', x_date=good), I('agree')])
                break
        for key, it in (E.get('intents') or {}).items():
            iid = it['id']
            kind = it.get('kind')
            ex = None
            if single:
                if kind == 'transfer':
                    ex = eq(it['close'].get('outcome'), it['close'].get('reason'), [it['queue']], 'intent %s' % iid)
                elif kind in ('note', 'close') and it.get('close') and not it.get('continues'):
                    ex = eq(it['close'].get('outcome'), it['close'].get('reason'), None, 'intent %s' % iid)
                elif kind == 'quit':
                    ex = eq(it['close_verified'].get('outcome'), it['close_verified'].get('reason'), None, 'intent %s' % iid)
            if kind == 'offer':
                a = it['on_accept']
                add(tag + 'intent_%s_accept' % iid, raws, now, [I(iid), I('agree')],
                    eq(a['close'].get('outcome'), a['close'].get('reason'), [a['queue']], 'intent %s accepted' % iid) if single and a.get('queue') else None)
                d = it['on_decline']
                add(tag + 'intent_%s_decline' % iid, raws, now, [I(iid), I('refuse')],
                    eq(d.get('outcome'), d.get('reason'), None, 'intent %s declined' % iid) if single and d.get('outcome') else None)
            elif kind == 'continue':
                add(tag + 'intent_%s' % iid, raws, now, [I(iid), I('agree')])
            else:
                add(tag + 'intent_%s' % iid, raws, now, [I(iid)], ex)
        if single:
            cf = E['create_failed']
            if (E.get('max_tries') or 0) >= 2:
                add(tag + 'promise_fails_once', raws, now, [I('agree')], promised, [{'tool': 'create_promise', 'fail_first_n': 1}])
            add(tag + 'promise_always_fails', raws, now, [I('agree')],
                (lambda E_, led, case: ['promise on record although every create_promise failed'] if led.get('promises') else
                 (eq(cf['outcome'], cf['reason'], label='service error')(E_, led, case) if cf.get('outcome') else [])),
                [{'tool': 'create_promise', 'fail_first_n': 99}])
        else:
            add(tag + 'promise_always_fails', raws, now, [I('agree')], None, [{'tool': 'create_promise', 'fail_first_n': 99}])

    for ni, now in enumerate(nows):
        tag0 = '' if ni == 0 else 'hol%d:' % ni
        for bi, b in enumerate(bands):
            days = band_days(b)
            for ti, t in enumerate(types):
                if ni and bi != len(bands) - 1:
                    continue
                if ti and bi not in (0, len(bands) - 1):
                    continue
                tag = '%s%s/%s:' % (tag0, b.get('name') or 'band%d' % bi, t)
                customer_scen(tag, [make_product(E, items, t, days)], now, full=(ti == 0 and bi in (0, len(bands) - 1) and ni == 0) or (ti == 0 and ni == 0))
        if multi:
            n = min(3, int((spec.get('meta') or {}).get('max_products') or 2))
            prods = [make_product(E, items, types[i % len(types)], band_days(bands[i % len(bands)]), pd=1000.0 + 500 * i, nth=i + 1) for i in range(n)]
            customer_scen('%smulti%d:' % (tag0, n), prods, now, full=(ni == 0))
    now0 = nows[0]
    # identity
    if qs and truth:
        mw = int((spec.get('identity') or {}).get('max_wrong_answers_total') or 3)
        script = []
        for k in range(mw + 2):
            f = qs[k % len(qs)].get('field')
            script.append((f, wrong[f][(k // len(qs)) % len(wrong[f])]))
        f = E['idv']['failed']
        add('identity_wrong', [make_product(E, items, types[0], band_days(bands[0]))], now0, 'identity',
            (lambda E_, led, case: [x for x in eq(f['outcome'], f['reason'], label='failed verification')(E_, led, case)] +
             (['account tool called before verification passed'] if any(c['tool'] == 'get_account' for c in led['calls']) else [])))
        out[-1]['wrong_script'] = script
        out[-1]['max_wrong'] = mw
    # third party
    tpe = E['tp']
    tpn = lambda **k: {'products': [make_product(E, items, types[0], band_days(bands[0]))], 'now': now0, **k}
    cb_lo, cb_hi = cal.get('cb_start'), cal.get('cb_end')
    if tpe['wrong_number'].get('outcome'):
        add('tp_wrong_number', tpn()['products'], now0, [TP('wrong_number')], eq(tpe['wrong_number']['outcome'], tpe['wrong_number']['reason'], label='wrong number'))
    if tpe['deceased'].get('outcome'):
        add('tp_deceased', tpn()['products'], now0, [TP('deceased')], eq(tpe['deceased']['outcome'], tpe['deceased']['reason'], label='deceased'))
    nxt = sl.next_bd(now0, cal)
    if nxt and cb_lo is not None and cb_hi is not None and tpe['on_scheduled'].get('outcome'):
        good = _hhmm(min(cb_lo + 120, cb_hi))
        bad_t = _hhmm(cb_lo - 120) if cb_lo >= 180 else _hhmm(min(cb_hi + 120, 23 * 60 + 30))
        def sched(E_, led, case):
            p = eq(tpe['on_scheduled']['outcome'], tpe['on_scheduled']['reason'], label='callback')(E_, led, case)
            return p + ([] if len(led.get('callbacks') or []) == 1 else ['expected one callback on record'])
        add('tp_callback_ok', tpn()['products'], now0, [TP('other'), TP('gives_time', _date_text(nxt), good)], sched)
        add('tp_callback_bad_then_ok', tpn()['products'], now0, [TP('other'), TP('gives_time', _date_text(nxt), bad_t), TP('gives_time', _date_text(nxt), good)], None)
        if tpe['on_failed'].get('outcome'):
            def failed(E_, led, case):
                p = eq(tpe['on_failed']['outcome'], tpe['on_failed']['reason'], label='no callback')(E_, led, case)
                return p + (['callback on record although every time was outside the window'] if led.get('callbacks') else [])
            add('tp_callback_never_ok', tpn()['products'], now0, [TP('other'), TP('gives_time', _date_text(nxt), bad_t)], failed)
    for s in out:
        s['third_party'] = s['name'].startswith('tp_')
    return out


# ---------------------------------------------------------------- runner

def run(spec, api, verbose=False, only=None, deadline=None, echo=True):
    """-> {'total': n, 'failed': [(name, [problems])], 'errors': [...]}. Never raises for a bad scenario."""
    import time
    from builder.generate import local_sim as ls
    from harness.mock_bank import Bank
    E = build_E(spec)
    tools = _tools(spec)
    qs, truth, _ = _identity(spec)
    res = {'total': 0, 'failed': [], 'errors': []}
    cases, scen = [], scenarios(spec, E, tools)
    for i, s in enumerate(scen):
        if only and only not in s['name']:
            continue
        cid = 'AUTO-%03d' % i
        v = {'first_name': 'Alex', 'last_name': 'Auto', 'title': 'Mx', 'now': s['now'].isoformat() + 'T11:00'}
        for cv in spec.get('call_variables') or []:
            if cv.get('name') and cv['name'] not in v and cv['name'] != 'customer_id':
                v[cv['name']] = 'x'
        case = {'id': cid, 'family': 'Third party' if s['third_party'] else 'Auto', 'title': s['name'], 'variables': v,
                'identity': truth, 'products': s['products'], 'faults': s['faults'], 'bank': {'max_wrong': s.get('max_wrong', 3)},
                'expected': {'outcome': None, 'reason': None, 'promises': [], 'notes': [], 'callbacks': [], 'transfers': []}}
        if s['steps'] == 'identity':
            case['wrong_script'] = s['wrong_script']
        cases.append((s, case))
    allc = [c for _, c in cases]
    for s, case in cases:
        if deadline and time.time() > deadline:
            res['errors'].append('time slice used up; %d scenarios not run' % (len(cases) - res['total']))
            break
        res['total'] += 1
        try:
            led = ls.drive(spec, case, [] if s['steps'] == 'identity' else s['steps'], verbose=verbose, api=api, cases=allc, raw=True, cycle=True)
            probs = invariants(spec, E, case, led)
            if s['expect']:
                probs += s['expect'](E, led, case)
        except Exception as e:  # noqa: BLE001
            probs = ['engine error: %r' % (e,)]
        if probs:
            res['failed'].append((s['name'], sorted(set(probs))))
        if echo:
            print('FAIL' if probs else 'PASS', s['name'], '; '.join(sorted(set(probs))) if probs else '')
    return res


def summary(res):
    n_bad = len(res['failed'])
    head = 'generated local scenarios: %d run, %d failed' % (res['total'], n_bad)
    lines = ['%s: %s' % (n, '; '.join(p)) for n, p in res['failed'][:12]]
    return head, lines + res['errors']


if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if not a.startswith('-')]
    only = sys.argv[sys.argv.index('--only') + 1] if '--only' in sys.argv else None
    if only:
        args = [a for a in args if a != only]
    if len(args) != 2:
        sys.exit(__doc__)
    spec = json.load(open(args[0], encoding='utf-8-sig'))
    api = json.load(open(args[1], encoding='utf-8-sig'))
    r = run(spec, api, verbose='-v' in sys.argv, only=only)
    print(summary(r)[0])
    sys.exit(1 if r['failed'] or r['errors'] else 0)
