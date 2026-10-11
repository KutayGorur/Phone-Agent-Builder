"""A malformed spec section is coerced or dropped with a warning; generate still runs. No Freya, no model.

    python tests/logic/test_sanitize.py
"""
import copy
import json
import os
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, ROOT)

import builder.generate  # noqa: E402,F401
GEN = sys.modules["builder.generate.generate"].generate
from builder.generate.ecfg import blocking_warnings, build_E_warn  # noqa: E402
from builder.generate.sanitize import sanitize_spec  # noqa: E402
from builder.parse import validate  # noqa: E402

GM = sys.modules['builder.generate.generate']


def base():
    with open(os.path.join(ROOT, 'tests', 'fixtures', 'spec-e-fresh.json'), encoding='utf-8') as f:
        s = json.load(f)
    s['tools']['add_note']['fields']['reason']['enum'] = ['refused', 'hardship', 'disputed', 'paid_claim', 'write_failed']
    return s


class Sanitize(unittest.TestCase):
    def test_clean_spec_is_unchanged(self):
        s = base()
        out, notes = sanitize_spec(s)
        self.assertEqual(notes, [])
        self.assertEqual(out, s)

    def test_create_promise_failure_string_is_read_when_it_names_an_allowed_reason(self):
        s = base()
        s['multi_product']['create_promise_failure'] = 'retry once; if it still fails, note write_failed on that product'
        out, notes = sanitize_spec(s)
        self.assertEqual(out['multi_product']['create_promise_failure'], {'note': {'reason': 'write_failed'}})
        self.assertEqual([n['action'] for n in notes], ['coerced'])
        E, warns = build_E_warn(s)                                     # the compiler takes the string itself too
        self.assertEqual(E['create_failed']['reason'], 'write_failed')
        self.assertEqual(blocking_warnings(warns), [])

    def test_unreadable_string_is_dropped_with_a_blocking_warning(self):
        s = base()
        s['multi_product']['create_promise_failure'] = 'retry once and carry on'
        out, notes = sanitize_spec(s)
        self.assertIsNone(out['multi_product']['create_promise_failure'])
        GEN(s)
        self.assertEqual(len(blocking_warnings(GM.LAST_WARNINGS)), 1)

    def test_every_top_level_section_may_be_a_string_without_a_crash(self):
        for key in ('meta', 'opening', 'third_party', 'identity', 'debt_statement', 'amounts', 'persuasion', 'confirmation',
                    'multi_product', 'closing', 'calendar'):
            s = base()
            s[key] = 'see the brief'
            try:
                GEN(s)
            except Exception as e:  # noqa: BLE001
                self.fail('%s as a string: %r' % (key, e))
            self.assertTrue(any(key in w and 'dropped' in w for w in GM.LAST_WARNINGS), key)

    def test_lists_with_stray_strings_keep_the_objects(self):
        s = base()
        s['bands'].append('and a severe band')
        s['persuasion']['attempts'].insert(0, 'ask first')
        out, notes = sanitize_spec(s)
        self.assertEqual(out['bands'], base()['bands'])
        self.assertEqual(out['persuasion']['attempts'], base()['persuasion']['attempts'])
        self.assertEqual(len(notes), 2)
        GEN(s)

    def test_intent_branch_string(self):
        s = base()
        s['intents'][0]['action'] = 'be nice about it'
        GEN(s)
        self.assertTrue(any('intents' in w and 'dropped' in w for w in GM.LAST_WARNINGS))


class ShapeErrors(unittest.TestCase):
    def test_parser_flags_a_non_object_create_promise_failure(self):
        s = base()
        s['multi_product']['create_promise_failure'] = 'retry once'
        errs = validate.shape_errors(s)
        self.assertTrue(any(e.startswith('multi_product.create_promise_failure must be an object') for e in errs), errs)
        self.assertEqual(validate.shape_errors(base()), [])

    def test_parser_prompt_names_the_shape(self):
        from builder.parse import prompts
        self.assertIn('after_failed_tries', prompts.SECTION_HELP['g3'][1])


if __name__ == '__main__':
    unittest.main()
