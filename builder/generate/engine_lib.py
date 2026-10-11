"""Dialogue engine for the generated phone agent. Runs inside ONE Freya code node.

This file is appended to builder/logic/snippet_lib.py (calendar, bands, promise dates, callbacks,
dates of birth) and the result is the `code` of the engine node. It is also imported by the local
tests (builder/generate/local_sim.py), so the tested code is the shipped code.

The model never decides policy. After every customer turn the extraction step fills a few variables
(intent, date words, amount words); this engine reads them, updates the call state (one JSON string
in vars['st']), and writes the next instruction for the speaking node plus a `route` that tells
the graph where to go (speak, create a promise, add a note, transfer, close ...).

Sandbox rules: no double braces anywhere in this file, nothing raises out of main().
"""
import json
import re
import datetime

E = json.loads(__E__)
CAL = E['cal']
MONTH_NAMES = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August',
               'September', 'October', 'November', 'December']


# ------------------------------------------------------------------ small helpers

def S(k):
    v = vars.get(k)
    return '' if v is None else str(v).strip()


def money(x):
    return '%.2f' % float(x)


def plain_label(label):
    """'a revolving card' -> 'revolving card' for sentences that open with 'Your'."""
    return re.sub(r'^(a|an|the|your)\s+', '', str(label), flags=re.I)


def say_money(x):
    """An amount as it is spoken: the spec's currency words and thousands separator when it gives them ("1 250 kroner and 50
    ore"), else two decimals. The tool body keeps money()."""
    f = E.get('money')
    if not f:
        return money(x)
    cents = int(round(float(x) * 100))
    major, minor = divmod(cents, 100)
    if f.get('whole') and minor:
        major, minor = int(float(x) + 0.999999), 0           # whole units only: a spoken amount is never lower than the real one
    sep = f.get('sep') or ''
    txt = '{:,}'.format(major).replace(',', sep) if sep else str(major)
    out = '%s %s' % (txt, f['major'])
    if minor and f.get('minor') and not f.get('whole'):
        out += ' and %d %s' % (minor, f['minor'])
    return out


def today_d():
    d, mins = parse_now(S('now'))
    if d is None:
        d, mins = parse_now(S('system.todays_date_tr.iso_8601'))
    return d


def now_min():
    d, mins = parse_now(S('now'))
    return mins


def dstr(d):
    t = today_d()
    s = '%s %d %s' % (WD_NAMES[d.weekday()], d.day, MONTH_NAMES[d.month - 1])
    if t is not None and d.year != t.year:
        s += ' %d' % d.year
    return s


def iso(d):
    return d.isoformat()


def from_iso(s):
    return parse_iso(s)


# ------------------------------------------------------------------ number words, dates, times, amounts

_UN = {'zero': 0, 'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5, 'six': 6, 'seven': 7, 'eight': 8,
       'nine': 9, 'ten': 10, 'eleven': 11, 'twelve': 12, 'thirteen': 13, 'fourteen': 14, 'fifteen': 15,
       'sixteen': 16, 'seventeen': 17, 'eighteen': 18, 'nineteen': 19}
_TN = {'twenty': 20, 'thirty': 30, 'forty': 40, 'fifty': 50, 'sixty': 60, 'seventy': 70, 'eighty': 80, 'ninety': 90}
_OR = {'first': 1, 'second': 2, 'third': 3, 'fourth': 4, 'fifth': 5, 'sixth': 6, 'seventh': 7, 'eighth': 8,
       'ninth': 9, 'tenth': 10, 'eleventh': 11, 'twelfth': 12, 'thirteenth': 13, 'fourteenth': 14,
       'fifteenth': 15, 'sixteenth': 16, 'seventeenth': 17, 'eighteenth': 18, 'nineteenth': 19,
       'twentieth': 20, 'thirtieth': 30}


def _numval(w):
    if w in _UN:
        return _UN[w]
    if w in _TN:
        return _TN[w]
    if w in _OR:
        return _OR[w]
    return None


def digitize(text):
    """'twenty-second of October' -> '22 of october'; 'four hundred and fifty five' -> '455'."""
    toks = re.findall(r"[a-z]+|\d+(?:[.,]\d+)*|[^\sa-z\d]", str(text).lower())
    out = []
    i = 0
    n = len(toks)
    while i < n:
        w = toks[i]
        if _numval(w) is None and w not in ('hundred', 'thousand'):
            out.append(w)
            i += 1
            continue
        total = 0
        cur = 0
        prev = None
        j = i
        while j < n:
            t = toks[j]
            if t in ('and', '-'):
                nxt = _numval(toks[j + 1]) if j + 1 < n else None
                if prev in ('hundred', 'thousand') and nxt is not None:
                    j += 1
                    continue
                if t == '-' and prev == 'tens' and nxt is not None and 1 <= nxt <= 9:
                    j += 1
                    continue
                break
            if t == 'hundred':
                cur = (cur or 1) * 100
                prev = 'hundred'
                j += 1
                continue
            if t == 'thousand':
                total += (cur or 1) * 1000
                cur = 0
                prev = 'thousand'
                j += 1
                continue
            v = _numval(t)
            if v is None:
                break
            if prev is None or prev in ('hundred', 'thousand'):
                cur += v
                prev = 'tens' if (v >= 20 and v % 10 == 0) else 'unit'
                j += 1
                continue
            if prev == 'tens' and 1 <= v <= 9:
                cur += v
                prev = 'unit'
                j += 1
                continue
            break
        if j == i:
            out.append(w)
            i += 1
            continue
        out.append(str(total + cur))
        i = j
    return ' '.join(out)


_MON_RE = '|'.join(sorted(MONTH_ALIASES.keys(), key=len, reverse=True))
_VAGUE = re.compile(r'\b(next week|week after next|the week after|next month|end of (the )?(month|week|year)|month end|'
                    r'salary|pay ?check|payday|pay day|soon|later|sometime|some time|when i can|few days|'
                    r'couple of|a while|early next|beginning of|asap|whenever)\b')


def _mk(y, m, dd):
    try:
        return datetime.date(y, m, dd)
    except Exception:
        return None


