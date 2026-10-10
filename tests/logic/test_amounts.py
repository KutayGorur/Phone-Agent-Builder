"""Spoken amounts with pence, cents or a decimal part keep the fraction.

    python tests/logic/test_amounts.py
"""
import json
import os
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from builder.generate.ecfg import build_E  # noqa: E402
from builder.generate.generate import engine_code  # noqa: E402

SPEC = os.path.join(ROOT, 'builder', 'specs', 'brief-a.spec.json')
NS = {'vars': {}}
try:
    exec(compile(engine_code(build_E(json.load(open(SPEC, encoding='utf-8')))), '<engine>', 'exec'), NS)
except Exception:
    pass                      # the turn itself needs call variables; only the helpers are used here
free_amount = NS['free_amount']

CASES = [
    ('six hundred and thirty-seven pounds and fifty pence', 637.5),
    ('six hundred and thirty-seven, decimal five zero', 637.5),
    ('six hundred thirty seven point five', 637.5),
    ('637 pounds 50 pence', 637.5),
    ('1,250 pounds and 50 pence', 1250.5),
    ('five hundred dollars and five cents', 500.05),
    ('637.50', 637.5),
    ('1,250.00', 1250.0),
    ('four hundred and twenty', 420.0),
    ('300 dollars', 300.0),
]


class Amounts(unittest.TestCase):
    def test_spoken_amounts(self):
        for text, want in CASES:
            self.assertAlmostEqual(free_amount(text), want, places=2, msg=text)


if __name__ == '__main__':
    unittest.main()
