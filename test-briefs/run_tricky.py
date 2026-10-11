"""Offline runner for the tricky practice briefs (I, J, ...): scripted customers through the compiled engine and the
in-process stand-in bank. No Freya calls, no model calls.

    python3 test-briefs/run_tricky.py i out/brief-i.spec.json [-v] [--only TI-01]

Scripts live here (not in builder/generate/local_sim.py). Identity normalisation checks run the generated pre_process hooks."""
import json, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, 'tools'))
from builder.generate import local_sim as L
from builder.generate.generate import generate
from harness.mock_bank import Bank
I, TP = L.I, L.TP

SCEN = {
 'i': {
  'TI-01': [I('refuse'), I('offer', x_date='Thursday 1 April'), I('offer', x_date='Thursday 1 April'), I('agree'), I('offer', x_date='Thursday 1 April'), I('agree')],
  'TI-02': [TP('other'), TP('gives_time', 'today', 'quarter to six in the evening'), TP('gives_time', 'tomorrow', 'half past five in the evening')],
  'TI-03': 'identity',
  'TI-05': [I('offer', x_amount='200', x_date='1 April'), I('agree'), I('agree')],
  'TI-06': [I('offer', x_date='Thursday 15 April'), I('agree'), I('agree')],
  'TI-07': [TP('other'), TP('gives_time', 'tomorrow', 'ten in the morning'), TP('gives_time', 'Tuesday 30 March', 'ten in the morning')],
  'TI-08': [I('dispute', x_product='overdraft'), I('offer', x_date='today'), I('agree')],
  'TI-09': [I('already_paid')],
  'TI-10': [I('agree'), I('agree')],
  'TI-11': [I('restructuring')],
  'TI-12': ('cycle', [I('refuse')]),
 },
 'j': {
  'TJ-01': [I('offer', x_amount='10000', x_date='Saturday 1 May'), I('agree'), I('agree')],
  'TJ-02': [I('offer', x_date='Thursday 29 April'), I('agree'), I('agree')],
  'TJ-03': [I('offer', x_date='Sunday 2 May'), I('agree'), I('agree')],
  'TJ-04': [TP('other'), TP('gives_time', 'Saturday 1 May', 'ten in the morning'), TP('gives_time', 'Friday 30 April', 'seven in the evening')],
  'TJ-05': 'identity',
  'TJ-06': [I('refuse'), I('refuse'), I('agree'), I('agree')],
  'TJ-07': [I('offer', x_date='Friday 7 May'), I('agree')],
  'TJ-08': ('cycle', [I('refuse')]),
  'TJ-09': [I('restructuring')],
  'TJ-10': [I('agree'), I('agree')],
  'TJ-11': [I('already_paid', x_product='card'), I('offer', x_date='today'), I('agree')],
  'TJ-12': [I('already_paid')],
 },
}
WRONG = {
 'TI-03': [('date_of_birth', '12 July 1991'), ('date_of_birth', '21 August 1992'), ('national_id_last5', '11111'), ('national_id_last5', '22222')],
 'TJ-05': [('mobile_last4', '1111'), ('mobile_last4', '2222'), ('mobile_last4', '3333')],
}
# natural answer -> expected value sent to verify_identity (the hook must normalise; checked against the case truth)
NORM = {
 'i': [('date_of_birth', '4 March 1987', '1987-03-04'), ('date_of_birth', '04.03.87', '1987-03-04'),
       ('national_id_last5', '00417', '00417'), ('national_id_last5', 'zero zero four one seven', '00417'),
       ('home_town', 'Tromsø', 'tromso'), ('home_town', 'Ålesund', 'alesund'), ('home_town', 'Sør-Varanger', 'sorvaranger'), ('home_town', 'Tønsberg', 'tonsberg')],
 'j': [('date_of_birth', '1985/04/09', '1985-04-09'), ('date_of_birth', '9 April 1985', '1985-04-09'), ('mobile_last4', '0482', '0482')],
}


def run_set(name, spec, api, cases, scen, verbose):
    """Like local_sim.run_set; a script may be ('cycle', steps): the customer repeats the last step until the call closes."""
    bad = 0
    for c in cases:
        steps = scen.get(c['id'])
        if steps is None:
            continue
        cycle = isinstance(steps, tuple)
        if cycle:
            steps = steps[1]
        if steps == 'identity':
            c = dict(c, wrong_script=WRONG[c['id']])
            steps = []
        try:
            r = L.drive(spec, c, steps, verbose=verbose, api=api, cases=cases, cycle=cycle)
            ok, why = r['pass'], r['failed']
        except Exception as e:
            ok, why = False, [repr(e)]
        print('PASS' if ok else 'FAIL', name, c['id'], c['title'], '' if ok else why)
        bad += not ok
    return bad


def norm_check(tag, spec):
    wf = generate(spec)
    qs = spec['identity']['questions']
    bad = 0
    for field, said, want in NORM[tag]:
        qi = [i for i, q in enumerate(qs, 1) if q['field'] == field][0]
        fn = wf['nodes']['idq_%d' % qi]['tools'][0]
        cfg = {'body': {'answer': said, 'field': field}}
        try:
            exec(fn['pre_process_code'], {'config': cfg, 'vars': {'now': '2027-03-22T09:30'}})
            got = cfg['body']['answer']
        except Exception as e:
            got = repr(e)
        ok = got == want
        bad += not ok
        print('PASS' if ok else 'FAIL', 'norm', field, repr(said), '->', repr(got), '' if ok else 'expected %r' % want)
    return bad


def main():
    tag, specp = sys.argv[1], sys.argv[2]
    v = '-v' in sys.argv
    only = sys.argv[sys.argv.index('--only') + 1] if '--only' in sys.argv else None
    spec = json.load(open(specp, encoding='utf-8'))
    api = json.load(open(os.path.join(ROOT, 'test-briefs/tools-%s.openapi.json' % tag)))
    cases = json.load(open(os.path.join(ROOT, 'test-briefs/cases-%s.json' % tag)))
    if '--alias-amount' in sys.argv:     # models the compiler honouring per-product amount fields: copy arrears_nok -> amount_due
        for c in cases:
            for pr in c['products']:
                if 'arrears_nok' in pr:
                    pr['amount_due'] = pr['arrears_nok']
    L.WRONG.update(WRONG)
    scen = {k: val for k, val in SCEN[tag].items() if not only or k == only}
    bad = run_set(tag.upper(), spec, api, cases, scen, v)
    if not only:
        bad += norm_check(tag, spec)
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