def free_date(text, today):
    """Words of a customer -> ('date', date) | ('vague', None) | ('none', None)."""
    try:
        m = re.search(r'\b(\d{4})-(\d{1,2})-(\d{1,2})\b', str(text))
        if m:
            d = _mk(int(m.group(1)), int(m.group(2)), int(m.group(3)))
            if d:
                return 'date', d
        raw = str(text).lower()
        m = re.search(r'(?<![\d/.])(\d{1,2})([/.-])(\d{1,2})\2(\d{2}|\d{4})(?![\d/.])', raw)
        if m:                                   # an explicit day/month/year is read before anything else
            a, b = int(m.group(1)), int(m.group(3))
            if str(CAL.get('dob_order') or 'DMY').upper() == 'MDY':
                a, b = b, a
            y = int(m.group(4))
            return _month_day(a, b, str(y if y > 99 else 2000 + y), today)
        t = digitize(text)
        t = re.sub(r'(\d)\s*(st|nd|rd|th)\b', r'\1', t)
        t = re.sub(r'\s+', ' ', t).strip()
        if not t:
            return 'none', None
        m = re.search(r'\b(\d{4})-(\d{1,2})-(\d{1,2})\b', t)
        if m:
            d = _mk(int(m.group(1)), int(m.group(2)), int(m.group(3)))
            if d:
                return 'date', d
        m = re.search(r'\b(\d{1,2}) ?(?:of |th of )?(' + _MON_RE + r')\b(?: ?,? ?(\d{4}))?', t)
        if m:
            return _month_day(int(m.group(1)), MONTH_ALIASES[m.group(2)], m.group(3), today)
        m = re.search(r'\b(' + _MON_RE + r')\.? (\d{1,2})\b(?: ?,? ?(\d{4}))?', t)
        if m:
            return _month_day(int(m.group(2)), MONTH_ALIASES[m.group(1)], m.group(3), today)
        m = re.search(r'\b(\d{1,2})[/.](\d{1,2})(?:[/.](\d{2,4}))?\b', t)
        if m:
            a, b = int(m.group(1)), int(m.group(2))
            if str(CAL.get('dob_order') or 'DMY').upper() == 'MDY':
                a, b = b, a
            y = m.group(3)
            if y and len(y) == 2:
                y = str(2000 + int(y))
            return _month_day(a, b, y, today)
        m = re.search(r'\b(?:in |after )?(\d{1,3}|a|an) (day|days|week|weeks)(?: (?:from (?:now|today)|later|time))?\b', t)
        if m and (m.group(0).startswith(('in ', 'after ')) or ' from ' in m.group(0) or m.group(0).endswith(('later', 'time'))):
            n = (1 if m.group(1) in ('a', 'an') else int(m.group(1))) * (7 if m.group(2).startswith('week') else 1)
            return 'date', today + datetime.timedelta(days=n)
        words = re.findall(r'[a-z]+', t)
        has_wd = any(w in WD_ALIASES for w in words)
        m = re.search(r'\b(?:the |on )(\d{1,2})\b', t) if has_wd else None
        if m and 1 <= int(m.group(1)) <= 31:
            return _dom(int(m.group(1)), today)
        if 'day after tomorrow' in t:
            return 'date', today + datetime.timedelta(days=2)
        if has_wd or 'tomorrow' in words or 'today' in words:
            st, d = resolve_phrase(t, today, CAL)
            if st == 'ok':
                return 'date', d
        if re.search(r'\b(right now|now|asap)\b', t) and not _VAGUE.search(t.replace('asap', '')):
            return 'date', today
        if _VAGUE.search(t):
            return 'vague', None
        m = re.search(r'\b(\d{1,2})\b', t)
        if m and 1 <= int(m.group(1)) <= 31:
            return _dom(int(m.group(1)), today)
        return 'vague', None
    except Exception:
        return 'none', None


def _month_day(dd, mo, year, today):
    if not (1 <= mo <= 12) or not (1 <= dd <= 31):
        return 'vague', None
    if year:
        d = _mk(int(year), mo, dd)
        return ('date', d) if d else ('vague', None)
    d = _mk(today.year, mo, dd)
    if d is None:
        return 'vague', None
    if d < today and (today - d).days > 150:
        d = _mk(today.year + 1, mo, dd) or d
    return 'date', d


def _dom(dd, today):
    y, mo = today.year, today.month
    for _ in range(14):
        d = _mk(y, mo, dd)
        if d is not None and d >= today:
            return 'date', d
        mo += 1
        if mo > 12:
            mo = 1
            y += 1
    return 'vague', None


def amount_check(text):
    """Words of a customer -> ('ok', x) | ('unclear', None) | ('none', None). Unclear: a negative number, a range,
    two different numbers, comma decimals ("150,50") or pence without a whole amount; the caller asks again instead of picking one."""
    try:
        t = str(text).lower().strip()
        if not t:
            return 'none', None
        if re.search(r'(?<!\w)-\s*[^\w\s]?\s*\d|\b(minus|negative)\b', t):
            return 'unclear', None
        d = digitize(t)
        m = re.search(r'(\d[\d,]*) ?,? ?(?:point|decimal|dot) ((?:\d ?)+)', d)
        if m:
            if re.search(r'\d', d[:m.start()] + ' ' + d[m.end():]):      # a second number: an alternative or a range
                return 'unclear', None
            return 'ok', float(m.group(1).replace(',', '') + '.' + m.group(2).replace(' ', ''))
        m = re.search(r'(\d[\d,]*)(?: [a-z]+)?(?: and)? (\d{1,2}) (?:pence|penny|pennies|p|cents?|c)\b', d)
        if m:
            if re.search(r'\d', d[:m.start()] + ' ' + d[m.end():]):
                return 'unclear', None
            return 'ok', float(m.group(1).replace(',', '')) + int(m.group(2)) / 100.0
        if re.search(r'\d,\d{1,2}(?!\d)|\d\s*p\b|\b(pence|pennies|penny)\b', t):
            return 'unclear', None
        d = re.sub(r'(?<![\w.])(\d+(?:\.\d+)?) ?(?:k|grand)\b', lambda mm: str(int(float(mm.group(1)) * 1000)), d)   # "2k", "two grand"
        if re.search(r'\b(half|grand)\b', d):             # "one and a half grand": not worked out, ask again
            return 'unclear', None
        nums = set()
        for x in re.findall(r'\d+(?:,\d{3})*(?:\.\d+)?', d):
            nums.add(float(x.replace(',', '')))
        if len(nums) > 1:
            return 'unclear', None
        if nums:
            return 'ok', nums.pop()
    except Exception:
        pass
    return 'none', None


def free_amount(text):
    kind, x = amount_check(text)
    return x if kind == 'ok' else None


def free_time(text):
    """Spoken time -> list of candidate minutes since midnight (am and pm when unclear)."""
    try:
        t = digitize(text)
        t = re.sub(r'\s+', ' ', t).strip()
        if re.search(r'\b(noon|midday)\b', t):
            return [720]
        ampm = None
        if re.search(r'\b(a ?m|morning)\b', t):
            ampm = 'am'
        elif re.search(r'\b(p ?m|afternoon|evening|tonight)\b', t):
            ampm = 'pm'
        mi = 0
        h24 = False                              # "07:00" and "1900" are 24-hour times, not am or pm
        m = re.search(r'\b(\d{1,2}) ?[:.h] ?(\d{2})\b', t)
        m4 = re.search(r'\b([01]\d|2[0-3])([0-5]\d)\b', t)
        if m:
            h, mi = int(m.group(1)), int(m.group(2))
            h24 = len(m.group(1)) == 2 and m.group(1).startswith('0') and ampm is None
        elif m4 and not ampm:
            h, mi = int(m4.group(1)), int(m4.group(2))
            h24 = True
        else:
            m = re.search(r'\b(\d{1,2})\b(?: (\d{2})\b)?', t)
            if not m:
                return []
            h = int(m.group(1))
            mi = int(m.group(2)) if m.group(2) else 0
            if 'half past' in t or 'half ' + str(h) in t:
                mi = 30
            elif 'quarter past' in t:
                mi = 15
            elif 'quarter to' in t:
                h -= 1
                mi = 45
        if h > 24 or mi > 59:
            return []
        if h >= 13 or h24:
            return [h * 60 + mi]
        if ampm == 'am':
            return [(0 if h == 12 else h) * 60 + mi]
        if ampm == 'pm':
            return [(12 if h == 12 else h + 12) * 60 + mi]
        if h == 12:
            return [720 + mi]
        return [h * 60 + mi, (h + 12) * 60 + mi]
    except Exception:
        return []


# ------------------------------------------------------------------ state

def new_state():
    return {'phase': 'plan', 'cur': 0, 'all': False, 'prods': [], 'hard': 0, 'human': 0, 'quit': 0,
            'idv_ref': 0, 'idv_human': 0, 'tp_bad': 0, 'tp_n': 0, 'cq': [], 'nq': [], 'tries': 0,
            'transfer': None, 'lead': '', 'vg_all': 0}


def load():
    try:
        st = json.loads(S('st') or '{}')
    except Exception:
        st = {}
    base = new_state()
    base.update(st or {})
    return base


def save(st):
    vars['st'] = json.dumps(st, separators=(',', ':'))


