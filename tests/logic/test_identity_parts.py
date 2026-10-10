"""The digits hook joins an answer given in two parts and leaves whole answers alone.

    python tests/logic/test_identity_parts.py
"""
import os
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from builder.generate.generate import verify_pre  # noqa: E402

Q = {'field': 'phone_last4', 'ask': 'the last four digits', 'format': '4 digits'}
HOOK = verify_pre(Q, {'cal': {}})


def send(answers):
    v, sent = {}, []
    for a in answers:
        config = {'body': {'answer': a}}
        exec(HOOK, {'config': config, 'vars': v})
        sent.append(config['body']['answer'])
    return sent


class Parts(unittest.TestCase):
    def test_two_halves(self):
        self.assertEqual(send(['22', '19'])[-1], '2219')

    def test_whole_answers(self):
        self.assertEqual(send(['4401', '4410']), ['4401', '4410'])

    def test_whole_after_part(self):
        self.assertEqual(send(['22', '2219'])[-1], '2219')

    def test_part_after_whole(self):
        self.assertEqual(send(['4401', '44', '10']), ['4401', '44', '4410'])

    def test_longer_number(self):
        self.assertEqual(send(['0555 123 4471']), ['4471'])


if __name__ == '__main__':
    unittest.main()
