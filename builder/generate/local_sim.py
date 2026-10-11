"""Local engine test: scripted customer extractions + the in-process stand-in bank + the real scorer. No Freya calls.

    python -m builder.generate.local_sim [-v]     # A/B public cases, then variant briefs C, D, E; asserts bank records == expected
"""
import json, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, 'tools'))
from builder.generate.ecfg import build_E
from builder.generate.generate import engine_code, generate
from harness.mock_bank import Bank
from score import score_ledger


def load(path):
    return json.load(open(os.path.join(ROOT, path), encoding='utf-8'))


API = load('tools/openapi.json')
CASES = load('public-test-set.json')


def drive_identity(spec, case, bank, sess, cid, raw=False):
    """Identity phase: replay the answers through the generated hooks and the bank; the check must end."""
    wf = generate(spec)
    qs = spec['identity']['questions']
    locked = False
    for field, ans in case['wrong_script']:
        qi = [i for i, q in enumerate(qs, 1) if q['field'] == field][0]
        fn = wf['nodes']['idq_%d' % qi]['tools'][0]
        cfg = {'body': {'answer': ans, 'field': field}}
        exec(fn['pre_process_code'], {'config': cfg, 'vars': {'now': sess['now']}})
        status, res = bank.tool('verify_identity', {'customer_id': cid, 'field': field, 'answer': cfg['body']['answer']})
        result = {'status': 'success', 'data': dict(res)}
        exec(fn['post_process_code'], {'result': result})
        if result['data']['state'] == 'locked':
            locked = True
            break
    if not locked:
        raise RuntimeError('check did not end')
    f = build_E(spec)['idv']['failed']
    body = {'customer_id': cid, 'outcome': f['outcome']}
    if f.get('reason'):
        body['reason'] = f['reason']
    bank.tool('close_call', body)
    return bank.ledger(cid) if raw else score_ledger(case, bank.ledger(cid))


def drive(spec, case, steps, verbose=False, api=None, cases=None, raw=False, cycle=False, said=None):
    """steps: one dict of extraction vars (x_intent, x_date, ... or tp_event ...) per customer turn.
    raw: return the bank's ledger instead of the score. cycle: when the steps run out (or the call closes early) the
    customer repeats the last step until the call closes, and steps left after the close are ignored (generated scenarios).
    said: a list that receives the engine's instruction text for every spoken turn."""
    code = engine_code(build_E(spec))
    bank = Bank(api or API, cases or CASES)
    sess = bank.new_session(case['id'])['variables']
    cid = sess['customer_id']
    if case.get('wrong_script'):
        return drive_identity(spec, case, bank, sess, cid, raw)
    v = {'now': sess['now'], 'st': '', 'customer_id': cid}

    def tool(name, body):
        return bank.tool(name, dict(body, customer_id=cid))
    third_party = case['family'] == 'Third party'
    if not third_party:
        for f, a in case['identity'].items():
            tool('verify_identity', {'field': f, 'answer': a})
        s, r = tool('get_account', {})
        for i, p in enumerate(r['products']):
            for k, x in p.items():
                v['get_account_response.data.products.%d.%s' % (i, k)] = str(x)
    else:
        v['st'] = json.dumps({'phase': 'tp'})

    def engine():
        ns = {'vars': v}
        exec(compile(code, '<engine>', 'exec'), ns)
        if v.get('engine_err'):
            raise RuntimeError(v['engine_err'])
        r = v.get('route')
        if said is not None and r in ('say', 'tp_say', 'ask'):
            said.append(v.get('instruction') or '')
        if verbose:
            print('   route=%s %s' % (r, (v.get('instruction') or '')[-200:] if r in ('say', 'tp_say') else ''))
        return r

    def follow(r):
        for _ in range(30):
            if r == 'create':
                s, res = tool('create_promise', {'product_id': v['cp_pid'], 'amount': float(v['cp_amount']), 'date': v['cp_date']})
                v['cp_ok'] = str(bool(res.get('ok'))).lower()
            elif r == 'note':
                s, res = tool('add_note', {'product_id': v['nt_pid'], 'reason': v['nt_reason']})
                v['nt_ok'] = str(bool(res.get('ok'))).lower()
            elif r == 'transfer':
                tool('transfer_to_agent', {'queue': v['tr_queue']})
            elif r == 'callback':
                s, res = tool('schedule_callback', {'date': v['cb_date'], 'time': v['cb_time']})
                v['cb_ok'] = str(bool(res.get('ok'))).lower()
            elif r == 'fin':
                body = {'outcome': v['close_outcome']}
                if v.get('close_reason'):
                    body['reason'] = v['close_reason']
                tool('close_call', body)
                return 'closed'
            else:
                return r
            r = engine()
        raise RuntimeError('route loop')
    r = 'say' if third_party else follow(engine())
    steps = list(steps)
    for s in steps + ([steps[-1]] * 14 if cycle and steps else []):
        if r == 'closed':
            if cycle:
                break
            raise RuntimeError('steps left after close: %s' % s)
        v.update(s)
        if verbose:
            print('>>', s)
        r = follow(engine())
    if r != 'closed':
        raise RuntimeError('not closed, last route %s' % r)
    return bank.ledger(cid) if raw else score_ledger(case, bank.ledger(cid))


