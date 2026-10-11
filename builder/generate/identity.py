"""Identity answers: which scheme a security question uses and the code that turns what the customer said into what the bank checks.

    sch = scheme(question, hint)      # hint: what the tool API says about this field's answer
    code = hook_body(sch, field)      # statements for the verify_identity pre_process hook (uses `a`, `vars`, `re`)

Schemes (read from the question's format and wording and from the tool API's description of the answer, never from a field name list):
  date    a date of birth or any date: handled by the date normaliser in generate.verify_pre
  digits  N digits (last 4 of a phone, last 5 of an ID, a 4-digit year or postcode): spoken digits become digits ("zero zero four one seven"
          -> 00417, "double four" -> 44), an answer given in two parts is joined, a longer number keeps its last N digits
  alnum   letters and digits (postcodes such as SW1A 1AA): spelled letters and NATO words are joined, case and spacing follow the format
  text    free text (home town, maiden name): whitespace tidied, accents removed and case set only when the format says so
The platform sandbox has no unicodedata: accents are removed with a table.
"""
import re

WORDNUM = {'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5, 'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10, 'eleven': 11, 'twelve': 12}

# lower-case letters with accents -> ASCII (upper case is derived)
ASCII_FOLD = {
    'ø': 'o', 'å': 'a', 'æ': 'ae', 'œ': 'oe', 'ß': 'ss', 'ð': 'd', 'þ': 'th', 'ł': 'l', 'đ': 'd', 'ħ': 'h', 'ı': 'i',
    'á': 'a', 'à': 'a', 'â': 'a', 'ä': 'a', 'ã': 'a', 'ā': 'a', 'ă': 'a', 'ą': 'a', 'ç': 'c', 'ć': 'c', 'č': 'c', 'ĉ': 'c',
    'é': 'e', 'è': 'e', 'ê': 'e', 'ë': 'e', 'ē': 'e', 'ė': 'e', 'ę': 'e', 'ě': 'e', 'ğ': 'g', 'ģ': 'g',
    'í': 'i', 'ì': 'i', 'î': 'i', 'ï': 'i', 'ī': 'i', 'į': 'i', 'ķ': 'k', 'ļ': 'l', 'ľ': 'l', 'ñ': 'n', 'ń': 'n', 'ň': 'n', 'ņ': 'n',
    'ó': 'o', 'ò': 'o', 'ô': 'o', 'ö': 'o', 'õ': 'o', 'ō': 'o', 'ő': 'o', 'ř': 'r', 'ŕ': 'r', 'ś': 's', 'š': 's', 'ş': 's', 'ș': 's',
    'ť': 't', 'ţ': 't', 'ț': 't', 'ú': 'u', 'ù': 'u', 'û': 'u', 'ü': 'u', 'ū': 'u', 'ů': 'u', 'ű': 'u', 'ų': 'u',
    'ý': 'y', 'ÿ': 'y', 'ź': 'z', 'ž': 'z', 'ż': 'z',
}
FOLD_TABLE = dict(ASCII_FOLD)
FOLD_TABLE.update({k.upper(): v.capitalize() for k, v in ASCII_FOLD.items() if k.upper() != k})
FOLD_TABLE['ẞ'] = 'SS'

SPOKEN_DIGITS = {'zero': '0', 'oh': '0', 'o': '0', 'nought': '0', 'naught': '0', 'one': '1', 'two': '2', 'three': '3', 'four': '4',
                 'five': '5', 'six': '6', 'seven': '7', 'eight': '8', 'nine': '9', 'ten': '10'}
NATO = {'alpha': 'a', 'alfa': 'a', 'bravo': 'b', 'charlie': 'c', 'delta': 'd', 'echo': 'e', 'foxtrot': 'f', 'golf': 'g', 'hotel': 'h',
        'india': 'i', 'juliet': 'j', 'juliett': 'j', 'kilo': 'k', 'lima': 'l', 'mike': 'm', 'november': 'n', 'oscar': 'o', 'papa': 'p',
        'quebec': 'q', 'romeo': 'r', 'sierra': 's', 'tango': 't', 'uniform': 'u', 'victor': 'v', 'whiskey': 'w', 'xray': 'x',
        'yankee': 'y', 'zulu': 'z'}
FILLER = ('and', 'dash', 'hyphen', 'space', 'point', 'the', 'is', 'its', 'it', 'my', 'answer', 'number', 'digits', 'digit', 'um', 'uh', 'erm',
          'so', 'that', 'postcode', 'postal', 'code', 'zip', 'capital', 'letter', 'letters', 'of', 'a')


def _num(tok):
    tok = str(tok).lower()
    return int(tok) if tok.isdigit() else WORDNUM.get(tok)


