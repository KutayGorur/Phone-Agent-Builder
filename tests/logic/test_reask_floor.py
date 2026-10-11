"""While an offer is pending, a question must not make the agent name the floor a second time (PUB-06 judge failure).
local_sim drives the compiled engine; `said` collects the instruction text of every spoken turn. No Freya, no model.

    python tests/logic/test_reask_floor.py
"""
import json
import os
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, ROOT)

from builder.generate import local_sim as L  # noqa: E402


def spec(n):
    with open(os.path.join(ROOT, 'builder', 'specs', 'brief-%s.spec.json' % n), encoding='utf-8') as f:
        return json.load(f)


class ReaskFloor(unittest.TestCase):
    def run_it(self, steps, case_id='PUB-06', brief='a'):
        case = next(c for c in L.CASES if c['id'] == case_id)
        said = []
        L.drive(spec(brief), case, steps, said=said, raw=True, cycle=True)
        return said

    def test_question_after_floor_offer_hides_the_floor(self):
        said = self.run_it([L.I('too_much'), L.I('question'), L.I('agree'), L.I('agree')])
        offer = said[1]
        self.assertIn('637.50', offer)                       # the offer itself names the floor once
        asked = said[2]
        self.assertNotIn('637.50', asked)                    # the answer to a question does not
        self.assertNotIn('minimum payment', asked)
        self.assertIn('I do not have that information.', asked)
        self.assertTrue(asked.rstrip().endswith('Can you do that on Friday 16 October?'))

    def test_question_before_any_offer_keeps_the_facts(self):
        said = self.run_it([L.I('question'), L.I('agree'), L.I('agree')])
        self.assertIn('minimum payment 637.50', said[1])
        self.assertNotIn('That is the amount I mentioned', said[1])

    def test_live_evasive_sequence_is_fixed_and_keeps_offer_and_acceptance(self):
        from test_engine_state import Probe
        product = {'product_id': 'p1', 'type': 'credit_card', 'card_last4': '1903',
                   'past_due': '2125.10', 'days_late': '12', 'minimum_payment': '637.50'}
        p = Probe('a', products=(product,))
        p.say('too_much')
        before = p.prod(0)
        p.say('evasive')
        self.assertEqual(p.v['route'], 'say')
        self.assertEqual(p.text, 'I do not have that information. Can you do that on Friday 16 October?')
        self.assertEqual(p.prod(0), before)
        p.say('agree')
        self.assertIn('637.50', p.text)
        p.say('agree')
        self.assertEqual(p.create(), ('p1', '637.50', '2026-10-16'))

    def test_pending_offer_answers_once_and_still_allows_changes_and_transfer(self):
        from test_engine_state import Probe
        product = {'product_id': 'p1', 'type': 'credit_card', 'past_due': '2125.10',
                   'days_late': '12', 'minimum_payment': '637.50'}
        for kind, expected in [('ai', 'digital assistant'), ('scam', 'customer service number'),
                               ('balance', '2125.10'), ('deadline', 'Friday 23 October'),
                               ('unknown', 'I do not have that information.')]:
            with self.subTest(kind=kind):
                p = Probe('a', products=(product,))
                p.say('too_much')
                p.say('question', q='yes', x_question_kind=kind)
                self.assertEqual(p.v['route'], 'say')
                self.assertEqual(p.text.count(expected), 1)
                self.assertNotIn('637.50', p.text)
                p.say('offer', date='today', amount='700')
                p.say('agree')
                self.assertEqual(p.create(), ('p1', '700.00', '2026-10-14'))
        p = Probe('a', products=(product,))
        p.say('too_much')
        p.say('evasive')
        p.say('sp_restructuring')
        self.assertEqual(p.v['route'], 'transfer')


if __name__ == '__main__':
    unittest.main()
