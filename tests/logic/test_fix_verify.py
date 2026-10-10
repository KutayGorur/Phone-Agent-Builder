"""Fixes for the independent fix verification (team/comms/fix-verification-verdicts.md, R1..R12). Same probe pattern as
test_engine_state.py: hand-set extraction variables, assert on route, tool variables and spoken text.

    python tests/logic/test_fix_verify.py
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_engine_state import (Probe, probe_with, ns_for, spec, PERSONAL, CAR, NOW, D, G1, G2, build_E, engine_code, json)  # noqa: E402,F401


class R1R2R4Scope(unittest.TestCase):
    def test_r1_amount_and_date_survive_a_product_only_answer(self):
        p = Probe()
        p.say('offer', date='tomorrow', amount='250', product='all')
        self.assertIn('Which account', p.text)
        p.say('offer', product='car loan')
        self.assertEqual((p.prod(1)['status'], p.prod(1)['amt'], p.prod(1)['date']), ('agreed', 250.0, '2026-10-15'))
        self.assertEqual(p.prod(0)['status'], 'open')

    def test_r1_ambiguous_name_keeps_amount_and_date(self):
        p = Probe()
        p.say('offer', date='tomorrow', amount='250', product='loan')
        self.assertIn('Which one', p.text)
        p.say('offer', product='car loan')
        self.assertEqual((p.prod(1)['amt'], p.prod(1)['date']), (250.0, '2026-10-15'))

    def test_r1_a_question_between_does_not_lose_it(self):
        p = Probe()
        p.say('offer', date='tomorrow', amount='250', product='all')
        p.say('question', q='yes')
        p.say('offer', product='car loan')
        self.assertEqual((p.prod(1)['amt'], p.prod(1)['date']), (250.0, '2026-10-15'))

    def test_r1_a_new_amount_wins_over_the_kept_one(self):
        p = Probe()
        p.say('offer', date='tomorrow', amount='250', product='all')
        p.say('offer', product='car loan', amount='300')
        self.assertEqual(p.prod(1)['amt'], 300.0)

    def test_r2_unknown_product_is_not_the_current_one(self):
        p = Probe()
        p.say('offer', date='tomorrow', amount='250', product='mortgage')
        self.assertIn('Which one', p.text)
        self.assertEqual([x['status'] for x in p.st['prods']], ['open', 'open'])
        p.say('offer', product='personal loan')
        self.assertEqual((p.prod(0)['amt'], p.prod(0)['date']), (250.0, '2026-10-15'))

    def test_r2_ordinal_and_id_references(self):
        p = Probe()
        p.say('offer', date='tomorrow', amount='250', product='the second one')
        self.assertEqual(p.prod(1)['status'], 'agreed')
        p = Probe()
        p.say('offer', date='tomorrow', amount='250', product='p2')
        self.assertEqual(p.prod(1)['status'], 'agreed')

    def test_r2_generic_words_do_not_ask(self):
        p = Probe()
        p.say('offer', date='tomorrow', amount='250', product='that one')
        self.assertEqual(p.prod(0)['status'], 'agreed')

    def test_r4_compound_alternatives_are_unclear(self):
        ns = ns_for()
        for t in ('150 point five zero to 200', '150 pounds 50 pence or 200 pounds', '150,50'):
            self.assertEqual(ns['amount_check'](t)[0], 'unclear', t)
        self.assertEqual(ns['amount_check']('150 point five zero'), ('ok', 150.5))
        self.assertEqual(ns['amount_check']('150 pounds 50 pence'), ('ok', 150.5))

    def test_r4_clarification_wording_and_date_kept(self):
        p = Probe(products=(PERSONAL,))
        p.say('offer', date='tomorrow', amount='150,50')
        self.assertNotIn('how much can you pay', p.text.lower())     # brief A rule 24
        p.say('offer', amount='150')
        self.assertEqual((p.prod(0)['amt'], p.prod(0)['date']), (150.0, '2026-10-15'))


class R3Confirmation(unittest.TestCase):
    def _readback(self):
        p = Probe(products=(PERSONAL,))
        p.say('offer', date='tomorrow', amount='150')
        self.assertEqual(p.st['phase'], 'confirm')
        return p

    def test_r3_yes_but_friday_changes_the_date_and_writes_nothing(self):
        p = self._readback()
        p.say('agree', date='Friday')
        self.assertNotEqual(p.v['route'], 'create')
        self.assertEqual((p.prod(0)['amt'], p.prod(0)['date']), (150.0, '2026-10-16'))
        self.assertIn('Friday 16 October', p.text)
        p.say('agree')
        self.assertEqual((p.v['route'], p.v['cp_date']), ('create', '2026-10-16'))

    def test_r3_question_does_not_erase_the_correction(self):
        p = self._readback()
        p.say('agree', date='Friday', q='yes')
        self.assertNotEqual(p.v['route'], 'create')
        self.assertEqual(p.prod(0)['date'], '2026-10-16')
        self.assertEqual(p.v['route'], 'ask')

    def test_r3_yes_but_other_amount(self):
        p = self._readback()
        p.say('agree', amount='200')
        self.assertNotEqual(p.v['route'], 'create')
        self.assertEqual((p.prod(0)['amt'], p.prod(0)['date']), (200.0, '2026-10-15'))


class R5R6History(unittest.TestCase):
    def test_r5_refused_counter_offer_is_not_offered_again(self):
        late = dict(PERSONAL, past_due='500.0', days_late='10', instalment_amount='100.0')
        p = Probe(products=(late,))
        p.say('offer', date='23 October', amount='50')
        self.assertEqual((p.prod(0)['pend']['a'], p.prod(0)['pend']['d']), (100.0, '2026-10-23'))
        p.say('refuse')
        self.assertEqual(p.prod(0)['pend']['a'], 500.0)
        p.say('refuse')                                                 # attempt 2 would be the refused 100 on 23 Oct
        self.assertEqual(p.v['route'], 'note')
        self.assertEqual(p.prod(0)['status'], 'noted')

    def test_r6_hardship_with_shared_date_keeps_all_products_and_stops_persuasion(self):
        p = Probe()
        p.say('sp_hardship', date='tomorrow', product='all')
        p.say('refuse')                                                 # no thanks to the support team
        self.assertEqual([x['status'] for x in p.st['prods']], ['agreed', 'agreed'])
        self.assertEqual([x['date'] for x in p.st['prods']], ['2026-10-15', '2026-10-15'])
        self.assertEqual(p.st['phase'], 'confirm')

    def test_r6_one_named_product_then_no_persuasion_on_the_other(self):
        p = Probe()
        p.say('sp_hardship', date='tomorrow', amount='300', product='car loan')
        p.say('refuse')
        self.assertEqual(p.prod(1)['status'], 'agreed')
        self.assertEqual(p.prod(0)['status'], 'noted')                  # not asked, noted with the hardship reason
        self.assertEqual(p.prod(0)['note'], 'hardship')
        self.assertEqual(p.st['phase'], 'confirm')

    def test_r6_ambiguous_scope_asks_instead_of_defaulting(self):
        p = Probe()
        p.say('sp_hardship', date='tomorrow', amount='300', product='loan')
        p.say('refuse')
        self.assertIn('Which one', p.text)
        self.assertEqual([x['status'] for x in p.st['prods']], ['open', 'open'])
        p.say('offer', product='car loan')
        self.assertEqual((p.prod(1)['amt'], p.prod(1)['date']), (300.0, '2026-10-15'))

    def test_r6_hardship_without_offer_is_unchanged(self):
        p = Probe()
        p.say('sp_hardship')
        p.say('refuse')
        self.assertEqual(p.v['route'], 'note')
        self.assertEqual([x['note'] for x in p.st['prods']], ['hardship', 'hardship'])


if __name__ == '__main__':
    unittest.main()