def field_hint(desc, field):
    """The part of the tool API's answer description that talks about this field ("home_town: lower case ASCII.")."""
    if not desc or not field:
        return ''
    m = re.search(r'(?:^|[.;]\s*)(?:for\s+)?' + re.escape(str(field)) + r'\s*:\s*([^.;]*)', str(desc), re.I)
    return m.group(1).strip() if m else ''


def scheme(q, hint=''):
    fmt = str(q.get('format') or '')
    ask = str(q.get('ask') or '')
    field = str(q.get('field') or '').lower()
    text = ' '.join((fmt, ask, hint or '')).lower()
    f_and_fmt = (field + ' ' + fmt).lower()
    if (re.search(r'birth|\bdob\b', f_and_fmt) or field.endswith('_date') or field == 'date'
            or (re.search(r'yyyy', fmt.lower()) and re.search(r'mm|dd', fmt.lower()))):
        return {'kind': 'date'}
    letters = bool(re.search(r'letter|alphanumeric|alpha-numeric|lower ?case|upper ?case|ascii|accent|capital|spell', text))
    n = None
    for rx in (r'(\d+|' + '|'.join(WORDNUM) + r')[\s-]*digits?\b', r'last[\s_]*(\d+|' + '|'.join(WORDNUM) + r')\b', r'last_?(\d+)$'):
        m = re.search(rx, text) or (re.search(rx, field) if rx.startswith('last') else None)
        if m:
            n = _num(m.group(1))
            break
    if n is None and re.search(r'year|yyyy', f_and_fmt) and not letters:
        n = 4
    digit_words = bool(re.search(r'\bdigits?\b|numeric|numbers? only|only numbers', text))
    if (n or digit_words) and not letters:
        return {'kind': 'digits', 'n': n}
    out = {'kind': 'text'}
    if re.search(r'lower[\s-]?case', text):
        out['case'] = 'lower'
    elif re.search(r'upper[\s-]?case|capital letters|all caps', text):
        out['case'] = 'upper'
    if re.search(r'ascii|no accents?|no diacritics|without accents|latin letters', text):
        out['ascii'] = True
    if re.search(r'no spaces?( or hyphens?)?|without spaces?|no whitespace', text):
        out['nospace'] = True
    if re.search(r'no hyphens?|without hyphens?|no spaces? or hyphens?|no punctuation', text):
        out['nohyphen'] = True
    if re.search(r'postcode|postal code|post code|zip', text) and re.search(r'letter|alphanumeric|\d[a-z]|[a-z]\d', text):
        out['kind'] = 'alnum'
        out.setdefault('case', 'upper')
        m = re.search(r'\b[A-Z0-9]{1,4}\s([A-Z0-9]{2,4})\b', fmt)
        if m and not out.get('nospace'):
            out['tail'] = len(m.group(1))
        else:
            out['nospace'] = True
    elif re.search(r'alphanumeric|letters and digits|digits and letters|letters and numbers', text):
        out['kind'] = 'alnum'
    return out


UNITS = {'zero': 0, 'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5, 'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10,
         'eleven': 11, 'twelve': 12, 'thirteen': 13, 'fourteen': 14, 'fifteen': 15, 'sixteen': 16, 'seventeen': 17, 'eighteen': 18,
         'nineteen': 19}
TENS = {'twenty': 20, 'thirty': 30, 'forty': 40, 'fifty': 50, 'sixty': 60, 'seventy': 70, 'eighty': 80, 'ninety': 90}


