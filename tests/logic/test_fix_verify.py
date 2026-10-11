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
        self.assertEqual(p.v['route'], 'say')
        self.assertIn('Friday 16 October', p.text)
        p.say('agree')
        self.assertEqual((p.v['route'], p.v['cp_date']), ('create', '2026-10-16'))

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


class R7Interruptions(unittest.TestCase):
    def _after_first_record(self):
        p = probe_with('g', [G1, G2])
        p.say('agree')
        p.say('agree')
        p.create()
        self.assertEqual(p.v['route'], 'say')
        return p

    def test_r7_transfer_request_during_the_acknowledgement(self):
        p = self._after_first_record()
        p.say('sp_restructuring')
        self.assertEqual(p.v['route'], 'transfer')
        self.assertEqual(p.prod(1)['status'], 'agreed')                  # never recorded
        p.v['tr_ok'] = 'true'
        p.run()
        self.assertEqual((p.v['route'], p.v['close_outcome']), ('fin', 'handoff'))

    def test_r7_correction_during_the_acknowledgement_goes_back_to_the_readback(self):
        p = self._after_first_record()
        p.say('change', date='Friday', product='charge card')
        self.assertNotEqual(p.v['route'], 'create')
        self.assertEqual(p.prod(0)['status'], 'recorded')
        self.assertEqual(p.prod(1)['date'], '2026-10-16')
        self.assertNotIn('term loan', p.text)                            # only the unrecorded one is read back
        p.say('agree')
        self.assertEqual((p.v['route'], p.v['cp_pid'], p.v['cp_date']), ('create', 'g2', '2026-10-16'))

    def test_r7_plain_continuation_still_records_the_next(self):
        p = self._after_first_record()
        p.say('none')
        self.assertEqual((p.v['route'], p.v['cp_pid']), ('create', 'g2'))

    def test_r7_close_question_gets_an_answer_without_negotiation_text(self):
        p = Probe(products=(PERSONAL,))
        p.say('sp_already_paid', q='yes')
        self.assertEqual(p.v['route'], 'say')
        self.assertIn('I do not have that information', p.v['say_text'])
        self.assertNotIn('Then say', p.v['say_text'])
        self.assertNotIn('make this payment', p.v['say_text'])

    def test_r7_transfer_request_while_the_close_waits(self):
        p = Probe(products=(PERSONAL,))
        p.say('sp_already_paid', q='yes')
        p.say('sp_restructuring')
        self.assertEqual(p.v['route'], 'transfer')
        p.v['tr_ok'] = 'true'
        p.run()
        self.assertEqual(p.v['close_outcome'], 'transferred')

    def test_r7_silent_next_turn_still_closes(self):
        p = Probe(products=(PERSONAL,))
        p.say('sp_already_paid', q='yes')
        p.say('none')
        self.assertEqual(p.v['route'], 'note')


class R8DurablePromiseFlag(unittest.TestCase):
    def test_r8_flag_is_set_by_the_engine_and_survives_a_later_failure(self):
        p = probe_with('ab', [PERSONAL, CAR])
        p.say('agree')
        p.say('agree')
        p.create(ok=True)
        self.assertEqual(p.v['promise_recorded'], 'true')
        p.create(ok=False)
        self.assertEqual(p.v['cp_ok'], 'pending')                        # the next write overwrote the result

    def test_r8_fallbacks_use_the_flag(self):
        from builder.generate.generate import generate
        wf = generate(spec('ab'))
        code = wf['nodes']['transfer_failed']['pre_actions'][0]['function']['parameters']['properties']['code']['default']
        for state, want in (({'cp_ok': 'false', 'promise_recorded': 'true'}, 'promise'), ({'cp_ok': 'false'}, 'no_promise'), ({'cp_ok': 'true'}, 'promise')):
            v = dict(state)
            exec(code, {'vars': v})
            self.assertEqual(v['close_outcome'], want, state)
        eng = wf['nodes']['engine']['transitions']
        guard = [t for t in eng if t['target_node'] == 'eng_fail_promise'][0]
        vs = [c['conditions'][-1]['variable'] for c in guard['condition']['conditions']]
        self.assertEqual(sorted(vs), ['cp_ok', 'promise_recorded'])


