"""spec.json -> the config dict `E` that engine_lib.py runs on, plus text helpers for the generator.

Everything is read from the spec; missing pieces get neutral defaults (never values from a particular brief).
"""
import re

from builder.logic.config import config_from_spec

DEFAULT_INTENT_DESC = {
    'already_paid': 'says they already paid this past-due amount',
    'dispute': 'says the debt is not theirs, never had this product, or the product was closed or paid off long ago',
    'restructuring': 'asks for a new payment plan, lower instalments or to restructure the debt',
    'human': 'asks to speak to a person, a human, an agent or a manager',
    'hardship': 'mentions illness, a death in the family or losing their job',
    'scam': 'asks whether this call is a scam, fraud or real',
    'unknown_question': 'asks a factual question about the account or bank that the agent cannot answer',
    'does_not_want_to_talk': 'says they do not want to talk, asks to stop the call or to be left alone',
}


def _s(x):
    return '' if x is None else str(x)


def _oc(d):
    """Outcome/reason pair from any of the shapes the spec uses (plain, {note: {reason}}, {close: {..}}, {base: {..}})."""
    if not isinstance(d, dict):
        return {'outcome': None, 'reason': None}
    for k in ('close', 'base'):
        if isinstance(d.get(k), dict):
            r = _oc(d[k])
            if r['outcome'] or r['reason']:
                return r
    reason = d.get('reason')
    if reason is None:
        n = d.get('note') if d.get('note') else d.get('add_note')
        if isinstance(n, dict):
            reason = n.get('reason')
        elif isinstance(n, str):
            reason = n
        elif isinstance(d.get('note_products_without_promise'), str):
            reason = d['note_products_without_promise']
    return {'outcome': d.get('outcome'), 'reason': reason}


def _amt_tok(t):
    t = _s(t).lower()
    if 'floor' in t and ('full' in t or 'past' in t):
        return 'full_or_floor'
    if 'floor' in t:
        return 'floor'
    return 'full'


def _date_tok(t):
    t = _s(t).lower()
    if 'deadline' in t:
        return 'deadline'
    if 'last business day' in t or 'this week' in t:
        return 'week'
    if 'today' in t:
        return 'today'
    return 'week'


def _words(field):
    return _s(field).replace('_', ' ')


def normalize_intents(spec):
    out = {}
    note_reasons = ((spec.get('multi_product') or {}).get('note_reasons')) or []
    for it in spec.get('intents') or []:
        iid = it.get('id')
        if not iid:
            continue
        act = it.get('action') or {}
        d = {'id': iid, 'say': it.get('say') or '', 'desc': it.get('description') or DEFAULT_INTENT_DESC.get(iid) or _words(iid),
             'ask_first': bool(it.get('ask_once_first'))}
        if 'on_accept' in it or it.get('offer_transfer'):
            d['kind'] = 'offer'
            d['offer_name'] = (_s(it.get('offer_transfer')) + ' team').strip()
            acc = it.get('on_accept') or {}
            d['on_accept'] = {'queue': acc.get('transfer') or it.get('offer_transfer'), 'close': _oc(acc)}
            dec = it.get('on_decline') or {}
            d['on_decline'] = _oc(dec)
        elif it.get('max') and (it.get('close_verified') or it.get('close_unverified')):
            d['kind'] = 'quit'
            d['max'] = it.get('max')
            d['close_verified'] = _oc(it.get('close_verified'))
            d['close_unverified'] = _oc(it.get('close_unverified'))
        elif act.get('transfer'):
            d['kind'] = 'transfer'
            d['queue'] = act['transfer']
            d['close'] = _oc(act.get('close') if isinstance(act.get('close'), dict) else {})
            d['transfer_say'] = 'I am transferring you now.'
        elif act.get('note') or act.get('add_note') or act.get('close'):
            d['kind'] = 'note' if (act.get('note') or act.get('add_note')) else 'close'
            if isinstance(act.get('close'), dict):
                d['close'] = _oc(act['close'])
            if act.get('note') or act.get('add_note'):
                d['note_reason'] = _oc({'note': act.get('note') or act.get('add_note')})['reason']
            else:
                c = act['close'] if isinstance(act['close'], dict) else {}
                d['note_reason'] = c.get('reason') or c.get('outcome')
            d['continues'] = bool(act.get('continue_with_other_products') or act.get('continue'))
        elif it.get('continue'):
            d['kind'] = 'continue'
        else:
            continue
        out['sp_' + iid] = d
    return out


