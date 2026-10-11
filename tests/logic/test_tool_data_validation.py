"""Malformed tool data must not become a spoken amount or a policy-band choice."""
import copy
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_engine_state import Probe, PERSONAL, CAR, spec, build_E, engine_code
from builder.generate.generate import generate
from ci.lint_workflow import lint


class ToolNumbers(unittest.TestCase):
    def test_nonfinite_and_boolean_floor_never_become_an_offer(self):
        for bad in ('NaN', 'Infinity', '-Infinity', '1e999', True, False):
            with self.subTest(bad=bad):
                p = Probe('a', products=(dict(PERSONAL, instalment_amount=bad),))
                self.assertEqual(p.prod(0)['fl'], 300.0)
                p.say('too_much')
                self.assertNotIn('nan', p.text.lower())
                self.assertNotIn('inf', p.text.lower())
                self.assertEqual(p.prod(0)['pend']['a'], 300.0)

    def test_invalid_balance_does_not_create_an_account(self):
        for bad in (True, False, 'NaN', 'Infinity', '-1'):
            with self.subTest(bad=bad):
                p = Probe('ab', products=(dict(PERSONAL, past_due=bad), CAR))
                self.assertEqual([product['id'] for product in p.st['prods']], ['p2'])

    def test_days_must_be_nonnegative_finite_integer(self):
        for bad in ('7.9', '-0.5', True, False, 'NaN', 'Infinity'):
            with self.subTest(bad=bad):
                p = Probe('ab', products=(dict(PERSONAL, days_late=bad), CAR))
                self.assertEqual([product['id'] for product in p.st['prods']], ['p2'])
        p = Probe('a', products=(dict(PERSONAL, days_late='8.0'),))
        self.assertEqual((p.prod(0)['dl'], p.prod(0)['band']), (8, 'late'))

    def test_boolean_product_id_is_not_a_record_identifier(self):
        p = Probe('ab', products=(dict(PERSONAL, product_id=True), CAR))
        self.assertEqual([product['id'] for product in p.st['prods']], ['p2'])

    def test_greater_of_and_formula_require_finite_values(self):
        E = build_E(spec('a'))
        E['floor_field'] = {}
        E['formula'] = {'personal_loan': {'field': 'past_due', 'percent_of_field': 20, 'greater_of': 'instalment_amount'}}
        ns = {'vars': {'st': '', 'now': '2026-10-14T11:00'}}
        exec(engine_code(E), ns)
        self.assertIsNone(ns['floor_for'](dict(PERSONAL, instalment_amount='NaN')))
        self.assertEqual(ns['floor_for'](PERSONAL), 150.0)
        E['formula']['personal_loan']['percent_of_field'] = True
        exec(engine_code(E), ns)
        self.assertIsNone(ns['floor_for'](PERSONAL))


class ExtractionSchema(unittest.TestCase):
    def test_duplicate_field_fails_lint_before_platform_use(self):
        w = generate(spec('a'))
        node = w['nodes']['say_fixed']
        node['extraction_schema'].append(copy.deepcopy(node['extraction_schema'][0]))
        self.assertTrue(any('duplicate extraction' in e for e in lint(w)[0]))

    def test_malformed_or_empty_field_names_fail_lint(self):
        for field in ({'name': ''}, {'name': 42}, 'x_security'):
            w = generate(spec('a'))
            w['nodes']['opening']['extraction_schema'].append(field)
            self.assertTrue(any('extraction fields' in e for e in lint(w)[0]))

    def test_all_generated_schemas_are_unique(self):
        for name in ('a', 'ab', 'f', 'g', 'h'):
            self.assertFalse(lint(generate(spec(name)))[0], name)


if __name__ == '__main__':
    unittest.main()