def speak(core):
    """A fixed line, spoken word for word (no model call)."""
    vars['say_text'] = core
    vars['instruction'] = ('Say the following to the customer in natural spoken English, in one to three short '
                           'sentences. Keep every name, number, amount and date exactly as written and add nothing '
                           'else: ' + core)
    vars['route'] = 'say'


def ask(instr):
    """An instruction the speaking model words itself (used when the customer asked something)."""
    vars['instruction'] = instr
    vars['route'] = 'ask'


def route(r):
    vars['route'] = r


# ------------------------------------------------------------------ products

def label_for(raw):
    tpl = (E.get('pn') or {}).get(raw.get('type')) or str(raw.get('type') or 'account').replace('_', ' ')

    for k in re.findall(r'\{(\w+)\}', tpl):
        if raw.get(k) in (None, ''):               # a placeholder with no data: name the product by its type alone
            return str(raw.get('type') or 'account').replace('_', ' ')

    def rep(m):
        return str(raw.get(m.group(1)))
    return re.sub(r'\{(\w+)\}', rep, tpl).strip()


def pd_field(raw):
    """The field holding this product's past-due amount: the type's own field when the spec or API names one and the bank
    sent it, else the common field."""
    f = (E.get('pd_by_type') or {}).get(raw.get('type'))
    return f if f and raw.get(f) not in (None, '') else E['f_pd']


def days_field(raw):
    f = (E.get('days_by_type') or {}).get(raw.get('type'))
    return f if f and raw.get(f) not in (None, '') else E['f_days']


def usable(raw):
    """A product the bank sent without an id, a finite amount past due or the days late cannot be spoken about or
    recorded. An unfamiliar type is kept: it is the bank's own data and the spec's type list may be incomplete."""
    try:
        if not str(raw.get('product_id') or '').strip():
            return False
        pd = float(raw.get(pd_field(raw)))
        if pd != pd or pd in (float('inf'), float('-inf')):
            return False
        return pd > 0 and int(float(raw.get(days_field(raw)))) >= 0
    except Exception:
        return False


def floor_for(raw):
    f = (E.get('floor_field') or {}).get(raw.get('type'))
    try:
        v = float(raw.get(f)) if f and raw.get(f) not in (None, '') else None
    except Exception:
        v = None
    fm = (E.get('formula') or {}).get(raw.get('type'))
    if v is None and isinstance(fm, dict):
        try:
            base = float(raw.get(fm.get('field') or pd_field(raw)))
            v = round(base * float(fm.get('percent_of_field')) / 100.0 + 0.004999, 2)
            g = fm.get('greater_of')
            if g and raw.get(g) not in (None, ''):
                v = max(v, float(raw.get(g)))
            rd = fm.get('round')
            if rd:
                v = round_to(v, rd)
        except Exception:
            v = None
    return v


def round_to(v, rd):
    """Round a floor to a multiple of rd['to'] (mode up, down or nearest); the 1e-9 slack keeps exact multiples exact."""
    q = v / float(rd['to'])
    n = int(q)
    if rd.get('mode') == 'down':
        pass
    elif rd.get('mode') == 'nearest':
        n = int(q + 0.5)
    elif q - n > 1e-9:
        n += 1
    return round(n * float(rd['to']), 2)


def floor_word(p):
    return (E.get('floor_word') or {}).get(p['type']) or 'minimum amount'


def read_products():
    node = E.get('acct_node') or 'get_account'
    pat = re.compile('^' + re.escape(node) + r'_response\.data\.products\.(\d+)\.(\w+)$')
    rows = {}
    for k in list(vars.keys()):
        m = pat.match(str(k))
        if m:
            rows.setdefault(int(m.group(1)), {})[m.group(2)] = vars[k]
    return [rows[i] for i in sorted(rows)]


def make_product(i, raw, today):
    try:
        pd = float(raw.get(pd_field(raw)))
    except Exception:
        pd = 0.0
    try:
        days = int(float(raw.get(days_field(raw))))
    except Exception:
        days = 0
    band = band_for(days, CAL)
    bands = CAL.get('bands') or []
    if band is None and bands:
        band = bands[-1] if (CAL['bands'][-1].get('max') is not None and days > CAL['bands'][-1]['max']) else bands[0]
    dead = deadline_for(today, band, CAL) if band else None
    fl = floor_for(raw)
    if fl is None or fl <= 0 or fl > pd:
        fl = pd
    try:
        am = int(band.get('attempts')) if band and band.get('attempts') is not None else 1
    except Exception:
        am = 1
    return {'i': i, 'id': str(raw.get('product_id') or ('p%d' % (i + 1))), 'type': str(raw.get('type') or ''),
            'label': label_for(raw), 'pd': pd, 'dl': days, 'fl': fl, 'band': band_name(band),
            'am': am, 'dead': iso(dead) if dead else '', 'att': 0, 'status': 'open', 'pend': None, 'vg': 0,
            'tm': False, 'fb': 0, 'amt': None, 'date': '', 'cap': '', 'note': ''}


def band_name(band):
    """A band's name, or "min-max" (the label the spec uses to point at an unnamed band)."""
    if not band:
        return ''
    if band.get('name'):
        return band['name']
    return '%s-%s' % (band.get('min'), band.get('max')) if band.get('max') is not None else '%s+' % band.get('min')


def def_amt(p):
    return p['fl'] if p['tm'] else p['pd']


def first_day(today):
    d = next_bd(today, CAL, include_self=True)
    return d or today


def multi(st):
    return len(st['prods']) > 1


def facts(st, hide_floor=False):
    lines = []
    for p in st['prods']:
        s = '%s: %s %s, %d days %s' % (p['label'], say_money(p['pd']), E['pd_word'], p['dl'], E['days_word'])
        if p['fl'] and p['fl'] < p['pd'] and not hide_floor:
            s += ', %s %s' % (floor_word(p), say_money(p['fl']))
        if p['dead']:
            s += ', latest promise date %s' % dstr(from_iso(p['dead']))
        lines.append(s)
    return '; '.join(lines)


# ------------------------------------------------------------------ questions the agent asks

def offer_q(st, p):
    pe = p.get('pend')
    if not pe:
        return ''
    k = pe['k']
    if k == 'today':
        return E['first_q']
    if k == 'day':
        return 'On which day can you pay %s?' % say_money(pe['a'])
    amt = say_money(pe['a'])
    q = 'Can you pay %s on %s?' % (amt, dstr(from_iso(pe['d'])))
    if pe['a'] + 0.004 < p['pd']:
        q += ' The rest would stay overdue.'
    return q


def readback(st):
    items = []
    for p in st['prods']:
        if p['status'] != 'agreed':
            continue
        s = '%s, %s on %s' % (p['label'], say_money(p['amt']), dstr(from_iso(p['date'])))
        if p['cap']:
            s += ' (the latest date I can record for this one)'
        items.append(s)
    if len(items) == 1:
        body = 'So that is ' + items[0] + '.'
    else:
        body = 'So that is: ' + '; '.join(items) + '.'
    return body + ' ' + E['confirm_q']


def cur_question(st):
    if st.get('hard_pending'):
        return hardship_offer_text()
    if st['phase'] == 'confirm':
        return readback(st)
    if st['all']:
        return E['first_q_all']
    p = st['prods'][st['cur']]
    return offer_q(st, p) or E['first_q']


