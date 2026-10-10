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


DATE_TOKENS = ('next_business_day', 'capped_next_business_day', 'deadline', 'midpoint', 'week_end', 'today')


def _date_tok(t, warn=None, where='persuasion attempt'):
    """Persuasion date text -> one explicit token. Text that matches no known phrase becomes 'unknown' (and a warning),
    never a guess: 'deadline' only for the deadline itself, 'week_end' only for the last business day of a week."""
    raw = _s(t).strip()
    key = re.sub(r'[\s\-]+', '_', raw.lower())
    if key in DATE_TOKENS:
        return key
    low = re.sub(r'\bwork(?:ing)?[ -]?days?\b', 'business day', raw.lower())      # "working day" is the business day
    tok = None
    if re.match(r'^(the )?(deadline|latest promise date)\.?$', low):
        tok = 'deadline'
    elif 'midpoint' in low or 'index ceiling' in low or re.search(r'ceil\w*\s*\(', low) or re.search(r'half\w*\s+(of|way|to)\b', low):
        tok = 'midpoint'
    elif 'last business day' in low and 'week' in low:
        tok = 'week_end'
    elif 'next business day' in low:
        tok = 'capped_next_business_day' if ('cap' in low or 'deadline' in low) else 'next_business_day'
    elif re.match(r'^(today|same day)\.?$', low):
        tok = 'today'
    if tok is None:
        tok = 'unknown'
        if warn is not None:
            warn.append('%s date %r is not a known date rule: compiled as "unknown" (engine default), not guessed' % (where, raw))
    return tok


_PCT_KEYS = ('percent_of_field', 'percent', 'percentage', 'pct', 'percent_of_overdue', 'percent_of_arrears')
_FRAC_KEYS = ('fraction', 'ratio', 'multiplier', 'factor')


def _formula(v, f_pd, fields=None):
    """A floor computed from the product: {'field', 'percent_of_field'} from any shape a parser may produce
    ({"field": "arrears", "percent": 25}, "25% of arrears", 0.25, ...). None when no percentage can be read."""
    pct, field = None, None
    if isinstance(v, dict):
        for k in _PCT_KEYS:
            if isinstance(v.get(k), (int, float)) and not isinstance(v.get(k), bool):
                pct = float(v[k]); break
        for k in _FRAC_KEYS:
            if pct is None and isinstance(v.get(k), (int, float)) and not isinstance(v.get(k), bool):
                pct = float(v[k]) * 100.0
        for k in ('field', 'of', 'base_field', 'of_field', 'applied_to'):
            if isinstance(v.get(k), str):
                field = v[k]; break
        if field is None and isinstance(v.get('percent_of'), str):
            field = v['percent_of']
        if pct is None and isinstance(v.get('percent_of_field'), str):
            return None
    elif isinstance(v, str):
        m = re.search(r'(\d+(?:\.\d+)?)\s*(?:%|per\s*cent|percent)', v, re.I)
        if m:
            pct = float(m.group(1))
            m2 = re.search(r'\bof\s+(?:the\s+)?([A-Za-z_]+)', v)
            field = m2.group(1) if m2 else None
    elif isinstance(v, (int, float)) and not isinstance(v, bool):
        pct = float(v) * 100.0 if 0 < v <= 1 else float(v)
    if pct is None or pct <= 0 or pct > 100:
        return None
    if fields and field not in fields:
        field = f_pd
    return {'field': field or f_pd, 'percent_of_field': pct}


def floor_rules(amts, f_pd, fields=None):
    """-> (floor_field_by_product, floor_formula_by_product). Field names stay; entries that are really formulas
    (a percentage text or object in floor_field_by_product, floor_percent_by_product) are moved to the formulas."""
    ff, fm = {}, {}
    for t, f in (amts.get('floor_field_by_product') or {}).items():
        if isinstance(f, str) and (not fields or f in fields) and not re.search(r'%|percent|per\s*cent', f, re.I):
            ff[t] = f
        elif f:
            r = _formula(f, f_pd, fields)
            if r:
                fm[t] = r
            elif isinstance(f, str):
                ff[t] = f
    for key in ('floor_percent_by_product', 'floor_percentage_by_product'):
        for t, v in (amts.get(key) or {}).items():
            r = _formula(v if isinstance(v, dict) else {'percent': v} if isinstance(v, (int, float)) else v, f_pd, fields)
            if r:
                fm[t] = r
    for t, v in (amts.get('floor_formula_by_product') or {}).items():
        r = _formula(v, f_pd, fields)
        if r:
            fm[t] = r
    return ff, fm


