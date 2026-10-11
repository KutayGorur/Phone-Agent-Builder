"""A question asked once nothing more is to be asked (support on offer after hardship, or the call is closing) is
answered with a fixed line, never by a turn the speaking model words itself. Background: platform call
c4a6b975 (team/comms/log-codex-flight.md) - after hardship the model answered a discount question and then proposed
the full amount on a date of its own, although the instruction forbade it. Same probe pattern as test_engine_state.py.

    python tests/logic/test_terminal_questions.py
"""
import copy
import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_engine_state import Probe, spec, PERSONAL, NOW, build_E, engine_code, json  # noqa: E402

from builder.generate.generate import generate  # noqa: E402

UNKNOWN = 'I do not have that information.'
AI = "I am Freya Bank's digital assistant."
OFFER = 'Would you like me to connect you with our support team?'
DAYS = re.compile(r'monday|tuesday|wednesday|thursday|friday|saturday|sunday|october|november|tomorrow|today', re.I)


class SpecProbe(Probe):
    """Probe on a spec given as a dict (so a test can change one field of it)."""
    def __init__(self, sp, products=(PERSONAL,)):
        self.code = engine_code(build_E(sp))
        self.v = {'now': NOW, 'st': ''}
        for i, p in enumerate(products):
            for k, x in p.items():
                self.v['get_account_response.data.products.%d.%s' % (i, k)] = x
        self.run()


def hardship():
    p = Probe(products=(PERSONAL,))
    p.say('sp_hardship')
    assert p.v['route'] == 'say' and p.v['say_text'].endswith(OFFER), p.v
    return p


def closed(p):
    """Play the note round trips, if the brief records notes, up to the closing line."""
    for _ in range(4):
        if p.v['route'] != 'note':
            break
        p.v['nt_ok'] = 'true'
        p.run()
    assert p.v['route'] == 'fin', p.v['route']
    return p.v['bye_text']


class AfterHardship(unittest.TestCase):
    def assertNoProposal(self, text):
        self.assertNotRegex(text, r'\d', text)                       # no amount, no date
        self.assertNotRegex(text, DAYS, text)
        self.assertNotIn('?', text)                                  # nothing further is asked
        for w in ('discount', 'waiver', 'plan', 'instalment'):
            self.assertNotIn(w, text.lower())

    def test_declining_support_with_a_discount_question_closes_with_the_fixed_answer(self):
        p = hardship()
        p.say('sp_restructuring', q='yes', x_qk='other')             # what the extractor returned in the failed call
        self.assertNotEqual(p.v['route'], 'ask')                     # no turn worded by the model
        bye = closed(p)
        self.assertTrue(bye.startswith(UNKNOWN + ' I understand.'), bye)
        self.assertTrue(bye.endswith('Goodbye.'), bye)
        self.assertNoProposal(bye)
        self.assertEqual((p.v['close_outcome'], p.v['close_reason']), ('no_promise', 'hardship'))
        self.assertFalse(p.st.get('defer'))

    def test_refusing_the_transfer_and_asking_in_one_sentence(self):
        p = hardship()
        p.say('refuse', q='yes', x_qk='other')
        bye = closed(p)
        self.assertTrue(bye.startswith(UNKNOWN), bye)
        self.assertNoProposal(bye)
        self.assertEqual((p.v['close_outcome'], p.v['close_reason']), ('no_promise', 'hardship'))

    def test_a_repeated_question_is_answered_twice_and_then_the_call_closes(self):
        p = hardship()
        p.say('question', q='yes', x_qk='other')
        self.assertEqual((p.v['route'], p.v['say_text']), ('say', UNKNOWN))       # fixed line, the offer is not repeated
        self.assertTrue(p.st['hard_pending'])
        p.say('question', q='yes', x_qk='other')
        bye = closed(p)
        self.assertEqual(bye.count(UNKNOWN), 1)
        self.assertNoProposal(bye)
        self.assertEqual(p.v['close_reason'], 'hardship')

    def test_balance_question_gets_the_account_facts_and_no_proposal(self):
        p = hardship()
        p.say('question', q='yes', x_qk='amount')
        self.assertEqual(p.v['route'], 'say')
        self.assertEqual(p.v['say_text'], 'Your personal loan is 300.00 past due and 3 days late.')
        p.say('refuse', q='yes', x_qk='amount')
        bye = closed(p)
        self.assertTrue(bye.startswith('Your personal loan is 300.00 past due and 3 days late. I understand.'), bye)
        self.assertNotRegex(bye, DAYS)
        self.assertNotIn('?', bye)

    def test_ai_and_scam_questions_keep_the_answers_of_the_brief(self):
        p = hardship()
        p.say('question', q='yes', x_qk='ai')
        self.assertEqual(p.v['say_text'], AI)
        p.say('refuse', q='yes', x_qk='scam')
        bye = closed(p)
        self.assertTrue(bye.startswith("You can verify this call by phoning Freya Bank's customer service number."), bye)

    def test_question_without_a_kind_gets_the_unknown_answer(self):
        p = hardship()
        p.say('refuse', q='yes')
        self.assertTrue(closed(p).startswith(UNKNOWN))
        p = hardship()
        p.say('refuse', q='no', x_qk='ai')                           # x_q decides whether there was a question
        self.assertTrue(closed(p).startswith('I understand.'))

    def test_unclear_reply_repeats_the_offer_as_a_fixed_line(self):
        p = hardship()
        p.say('none')
        self.assertEqual((p.v['route'], p.v['say_text']), ('say', OFFER))
        p = hardship()
        p.say('none', q='yes', x_qk='ai')
        self.assertEqual((p.v['route'], p.v['say_text']), ('say', AI + ' ' + OFFER))

    def test_hardship_said_together_with_a_question(self):
        p = Probe(products=(PERSONAL,))
        p.say('sp_hardship', q='yes', x_qk='other')
        self.assertEqual(p.v['route'], 'say')
        self.assertTrue(p.v['say_text'].startswith(UNKNOWN + ' I am sorry to hear that.'), p.v['say_text'])
        self.assertTrue(p.v['say_text'].endswith(OFFER))

    def test_a_payment_the_customer_volunteers_after_hardship_still_stands(self):
        p = hardship()
        p.say('offer', date='tomorrow', amount='300')
        self.assertEqual((p.prod(0)['status'], p.prod(0)['amt'], p.prod(0)['date']), ('agreed', 300.0, '2026-10-15'))
        self.assertEqual(p.st['phase'], 'confirm')
        p.say('agree')
        self.assertEqual(p.v['route'], 'create')

    def test_accepting_support_still_transfers(self):
        p = hardship()
        p.say('agree', q='yes', x_qk='other')
        self.assertEqual((p.v['route'], p.v['tr_queue']), ('transfer', 'support'))


