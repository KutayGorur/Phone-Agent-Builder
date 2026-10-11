"""Floor rounding and greater-of floors (briefs I and J). Offline.

    python tests/logic/test_floor_rounding.py
"""
import json
import os
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, ROOT)

from builder.generate.ecfg import blocking_warnings, build_E_warn, parse_rounding  # noqa: E402
from builder.generate.generate import engine_code  # noqa: E402


def fixture(n):
    with open(os.path.join(ROOT, 'tests', 'fixtures', 'spec-%s-fresh.json' % n), encoding='utf-8') as f:
        return json.load(f)


def floor_in_engine(E, raw):
    """Run the compiled engine's floor_for on one product."""
    ns = {'vars': {'now': '2026-10-14T11:00', 'st': ''}}
    exec(compile(engine_code(E), 'engine', 'exec'), ns)
    return ns['floor_for'](raw)


class Parse(unittest.TestCase):
    def test_spellings(self):
        cases = [
            ('round up to a whole krone', ('up', 1)), ('rounded UP to the next 100 yen', ('up', 100)),
            ('to the nearest cent', ('nearest', 0.01)), ('round down to the nearest 10', ('down', 10)),
            ({'round_up_to': 100}, ('up', 100)), ({'mode': 'up', 'to': 5}, ('up', 5)), ({'mode': 'nearest', 'to': 0.05}, ('nearest', 0.05)),
            (50, ('up', 50)),
        ]
        for v, (mode, to) in cases:
            r = parse_rounding(v)
            self.assertEqual((r['mode'], r['to']), (mode, to), v)

    def test_unreadable_is_none(self):
        for v in (None, False, 'say the rest stays overdue', {'x': 1}, 0, -5):
            self.assertIsNone(parse_rounding(v), v)


class Engine(unittest.TestCase):
    def test_brief_i_overdraft_floor_is_rounded_up_to_a_krone(self):
        E, warns = build_E_warn(fixture('i'))
        self.assertEqual(E['formula']['overdraft']['round'], {'mode': 'up', 'to': 1.0})
        self.assertEqual(floor_in_engine(E, {'type': 'overdraft', 'arrears_nok': 1250.5, 'days_past_due': 4}), 251.0)   # 20% = 250.10
        self.assertEqual(floor_in_engine(E, {'type': 'overdraft', 'arrears_nok': 1255.0, 'days_past_due': 4}), 251.0)   # exact 251.00 stays
        self.assertEqual(blocking_warnings(warns), [])

    def test_brief_j_card_floor_is_the_greater_of_minimum_and_ten_percent_rounded_up_to_100(self):
        E, _ = build_E_warn(fixture('j'))
        f = lambda out, mn: floor_in_engine(E, {'type': 'card_revolving', 'outstanding_jpy': out, 'minimum_due': mn, 'overdue_days': 5})
        self.assertEqual(f(184300, 5000), 18500)        # 18430 -> 18500
        self.assertEqual(f(184300, 20000), 20000)       # the minimum is greater, and already a multiple of 100
        self.assertEqual(f(184300, 18450), 18500)       # the greater of the two, then rounded

    def test_unreadable_rounding_text_is_blocking(self):
        s = fixture('i')
        s['amounts']['floor_rounding'] = 'round it sensibly'
        _, warns = build_E_warn(s)
        self.assertTrue([w for w in blocking_warnings(warns) if 'rounding' in w])


if __name__ == '__main__':
    unittest.main()