def _words(field):
    return _s(field).replace('_', ' ')


def normalize_intents(spec):
    out = {}
    mp = spec.get('multi_product') or {}
    note_reasons = mp.get('note_reasons') or []
    # SPEC_CONTRACT: multi_product.dispute_or_paid_continues says these two intents note the product and go on with the others,
    # even when the intent's own action does not repeat it (a parser may put the fact in either place)
    cont_ids = ('dispute', 'already_paid') if mp.get('dispute_or_paid_continues') else ()
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
            d['continues'] = bool(act.get('continue_with_other_products') or act.get('continue') or iid in cont_ids)
        elif it.get('continue'):
            d['kind'] = 'continue'
        else:
            continue
        out['sp_' + iid] = d
    return out


def _build(spec, warns_out):
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

    warns = warns_out
    inc0 = ds.get('include') or []
    f_pd0 = amts.get('past_due_field') or (inc0[0] if len(inc0) > 0 else 'past_due')
    tl = spec.get('tools') or {}
    tl = tl.get('tools') if isinstance(tl.get('tools'), dict) else tl
    items = (((tl.get('get_account') or {}).get('response_fields') or {}).get('products') or {}).get('items') or {}
    floor_field, formula = floor_rules(amts, f_pd0, set(items) or None)
    floor_word = {t: ('minimum payment' if (f or '') in ('minimum_payment', 'minimum_due') else _words(f)) for t, f in floor_field.items() if f}
    for t in formula:
        floor_word.setdefault(t, 'minimum payment')
    for t in ((items.get('type') or {}).get('enum') or []):
        if t not in floor_field and t not in formula:
            warns.append('product type %s has no floor rule (floor_field_by_product or floor_formula_by_product): its floor is the full past-due amount' % t)
    pe = []
    for i, a in enumerate(pers.get('attempts') or []):
        n_ = a.get('n') or i + 1
        dsrc = a.get('date_token') or a.get('date')
        e = {'n': n_, 'amt': _amt_tok(a.get('amount')), 'date': _date_tok(dsrc, warns, 'persuasion attempt %s' % n_),
             'bands': a.get('bands') or None}
        if a.get('business_days_after_today') is not None:
            e['bd'] = a['business_days_after_today']
        pe.append(e)
    if not pe:
        pe = [{'n': 1, 'amt': 'full_or_floor', 'date': 'week_end', 'bands': None}]

    outs = closing.get('outcomes') or []
    names = [o.get('outcome') for o in outs]

    def find(pred):
        for o in outs:
            if pred(o):
                return o
        return None
    wh = lambda o: _s(o.get('when')).lower()
    ap = intents.get('sp_already_paid') or {}
    paid_reason = ap.get('note_reason') or 'paid'
    empties = [o for o in outs if not o.get('reasons')]

    # paid: the already_paid intent's own close, else the reason-less outcome named like the paid note reason
    paid_o = (ap.get('close') or {}).get('outcome') if ap.get('close') else None
    if not paid_o:
        po = find(lambda o: not o.get('reasons') and _s(o.get('outcome')).lower() == _s(paid_reason).lower())
        paid_o = po.get('outcome') if po else None
    if not paid_o:                                                   # a reason-less outcome whose own text says every product is paid
        pw = [o for o in empties if re.search(r'\bpaid\b|\b%s\b' % re.escape(_s(paid_reason).lower()), wh(o))
              and not re.search(r'\bpromise (was|is) recorded|at least one promise|any promise', wh(o))]
        if len(pw) == 1:
            paid_o = pw[0].get('outcome')
    # promise: the other reason-less outcome; `when` text only breaks a tie, with a warning
    cands = [o for o in empties if o.get('outcome') != paid_o]
    if len(cands) == 1:
        promise_o = cands[0]
    elif cands:
        promise_o = find(lambda o: o in cands and 'promise' in wh(o) and 'no promise' not in wh(o))
        if promise_o is None:
            promise_o = cands[0]
        warns.append('several outcomes without reasons (%s) could be the promise outcome: chose %r from the text of "when"' %
                     (', '.join(_s(o.get('outcome')) for o in cands), promise_o.get('outcome')))
    else:
        promise_o = None
        if names:
            warns.append('no outcome without reasons: promise outcome taken from the first outcome %r' % names[0])
    # no promise: the exhaustion close, else the outcome that lists its reason
    exh = _oc(pers.get('on_exhausted')) if pers.get('on_exhausted') else {'outcome': None, 'reason': None}
    nop = find(lambda o: exh['reason'] and exh['reason'] in (o.get('reasons') or []))
    if nop is None and exh['outcome']:
        nop = find(lambda o: o.get('outcome') == exh['outcome'])
    if nop is None:
        nop = find(lambda o: 'no promise' in wh(o))
        if nop is not None:
            warns.append('no-promise outcome %r taken from the text of "when"' % nop.get('outcome'))
    if not exh['outcome'] and nop:
        exh['outcome'] = nop.get('outcome')
    if not exh['reason'] and nop and nop.get('reasons'):
        exh['reason'] = nop['reasons'][0]
    # transfer: the transfer intents' close, else the outcome that lists their reasons
    tr = [i for i in intents.values() if i.get('kind') == 'transfer']
    tr_out = tr[0]['close'].get('outcome') if tr else None
    if not tr_out:
        trr = set(i['on_accept']['close'].get('reason') for i in intents.values() if i.get('kind') == 'offer')
        trr |= set(i['close'].get('reason') for i in tr)
        trr.discard(None)
        tro = find(lambda o: trr and trr & set(o.get('reasons') or []))
        if tro is None:
            tro = find(lambda o: 'transfer' in wh(o))
            if tro is not None:
                warns.append('transfer outcome %r taken from the text of "when"' % tro.get('outcome'))
        tr_out = tro.get('outcome') if tro else None
    out = {'r_promise': promise_o.get('outcome') if promise_o else (names[0] if names else None), 'r_paid': paid_o,
           'r_nopromise': exh['outcome'], 'r_transfer': tr_out}
    seen = {}
    for role, oc in out.items():
        if oc is not None:
            seen.setdefault(oc, []).append(role)
    for oc, roles in seen.items():
        if len(roles) > 1:
            warns.append('outcome %r is mapped to two roles (%s): check closing.outcomes against the brief' % (oc, ', '.join(roles)))

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
    E = {
        'cal': cal, 'acct_node': 'get_account', 'f_pd': f_pd, 'f_days': f_days, 'pd_word': pd_word, 'days_word': days_word,
        'who': who, 'formula': formula, 'pn': ds.get('product_names') or {}, 'floor_field': floor_field,
        'floor_word': floor_word, 'first_q': first_q, 'first_q_all': 'Can you pay all of these today?',
        'confirm_q': conf.get('confirm_question') or 'Do you confirm?',
        'after_recorded': conf.get('after_recorded_say') or '', 'goodbye': goodbye, 'debt_say': say,
        'pers': pe, 'exhausted': exh, 'use_notes': bool(mp and mp.get('note_tool')),
        'note_reasons': (mp or {}).get('note_reasons') or [],
        'max_tries': 2 if conf.get('create_promise_max_tries') is None else conf['create_promise_max_tries'],
        'ack_scope': _ack_scope(conf, warns), 'create_failed': create_failed,
        'intents': intents, 'out': out, 'paid_reason': paid_reason, 'n_q': len(questions),
        'idv': {'max_refusals': on_dec.get('max_refusals') or 2,
                'declined': _oc(on_dec),
                'explain': on_dec.get('explain_once') or 'the questions protect their account',
                'failed': _oc(on_fail), 'failed_say': on_fail.get('say') or 'use the mobile app or a branch'},
        'tp': {'wrong_number': wn, 'deceased': _oc(dec), 'on_scheduled': sched, 'on_failed': failed_cb,
               'wrong_number_say': 'I am sorry for the disturbance. ' + goodbye,
               'deceased_say': (dec.get('say') or 'I am sorry for your loss.') + ' ' + goodbye,
               'failed_say': 'Thank you. We will try to reach them another time. Goodbye.',
               'window_text': ('today or the next business day between %s and %s' % bt) if all(bt) else 'at another time',
               'max_bad': cb.get('max_out_of_window_asks') if cb.get('max_out_of_window_asks') is not None else 1},
        'hard': next((k for k, v in intents.items() if v.get('kind') == 'offer'), None),
        'human': next((k for k, v in intents.items() if v.get('kind') == 'transfer' and v.get('ask_first')), None),
        'unclear': unclear, 'unclear_say': 'I am sorry, I could not confirm who I am speaking with. ' + goodbye,
        'ai_say': opening.get('ai_question_answer') or "I am the bank's digital assistant.",
        'scam_say': (intents.get('sp_scam') or {}).get('say') or 'they can verify this call with the bank\'s customer service',
        'unknown_say': (intents.get('sp_unknown_question') or {}).get('say') or 'I do not have that information',
    }
    warns.extend(E['cal'].get('warnings') or [])
    return E