def helpers_code():
    return ('FOLD = %r\nSPOKEN = %r\nNATO = %r\nFILLER = %r\nUNITS = %r\nTENS = %r\n' % (FOLD_TABLE, SPOKEN_DIGITS, NATO, FILLER, UNITS, TENS) + '''
def spoken_digits(a):
    """'zero zero four one seven', 'oh four', 'double four two' -> digits; None when the words are not all digits."""
    t = re.findall(r"[a-z]+|\\d+", a.lower())
    out = []
    i = 0
    while i < len(t):
        w = t[i]
        if w in ('double', 'triple', 'treble') and i + 1 < len(t) and (t[i + 1] in SPOKEN or t[i + 1].isdigit()):
            out.append(SPOKEN.get(t[i + 1], t[i + 1]) * (2 if w == 'double' else 3))
            i += 2
            continue
        if w in SPOKEN:
            out.append(SPOKEN[w])
        elif w.isdigit():
            out.append(w)
        elif w in FILLER:
            pass
        else:
            return None
        i += 1
    return ''.join(out) or None


def year_words(a):
    """'nineteen eighty four' -> '1984', 'twenty fourteen' -> '2014', 'two thousand and five' -> '2005'; None otherwise."""
    t = [w for w in re.findall(r"[a-z]+", a.lower()) if w not in ('and', 'the', 'year', 'in', 'is', 'it', 'its', 'my')]
    if not t:
        return None
    groups = []
    cur = None
    thousand = 0
    i = 0
    while i < len(t):
        w = t[i]
        if w in ('oh', 'o', 'zero') and i + 1 < len(t) and t[i + 1] in UNITS and 0 < UNITS[t[i + 1]] < 10:
            if cur is not None:
                groups.append(cur)
                cur = None
            groups.append(UNITS[t[i + 1]])
            i += 2
            continue
        if w == 'thousand':
            if cur is None:
                return None
            thousand = cur * 1000
            cur = None
        elif w == 'hundred':
            if cur is None:
                return None
            cur = cur * 100
        elif w in TENS or w in UNITS:
            val = TENS[w] if w in TENS else UNITS[w]
            if w in TENS and i + 1 < len(t) and t[i + 1] in UNITS and 0 < UNITS[t[i + 1]] < 10:
                val += UNITS[t[i + 1]]
                i += 1
            if cur is not None and cur >= 100 and cur % 100 == 0:
                cur += val
            else:
                if cur is not None:
                    groups.append(cur)
                cur = val
        else:
            return None
        i += 1
    if thousand:
        return str(thousand + (cur or 0)) if not groups else None
    if cur is not None:
        groups.append(cur)
    if len(groups) == 2 and 10 <= groups[0] <= 99 and 0 <= groups[1] <= 99:
        return '%d%02d' % (groups[0], groups[1])
    if len(groups) == 3 and 10 <= groups[0] <= 99 and groups[1] == 0 and 1 <= groups[2] <= 9:
        return '%d%02d' % (groups[0], groups[2])
    if len(groups) == 1 and 1000 <= groups[0] <= 2999:
        return str(groups[0])
    return None


def spelled(a):
    """'S W one A', 'sierra whiskey one alpha' -> 'SW1A'; text that is not spelled out is returned unchanged."""
    t = re.findall(r"[A-Za-z]+|\\d+", a)
    if len(t) < 2:
        return a
    out = []
    for w in t:
        lw = w.lower()
        if len(w) == 1 or w.isdigit():
            out.append(w)
        elif lw in NATO:
            out.append(NATO[lw])
        elif lw in SPOKEN:
            out.append(SPOKEN[lw])
        elif lw in FILLER:
            continue
        else:
            return a
    return ''.join(out)
''')


def hook_body(sch, field):
    """Statements for the pre_process hook: `a` holds the answer, `vars` the call variables. Pure Python with re only."""
    kind = sch.get('kind')
    if kind == 'digits':
        n = sch.get('n')
        key = 'part_%s' % re.sub(r'[^a-z0-9_]', '', str(field).lower())
        body = ("        sp = spoken_digits(a)\n"
                "        if sp is None and %s:\n            sp = year_words(a)\n"
                "        dg = sp if sp is not None else re.sub(r'[^0-9]', '', a)\n" % ('True' if n in (None, 4) else 'False'))
        if n:
            body += ("        prev = str(vars.get('%s') or '')\n"
                     "        if 0 < len(dg) < %d and len(prev + dg) == %d:\n            dg = prev + dg\n            prev = ''\n"
                     "        elif 0 < len(dg) < %d:\n            prev = dg\n"
                     "        else:\n            prev = ''\n"
                     "        vars['%s'] = prev\n"
                     "        if len(dg) >= %d:\n            a = dg[-%d:]\n" % (key, n, n, n, key, n, n))
        else:
            body += "        if dg:\n            a = dg\n"
        return body
    if kind in ('text', 'alnum'):
        body = ""
        if kind == 'alnum':
            body += "        a = spelled(a)\n"
        elif sch.get('case') or sch.get('ascii') or sch.get('nospace') or sch.get('nohyphen'):
            body += "        a = spelled(a) if all(len(w) == 1 for w in a.split()) and len(a.split()) > 1 else a\n"
        if sch.get('ascii'):
            body += "        a = ''.join(FOLD.get(c, c) for c in a)\n"
        if sch.get('case') == 'lower':
            body += "        a = a.lower()\n"
        elif sch.get('case') == 'upper':
            body += "        a = a.upper()\n"
        if sch.get('nohyphen') or sch.get('nospace') or kind == 'alnum':
            body += "        a = re.sub(r\"[-_.']\", '', a)\n" if (sch.get('nohyphen') or kind == 'alnum') else ""
        body += "        a = re.sub(r'\\s+', ' ', a).strip()\n"
        if sch.get('nospace'):
            body += "        a = a.replace(' ', '')\n"
        elif sch.get('tail'):
            body += ("        c = a.replace(' ', '')\n"
                     "        a = c[:-%d] + ' ' + c[-%d:] if len(c) > %d else c\n" % (sch['tail'], sch['tail'], sch['tail']))
        return body
    return ""
