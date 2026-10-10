"""Parser variance the compiler must absorb (found in the fresh-clone run: D TD-03 floor 480 instead of 120, E TE-04 closed
after a dispute). The fact is the same, only the spelling in the spec differs. No Freya calls, no model calls."""
import copy
import json
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

from builder.generate import ecfg, local_sim as ls  # noqa: E402


def load(path):
    with open(os.path.join(ROOT, path), encoding='utf-8') as f:
        return json.load(f)


class Formula(unittest.TestCase):
    def test_shapes_all_mean_25_percent_of_arrears(self):
        for v in ({'field': 'arrears', 'percent_of_field': 25}, {'field': 'arrears', 'percent': 25}, {'of': 'arrears', 'percentage': 25},
                  {'field': 'arrears', 'fraction': 0.25}, '25% of arrears', '25 percent of the arrears', {'percent': 25}):
            r = ecfg._formula(v, 'arrears', {'arrears', 'days_past_due'})
            self.assertEqual(r, {'field': 'arrears', 'percent_of_field': 25.0}, v)

    def test_not_a_formula(self):
        for v in ('minimum_payment', {'field': 'x'}, '', None, 0, 150):
            self.assertIsNone(ecfg._formula(v, 'arrears', {'arrears'}), v)

    def test_unknown_base_field_falls_back_to_past_due(self):
        self.assertEqual(ecfg._formula('25% of the overdue amount', 'arrears', {'arrears'})['field'], 'arrears')

    def test_floor_rules_move_percentages_out_of_floor_field(self):
        ff, fm = ecfg.floor_rules({'floor_field_by_product': {'card': 'minimum_payment', 'overdraft': '25% of arrears'}}, 'arrears', {'arrears', 'minimum_payment'})
        self.assertEqual(ff, {'card': 'minimum_payment'})
        self.assertEqual(fm, {'overdraft': {'field': 'arrears', 'percent_of_field': 25.0}})
        ff, fm = ecfg.floor_rules({'floor_percent_by_product': {'overdraft': 25}}, 'arrears', None)
        self.assertEqual(fm['overdraft']['percent_of_field'], 25.0)

    def test_engine_uses_the_floor_whatever_the_spelling(self):
        for shape in ({'car_loan': {'field': 'past_due', 'percent_of_field': 25}}, {'car_loan': '25% of past_due'}, {'car_loan': {'percent': 25}}):
            spec = copy.deepcopy(load('builder/specs/brief-a.spec.json'))
            spec['amounts'].pop('floor_formula_by_product', None)
            spec['amounts']['floor_field_by_product'] = {k: v for k, v in spec['amounts']['floor_field_by_product'].items() if k != 'car_loan'}
            spec['amounts']['floor_field_by_product'].update(shape)
            case = {'id': 'X-1', 'family': 'Amounts', 'title': 'floor', 'variables': {'first_name': 'A', 'last_name': 'B', 'title': 'Ms', 'now': '2026-10-14T11:00'},
                    'identity': {'date_of_birth': '1980-03-14', 'phone_last4': '4821'},
                    'products': [{'type': 'car_loan', 'past_due': 1000.0, 'days_late': 3, 'instalment_amount': 999.0}],
                    'expected': {'outcome': 'promise', 'reason': None, 'promises': [], 'notes': [], 'callbacks': [], 'transfers': []}}
            led = ls.drive(spec, case, [ls.I('too_much'), ls.I('agree')], api=ls.API, cases=[case], raw=True, cycle=True)
            self.assertEqual([p['amount'] for p in led['promises']], [250.0], shape)


class Continues(unittest.TestCase):
    def test_contract_flag_makes_dispute_and_paid_continue(self):
        spec = copy.deepcopy(load('builder/specs/brief-ab.spec.json'))
        for it in spec['intents']:
            if isinstance(it.get('action'), dict):
                it['action'].pop('continue_with_other_products', None)
        spec['multi_product']['dispute_or_paid_continues'] = False
        self.assertFalse(ecfg.build_E(spec)['intents']['sp_dispute'].get('continues'))      # nothing says so: closes
        spec['multi_product']['dispute_or_paid_continues'] = True
        E = ecfg.build_E(spec)
        self.assertTrue(E['intents']['sp_dispute']['continues'])
        self.assertTrue(E['intents']['sp_already_paid']['continues'])
        self.assertFalse(E['intents']['sp_restructuring'].get('continues'))

    def test_te04_shape_notes_the_card_then_promises_the_loan(self):
        spec = copy.deepcopy(load('builder/specs/brief-ab.spec.json'))
        for it in spec['intents']:
            if isinstance(it.get('action'), dict):
                it['action'].pop('continue_with_other_products', None)
        spec['multi_product']['dispute_or_paid_continues'] = True
        case = {'id': 'X-2', 'family': 'Multi-product', 'title': 'dispute', 'variables': {'first_name': 'A', 'last_name': 'B', 'title': 'Mr', 'now': '2026-10-14T11:00'},
                'identity': {'date_of_birth': '1980-03-14', 'phone_last4': '4821'},
                'products': [{'type': 'credit_card', 'card_last4': '0377', 'past_due': 200.0, 'days_late': 4, 'minimum_payment': 60.0},
                             {'type': 'personal_loan', 'past_due': 500.0, 'days_late': 7, 'instalment_amount': 170.0}],
                'expected': {'outcome': 'promise', 'reason': None, 'promises': [], 'notes': [], 'callbacks': [], 'transfers': []}}
        led = ls.drive(spec, case, [ls.I('dispute', x_product='card'), ls.I('offer', x_date='today'), ls.I('agree')], api=ls.API, cases=[case], raw=True, cycle=True)
        self.assertEqual([(n['product_id'], n['reason']) for n in led['notes']], [('p1', 'dispute')])
        self.assertEqual([(p['product_id'], p['amount']) for p in led['promises']], [('p2', 500.0)])
        self.assertEqual(led['outcome'], 'promise')


class ContinuesShapes(unittest.TestCase):
    def build(self, mutate):
        spec = copy.deepcopy(load('builder/specs/brief-ab.spec.json'))
        for it in spec['intents']:
            if isinstance(it.get('action'), dict):
                it['action'].pop('continue_with_other_products', None)
        spec['multi_product'].pop('dispute_or_paid_continues', None)
        mutate(spec)
        return ecfg.build_E_warn(spec)

    def test_unsaid_defaults_to_continue_with_a_warning(self):
        E, warns = self.build(lambda s: None)
        self.assertTrue(E['intents']['sp_dispute']['continues'])
        self.assertTrue(E['intents']['sp_already_paid']['continues'])
        self.assertFalse(E['intents']['sp_restructuring'].get('continues'))
        self.assertTrue(any('intent dispute' in w for w in warns))

    def test_any_continue_spelling_in_the_intent_or_multi_product(self):
        def a(s):
            next(i for i in s['intents'] if i['id'] == 'dispute')['action']['continue_after_note'] = True
        def b(s):
            s['multi_product']['continue_after_dispute'] = True
        def c(s):
            next(i for i in s['intents'] if i['id'] == 'dispute')['continues'] = True
        for m in (a, b, c):
            E, warns = self.build(m)
            self.assertTrue(E['intents']['sp_dispute']['continues'])
            self.assertFalse(any('intent dispute' in w for w in warns))

    def test_explicit_no_is_respected(self):
        def m(s):
            next(i for i in s['intents'] if i['id'] == 'dispute')['action']['continue_with_other_products'] = False
        E, _ = self.build(m)
        self.assertFalse(E['intents']['sp_dispute']['continues'])


if __name__ == '__main__':
    unittest.main()