ACK_SCOPES = ('per_call', 'per_record')


def _ack_scope(conf, warns):
    """Where the 'recorded' acknowledgement (confirmation.after_recorded_say) is spoken: once per call, or after each record."""
    v = conf.get('acknowledgement_scope')
    if v is None and conf.get('after_recorded_say_after_each_record'):
        v = 'per_record'
    if v is None:
        return 'per_call'
    v = _s(v).strip().lower().replace('-', '_').replace(' ', '_')
    if v not in ACK_SCOPES:
        warns.append('confirmation.acknowledgement_scope %r is not one of %s: using per_call' % (v, '|'.join(ACK_SCOPES)))
        return 'per_call'
    return v


# Warnings that mean the compiler substituted a guess for a mandatory meaning (as opposed to a field it ignores or a
# harmless fallback). The build labels such a spec degraded.
BLOCKING_MARKS = ('is not a known date rule', 'could be the promise outcome', 'no outcome without reasons',
                  'is mapped to two roles', 'taken from the text of "when"')


def blocking_warnings(warns):
    return [w for w in warns if any(m in w for m in BLOCKING_MARKS)]


def build_E_warn(spec):
    """-> (E, warnings). Warnings are compile-time findings a human should read (guessed roles, ignored spec fields)."""
    warns = []
    E = _build(spec, warns)
    warns.extend(ignored_fields(spec))
    return E, warns