BUILTIN = ('agree', 'refuse', 'too_much', 'offer', 'evasive', 'question', 'none')
I = lambda i, **k: dict(x_intent=(i if i in BUILTIN else 'sp_' + i), **k)
TP = lambda ev, d='', t='': dict(tp_event=ev, tp_date=d, tp_time=t)

SCEN = {
    'PUB-01': [I('agree'), I('agree')],
    'PUB-02': [TP('other'), TP('gives_time', 'tomorrow', 'eleven in the morning')],
    'PUB-03': 'identity',
    'PUB-04': [I('offer', x_date='6 November'), I('agree'), I('question'), I('agree')],
    'PUB-05': [I('hardship', x_amount='anything'), I('question'), I('refuse')],
    'PUB-06': [I('too_much'), I('too_much'), I('agree'), I('agree')],
    'PUB-07': [I('refuse'), I('offer', x_date='the week after next'), I('offer', x_date='Monday the 26th'), I('agree'), I('agree')],
    'PUB-08': [I('already_paid')],
    'PUB-09': [I('restructuring')],
    'PUB-10': [I('refuse'), I('agree'), I('agree')],
    'PUB-11': [I('refuse'), I('offer', x_date='this Friday'), I('agree'), I('agree'), I('agree')],
    'PUB-12': [I('offer', x_date='tomorrow', x_product='credit card'), I('refuse'), I('refuse'), I('refuse'), I('agree')],
    'PUB-13': [I('offer', x_date='30 October'), I('agree')],
}
WRONG = {
    'PUB-03': [('date_of_birth', '12 July 1991'), ('date_of_birth', '21 August 1992'), ('date_of_birth', '21 July 1990')],
    'TC-03': [('date_of_birth', '5 July 1991'), ('date_of_birth', '5 June 1991'), ('postcode', '7001'), ('postcode', '7002')],
    'TF-03': [('membership_year', '2001'), ('membership_year', '2002')],
    'TG-03': [('membership_year', str(y)) for y in range(2001, 2006)],
    'TH-03': [('membership_year', str(y)) for y in range(2001, 2005)],
    'TE-05': [('date_of_birth', '12 May 1980'), ('date_of_birth', '13 May 1980'), ('date_of_birth', '14 May 1980'), ('date_of_birth', '15 May 1980'),
              ('postcode', '4200'), ('postcode', '4201'), ('postcode', '4202'), ('postcode', '4203')],
}
VARIANTS = {
    'c': {'TC-01': [I('agree'), I('agree')],
          'TC-02': [I('refuse'), I('too_much'), I('offer', x_date='Saturday'), I('agree'), I('agree')],
          'TC-03': 'identity', 'TC-04': [I('offer', x_date='tomorrow'), I('agree')],
          'TC-05': [I('refuse'), I('refuse'), I('refuse'), I('agree'), I('agree')],
          'TC-06': [TP('other'), TP('gives_time', 'tomorrow', 'six in the evening'), TP('gives_time', 'Friday', 'ten in the morning')],
          'TC-07': [I('hardship'), I('agree')], 'TC-08': [I('already_paid')]},
    'd': {'TD-01': [I('offer', x_date='Wednesday 25 November'), I('agree')], 'TD-02': [I('offer', x_date='1 December'), I('agree')],
          'TD-03': [I('refuse'), I('offer', x_date='today'), I('too_much'), I('offer', x_date='Tuesday next week'), I('agree')],
          'TD-04': [I('refuse'), I('dispute', x_product='loan'), I('offer', x_date='Friday'), I('agree')],
          'TD-05': [I('refuse'), I('refuse'), I('refuse'), I('refuse')],
          'TD-06': [TP('wrong_number')],
          'TD-07': [TP('other'), TP('gives_time', 'today', 'half past six in the evening'), TP('gives_time', 'tomorrow', 'half past nine in the morning')],
          'TD-08': [I('offer', x_date='next Friday'), I('agree'), I('agree')],
          'TD-09': [I('offer', x_date='tomorrow'), I('agree')], 'TD-10': [I('restructuring')], 'TD-11': [I('agree'), I('agree')]},
    'e': {'TE-01': [I('offer', x_date='Friday'), I('agree')], 'TE-02': [I('offer', x_date='1 December'), I('agree')],
          'TE-03': [I('offer', x_date='27 November'), I('agree'), I('agree')],
          'TE-04': [I('dispute', x_product='card'), I('offer', x_date='today'), I('agree')], 'TE-05': 'identity',
          'TE-06': [I('restructuring')], 'TE-07': [I('offer', x_date='Thursday'), I('agree')],
          'TE-08': [TP('other'), TP('gives_time', 'tomorrow', 'nine in the morning')], 'TE-09': [TP('deceased')]},
    'f': {'TF-01': [I('agree'), I('agree')],
          'TF-02': [TP('other'), TP('gives_time', 'tomorrow', 'eight forty-five in the morning')],
          'TF-03': 'identity',
          'TF-04': [I('hardship'), I('refuse')],
          'TF-05': [I('offer', x_date='Wednesday 16 December'), I('offer', x_amount='72', x_date='Wednesday 16 December'), I('agree'), I('agree')],
          'TF-06': [I('refuse'), I('refuse'), I('refuse')],
          'TF-08': [I('restructuring')]},
    'g': {'TG-01': [I('agree'), I('agree')],
          'TG-02': [TP('other'), TP('gives_time', 'tomorrow', 'eleven fifteen in the morning')],
          'TG-03': 'identity',
          'TG-04': [I('hardship'), I('refuse')],
          'TG-05': [I('offer', x_date='Wednesday 20 January'), I('offer', x_amount='72', x_date='Wednesday 20 January'), I('agree'), I('agree')],
          'TG-06': [I('offer', x_date='tomorrow', x_product='card'), I('agree'), I('refuse'), I('refuse'), I('refuse'), I('agree')],
          'TG-08': [I('restructuring')]},
    'h': {'TH-01': [I('agree'), I('agree')],
          'TH-02': [TP('other'), TP('gives_time', 'tomorrow', 'nine forty-five in the morning')],
          'TH-03': 'identity',
          'TH-04': [I('hardship'), I('refuse')],
          'TH-05': [I('offer', x_date='Wednesday 10 February'), I('offer', x_amount='72', x_date='Wednesday 10 February'), I('agree'), I('agree')],
          'TH-06': [I('offer', x_date='tomorrow', x_product='card'), I('refuse'), I('refuse'), I('agree')],
          'TH-08': [I('restructuring')]}
}


