"""Local engine test: scripted customer extractions + the in-process stand-in bank + the real scorer. No Freya calls.

    python -m builder.generate.local_sim            # every scenario below, asserts bank records == expected
"""
import json, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, 'tools'))
from builder.generate.ecfg import build_E
from builder.generate.generate import engine_code
from harness.mock_bank import Bank
from score import score_ledger

API = json.load(open(os.path.join(ROOT, 'tools', 'openapi.json')))
CASES = json.load(open(os.path.join(ROOT, 'public-test-set.json')))


def drive(spec, case, steps, verbose=False):
    """steps: list of dicts of extraction vars (x_intent, x_date, ...) or tp vars, one per customer turn."""
    code = engine_code(build_E(spec))
    bank = Bank(API, CASES)
    sess = bank.new_session(case['id'])['variables']
    cid = sess['customer_id']
    v = {'now': sess['now'], 'st': '', 'customer_id': cid}
    def tool(name, body):
        s, r = bank.tool(name, dict(body, customer_id=cid)); return s, r
    third_party = case['family'] == 'Third party'
    if not third_party:
        for f, a in case['identity'].items():
            tool('verify_identity', {'field': f, 'answer': a})
        s, r = tool('get_account', {})
        for i, p in enumerate(r['products']):
            for k, x in p.items(): v['get_account_response.data.products.%d.%s' % (i, k)] = str(x)
    else:
        v['st'] = json.dumps({'phase': 'tp'})
    def engine():
        ns = {'vars': v}; exec(compile(code, '<engine>', 'exec'), ns)
        if v.get('engine_err'): raise RuntimeError(v['engine_err'])
        r = v.get('route')
        if verbose: print('   route=%s %s' % (r, (v.get('instruction') or '')[-200:] if r in ('say', 'tp_say') else ''))
        return r
    def follow(r):
        for _ in range(30):
            if r == 'create':
                s, res = tool('create_promise', {'product_id': v['cp_pid'], 'amount': float(v['cp_amount']), 'date': v['cp_date']}); v['cp_ok'] = str(bool(res.get('ok'))).lower()
            elif r == 'note':
                s, res = tool('add_note', {'product_id': v['nt_pid'], 'reason': v['nt_reason']}); v['nt_ok'] = str(bool(res.get('ok'))).lower()
            elif r == 'transfer':
                tool('transfer_to_agent', {'queue': v['tr_queue']})
            elif r == 'callback':
                s, res = tool('schedule_callback', {'date': v['cb_date'], 'time': v['cb_time']}); v['cb_ok'] = str(bool(res.get('ok'))).lower()
            elif r == 'fin':
                body = {'outcome': v['close_outcome']}
                if v.get('close_reason'): body['reason'] = v['close_reason']
                tool('close_call', body); return 'closed'
            else:
                return r
            r = engine()
        raise RuntimeError('route loop')
    if not third_party:
        r = follow(engine())          # plan
    else:
        r = 'say'
    for s in steps:
        if r == 'closed': raise RuntimeError('steps left after close: %s' % s)
        v.update(s)
        if verbose: print('>>', s)
        r = follow(engine())
    if r != 'closed': raise RuntimeError('not closed, last route %s' % r)
    return score_ledger(case, bank.ledger(cid))


I = lambda i, **k: dict(x_intent=i, **k)
SCEN = {
    'PUB-01': [I('agree'), I('agree')],
    'PUB-02': [dict(tp_event='other'), dict(tp_event='gives_time', tp_date='tomorrow', tp_time='eleven in the morning')],
    'PUB-04': [I('offer', x_date='6 November'), I('agree'), I('question'), I('agree')],
    'PUB-05': [I('hardship'), I('question'), I('refuse')],
    'PUB-06': [I('too_much'), I('agree'), I('agree')],
    'PUB-07': [I('refuse'), I('offer', x_date='the week after next'), I('offer', x_date='Monday the 26th'), I('agree'), I('agree')],
    'PUB-08': [I('already_paid')],
    'PUB-09': [I('restructuring')],
    'PUB-10': [I('refuse'), I('agree'), I('agree')],
    'PUB-11': [I('refuse'), I('offer', x_date='this Friday'), I('agree'), I('agree'), I('agree')],
    'PUB-12': [I('refuse'), I('offer', x_date='tomorrow'), I('refuse'), I('refuse'), I('refuse'), I('agree')],
    'PUB-13': [I('offer', x_date='30 October'), I('agree')],
}

if __name__ == '__main__':
    A = json.load(open(os.path.join(ROOT, 'builder/specs/brief-a.spec.json'))); AB = json.load(open(os.path.join(ROOT, 'builder/specs/brief-ab.spec.json')))
    bad = 0
    for c in CASES:
        steps = SCEN.get(c['id'])
        if steps is None: continue
        try:
            r = drive(AB if c['brief'] == 'B' else A, c, steps, verbose='-v' in sys.argv)
            ok, why = r['pass'], r['failed']
        except Exception as e:
            ok, why = False, [repr(e)]
        print('PASS' if ok else 'FAIL', c['id'], c['title'], '' if ok else why); bad += not ok
    sys.exit(1 if bad else 0)