def reask(st, lead='', kind='question', then=True):
    """The customer said something that needs no policy change: answer it and ask the pending question again."""
    q = cur_question(st)
    offered = False
    if not st.get('hard_pending') and st['phase'] != 'confirm' and not st['all']:
        pe = st['prods'][st['cur']].get('pend')
        if pe and pe.get('k') == 'attempt':
            offered = True                                          # an offer is on the table: no figure is named a second time
            if pe.get('d'):
                q = 'Can you do that on %s?' % dstr(from_iso(pe['d']))   # an offer already made is answered, not repeated
    amount_rule = (' The offer is already made: if they ask how much you can do, for a lower amount or what the figure is, say only "That is the amount I mentioned." '
                   'and name no amount.') if offered else ''
    ans = ('The customer asked something or said something unclear. First reply to it in one short sentence: '
           'use only these facts: ' + facts(st, hide_floor=offered) + '. If the facts do not answer it, say exactly "' +
           E['unknown_say'] + '". Never invent figures, dates or reasons, and never offer a discount, waiver or '
           'payment plan.' + amount_rule + ' If they ask whether you are a robot or an AI, say "' + E['ai_say'] + '". '
           'If they ask whether this call is a scam, say that ' + E['scam_say'] + '.' + (' Then say: ' + q if then else ''))
    ask((lead + ' ' if lead else '') + ans)


# ------------------------------------------------------------------ closing

def set_close(outcome, reason, text):
    vars['close_outcome'] = outcome
    if reason:
        vars['close_reason'] = reason
    vars['bye_text'] = text
    route('fin')


def goodbye(lead=''):
    return ((lead + ' ') if lead else '') + E['goodbye']


def final(st, lead=''):
    prods = st['prods']
    lead = (lead + ' ' if lead else '') + st.get('lead', '')
    if st.get('transfer'):
        tr = st['transfer']
        return set_close(tr['outcome'], tr.get('reason'), goodbye(lead.strip()))
    rec = [p for p in prods if p['status'] == 'recorded']
    bad = [p for p in prods if p['status'] in ('noted', 'failed')]
    if rec:
        items = ['%s, %s on %s' % (p['label'], say_money(p['amt']), dstr(from_iso(p['date']))) for p in rec]
        txt = 'Your promise is recorded: ' + '; '.join(items) + '.'
        if not all(p.get('ack') for p in rec):      # a record already acknowledged one by one is not announced again
            txt += ' ' + E['after_recorded']
        fails = [p for p in prods if p['status'] == 'failed']
        if fails:
            txt += ' I could not record the promise for ' + ' and '.join(p['label'] for p in fails) + '.'
        return set_close(E['out']['r_promise'], (E.get('out_reason') or {}).get('r_promise'), goodbye((lead + ' ' + txt).strip()))
    reasons = [(p['note'] if p['status'] == 'noted' else E['create_failed']['reason']) for p in bad]
    paid_reason = E['paid_reason']
    if reasons and all(r == paid_reason for r in reasons) and E['out'].get('r_paid'):
        return set_close(E['out']['r_paid'], (E.get('out_reason') or {}).get('r_paid'), goodbye(lead.strip()))
    first = next((r for r in reasons if r != paid_reason), reasons[0] if reasons else E['exhausted']['reason'])
    if any(p['status'] == 'failed' for p in prods) and not rec:
        txt = (lead + ' ' + E['create_failed']['say_text']).strip()
        return set_close(E['create_failed']['outcome'], first, goodbye(txt)) if len(prods) == 1 else \
            set_close(E['out']['r_nopromise'], first, goodbye(txt))
    return set_close(E['out']['r_nopromise'], first, goodbye(lead.strip()))


def conclude(st, lead=''):
    prods = st['prods']
    if lead:
        st['lead'] = (st.get('lead', '') + ' ' + lead).strip()
    if E['use_notes'] and not st.get('transfer'):
        q = [p['i'] for p in prods if p['status'] in ('noted', 'failed')]
        if q:
            st['nq'] = q
            st['phase'] = 'noting'
            st['tries'] = 0
            return set_note(st)
    final(st)


def set_note(st):
    p = st['prods'][st['nq'][0]]
    reason = E['create_failed']['reason'] if p['status'] == 'failed' else p['note']
    vars['nt_pid'] = p['id']
    vars['nt_reason'] = reason
    vars['nt_ok'] = 'pending'
    route('note')


def noted(st):
    ok = S('nt_ok').lower() == 'true'
    if not ok and st['tries'] < 2:                 # three attempts in all before the note is given up
        st['tries'] += 1
        return set_note(st)
    st['nq'].pop(0)
    st['tries'] = 0
    if st['nq']:
        return set_note(st)
    final(st)


# ------------------------------------------------------------------ negotiation core

def accept(p, amount, d, cap=''):
    p['status'] = 'agreed'
    p['amt'] = round(float(amount), 2)
    p['date'] = iso(d)
    p['cap'] = cap
    p['pend'] = None


def note_product(p, reason):
    p['status'] = 'noted'
    p['note'] = reason
    p['pend'] = None


def next_open(st):
    for p in st['prods']:
        if p['status'] == 'open':
            return p
    return None


def advance(st, lead=''):
    nxt = next_open(st)
    if nxt is None:
        return finish_nego(st, lead)
    st['cur'] = nxt['i']
    st['all'] = False
    intro = 'Now your %s.' % plain_label(nxt['label']) if multi(st) else ''
    return refusal(st, nxt, ((lead + ' ') if lead else '') + intro, start=True)


def finish_nego(st, lead=''):
    agreed = [p for p in st['prods'] if p['status'] == 'agreed']
    if agreed:
        st['phase'] = 'confirm'
        st['hard_pending'] = False
        return speak(((lead + ' ') if lead else '') + readback(st))
    st['phase'] = 'nego'
    conclude(st, lead)


def pers_entry(p, n):
    for e in E['pers']:
        if int(e.get('n') or 0) == n and (not e.get('bands') or p['band'] in e['bands']):
            return e
    return None