class OtherClosings(unittest.TestCase):
    def test_question_with_a_closing_intent(self):
        p = Probe(products=(PERSONAL,))
        p.say('sp_already_paid', q='yes', x_qk='ai')
        self.assertNotEqual(p.v['route'], 'ask')
        self.assertTrue(closed(p).startswith(AI))
        self.assertEqual(p.v['close_outcome'], 'paid')

    def test_scam_answer_given_as_an_instruction_is_worded_by_the_model_without_account_facts(self):
        sp = copy.deepcopy(spec('ab'))
        for i in sp['intents']:
            if i['id'] == 'scam':
                i['say'] = 'invite them to call the number on their card'
        p = SpecProbe(sp)
        p.say('sp_hardship')
        p.say('refuse', q='yes', x_qk='scam')
        self.assertEqual(p.v['route'], 'ask')
        self.assertIn('invite them to call the number on their card', p.v['instruction'])
        self.assertNotRegex(p.v['instruction'], r'\d')               # no amount or date to build a proposal from
        self.assertIn('Ask nothing', p.v['instruction'])
        p.say('none')                                                # whatever they say next, the close follows
        closed(p)
        self.assertEqual(p.v['close_reason'], 'hardship')

    def test_transfer_request_while_that_close_waits(self):
        sp = copy.deepcopy(spec('ab'))
        for i in sp['intents']:
            if i['id'] == 'scam':
                i['say'] = 'invite them to call the number on their card'
        p = SpecProbe(sp)
        p.say('sp_already_paid', q='yes', x_qk='scam')
        p.say('sp_restructuring')
        self.assertEqual(p.v['route'], 'transfer')


class Graph(unittest.TestCase):
    def test_the_question_kind_is_extracted_wherever_the_engine_reads_it(self):
        for name in ('a', 'ab', 'f', 'g', 'h'):
            wf = generate(spec(name))
            for node in ('say_main', 'say_fixed', 'eng_retry'):
                blob = json.dumps(wf['nodes'][node])
                self.assertIn('x_qk', blob, (name, node))
            self.assertIn('x_qk', json.dumps(wf['nodes']['init']), name)
            self.assertIn("S('x_qk')", json.dumps(wf['nodes']['engine']), name)


if __name__ == '__main__':
    unittest.main()