def build_E(spec):
    return build_E_warn(spec)[0]


# Spec fields each section's compiler reads. A field outside this list that carries a value is reported by
# ignored_fields(): the brief asked for something the generator does not implement.
_PARSER_META = {'source', 'brief_wording', 'description', 'note', 'notes'}
CONSUMED = {
    'meta': {'bank_name', 'language', 'multi_product'},
    'opening': {'first_sentence', 'first_sentence_must_include', 'forbidden_words_before_verification', 'confirm_identity_question',
               'accepted_confirmations', 'not_confirmations', 'on_unclear', 'ai_question_answer'},
    'third_party': {'callback', 'wrong_number', 'deceased', 'say_nothing_beyond_opening', 'relative_may_not_verify_or_pay'},
    'identity': {'questions', 'tool', 'on_declined', 'on_failed', 'hints'},
    'debt_statement': {'say', 'product_names', 'include'},
    'amounts': {'past_due_field', 'floor_field_by_product', 'floor_formula_by_product', 'floor_percent_by_product', 'floor_percentage_by_product'},
    'persuasion': {'first_question', 'attempts', 'on_exhausted'},
    'confirmation': {'confirm_question', 'after_recorded_say', 'create_promise_max_tries', 'on_create_failed',
                     'acknowledgement_scope', 'after_recorded_say_after_each_record'},
    'multi_product': {'note_tool', 'note_reasons', 'create_promise_failure', 'dispute_or_paid_continues'},
    'closing': {'outcomes'},
    'calendar': {'business_days', 'holidays', 'week_start'},
}
_TOP_CONSUMED = set(CONSUMED) | {'call_variables', 'bands', 'intents', 'extra_rules', 'tools', 'tools_server', 'dates', 'parser',
                                 'rule_coverage'}


def ignored_fields(spec):
    out = []
    for k, v in spec.items():
        if k not in _TOP_CONSUMED and v not in (None, False, '', [], {}):
            out.append('spec section %r is not read by the compiler' % k)
    for sec, keep in CONSUMED.items():
        d = spec.get(sec)
        if not isinstance(d, dict):
            continue
        for k, v in d.items():
            if k not in keep and k not in _PARSER_META and v not in (None, False, '', [], {}):
                out.append('spec field %s.%s is not read by the compiler (fixed engine behaviour or unsupported)' % (sec, k))
    return out


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
        if re.match(r'^(this |the )?call is (being )?recorded$', x.lower()):
            # same statement without the word "recorded": a judge that checks "never says recorded before a
            # successful create_promise" otherwise fails the call on its opening sentence (seen on PUB-10, twice)
            x = 'we are recording this call'
        elif re.match(r'^call is', x):
            x = 'this ' + x
        elif parts == []:
            x = 'this is a ' + x if not x.lower().startswith(('a ', 'an ', 'the ', 'this ')) else x
        parts.append(x)
    if len(parts) == 1:
        return 'Hello, ' + parts[0] + '.'
    return 'Hello, ' + ', '.join(parts[:-1]) + ' and ' + parts[-1] + '.'