def attempt_date(p, e, today):
    """The date a persuasion attempt offers, from the spec token of that attempt."""
    dtok = e.get('date')
    d = None
    if dtok == 'deadline' and p['dead']:
        d = from_iso(p['dead'])
    elif dtok == 'today':
        d = first_day(today)
    elif dtok in ('next_business_day', 'capped_next_business_day'):
        d = next_bd(today, CAL)
    elif dtok == 'midpoint':
        n = e.get('bd')
        if n is None:
            band = band_for(p['dl'], CAL)
            n = -(-deadline_bd_count(today, band, CAL) // 2)
        d = add_bd(today, int(n), CAL) if n else None
    else:                                          # week_end, unknown
        d = persuasion_date(today, CAL)
    d = d or first_day(today)
    if p['dead'] and d > from_iso(p['dead']):
        d = from_iso(p['dead'])
    return d


def refusal(st, p, lead='', start=False):
    """A flat refusal (or the start of a product in a multi-product call): make the next persuasion attempt.
    An amount and date pair already put to the customer is never offered again."""
    today = today_d()
    if st.get('nopers'):                           # hardship: no persuasion on any product
        note_product(p, st['nopers'])
        return advance(st, lead)
    hist = p.setdefault('hist', [])
    pe = p.get('pend')
    if pe and pe.get('k') == 'adj' and pe.get('a') and pe.get('d'):       # a counter-offer the customer just turned down
        pair = [round(pe['a'], 2), pe['d']]
        if pair not in hist:
            hist.append(pair)
    while True:
        if p['att'] >= p['am']:
            return exhaust(st, p, lead)
        e = pers_entry(p, p['att'] + 1)
        if e is None:
            return exhaust(st, p, lead)
        p['att'] += 1
        tok = e.get('amt')
        if tok == 'floor':
            a = p['fl']
        elif tok == 'full_or_floor':
            a = p['fl'] if p['tm'] else p['pd']
        else:
            a = p['pd']
        d = attempt_date(p, e, today)
        if [round(a, 2), iso(d)] not in hist:
            break
    hist.append([round(a, 2), iso(d)])
    p['pend'] = {'a': a, 'd': iso(d), 'k': 'attempt'}
    st['phase'] = 'nego'
    pre = lead if lead else ('I understand.' if not start else '')
    speak((pre + ' ' if pre else '') + offer_q(st, p))


def exhaust(st, p, lead=''):
    note_product(p, E['exhausted']['reason'])
    return advance(st, lead if lead else '')


def check_day(p, d, today):
    """-> (status, final_date). status: ok | moved | late | past"""
    dead = from_iso(p['dead']) if p['dead'] else None
    s, f = check_promise_date(d, today, dead, CAL)
    if s == 'ok':
        return 'ok', d
    if s == 'moved_to_next_business_day':
        return 'moved', f
    if s == 'after_deadline':
        return 'late', f
    return 'past', None


def offer(st, p, dt, am, lead=''):
    """The customer proposes a date and/or an amount for product p."""
    today = today_d()
    pre = (lead + ' ') if lead else ''
    if not dt and st.get('sd'):
        dt = st['sd']                             # a date given earlier for "all of them", now with its account
    st['sd'] = ''
    pe = p.get('pend') or {}
    carried_a = pe.get('a') if pe.get('k') in ('day', 'adj', 'edit') else None   # what the customer already put forward
    if pe.get('k') == 'edit' and pe.get('d') and am and not dt:
        dt = pe['d']                              # an agreed date stays when only the amount is changed
    amt = None
    below = False
    if am:
        kind, a = amount_check(am)
        if kind == 'unclear':
            st['sd'] = dt or ''                       # the date stays for the repeated amount
            return speak(pre + 'Sorry, I did not catch the amount clearly. Could you repeat the amount you just mentioned as one number?')
        if a is not None and a > 0:
            if a + 0.004 < p['fl']:
                if p['fb']:
                    return refusal(st, p, lead)
                p['fb'] = 1
                amt = p['fl']
                below = True
            elif a > p['pd'] + 0.004:
                amt = p['pd']
            else:
                amt = round(a, 2)
    use_amt = amt if amt is not None else (carried_a if carried_a else def_amt(p))
    d = None
    flag = ''
    req = None
    if dt:
        kind, dd = free_date(dt, today)
        if kind == 'vague':
            if not p['vg']:
                p['vg'] = 1
                p['pend'] = {'a': use_amt, 'd': None, 'k': 'day'}
                return speak(pre + 'Which exact day can you pay? Please give me a date.')
            if p['dead']:
                d = from_iso(p['dead'])
                flag = 'late'
        elif kind == 'date':
            req = dd
            s, f = check_day(p, dd, today)
            if s == 'past':
                p['pend'] = {'a': use_amt, 'd': None, 'k': 'day'}
                return speak(pre + 'That day has already passed. Which day, starting today, can you pay?')
            d, flag = f, s
    if d is None:
        if amt is not None:
            p['pend'] = {'a': use_amt, 'd': None, 'k': 'day'}
            core = ''
            if below:
                core = 'I cannot record less than the %s of %s; the rest would stay overdue. ' % (floor_word(p), say_money(p['fl']))
            return speak(pre + core + 'On which day can you pay %s?' % say_money(use_amt))
        return reask(st, lead)
    pieces = []
    if below:
        pieces.append('I cannot record less than the %s of %s.' % (floor_word(p), say_money(p['fl'])))
    if flag == 'late':
        pieces.append('The latest date I can record is %s.' % dstr(d))
    elif flag == 'moved':
        pieces.append('%s is not a business day, so the next date I can record is %s.' % (dstr(req), dstr(d)))
    if flag == 'ok' and not below:
        accept(p, use_amt, d)
        return advance(st, lead)
    p['pend'] = {'a': use_amt, 'd': iso(d), 'k': 'adj'}
    pieces.append(offer_q(st, p))
    speak(pre + ' '.join(pieces))


# ------------------------------------------------------------------ special intents

def hardship_offer_text():
    I = E['intents'].get(E['hard']) or {}
    qn = I.get('offer_name') or 'team'
    return 'Would you like me to connect you with our %s?' % qn


_STOPW = ('the', 'and', 'for', 'with', 'ending', 'end', 'one')
_ORD = ('first', 'second', 'third', 'fourth')
_GENERIC = set(('it', 'that', 'this', 'one', 'ones', 'the', 'my', 'your', 'our', 'a', 'an', 'of', 'to', 'for', 'and', 'or', 'on', 'in', 'is',
                'account', 'accounts', 'product', 'products', 'debt', 'debts', 'payment', 'payments', 'balance', 'balances',
                'same', 'other', 'another', 'current', 'last', 'next', 'these', 'those', 'them', 'there', 'here', 'none',
                'first', 'second', 'third', 'fourth', 'overdue', 'late', 'past', 'due'))


def _keys(p):
    toks = re.findall(r'[a-z]+|\d+', (p['type'] + ' ' + p['label']).lower())
    return set(x for x in toks if x not in _STOPW and (len(x) >= 3 or x.isdigit()))


def target_products(st, pref):
    """-> (kind, products). kind: 'all' | 'one' (a unique match) | 'ambig' (several match equally) | 'none'
    (nothing named: the products in play)."""
    prods = st['prods']
    w = str(pref or '').lower().strip()
    if w:
        if re.search(r'\b(all|both|every|each|everything)\b', w):
            return 'all', [p for p in prods if p['status'] in ('open', 'agreed')]
        words = set(re.findall(r'[a-z]+|\d+', w))
        words |= set(x[:-1] for x in words if x.endswith('s') and len(x) > 3)
        for p in prods:                                   # a product id said as it is in the account data
            pid = str(p.get('id') or '').lower()
            if pid and pid in re.findall(r'[a-z0-9]+', w):
                return 'one', [p]
        for i, o in enumerate(_ORD):                      # "the first one", "the second"
            if o in words and i < len(prods):
                return 'one', [prods[i]]
        cands = [p for p in prods if _keys(p) & words]
        if cands:
            def wt(k):
                return 1.0 / sum(1 for q in prods if k in _keys(q))
            sc = dict((p['i'], sum(wt(k) for k in _keys(p) & words)) for p in cands)
            top = max(sc.values())
            best = [p for p in cands if sc[p['i']] >= top - 1e-9]
            return ('one' if len(best) == 1 else 'ambig'), best
        named = words - _GENERIC
        if named and len(prods) > 1:                      # a product that is not one of the customer's: ask, never guess
            play = [p for p in prods if p['status'] in ('open', 'agreed')] or prods
            return 'ambig', play
    opened = [p for p in prods if p['status'] == 'open']
    if st['all'] and len(opened) > 1:
        return 'none', opened
    return 'none', [prods[st['cur']]]


def ask_which(st, cands, dt='', am=''):
    """Several products fit what the customer named (or none of them does): ask, change nothing. The amount and date
    they gave are kept for the answer."""
    st['sd'] = dt or ''
    st['sa'] = am or ''
    speak('Which one do you mean: %s?' % ' or '.join(p['label'] for p in cands))


def do_transfer(st, queue, outcome, reason, text=''):
    st['transfer'] = {'queue': queue, 'outcome': outcome, 'reason': reason}
    vars['tr_queue'] = queue
    vars['tr_text'] = text or 'I am transferring you now.'
    vars['tr_ok'] = 'pending'
    st['phase'] = 'transfer'
    route('transfer')


def special(st, it, pref):
    """Spec intents. Returns True when the intent was handled."""
    I = E['intents'].get(it)
    if not I:
        return False
    kind = I['kind']
    say = I.get('say') or ''
    if kind == 'continue':
        reask(st, say)
        return True
    if kind == 'quit':
        st['quit'] += 1
        if st['quit'] >= int(I.get('max') or 2):
            cv = I.get('close_verified') or E['exhausted']
            for p in st['prods']:
                if p['status'] in ('open', 'agreed'):          # agreed but never recorded: the bank must still hear why
                    note_product(p, cv.get('reason') or E['exhausted']['reason'])
            conclude(st, 'I understand.')
            return True
        reask(st, 'The customer says they do not want to talk. Acknowledge that politely in a few words, and make no new offer.')
        return True
    if kind == 'transfer':
        if I.get('ask_first') and not st['human']:
            st['human'] += 1
            speak('I can try to help you first. What do you need help with?')
            return True
        text = I.get('transfer_say') or 'I am transferring you now.'
        do_transfer(st, I['queue'], I['close']['outcome'], I['close'].get('reason'), text)
        return True
    if kind in ('note', 'close'):
        kind, ts = target_products(st, pref)
        if kind == 'ambig':
            ask_which(st, ts)
            return True
        reason = I['note_reason']
        if E['use_notes'] and I.get('continues'):
            for p in ts:
                note_product(p, reason)
            return advance(st, say) or True
        for p in st['prods']:
            if p['status'] in ('open', 'agreed'):
                note_product(p, reason)
        conclude(st, say)
        return True
    if kind == 'offer':
        if st.get('hard_pending'):
            hardship_offer(st, I)
            return True
        st['hard_pending'] = True
        st['hard'] += 1
        st['nopers'] = (I.get('on_decline') or {}).get('reason') or E['exhausted']['reason']
        speak('I am sorry to hear that. ' + hardship_offer_text())
        return True
    return False


def hardship_offer(st, I):
    speak(hardship_offer_text())


def hardship_reply(st, it, dt, am, pref, scope_all):
    """The customer's reply while a support transfer is on offer."""
    I = E['intents'].get(E['hard']) or {}
    if it == 'agree':
        acc = I.get('on_accept') or {}
        st['hard_pending'] = False
        st['hs'] = None
        do_transfer(st, acc.get('queue'), (acc.get('close') or {}).get('outcome') or E['out']['r_transfer'],
                    (acc.get('close') or {}).get('reason'), 'I am connecting you now.')
        return True
    if it in ('offer', 'change'):
        st['hard_pending'] = False
        return False
    if it in ('question', 'none') and not st.get('hard_reasked'):
        st['hard_reasked'] = True                 # the transfer is offered once: a question is answered without repeating it,
        reask(st, then=(it == 'none'))            # and a second non-answer ("no, but can you...") counts as declining
        return True
    dec = I.get('on_decline') or {}
    st['hard_pending'] = False
    hs, st['hs'] = st.get('hs'), None
    if hs:                                        # they offered a payment along with the hardship: that offer stands,
        return {'it': 'offer', 'dt': hs.get('dt') or '', 'am': hs.get('am') or '', 'pref': hs.get('pref') or ''}   # with its own scope
    reason = dec.get('reason') or E['exhausted']['reason']
    for p in st['prods']:
        if p['status'] in ('open',):
            note_product(p, reason)
    finish_nego(st, 'I understand.')
    return True


# ------------------------------------------------------------------ the turns

def turn(st):
    q = S('x_q').lower()
    vars['x_q'] = 'no'
    if S('x_intent').lower() == 'agree' and (S('x_date') or S('x_amount')) and st['phase'] in ('nego', 'confirm'):
        vars['x_intent'] = 'change'               # "yes, but Friday": the correction comes first, nothing is recorded on the old terms
    if q == 'yes' and st['phase'] == 'confirm' and S('x_intent').lower() == 'agree':
        for k in ('x_date', 'x_amount', 'x_product'):
            vars[k] = ''
        vars['x_intent'] = 'none'
        return reask(st, 'The customer said yes but also asked something. Answer that first; do not record anything yet.')
    turn_inner(st)
    if q == 'yes' and vars.get('route') in ('fin', 'note') and not st.get('transfer'):
        st['defer'] = vars['route']                # answer first; the close follows on the next turn
        reask(st, 'The customer also asked a question before the call ends. Answer it, then ask nothing further.', then=False)
        return
    if q == 'yes' and vars.get('route') == 'say' and vars.get('say_text'):
        core = vars['say_text']
        ask('The customer also asked a question. First answer it in one short sentence, using only these facts: ' + facts(st, hide_floor=True) +
            '. If the facts do not answer it, say exactly "' + E['unknown_say'] + '". If they ask whether you are a robot or an AI, say "' +
            E['ai_say'] + '". If they ask whether this call is a scam, say that ' + E['scam_say'] +
            '. Never invent figures, dates or reasons. Then say exactly this, word for word: ' + core)


def turn_inner(st):
    it = S('x_intent').lower()
    dt = S('x_date')
    am = S('x_amount')
    pref = S('x_product')
    for k in ('x_date', 'x_amount', 'x_product'):
        vars[k] = ''
    vars['x_intent'] = 'none'
    if not it:
        it = 'none'
    prods = st['prods']
    scope_all = False
    if it in ('offer', 'change'):
        if not am and st.get('sa'):
            am = st['sa']                         # the amount asked about earlier, now with its account
        st['sa'] = ''
    elif it not in ('question', 'none'):
        st['sd'] = ''
        st['sa'] = ''
    if st.get('hard_pending') and st['phase'] == 'nego':
        hs = st.get('hs')
        if hs and it in ('offer', 'change') and not dt and not am:
            dt, am, pref = hs.get('dt') or '', hs.get('am') or '', hs.get('pref') or pref
        if it in ('offer', 'change'):
            st['hs'] = None
        r = hardship_reply(st, it, dt, am, pref, scope_all)
        if isinstance(r, dict):
            it, dt, am, pref = r['it'], r['dt'], r['am'], r['pref']
        elif r:
            return
    if it == E['hard'] and (dt or (am and amount_check(am)[0] == 'ok')) and not st.get('hard_pending'):
        st['hs'] = {'dt': dt, 'am': am if amount_check(am)[0] == 'ok' else '', 'pref': pref}   # "cannot pay anything" is no offer      # a payment offered together with the hardship is kept
    if it in E['intents']:
        if special(st, it, pref):
            return
    if st['phase'] == 'confirm':
        return turn_confirm(st, it, dt, am, pref)
    if st['all']:
        return turn_all(st, it, dt, am, pref)
    p = prods[st['cur']]
    if it == 'agree':
        pe = p.get('pend')
        if pe and pe.get('d'):
            accept(p, pe['a'], from_iso(pe['d']))
            return advance(st)
        return reask(st)
    pe0 = p.get('pend')
    if it in ('refuse', 'evasive', 'too_much') and p['tm'] and pe0 and pe0.get('k') == 'attempt' and pe0['a'] <= p['fl'] + 0.004 and p['fl'] < p['pd'] and it != 'refuse':
        return reask(st)              # the floor is already on the table: "can't do the full amount" is not a new refusal
    if it in ('refuse', 'evasive'):
        return refusal(st, p)
    if it == 'too_much':
        pe = p.get('pend')
        if p['tm'] and pe and pe['a'] + 0.004 < p['pd']:
            return reask(st)          # repeating "the full amount is too much" is not a refusal of the floor already offered
        p['tm'] = True
        return refusal(st, p)
    if it in ('offer', 'change'):
        kind, ts = target_products(st, pref)
        if kind == 'ambig':
            return ask_which(st, ts, dt, am)
        if kind == 'one' and ts[0]['i'] != p['i'] and ts[0]['status'] == 'open':
            st['cur'] = ts[0]['i']                # the customer named another product: the offer is for that one
            p = ts[0]
        elif kind == 'all' and len(ts) > 1 and any(q['status'] == 'open' and q['i'] != p['i'] for q in ts):
            if am:
                return ask_amount_account(st, dt, am)
            if dt:
                r = all_date(st, dt)
                if r is not None:
                    return r
        return offer(st, p, dt, am)
    return reask(st)


def ask_amount_account(st, dt, am=''):
    """An amount for "all of them" cannot be split by guessing: keep the date, ask which account the amount is for."""
    st['sd'] = dt or ''
    st['sa'] = am or ''
    speak('Which account is that amount for?')


def all_date(st, dt):
    """One date for every open product, each at its default amount. None when the words are not a date at all."""
    today = today_d()
    kind, dd = free_date(dt, today)
    if kind == 'vague' and not st['vg_all']:
        st['vg_all'] = 1
        return speak('Which exact day can you pay? Please give me a date.') or True
    if kind not in ('vague', 'date'):
        return None
    bad_past = False
    res = []
    for q in st['prods']:
        if q['status'] != 'open':
            continue
        if kind == 'vague':
            if q['dead']:
                res.append((q, def_amt(q), from_iso(q['dead']), 'late'))
            continue
        s, f = check_day(q, dd, today)
        if s == 'past':
            bad_past = True
            break
        res.append((q, def_amt(q), f, 'late' if s == 'late' else ''))
    if bad_past:
        return speak('That day has already passed. Which day, starting today, can you pay?') or True
    for q, a, f, cap in res:
        accept(q, a, f, cap)
    st['all'] = False
    return finish_nego(st) or True


def turn_all(st, it, dt, am, pref):
    prods = st['prods']
    today = today_d()
    if it == 'agree':
        d = first_day(today)
        for p in prods:
            if p['status'] == 'open':
                accept(p, p['pd'], d)
        st['all'] = False
        return finish_nego(st)
    if it in ('refuse', 'evasive', 'too_much'):
        st['all'] = False
        if it == 'too_much':
            for p in prods:
                p['tm'] = True
        st['cur'] = 0
        p0 = prods[0]
        intro = "Let's go through them one by one."
        return refusal(st, p0, intro + ' Your %s.' % plain_label(p0['label']))
    if it in ('offer', 'change'):
        kind, named = target_products(st, pref)
        opened = [q for q in prods if q['status'] == 'open']
        if kind == 'ambig':
            return ask_which(st, named, dt, am)
        if kind == 'one' and len(opened) > 1:
            st['all'] = False
            st['cur'] = named[0]['i']
            return offer(st, named[0], dt, am)
        if am and len(opened) > 1 and kind == 'all':
            return ask_amount_account(st, dt, am)
        if am:
            st['all'] = False                       # an amount (with its date, if any) is taken product by product
            st['cur'] = 0
            return offer(st, prods[0], dt, am)
        if dt:
            r = all_date(st, dt)
            if r is not None:
                return r
    return reask(st)


def confirm_all_date(st, dt):
    """At the read-back: one new date for every agreed product, amounts kept."""
    today = today_d()
    kind, dd = free_date(dt, today)
    if kind != 'date':
        return speak('Which exact day can you pay? Please give me a date.')
    agreed = [q for q in st['prods'] if q['status'] == 'agreed']
    res = []
    for q in agreed:
        s, f = check_day(q, dd, today)
        if s == 'past':
            return speak('That day has already passed. Which day, starting today, can you pay?')
        res.append((q, f, s))
    for q, f, s in res:
        q['date'] = iso(f)
        q['cap'] = 'late' if s == 'late' else ''
    notes = []
    if any(s == 'late' for q, f, s in res):
        notes.append('Some of those dates are later than I can record, so I used the latest date I can.')
    if any(s == 'moved' for q, f, s in res):
        notes.append('Some days are not business days, so I used the next date I can record.')
    return speak(' '.join(['Of course.'] + notes + [readback(st)]))


def turn_confirm(st, it, dt, am, pref):
    prods = st['prods']
    agreed = [p for p in prods if p['status'] == 'agreed']
    if it == 'agree':
        st['cq'] = [p['i'] for p in agreed]
        st['phase'] = 'creating'
        st['tries'] = 0
        return set_create(st)
    pick = None
    kind, ts = target_products(st, pref)
    if kind == 'ambig':
        return ask_which(st, ts, dt, am)
    for p in ts:
        if p['status'] == 'agreed':
            pick = p
            break
    if pick is None and agreed:
        pick = agreed[0]
    if it in ('offer', 'change') and kind == 'all' and len(agreed) > 1:
        if am:
            return ask_amount_account(st, dt, am)
        if dt:
            return confirm_all_date(st, dt)
    if it in ('offer', 'change') and pick is not None:
        pick['status'] = 'open'
        pick['pend'] = {'a': pick['amt'], 'd': pick['date'], 'k': 'edit'}   # what was agreed stays unless changed
        st['cur'] = pick['i']
        st['phase'] = 'nego'
        if not dt and not am:
            pick['pend'] = {'a': pick['amt'], 'd': None, 'k': 'day'}
            return speak('Of course. Which day or amount would you like instead?')
        return offer(st, pick, dt, am, 'Of course.')
    if it in ('refuse', 'too_much', 'evasive') and pick is not None:
        pick['status'] = 'open'
        pick['pend'] = None
        if it == 'too_much':
            pick['tm'] = True
        st['cur'] = pick['i']
        st['phase'] = 'nego'
        return refusal(st, pick)
    return reask(st)


# ------------------------------------------------------------------ promise creation

def set_create(st):
    p = st['prods'][st['cq'][0]]
    vars['cp_pid'] = p['id']
    vars['cp_amount'] = money(p['amt'])
    vars['cp_date'] = p['date']
    vars['cp_ok'] = 'pending'
    route('create')


def created(st):
    if st.get('ackw'):                             # the line after a record was spoken: on to the next promise
        st['ackw'] = 0
        if S('x_intent').lower() not in ('', 'none', 'agree', 'question', 'evasive'):
            st['cq'] = []                          # the customer spoke up: what is not recorded yet goes back to the read-back
            st['phase'] = 'confirm'
            return turn(st)
        return set_create(st)
    ok = S('cp_ok').lower() == 'true'
    p = st['prods'][st['cq'][0]]
    if ok:
        p['status'] = 'recorded'
        vars['promise_recorded'] = 'true'          # durable: the next write overwrites cp_ok
        st['cq'].pop(0)
        st['tries'] = 0
    else:
        st['tries'] += 1
        if st['tries'] >= (2 if E.get('max_tries') is None else int(E['max_tries'])):
            p['status'] = 'failed'
            st['cq'].pop(0)
            st['tries'] = 0
    if st['cq']:
        if ok and E.get('ack_scope') == 'per_record':
            st['ackw'] = 1
            p['ack'] = 1
            return speak('Your promise for %s is recorded. %s' % (p['label'], E['after_recorded']))
        return set_create(st)
    st['phase'] = 'nego'
    conclude(st)


# ------------------------------------------------------------------ plan, identity events, third party

def plan(st):
    today = today_d()
    raws = read_products()
    if today is None or not raws:
        st['phase'] = 'nego'
        c = E['create_failed']
        return set_close(c['outcome'], c['reason'], goodbye('I am sorry, I cannot access your account right now.'))
    kept, skipped, seen = [], [], set()
    for r in raws:
        pid = str(r.get('product_id') or '').strip()
        if usable(r) and pid not in seen:           # a repeated id would let one record stand for two products
            seen.add(pid)
            kept.append(r)
        else:
            skipped.append(pid or '?')
    raws = kept
    st['skipped'] = skipped
    vars['plan_skipped'] = ','.join(skipped)          # rows of the account that were left out, for the trace
    if not raws:
        st['phase'] = 'nego'
        c = E['create_failed']
        return set_close(c['outcome'], c['reason'], goodbye('I am sorry, I cannot access your account right now.'))
    prods = [make_product(i, r, today) for i, r in enumerate(raws)]
    st['prods'] = prods
    st['phase'] = 'nego'
    n = len(prods)
    sents = ['Your %s is %s %s and %d days %s.' % (plain_label(p['label']), say_money(p['pd']), E['pd_word'], p['dl'], E['days_word']) for p in prods]
    say = E['debt_say']
    if n > 1:
        say = say.replace('a late payment', 'late payments').replace('an overdue payment', 'overdue payments')
    head = 'I am %s.' % say
    if n == 1:
        p = prods[0]
        p['pend'] = {'a': p['pd'], 'd': iso(first_day(today)), 'k': 'today'}
        return speak(head + ' ' + sents[0] + ' ' + E['first_q'])
    st['all'] = True
    speak(head + ' ' + ' '.join(sents) + ' ' + E['first_q_all'])


def first_unpassed():
    for i in range(1, int(E.get('n_q') or 1) + 1):
        if S('idq%d_state' % i) != 'passed':
            return i
    return int(E.get('n_q') or 1)


def idv_event(st):
    ev = S('x_stance').lower()
    vars['x_stance'] = 'other'
    qi = first_unpassed()
    if ev == 'human' and E['intents'].get(E['human']):
        I = E['intents'][E['human']]
        st['idv_human'] += 1
        if st['idv_human'] == 1 and I.get('ask_first'):
            vars['idv_note'] = ('The customer asked for a person. First say that you can try to help and ask what they need, '
                                'without saying anything about the reason for the call. Then ask the question again.')
            return route('idq_%d' % qi)
        return do_transfer(st, I['queue'], I['close']['outcome'], I['close'].get('reason'), 'I am transferring you now.')
    st['idv_ref'] += 1
    if st['idv_ref'] >= int(E['idv'].get('max_refusals') or 2):
        c = E['idv']['declined']
        return set_close(c['outcome'], c.get('reason'), goodbye('I understand.'))
    vars['idv_note'] = ('The customer did not want to answer, or asked what the call is about. Explain once that ' +
                        E['idv']['explain'] + ' and that you cannot discuss anything else before the check. '
                        'Then ask the question again.')
    route('idq_%d' % qi)


def cb_check(d, m, today):
    """check_callback with support for 'today_or_next_N_business_days' and 'next_N_business_days' (N from the spec, any N)."""
    days = str(CAL.get('cb_days') or '')
    mm = re.search(r'next_(\d+)_business_days', days)
    if not mm:
        return check_callback(iso(d), fmt_time(m), today, now_min(), CAL)
    n = int(mm.group(1))
    cfg = dict(CAL)
    cfg['cb_days'] = 'any_day'
    s, dd, mm2 = check_callback(iso(d), fmt_time(m), today, now_min(), cfg)
    limit = add_bd(today, n, CAL) or today
    day_ok = (d == today and days.startswith('today')) or (d > today and is_bd(d, CAL) and d <= limit)
    if not day_ok and s in ('ok', 'out_of_window', 'not_after_now'):
        s = 'bad_day'
    return s, dd, mm2


def tp_turn(st):
    ev = S('tp_event').lower()
    dt = S('tp_date')
    tt = S('tp_time')
    vars['tp_event'] = 'other'
    vars['tp_date'] = ''
    vars['tp_time'] = ''
    tp = E['tp']
    if ev == 'wrong_number':
        c = tp['wrong_number']
        return set_close(c['outcome'], c.get('reason'), tp['wrong_number_say'])
    if ev == 'deceased':
        c = tp['deceased']
        return set_close(c['outcome'], c.get('reason'), tp['deceased_say'])
    today = today_d()
    st['tp_n'] += 1
    d_iso = ''
    t_cands = free_time(tt) if tt else []
    d = None
    if dt:
        kind, dd = free_date(dt, today)
        if kind == 'date':
            d = dd
    if d is None and not dt and st.get('tp_d'):
        d = from_iso(st['tp_d'])                  # the day they gave earlier still stands
    if d is not None:
        st['tp_d'] = iso(d)
    if d is None and t_cands and not dt:
        nb = next_bd(today, CAL)
        d = today
        res = [cb_check(today, m, today)[0] for m in t_cands]
        if 'ok' not in res and nb:
            d = nb
    if d is not None and t_cands:
        best = None
        for m in t_cands:
            s, dd, mm = cb_check(d, m, today)
            if s == 'ok':
                best = (iso(d), fmt_time(m))
                break
        if best:
            vars['cb_date'] = best[0]
            vars['cb_time'] = best[1]
            vars['cb_ok'] = 'pending'
            st['phase'] = 'cb'
            st['tries'] = 0
            return route('callback')
        st['tp_d'] = ''                           # that day and time did not work: ask for both again
        if st['tp_bad'] < int(tp.get('max_bad') or 1):
            st['tp_bad'] += 1
            vars['instruction'] = ('Say that unfortunately that time is not possible; you can call back ' + tp['window_text'] +
                                   '. Ask for another day and time. Say nothing about the reason for the call.')
            return route('tp_say')
        c = tp['on_failed']
        return set_close(c['outcome'], c.get('reason'), tp['failed_say'])
    if d is not None and not t_cands:
        vars['instruction'] = 'Ask at what time on that day the person can be reached. Say nothing about the reason for the call.'
        return route('tp_say')
    if st['tp_n'] >= 4:
        c = tp['on_failed']
        return set_close(c['outcome'], c.get('reason'), tp['failed_say'])
    vars['instruction'] = ('Say that you can only speak to the person you asked for, and that you cannot say anything about the '
                           'reason for the call or about any account. Ask on which day and at what time they can be reached. '
                           'Never mention any product, amount, debt or payment.')
    route('tp_say')


def cb_done(st):
    tp = E['tp']
    ok = S('cb_ok').lower() == 'true'
    if not ok and st['tries'] < 1:
        st['tries'] += 1
        vars['cb_ok'] = 'pending'
        return route('callback')
    if ok:
        c = tp['on_scheduled']
        d = from_iso(S('cb_date'))
        return set_close(c['outcome'], c.get('reason'), 'Thank you. We will call back on %s at %s. %s' % (dstr(d), S('cb_time'), E['goodbye']))
    c = tp['on_failed']
    set_close(c['outcome'], c.get('reason'), tp['failed_say'])


def transferred(st):
    final(st)


# ------------------------------------------------------------------ entry

def main():
    st = load()
    try:
        if st.get('defer'):
            r, st['defer'] = st['defer'], ''
            I = E['intents'].get(S('x_intent').lower()) or {}
            if I.get('kind') == 'transfer':        # asked for a person or a plan while the close was waiting: that comes first
                vars['x_intent'] = 'none'
                do_transfer(st, I['queue'], I['close']['outcome'], I['close'].get('reason'), I.get('transfer_say') or 'I am transferring you now.')
            else:
                route(r)
        elif S('x_stance').lower() in ('declines', 'human'):
            idv_event(st)
        elif st['phase'] == 'tp':
            tp_turn(st)
        elif st['phase'] == 'plan':
            plan(st)
        elif st['phase'] in ('nego', 'confirm'):
            turn(st)
        elif st['phase'] == 'creating':
            created(st)
        elif st['phase'] == 'noting':
            noted(st)
        elif st['phase'] == 'transfer':
            transferred(st)
        elif st['phase'] == 'cb':
            cb_done(st)
        else:
            reask(st)
    except Exception as ex:
        vars['engine_err'] = repr(ex)[:300]
        if st.get('prods'):
            ask('Apologise briefly and ask the customer to repeat what they just said.')
        else:
            set_close(E['create_failed']['outcome'], E['create_failed']['reason'], goodbye('I am sorry, there was a problem.'))
    save(st)


main()
