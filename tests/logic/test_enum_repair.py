"""Enum guard: values outside the tool API's enums are found, spelling variants are renamed for free, the rest goes to one
targeted model repair (faked here). No Freya calls, no model calls."""
import copy
import json
import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

from builder.parse import enum_repair as er, spec_parser  # noqa: E402


def spec():
    with open(os.path.join(ROOT, 'builder', 'specs', 'brief-a.spec.json'), encoding='utf-8') as f:
        return json.load(f)


def out(s, name):
    return next(o for o in s['closing']['outcomes'] if o['outcome'] == name)


class EnumRepair(unittest.TestCase):
    def test_saved_specs_have_no_problems(self):
        for n in ('a', 'ab', 'f', 'g', 'h'):
            with open(os.path.join(ROOT, 'builder', 'specs', 'brief-%s.spec.json' % n), encoding='utf-8') as f:
                self.assertEqual(er.enum_problems(json.load(f)), [], n)

    def test_finds_outcome_queue_note_reason_field_and_tool(self):
        s = spec()
        out(s, 'paid')['outcome'] = 'settled'
        s['intents'][2]['action']['transfer'] = 'plans'
        s['multi_product'] = {'note_tool': 'log_note', 'note_reasons': ['refused', 'weather']}
        s['identity']['questions'][0]['field'] = 'dob'
        kinds = sorted(p['kind'] for p in er.enum_problems(s))
        self.assertEqual(kinds, ['id_field', 'note_reason', 'outcome', 'queue', 'tool'])

    def test_spelling_variants_are_renamed_everywhere_meanings_are_not(self):
        s = spec()
        out(s, 'not_verified')['outcome'] = 'Not-Verified'
        out(s, 'no_promise')['outcome'] = 'declined'
        s['persuasion']['on_exhausted']['outcome'] = 'declined'
        s['intents'][2]['action']['transfer'] = 'Restructuring'
        fixed, changes = er.auto_repair(s)
        self.assertEqual(len(changes), 2)
        self.assertEqual([p['value'] for p in er.enum_problems(fixed)], ['declined', 'declined'])
        self.assertEqual(fixed['intents'][2]['action']['transfer'], 'restructuring')
        self.assertEqual(s['intents'][2]['action']['transfer'], 'Restructuring')        # input untouched

    def test_not_prefix_is_never_dropped(self):
        self.assertIsNone(er.closest('verified', ['not_verified', 'paid']))
        self.assertEqual(er.closest('NOT VERIFIED', ['not_verified', 'paid']), 'not_verified')

    def test_guard_enums_renames_then_asks_the_model_once(self):
        s = spec()
        out(s, 'not_verified')['outcome'] = 'notverified'
        out(s, 'no_promise')['outcome'] = 'declined'
        s['persuasion']['on_exhausted']['outcome'] = 'declined'
        calls = []

        def fake(purpose, system, prompt, model, timeout, retries=2):
            calls.append(purpose)
            self.assertIn("'declined'", prompt)
            fixed = copy.deepcopy(s)
            out(fixed, 'notverified')['outcome'] = 'not_verified'
            out(fixed, 'declined')['outcome'] = 'no_promise'
            fixed['persuasion']['on_exhausted']['outcome'] = 'no_promise'
            return {'sections': {'closing': fixed['closing'], 'persuasion': fixed['persuasion']}, 'notes': []}
        real, spec_parser._call_json = spec_parser._call_json, fake
        try:
            with tempfile.TemporaryDirectory() as d:
                p = os.path.join(d, 's.json')
                with open(p, 'w', encoding='utf-8') as f:
                    json.dump(s, f)
                new = spec_parser.guard_enums(p, [os.path.join(ROOT, 'briefs', 'brief-a.md')], os.path.join(ROOT, 'tools', 'openapi.json'))
        finally:
            spec_parser._call_json = real
        self.assertEqual(len(calls), 1)
        self.assertEqual(er.enum_problems(new), [])
        self.assertTrue(any('renamed' in x for x in new['parser']['enum_repair']))

    def test_model_repair_that_does_not_help_is_dropped(self):
        s = spec()
        out(s, 'no_promise')['outcome'] = 'declined'
        real, spec_parser._call_json = spec_parser._call_json, (lambda *a, **k: {'sections': {'closing': {'outcomes': [{'outcome': 'nonsense', 'reasons': []}]}}})
        try:
            with tempfile.TemporaryDirectory() as d:
                p = os.path.join(d, 's.json')
                with open(p, 'w', encoding='utf-8') as f:
                    json.dump(s, f)
                new = spec_parser.guard_enums(p, [os.path.join(ROOT, 'briefs', 'brief-a.md')], os.path.join(ROOT, 'tools', 'openapi.json'))
        finally:
            spec_parser._call_json = real
        self.assertIn('declined', [o['outcome'] for o in new['closing']['outcomes']])
        self.assertTrue(any('did not reduce' in x for x in new['parser']['enum_repair']))


if __name__ == '__main__':
    unittest.main()