def build_E(spec):
    cal = config_from_spec(spec)
    meta = spec.get('meta') or {}
    mp = spec.get('multi_product')
    opening = spec.get('opening') or {}
    ident = spec.get('identity') or {}
    tp = spec.get('third_party') or {}
    cb = tp.get('callback') or {}
    conf = spec.get('confirmation') or {}
    pers = spec.get('persuasion') or {}
    amts = spec.get('amounts') or {}
    ds = spec.get('debt_statement') or {}
    closing = spec.get('closing') or {}
    intents = normalize_intents(spec)

    floor_field = amts.get('floor_field_by_product') or {}
    floor_word = {t: _words(f) for t, f in floor_field.items() if f}
    floor_word = {t: ('minimum payment' if (f or '') in ('minimum_payment', 'minimum_due') else _words(f)) for t, f in floor_field.items() if f}
    for t in (amts.get('floor_formula_by_product') or {}):
        floor_word.setdefault(t, 'minimum payment')

    pe = []
    for i, a in enumerate(pers.get('attempts') or []):
        pe.append({'n': a.get('n') or i + 1, 'amt': _amt_tok(a.get('amount')), 'date': _date_tok(a.get('date')),
                   'bands': a.get('bands') or None})
    if not pe:
        pe = [{'n': 1, 'amt': 'full_or_floor', 'date': 'week', 'bands': None}]

    outs = closing.get('outcomes') or []
    names = [o.get('outcome') for o in outs]

    def find(pred):
        for o in outs:
            if pred(o):
                return o
        return None
    wh = lambda o: _s(o.get('when')).lower()
    promise_o = find(lambda o: not o.get('reasons') and 'promise' in wh(o) and 'no promise' not in wh(o)) or find(lambda o: not o.get('reasons'))
    ap = intents.get('sp_already_paid') or {}
    paid_reason = ap.get('note_reason') or 'paid'
    paid_o = (ap.get('close') or {}).get('outcome') if ap.get('close') else None
    if not paid_o:
        po = find(lambda o: not o.get('reasons') and o is not promise_o and 'paid' in wh(o))
        paid_o = po.get('outcome') if po else None
    exh = _oc(pers.get('on_exhausted')) if pers.get('on_exhausted') else {'outcome': None, 'reason': None}
    nop = find(lambda o: exh['reason'] and exh['reason'] in (o.get('reasons') or [])) or find(lambda o: 'no promise' in wh(o))
    if not exh['outcome'] and nop:
        exh['outcome'] = nop.get('outcome')
    if not exh['reason'] and nop and nop.get('reasons'):
        exh['reason'] = nop['reasons'][0]
    tr = [i for i in intents.values() if i.get('kind') == 'transfer']
    tro = find(lambda o: 'transfer' in wh(o))
    out = {'r_promise': promise_o.get('outcome') if promise_o else (names[0] if names else None), 'r_paid': paid_o,
           'r_nopromise': exh['outcome'], 'r_transfer': (tr[0]['close']['outcome'] if tr else (tro.get('outcome') if tro else None))}

    cf = conf.get('on_create_failed') or {}
    cfr = cf.get('reason') or _oc(cf)['reason']
    if mp and mp.get('create_promise_failure'):
        cfr = _oc({'note': (mp['create_promise_failure'] or {}).get('note')})['reason'] or cfr
    if not cfr and nop:
        cands = [r for r in (nop.get('reasons') or []) if 'error' in _s(r).lower() or 'service' in _s(r).lower() or 'fail' in _s(r).lower()]
        cfr = cands[0] if cands else (nop.get('reasons') or [None])[-1]
    create_failed = {'outcome': cf.get('outcome') or exh['outcome'], 'reason': cfr,
                     'say_text': 'I am sorry, I could not record your promise.'}

    on_dec = ident.get('on_declined') or {}
    on_fail = ident.get('on_failed') or {}
    questions = ident.get('questions') or []
    unclear = _oc(opening.get('on_unclear'))
    sched = _oc(cb.get('on_scheduled'))
    failed_cb = _oc(cb.get('on_failed'))
    wn = _oc(tp.get('wrong_number'))
    dec = tp.get('deceased') or {}
    bt = (cb.get('window_start'), cb.get('window_end'))
    goodbye = 'Thank you for your time. Goodbye.'

    inc = ds.get('include') or []
    f_pd = amts.get('past_due_field') or (inc[0] if len(inc) > 0 else 'past_due')
    b0 = (spec.get('bands') or [{}])[0]
    f_days = b0.get('days_late_field') or (inc[1] if len(inc) > 1 else 'days_late')
    pd_word = 'past due' if 'past' in f_pd else 'overdue'
    days_word = 'late' if 'late' in f_days else ('past due' if 'past' in f_days else 'overdue')
    first_q = pers.get('first_question') or 'Can you make this payment today?'
    say = ds.get('say') or 'calling about a late payment'
    if not re.match(r'^(calling|from|about|phoning)\b', say.strip().lower()):
        say = 'calling about your overdue products'
    cq = op_confirm = opening.get('confirm_identity_question') or 'Am I speaking with {title} {last_name}?'
    mwho = re.search(r'with (.+?)\?', cq)
    who = (mwho.group(1) if mwho else '{title} {last_name}').replace('{', '{{').replace('}', '}}')
    formula = amts.get('floor_formula_by_product') or {}
    E = {
        'cal': cal, 'acct_node': 'get_account', 'f_pd': f_pd, 'f_days': f_days, 'pd_word': pd_word, 'days_word': days_word,
        'who': who, 'formula': formula, 'pn': ds.get('product_names') or {}, 'floor_field': floor_field,
        'floor_word': floor_word, 'first_q': first_q, 'first_q_all': 'Can you pay all of these today?',
        'confirm_q': conf.get('confirm_question') or 'Do you confirm?',
        'after_recorded': conf.get('after_recorded_say') or '', 'goodbye': goodbye, 'debt_say': say,
        'pers': pe, 'exhausted': exh, 'use_notes': bool(mp and mp.get('note_tool')),
        'note_reasons': (mp or {}).get('note_reasons') or [],
        'max_tries': conf.get('create_promise_max_tries') or 2, 'create_failed': create_failed,
        'intents': intents, 'out': out, 'paid_reason': paid_reason, 'n_q': len(questions),
        'idv': {'max_refusals': on_dec.get('max_refusals') or 2,
                'declined': _oc(on_dec),
                'explain': on_dec.get('explain_once') or 'the questions protect their account',
                'failed': _oc(on_fail), 'failed_say': on_fail.get('say') or 'use the mobile app or a branch'},
        'tp': {'wrong_number': wn, 'deceased': _oc(dec), 'on_scheduled': sched, 'on_failed': failed_cb,
               'wrong_number_say': 'I am sorry for the disturbance. Goodbye.',
               'deceased_say': dec.get('say') or 'I am sorry for your loss.',
               'failed_say': 'Thank you. We will try to reach them another time. Goodbye.',
               'window_text': ('today or the next business day between %s and %s' % bt) if all(bt) else 'at another time',
               'max_bad': cb.get('max_out_of_window_asks') if cb.get('max_out_of_window_asks') is not None else 1},
        'hard': next((k for k, v in intents.items() if v.get('kind') == 'offer'), None),
        'human': next((k for k, v in intents.items() if v.get('kind') == 'transfer' and v.get('ask_first')), None),
        'unclear': unclear,
        'ai_say': opening.get('ai_question_answer') or "I am the bank's digital assistant.",
        'scam_say': (intents.get('sp_scam') or {}).get('say') or 'they can verify this call with the bank\'s customer service',
        'unknown_say': (intents.get('sp_unknown_question') or {}).get('say') or 'I do not have that information',
    }
    return E


def first_sentence(spec):
    op = spec.get('opening') or {}
    bank = (spec.get('meta') or {}).get('bank_name') or 'the bank'
    inc = op.get('first_sentence_must_include') or []
    if op.get('first_sentence'):
        return op['first_sentence']
    if not inc:
        return 'Hello, this is a digital assistant calling from %s, and this call is recorded.' % bank
    parts = []
    for x in inc:
        x = _s(x).strip()
        if re.match(r'^call is', x):
            x = 'this ' + x
        elif parts == []:
            x = 'this is a ' + x if not x.lower().startswith(('a ', 'an ', 'the ', 'this ')) else x
        parts.append(x)
    if len(parts) == 1:
        return 'Hello, ' + parts[0] + '.'
    return 'Hello, ' + ', '.join(parts[:-1]) + ' and ' + parts[-1] + '.'
