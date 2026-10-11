"""A product whose past-due amount sits in a differently named field (brief I: overdraft arrears_nok, loans amount_due) is
read, stated and processed like the others. Offline: compiler, generated scenarios, no Freya, no model.

    python tests/logic/test_amount_fields.py
"""
import copy
import json
import os
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, ROOT)

from builder.generate import auto_sim  # noqa: E402
from builder.generate.ecfg import blocking_warnings, build_E_warn  # noqa: E402


def spec():
    with open(os.path.join(ROOT, 'tests', 'fixtures', 'spec-i-fresh.json'), encoding='utf-8') as f:
        return json.load(f)


def api():
    with open(os.path.join(ROOT, 'test-briefs', 'tools-i.openapi.json'), encoding='utf-8') as f:
        return json.load(f)


class AmountFields(unittest.TestCase):
    def test_spec_mapping_is_read(self):
        E, warns = build_E_warn(spec())
        self.assertEqual(E['pd_by_type']['overdraft'], 'arrears_nok')
        self.assertEqual(E['pd_by_type']['consumer_loan'], 'amount_due')
        self.assertFalse([w for w in warns if 'by_product' in w or 'no amount field' in w], 'unexpected warnings')

    def test_other_spellings_of_the_map(self):
        s = spec()
        s['amounts']['amount_field_by_product'] = s['amounts'].pop('past_due_field_by_product')
        s['debt_statement'].pop('amount_field_by_product')
        E, _ = build_E_warn(s)
        self.assertEqual(E['pd_by_type']['overdraft'], 'arrears_nok')

    def test_api_description_is_enough_when_the_parser_gave_no_map(self):
        s = spec()
        s['amounts'].pop('past_due_field_by_product')
        s['debt_statement'].pop('amount_field_by_product')
        E, warns = build_E_warn(s)
        self.assertEqual(E['pd_by_type'].get('overdraft'), 'arrears_nok')
        self.assertEqual(blocking_warnings(warns), [])

    def test_type_without_any_amount_field_is_blocking(self):
        s = spec()
        s['amounts'].pop('past_due_field_by_product')
        s['debt_statement'].pop('amount_field_by_product')
        items = s['tools']['get_account']['response_fields']['products']['items']
        items['arrears_nok']['description'] = ''          # nothing ties the field to the overdraft any more
        E, warns = build_E_warn(s)
        self.assertTrue([w for w in blocking_warnings(warns) if 'has no amount field' in w], 'no blocking warning')

    def test_generated_customers_all_pass_and_every_product_is_handled(self):
        res = auto_sim.run(spec(), api(), echo=False)
        self.assertEqual(res['failed'], [], res['failed'][:3])
        self.assertGreater(res['total'], 40)


if __name__ == '__main__':
    unittest.main()
