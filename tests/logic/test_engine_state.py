"""Engine state and parsing fixes (Task 10, ACC-01..27). Probe pattern: build the engine code, set the extraction
variables by hand, assert on what the bank would see (route, tool variables, spoken text). No model, no Freya.

    python tests/logic/test_engine_state.py
"""
import datetime
import json
import os
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from builder.generate.ecfg import build_E  # noqa: E402
from builder.generate.generate import engine_code  # noqa: E402

NOW = '2026-10-14T11:00'          # Wednesday
D = datetime.date


def spec(name):
    return json.load(open(os.path.join(ROOT, 'builder', 'specs', 'brief-%s.spec.json' % name), encoding='utf-8'))


def ns_for(name='ab'):
    """The engine namespace (helpers included) with the clock set; main() ran once on empty state."""
    ns = {'vars': {'now': NOW, 'st': ''}}
    exec(compile(engine_code(build_E(spec(name))), '<engine>', 'exec'), ns)
    return ns


PERSONAL = {'product_id': 'p1', 'type': 'personal_loan', 'past_due': '300.0', 'days_late': '3', 'instalment_amount': '150.0'}
CAR = {'product_id': 'p2', 'type': 'car_loan', 'past_due': '500.0', 'days_late': '3', 'instalment_amount': '250.0'}


class Probe:
    def __init__(self, name='ab', products=(PERSONAL, CAR), now=NOW):
        self.code = engine_code(build_E(spec(name)))
        self.v = {'now': now, 'st': ''}
        for i, p in enumerate(products):
            for k, x in p.items():
                self.v['get_account_response.data.products.%d.%s' % (i, k)] = x
        self.run()                                   # plan turn

    def run(self):
        exec(compile(self.code, '<engine>', 'exec'), {'vars': self.v})
        assert not self.v.get('engine_err'), self.v.get('engine_err')
        return self

    def say(self, intent='none', date='', amount='', product='', q='no', **more):
        self.v.update(x_intent=intent, x_date=date, x_amount=amount, x_product=product, x_q=q, **more)
        return self.run()

    @property
    def st(self):
        return json.loads(self.v['st'])

    @property
    def text(self):
        return self.v.get('say_text') or self.v.get('instruction') or ''

    def prod(self, i):
        return self.st['prods'][i]

    def create(self, ok=True):
        """Play one create_promise round trip; returns (pid, amount, date)."""
        assert self.v['route'] == 'create', self.v['route']
        got = (self.v['cp_pid'], self.v['cp_amount'], self.v['cp_date'])
        self.v['cp_ok'] = 'true' if ok else 'false'
        self.run()
        return got


