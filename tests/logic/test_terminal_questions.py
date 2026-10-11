"""PUB-05 speech regression: critical answers must use fixed TTS, not an LLM task."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_engine_state import Probe, spec, build_E, engine_code, NOW
from builder.generate.generate import generate

PRODUCT = {'product_id': 'p1', 'type': 'personal_loan', 'past_due': '780',
           'days_late': '21', 'instalment_amount': '260'}


class TerminalQuestions(unittest.TestCase):
    def hardship(self):
        p = Probe('a', products=(PRODUCT,))
        p.say('sp_hardship', q='yes', x_question_kind='unknown')
        return p

    def test_real_decline_plus_discount_extraction_uses_fixed_answer(self):
        p = self.hardship()
        self.assertEqual(p.v['route'], 'say')
        self.assertEqual(p.text.count('I am sorry to hear that.'), 1)
        p.say('sp_restructuring', q='yes', x_question_kind='unknown')
        self.assertEqual(p.v['route'], 'say')
        self.assertEqual(p.text, 'I do not have that information.')
        self.assertEqual((p.v['close_outcome'], p.v['close_reason']), ('no_promise', 'hardship'))
        self.assertEqual(p.st['defer'], 'fin')
        self.assertNotIn('780', p.text)
        self.assertNotIn('Friday', p.text)
        self.assertNotIn('?', p.text)
        p.say('none')
        self.assertEqual(p.v['route'], 'fin')

    def test_terminal_ai_scam_balance_deadline_and_unknown_are_bounded(self):
        expected = {'ai': "digital assistant", 'scam': 'customer service number',
                    'balance': '780.00 past due', 'deadline': 'Friday 23 October',
                    'unknown': 'I do not have that information'}
        for kind, answer in expected.items():
            with self.subTest(kind=kind):
                p = self.hardship()
                p.say('refuse', q='yes', x_question_kind=kind)
                self.assertEqual(p.v['route'], 'say')
                self.assertIn(answer, p.text)
                self.assertNotIn('Can you', p.text)
                self.assertNotIn('Would', p.text)
                self.assertNotIn('?', p.text)

    def test_question_while_support_pending_is_answered_once(self):
        p = self.hardship()
        p.say('question', q='yes', x_question_kind='balance')
        self.assertEqual(p.v['route'], 'say')
        self.assertEqual(p.text.count('780.00'), 1)
        self.assertNotIn('support team', p.text)
        p.say('refuse')
        self.assertEqual(p.v['route'], 'fin')

    def test_question_kind_does_not_leak_into_the_next_question(self):
        p = self.hardship()
        p.say('question', q='yes', x_question_kind='balance')
        p.say('refuse', q='yes')
        self.assertEqual(p.text, 'I do not have that information.')

    def test_transfer_can_interrupt_pending_close(self):
        p = self.hardship()
        p.say('refuse', q='yes')
        p.say('sp_restructuring')
        self.assertEqual(p.v['route'], 'transfer')

    def test_volunteered_offer_after_hardship_still_requires_confirmation(self):
        p = Probe('a', products=(PRODUCT,))
        p.say('sp_hardship', amount='300', date='tomorrow')
        p.say('refuse')
        self.assertEqual(p.st['phase'], 'confirm')
        self.assertEqual((p.prod(0)['amt'], p.prod(0)['date']), (300.0, '2026-10-15'))
        p.say('agree')
        self.assertEqual(p.v['route'], 'create')

    def test_paid_close_question_also_uses_fixed_answer(self):
        p = Probe('a', products=(PRODUCT,))
        p.say('sp_already_paid', q='yes', x_question_kind='ai')
        self.assertEqual((p.v['route'], p.v['close_outcome']), ('say', 'paid'))
        self.assertIn('digital assistant', p.text)

    def test_fixed_reply_route_is_tts_with_question_extraction(self):
        wf = generate(spec('a'))
        self.assertEqual(wf['nodes']['say_fixed']['on_enter'], {'type': 'tts', 'text': '{{say_text}}'})
        self.assertIn('x_question_kind', str(wf['nodes']['say_fixed']['extraction_schema']))


class InstructionStyleScamAnswer(unittest.TestCase):
    """Briefs H, I and J give the scam answer as an instruction; it must not be read out as it stands."""
    SAY = 'invite them to call the number on their card'

    def probe(self):
        sp = spec('a')
        for i in sp['intents']:
            if i['id'] == 'scam':
                i['say'] = self.SAY
        p = Probe.__new__(Probe)
        p.code = engine_code(build_E(sp))
        p.v = {'now': NOW, 'st': ''}
        for k, x in PRODUCT.items():
            p.v['get_account_response.data.products.0.%s' % k] = x
        return p.run()

    def assertBounded(self, p):
        self.assertEqual(p.v['route'], 'ask')                        # worded by the model, never read out
        self.assertIn(self.SAY, p.v['instruction'])
        self.assertNotIn('780', p.v['instruction'])                  # no account facts to build a proposal from
        self.assertNotIn('October', p.v['instruction'])

    def test_before_the_close(self):
        p = self.probe()
        p.say('sp_hardship')
        p.say('refuse', q='yes', x_question_kind='scam')
        self.assertBounded(p)
        self.assertIn('Ask nothing', p.v['instruction'])
        self.assertEqual(p.st['defer'], 'fin')
        p.say('none')
        self.assertEqual((p.v['route'], p.v['close_reason']), ('fin', 'hardship'))

    def test_with_a_fixed_line_after_it(self):
        p = self.probe()
        p.say('sp_hardship', q='yes', x_question_kind='scam')
        self.assertBounded(p)
        self.assertIn('word for word: I am sorry to hear that.', p.v['instruction'])

    def test_a_sentence_style_answer_is_still_fixed_speech(self):
        p = Probe('a', products=(PRODUCT,))
        p.say('sp_hardship')
        p.say('refuse', q='yes', x_question_kind='scam')
        self.assertEqual((p.v['route'], p.text), ('say', "You can verify this call by phoning Freya Bank's customer service number."))


if __name__ == '__main__':
    unittest.main()
