"""A brief that requires a reason on every outcome (brief J): promise and paid closes carry their only allowed reason.

    python tests/logic/test_reason_every_outcome.py
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
    with open(os.path.join(ROOT, 'tests', 'fixtures', 'spec-j-fresh.json'), encoding='utf-8') as f:
        return json.load(f)


class Reasons(unittest.TestCase):
    def test_roles_and_reasons_without_a_reason_less_outcome(self):
        E, warns = build_E_warn(spec())
        self.assertEqual(E['out']['r_promise'], 'PTP')
        self.assertEqual(E['out']['r_paid'], 'PAID_CLAIMED')
        self.assertEqual(E['out_reason'], {'r_promise': 'RECORDED', 'r_paid': 'CUSTOMER_STATED'})
        self.assertFalse([w for w in warns if 'no outcome without reasons' in w])
        self.assertFalse([w for w in warns if 'every_outcome_carries_reason' in w])

    def test_promise_role_found_when_outcome_names_are_unusual(self):
        s = spec()
        for o in s['closing']['outcomes']:
            if o['outcome'] == 'PTP':
                o['outcome'], o['brief_code'] = 'KEPT_WORD', 'PTP'
        s['closing']['ending_priority'] = []
        E, _ = build_E_warn(s)
        self.assertEqual(E['out']['r_promise'], 'KEPT_WORD')

    def test_unsure_promise_outcome_is_blocking(self):
        s = spec()
        for o in s['closing']['outcomes']:
            o['brief_code'] = ''
            o['when'] = 'text that says nothing'
            if o['outcome'] == 'PTP':
                o['outcome'] = 'GOOD'
        E, warns = build_E_warn(s)
        self.assertTrue(blocking_warnings(warns))

    def test_exhaustion_and_other_closes_get_their_sole_reason(self):
        s = spec()
        for o in s['closing']['outcomes']:
            if o['outcome'] == 'NO_ID':
                o['reasons'] = ['FAILED']
        s['identity']['on_declined'] = {'outcome': 'NO_ID', 'reason': None}
        E, _ = build_E_warn(s)
        self.assertEqual(E['idv']['declined']['reason'], 'FAILED')

    def test_generated_customers_close_with_reasons(self):
        with open(os.path.join(ROOT, 'test-briefs', 'tools-j.openapi.json'), encoding='utf-8') as f:
            api = json.load(f)
        res = auto_sim.run(spec(), api, echo=False)
        bad = [(n, p) for n, p in res['failed'] if not n.startswith('tp_callback')]
        self.assertEqual(bad, [])


if __name__ == '__main__':
    unittest.main()
