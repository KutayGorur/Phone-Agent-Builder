"""Every line spoken before close_call thanks the customer and says goodbye (closing.goodbye_before_close).

    python tests/logic/test_closings.py
"""
import glob
import json
import os
import re
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from builder.generate import generate  # noqa: E402
from builder.generate.ecfg import build_E  # noqa: E402

SPECS = sorted(glob.glob(os.path.join(ROOT, 'builder', 'specs', '*.spec.json')))


def polite(text):
    t = text.lower()
    return 'thank' in t and 'goodbye' in t


class Closings(unittest.TestCase):
    def test_fixed_closing_lines(self):
        for path in SPECS:
            E = build_E(json.load(open(path, encoding='utf-8')))
            lines = {'goodbye': E['goodbye'], 'unclear': E['unclear_say'], 'wrong_number': E['tp']['wrong_number_say'],
                     'deceased': E['tp']['deceased_say'], 'callback_failed': E['tp']['failed_say']}
            for name, text in lines.items():
                self.assertTrue(polite(text), '%s: %s line lacks thanks or goodbye: %r' % (os.path.basename(path), name, text))

    def test_direct_close_nodes(self):
        for path in SPECS:
            wf = generate(json.load(open(path, encoding='utf-8')))
            byes = re.findall(r"vars\[\\?['\"]bye_text\\?['\"]\]\s*=\s*(\\?['\"])(.*?)\1\\n", json.dumps(wf))
            byes = [b for b in byes if b[1]]        # the init node resets bye_text to ''
            self.assertTrue(len(byes) >= 4, '%s: expected the direct-close nodes, found %d' % (os.path.basename(path), len(byes)))
            for _, text in byes:
                self.assertTrue(polite(text), '%s: direct close lacks thanks or goodbye: %r' % (os.path.basename(path), text))

    def test_deceased_asks_nothing(self):
        for path in SPECS:
            E = build_E(json.load(open(path, encoding='utf-8')))
            self.assertNotIn('?', E['tp']['deceased_say'])


if __name__ == '__main__':
    unittest.main()