class R11R12(unittest.TestCase):
    def test_r11_non_finite_and_duplicate_ids_are_left_out_and_recorded(self):
        p = probe_with('ab', [dict(PERSONAL, past_due='inf'), CAR])
        self.assertEqual([x['id'] for x in p.st['prods']], ['p2'])
        self.assertEqual(p.st['skipped'], ['p1'])
        self.assertEqual(p.v['plan_skipped'], 'p1')
        p = probe_with('ab', [dict(PERSONAL, type='mortgage'), CAR])          # an unfamiliar type is the bank's data: kept
        self.assertEqual([x['id'] for x in p.st['prods']], ['p1', 'p2'])
        p = probe_with('ab', [PERSONAL, dict(PERSONAL)])
        self.assertEqual([x['id'] for x in p.st['prods']], ['p1'])
        self.assertEqual(p.v['plan_skipped'], 'p1')

    def test_r11_all_rows_invalid_closes_as_service_error(self):
        p = probe_with('ab', [dict(PERSONAL, past_due='inf')])
        self.assertEqual((p.v['route'], p.v['close_outcome']), ('fin', 'no_promise'))

    def test_r11_valid_account_has_nothing_skipped(self):
        p = probe_with('ab', [PERSONAL, CAR])
        self.assertEqual(p.st['skipped'], [])
        self.assertEqual(p.v['plan_skipped'], '')

    def test_r12_closing_does_not_repeat_the_per_record_acknowledgement(self):
        p = probe_with('g', [G1, G2])
        p.say('agree')
        p.say('agree')
        p.create(ok=True)
        p.say('none')
        p.create(ok=False)
        p.create(ok=False)
        self.assertEqual(p.v['route'], 'note')                           # the failed product is noted first
        p.v['nt_ok'] = 'true'
        p.run()
        self.assertEqual(p.v['route'], 'fin')
        self.assertEqual(p.v['bye_text'].count('confirmed by email'), 0)
        self.assertIn('could not record', p.v['bye_text'])

    def test_r12_unacknowledged_records_still_get_the_sentence(self):
        p = probe_with('g', [G1])
        p.say('agree')
        p.say('agree')
        p.create(ok=True)
        self.assertEqual(p.v['bye_text'].count('confirmed by email'), 1)


class R10Compiler(unittest.TestCase):
    def test_r10_working_day_is_a_business_day(self):
        from builder.generate.ecfg import _date_tok
        w = []
        self.assertEqual(_date_tok('next working day after today, capped at the deadline', w), 'capped_next_business_day')
        self.assertEqual(w, [])
        self.assertEqual(_date_tok('the last working day of the week', w), 'week_end')

    def test_r10_unknown_date_rule_blocks_readiness(self):
        import copy
        from builder.generate.ecfg import build_E_warn, blocking_warnings
        s = copy.deepcopy(spec('a'))
        s['persuasion']['attempts'][0]['date'] = 'two business days after today'
        E, w = build_E_warn(s)
        self.assertEqual(E['pers'][0]['date'], 'unknown')
        self.assertEqual(len(blocking_warnings(w)), 1)
        E, w = build_E_warn(spec('a'))
        self.assertEqual(blocking_warnings(w), [])                    # ignored-field warnings alone never block

    def test_r10_renamed_paid_outcome_is_found_by_its_own_text(self):
        import copy
        from builder.generate.ecfg import build_E_warn, blocking_warnings
        s = copy.deepcopy(spec('ab'))
        outs = s['closing']['outcomes']
        for o in outs:
            if o['outcome'] == 'paid':
                o['outcome'] = 'settled_claim'
        outs[0], outs[1] = outs[1], outs[0]                           # and the rows swapped
        E, w = build_E_warn(s)
        self.assertEqual(E['out']['r_paid'], 'settled_claim')
        self.assertEqual(E['out']['r_promise'], 'promise')
        self.assertEqual(blocking_warnings(w), [])

    def test_r10_ambiguous_outcomes_without_any_hint_block(self):
        import copy
        from builder.generate.ecfg import build_E_warn, blocking_warnings
        s = copy.deepcopy(spec('ab'))
        for o in s['closing']['outcomes']:
            if o['outcome'] in ('paid', 'promise'):
                o.pop('when', None)
                if o['outcome'] == 'paid':
                    o['outcome'] = 'settled_claim'
        E, w = build_E_warn(s)
        self.assertTrue(blocking_warnings(w))


class R9NoteRetries(unittest.TestCase):
    def test_r9_note_is_tried_three_times_then_the_close_goes_on(self):
        p = Probe(products=(PERSONAL,))
        p.say('sp_already_paid')
        n = 0
        while p.v['route'] == 'note':
            n += 1
            p.v['nt_ok'] = 'false'
            p.run()
        self.assertEqual(n, 3)
        self.assertEqual((p.v['route'], p.v['close_outcome']), ('fin', 'paid'))

    def test_r9_a_late_success_is_enough(self):
        p = Probe(products=(PERSONAL,))
        p.say('sp_already_paid')
        p.v['nt_ok'] = 'false'; p.run()
        p.v['nt_ok'] = 'true'; p.run()
        self.assertEqual(p.v['route'], 'fin')


if __name__ == '__main__':
    unittest.main()
