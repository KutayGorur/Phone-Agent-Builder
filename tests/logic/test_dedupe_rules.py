"""extra_rules that repeat a line the compiler already generates are left out of the system prompt. Offline.

    python tests/logic/test_dedupe_rules.py
"""
import json
import os
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, ROOT)

import builder.generate  # noqa: E402,F401
GM = sys.modules['builder.generate.generate']


def spec(n='a'):
    with open(os.path.join(ROOT, 'builder', 'specs', 'brief-%s.spec.json' % n), encoding='utf-8') as f:
        return json.load(f)


class Dedupe(unittest.TestCase):
    def test_paraphrase_of_a_generated_line_goes(self):
        kept, dropped = GM.drop_duplicate_rules(
            ["If asked whether you are a robot or an AI, say that you are the digital assistant and continue."],
            ["If asked whether you are a robot or an AI, say: I am Freya Bank's digital assistant and continue."])
        self.assertEqual((kept, len(dropped)), ([], 1))

    def test_rule_with_new_information_stays(self):
        r = "If asked whether you are a robot or an AI, say that you are the digital assistant and continue, and never mention the team lead."
        kept, dropped = GM.drop_duplicate_rules([r], ["If asked whether you are a robot or an AI, say: I am Freya Bank's digital assistant and continue."])
        self.assertEqual(kept, [r])

    def test_a_number_that_is_not_in_the_line_keeps_the_rule(self):
        kept, dropped = GM.drop_duplicate_rules(["Allow the customer at most 3 wrong answers in total during the check"],
                                                ["Allow the customer at most wrong answers in total during the check"])
        self.assertEqual(len(kept), 1)

    def test_second_copy_of_an_extra_rule_goes(self):
        a = "A customer saying twice they do not want to talk does not add persuasion attempts."
        b = "Saying twice that they do not want to talk does not add persuasion attempts."
        kept, dropped = GM.drop_duplicate_rules([a, b], [])
        self.assertEqual((kept, dropped), ([a], [b]))

    def test_short_rules_stay(self):
        self.assertEqual(GM.drop_duplicate_rules(["Be kind."], ["Be kind."])[0], ["Be kind."])

    def test_generate_drops_and_reports(self):
        s = spec('a')
        s['extra_rules'] = [{'source': '1', 'text': "If asked whether you are a robot or an AI, say: I am Freya Bank's digital assistant and continue."},
                            {'source': '2', 'text': 'Never mention the weather.'}]
        wf = GM.generate(s)
        self.assertEqual(wf['system_prompt'].count('robot or an AI'), 1)
        self.assertIn('Never mention the weather.', wf['system_prompt'])
        self.assertTrue(any(w.startswith('extra rule left out') for w in GM.LAST_WARNINGS))


if __name__ == '__main__':
    unittest.main()