class Parsing(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ns = ns_for()
        cls.today = D(2026, 10, 14)

    def date(self, text):
        return self.ns['free_date'](text, self.today)

    def test_acc22_explicit_dmy_before_digitize(self):
        self.assertEqual(self.date('23/11/2026'), ('date', D(2026, 11, 23)))
        self.assertEqual(self.date('11/06/2026'), ('date', D(2026, 6, 11)))
        self.assertEqual(self.date('23.10.2026'), ('date', D(2026, 10, 23)))
        self.assertEqual(self.date('23-11-2026'), ('date', D(2026, 11, 23)))

    def test_acc22_n_days_from_now(self):
        self.assertEqual(self.date('two days from now'), ('date', D(2026, 10, 16)))
        self.assertEqual(self.date('one week from today'), ('date', D(2026, 10, 21)))
        self.assertEqual(self.date('in two days'), ('date', D(2026, 10, 16)))
        self.assertEqual(self.date('3 days from today'), ('date', D(2026, 10, 17)))

    def test_acc13_unclear_amounts_are_not_picked(self):
        ac = self.ns['amount_check']
        for t in ('150,50', '-150', 'minus fifty', '150 to 200', '150-200', 'fifty pence', '150p'):
            self.assertEqual(ac(t)[0], 'unclear', t)
            self.assertIsNone(self.ns['free_amount'](t), t)
        self.assertEqual(ac('one hundred and fifty'), ('ok', 150.0))
        self.assertEqual(ac('1,500'), ('ok', 1500.0))
        self.assertEqual(ac('150.50'), ('ok', 150.5))
        self.assertEqual(ac('150 and fifty pence'), ('ok', 150.5))
        self.assertEqual(ac('£150'), ('ok', 150.0))

    def test_acc13_engine_asks_again(self):
        p = Probe()
        p.say('offer', amount='150 to 200')
        self.assertEqual(p.v['route'], 'say')
        self.assertIn('did not catch the amount', p.text)
        self.assertNotEqual(p.st['phase'], 'confirm')

    def test_acc23_24h_time_is_not_moved_to_evening(self):
        ft = self.ns['free_time']
        self.assertEqual(ft('07:00'), [420])
        self.assertEqual(ft('0700'), [420])
        self.assertEqual(ft('7 am'), [420])
        self.assertEqual(ft('7:00'), [420, 1140])      # unmarked 7 stays ambiguous
        self.assertEqual(ft('19:00'), [1140])

    def test_acc23_third_party_07_00_is_reasked(self):
        v = {'now': NOW, 'st': json.dumps({'phase': 'tp'}), 'tp_event': 'callback', 'tp_date': 'tomorrow', 'tp_time': '07:00'}
        exec(compile(engine_code(build_E(spec('ab'))), '<engine>', 'exec'), {'vars': v})
        self.assertEqual(v['route'], 'tp_say')
        self.assertNotIn('cb_date', v)


class Scope(unittest.TestCase):
    def test_acc02_unique_match(self):
        ns = ns_for()
        st = {'all': False, 'cur': 0, 'prods': [
            {'i': 0, 'type': 'personal_loan', 'label': 'personal loan', 'status': 'open'},
            {'i': 1, 'type': 'car_loan', 'label': 'car loan', 'status': 'open'}]}
        t = ns['target_products']
        kind, ps = t(st, 'car loan')
        self.assertEqual((kind, [x['i'] for x in ps]), ('one', [1]))
        kind, ps = t(st, 'the personal loan please')
        self.assertEqual((kind, [x['i'] for x in ps]), ('one', [0]))
        self.assertEqual(t(st, 'loan')[0], 'ambig')
        self.assertEqual(t(st, 'both')[0], 'all')
        self.assertEqual(t(st, '')[0], 'none')

    def test_acc02_ambiguous_name_asks(self):
        p = Probe().say('refuse')
        before = json.dumps(p.st['prods'])
        p.say('offer', date='tomorrow', amount='250', product='loan')
        self.assertEqual(p.v['route'], 'say')
        self.assertIn('Which one do you mean', p.text)
        self.assertEqual(json.dumps(p.st['prods']), before)

    def test_acc20_named_product_gets_the_offer(self):
        p = Probe().say('refuse')                                       # product 1 (personal loan) in play
        p.say('offer', date='tomorrow', amount='250', product='car loan')
        self.assertEqual(p.prod(1)['status'], 'agreed')
        self.assertEqual((p.prod(1)['amt'], p.prod(1)['date']), (250.0, '2026-10-15'))
        self.assertNotEqual(p.prod(0)['status'], 'agreed')

    def test_acc03_all_correction_moves_every_product(self):
        p = Probe().say('agree')                                         # both at full amount today
        self.assertEqual(p.st['phase'], 'confirm')
        p.say('change', date='friday', product='all')
        self.assertEqual([x['date'] for x in p.st['prods']], ['2026-10-16', '2026-10-16'])
        self.assertEqual([x['amt'] for x in p.st['prods']], [300.0, 500.0])
        self.assertEqual(p.st['phase'], 'confirm')

    def test_acc04_all_with_amount_and_date_asks_which_account(self):
        p = Probe().say('offer', date='tomorrow', amount='150', product='all')
        self.assertEqual(p.v['route'], 'say')
        self.assertIn('Which account', p.text)
        self.assertEqual([x['status'] for x in p.st['prods']], ['open', 'open'])
        p.say('offer', amount='250', product='car loan')                 # the date given earlier is not lost
        self.assertEqual((p.prod(1)['amt'], p.prod(1)['date']), (250.0, '2026-10-15'))

    def test_acc04_amount_and_date_without_scope_are_both_kept(self):
        p = Probe().say('offer', date='tomorrow', amount='200')
        self.assertEqual((p.prod(0)['amt'], p.prod(0)['date']), (200.0, '2026-10-15'))


class ProposalState(unittest.TestCase):
    def test_acc01_amount_then_date(self):
        p = Probe().say('refuse')
        p.say('offer', amount='200')
        self.assertEqual(p.prod(0)['pend']['a'], 200.0)
        p.say('offer', date='tomorrow')
        self.assertEqual((p.prod(0)['amt'], p.prod(0)['date']), (200.0, '2026-10-15'))

    def _readback(self):
        p = Probe().say('offer', date='friday', amount='200', product='personal loan')
        p.say('offer', date='friday', amount='400', product='car loan')
        self.assertEqual(p.st['phase'], 'confirm')
        return p

    def test_acc01_readback_amount_only_keeps_date(self):
        p = self._readback()
        p.say('change', amount='450', product='car loan')
        self.assertEqual((p.prod(1)['amt'], p.prod(1)['date']), (450.0, '2026-10-16'))

    def test_acc01_readback_date_only_keeps_amount(self):
        p = self._readback()
        p.say('change', date='tomorrow', product='car loan')
        self.assertEqual((p.prod(1)['amt'], p.prod(1)['date']), (400.0, '2026-10-15'))

    def test_acc09_hardship_with_offer_is_kept_after_declining_support(self):
        p = Probe().say('refuse')
        p.say('sp_hardship', date='tomorrow', amount='200')
        self.assertTrue(p.st.get('hard_pending'))
        p.say('refuse')                                                  # no thanks to the support team
        self.assertEqual((p.prod(0)['status'], p.prod(0)['amt'], p.prod(0)['date']), ('agreed', 200.0, '2026-10-15'))

    def test_acc10_callback_day_kept_across_turns(self):
        v = {'now': NOW, 'st': json.dumps({'phase': 'tp'}), 'tp_event': 'callback', 'tp_date': 'tomorrow', 'tp_time': ''}
        code = engine_code(build_E(spec('ab')))
        exec(compile(code, '<engine>', 'exec'), {'vars': v})
        self.assertEqual(v['route'], 'tp_say')
        v.update(tp_event='callback', tp_date='', tp_time='three pm')
        exec(compile(code, '<engine>', 'exec'), {'vars': v})
        self.assertEqual((v.get('route'), v.get('cb_date'), v.get('cb_time')), ('callback', '2026-10-15', '15:00'))

    def test_acc19_stop_at_readback_notes_agreed_products(self):
        p = Probe().say('agree')
        self.assertEqual(p.st['phase'], 'confirm')
        p.say('sp_does_not_want_to_talk')
        p.say('sp_does_not_want_to_talk')
        seen = []
        for _ in range(4):
            if p.v['route'] != 'note':
                break
            seen.append((p.v['nt_pid'], p.v['nt_reason']))
            p.v['nt_ok'] = 'true'
            p.run()
        self.assertEqual(seen, [('p1', 'refused'), ('p2', 'refused')])
        self.assertEqual(p.v['route'], 'fin')


if __name__ == '__main__':
    unittest.main()