def run_set(name, spec, api, cases, scen, verbose):
    bad = 0
    for c in cases:
        steps = scen.get(c['id'])
        if steps is None:
            continue
        if steps == 'identity':
            c = dict(c, wrong_script=WRONG[c['id']])
            steps = []
        try:
            r = drive(spec, c, steps, verbose=verbose, api=api, cases=cases)
            ok, why = r['pass'], r['failed']
        except Exception as e:
            ok, why = False, [repr(e)]
        print('PASS' if ok else 'FAIL', name, c['id'], c['title'], '' if ok else why)
        bad += not ok
    return bad


if __name__ == '__main__':
    v = '-v' in sys.argv
    bad = run_set('AB', load('builder/specs/brief-ab.spec.json'), API, [c for c in CASES if c['brief'] == 'B'], SCEN, v)
    bad += run_set('A', load('builder/specs/brief-a.spec.json'), API, [c for c in CASES if c['brief'] == 'A'], SCEN, v)
    for x, scen in VARIANTS.items():
        p = 'out/e2e/brief-%s.spec.json' % x
        cands = [p, 'builder/specs/brief-%s.spec.json' % x, 'out/brief-%s.spec.json' % x, 'out/%s.spec.json' % x]
        found = next((c for c in cands if os.path.exists(os.path.join(ROOT, c))), None)
        if found is None:       # generated specs of the variant briefs live under out/ (gitignored): skip them on a fresh clone
            print('SKIP %s: no saved spec (%s)' % (x.upper(), ', '.join(cands)))
            continue
        spec = load(found)
        bad += run_set(x.upper(), spec, load('test-briefs/tools-%s.openapi.json' % x), load('test-briefs/cases-%s.json' % x), scen, v)
    sys.exit(1 if bad else 0)
