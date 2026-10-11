"""Spoken amounts follow the brief's currency wording; the tool body keeps the plain number; labels with an article read right. Offline.

    python tests/logic/test_spoken_amounts.py
"""
import json
import os
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, ROOT)

from builder.generate.ecfg import build_E_warn  # noqa: E402
from builder.generate.generate import engine_code  # noqa: E402


def engine(n):
    with open(os.path.join(ROOT, 'tests', 'fixtures', 'spec-%s-fresh.json' % n), encoding='utf-8') as f:
        spec = json.load(f)
    E, _ = build_E_warn(spec)
    ns = {'vars': {'now': '2026-10-14T11:00', 'st': ''}}
    exec(compile(engine_code(E), 'engine', 'exec'), ns)
    return E, ns


class Spoken(unittest.TestCase):
    def test_brief_i_kroner_and_ore(self):
        E, ns = engine('i')
        say = ns['say_money']
        self.assertEqual(say(1250.5), '1 250 kroner and 50 ore')
        self.assertEqual(say(1250), '1 250 kroner')
        self.assertEqual(say(251), '251 kroner')
        self.assertEqual(ns['money'](1250.5), '1250.50')                # the bank still gets a plain number

    def test_brief_j_whole_yen_never_sen(self):
        E, ns = engine('j')
        self.assertEqual(ns['say_money'](184300), '184300 yen')
        self.assertEqual(ns['say_money'](18430.0), '18430 yen')
        self.assertEqual(ns['say_money'](18430.4), '18431 yen')         # never lower than the real amount
        self.assertEqual(E['pd_word'], 'outstanding')

    def test_no_currency_in_the_spec_keeps_two_decimals(self):
        with open(os.path.join(ROOT, 'builder', 'specs', 'brief-a.spec.json'), encoding='utf-8') as f:
            spec = json.load(f)
        E, _ = build_E_warn(spec)
        self.assertIsNone(E['money'])
        ns = {'vars': {'now': '2026-10-14T11:00', 'st': ''}}
        exec(compile(engine_code(E), 'engine', 'exec'), ns)
        self.assertEqual(ns['say_money'](2125.1), '2125.10')

    def test_labels_with_an_article(self):
        E, ns = engine('j')
        self.assertEqual(ns['plain_label']('a revolving card'), 'revolving card')
        self.assertEqual(ns['plain_label']('an auto loan'), 'auto loan')
        self.assertEqual(ns['plain_label']('credit line ending 1234'), 'credit line ending 1234')

    def test_the_statement_has_no_double_article(self):
        from builder.generate import local_sim as L
        with open(os.path.join(ROOT, 'tests', 'fixtures', 'spec-j-fresh.json'), encoding='utf-8') as f:
            spec = json.load(f)
        with open(os.path.join(ROOT, 'test-briefs', 'tools-j.openapi.json'), encoding='utf-8') as f:
            api = json.load(f)
        with open(os.path.join(ROOT, 'test-briefs', 'cases-j.json'), encoding='utf-8') as f:
            cases = json.load(f)
        said = []
        L.drive(spec, next(c for c in cases if c['id'] == 'TJ-10'), [L.I('agree'), L.I('agree')], api=api, cases=cases, said=said, raw=True, cycle=True)
        text = ' '.join(said)
        self.assertNotIn('Your a ', text)
        self.assertNotIn('Your an ', text)
        self.assertIn(' yen', text)
        self.assertNotRegex(text, r'\d+\.\d\d yen')


if __name__ == '__main__':
    unittest.main()
