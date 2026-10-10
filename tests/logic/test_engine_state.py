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
        for t in ('150,50', '-150', 'minus fifty', '150 to 200', '150-200', '150 and fifty pence', '150p'):
            self.assertEqual(ac(t)[0], 'unclear', t)
            self.assertIsNone(self.ns['free_amount'](t), t)
        self.assertEqual(ac('one hundred and fifty'), ('ok', 150.0))
        self.assertEqual(ac('1,500'), ('ok', 1500.0))
        self.assertEqual(ac('150.50'), ('ok', 150.5))
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


if __name__ == '__main__':
    unittest.main()
