"""Parse twice: critical facts are compared after compiling, disagreements are settled by the safer value, a quoted model
decision, or the first parse. No Freya calls, no model calls (the arbiter is faked).

    python tests/logic/test_consistency.py
"""
import copy
import json
import os
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from builder.parse import consistency as cs, prompts, spec_parser  # noqa: E402


def load(*p):
    with open(os.path.join(ROOT, *p), encoding='utf-8') as f:
        return json.load(f)


def base():
    return load('tests', 'fixtures', 'spec-e-fresh.json')


UNITS = {'u1': 'Holidays are 2026-11-20 and 2026-12-24. Calls on the late band must be kept within 5 business days.'}


class Facts(unittest.TestCase):
    def test_same_spec_no_disagreement(self):
        self.assertEqual(cs.disagreements(base(), base()), [])

    def test_key_spelling_is_not_a_disagreement(self):
        b = base()
        b['calendar']['business_days'] = ['Monday', 'tuesday', 'WED', 'Thu', 'Fri']
        b['intents'][2]['id'] = 'restructuring'
        self.assertEqual(cs.disagreements(base(), b), [])

    def test_finds_changed_facts(self):
        b = base()
        b['calendar']['holidays'].append('2026-11-30')
        b['bands'][1]['deadline']['business_days_after_today'] = 6
        b['intents'][3]['action']['transfer'] = 'support'
        b['identity']['questions'].reverse()
        ids = sorted(d['id'] for d in cs.disagreements(base(), b))
        self.assertEqual(ids, ['bands', 'holidays', 'identity_fields', 'queues'])


class Resolve(unittest.TestCase):
    def test_holidays_union_and_days_intersection(self):
        a, b = base(), base()
        b['calendar']['holidays'] = ['2026-11-20', '2026-12-31']
        b['calendar']['business_days'] = ['Mon', 'Tue', 'Wed', 'Thu']
        spec, log = cs.resolve(a, b, cs.disagreements(a, b))
        self.assertEqual(spec['calendar']['holidays'], sorted(set(a['calendar']['holidays']) | {'2026-12-31'}))
        self.assertEqual(spec['calendar']['business_days'], ['Mon', 'Tue', 'Wed', 'Thu'])
        self.assertTrue(all(e['applied'] for e in log))
        self.assertEqual(cs.disagreements(spec, spec), [])

    def test_identity_limit_keeps_the_larger(self):
        a, b = base(), base()
        b['identity']['max_wrong_answers_total'] = 3
        spec, log = cs.resolve(a, b, cs.disagreements(a, b))
        self.assertEqual(spec['identity']['max_wrong_answers_total'], 4)

    def test_no_model_keeps_first_parse(self):
        a, b = base(), base()
        b['bands'][0]['deadline']['business_days_after_today'] = 9
        spec, log = cs.resolve(a, b, cs.disagreements(a, b), decide=None)
        self.assertEqual(spec['bands'], a['bands'])
        self.assertEqual(log[0]['rule'], 'kept the first parse')

    def test_model_choice_for_second_parse_is_applied(self):
        a, b = base(), base()
        b['bands'][1]['deadline']['business_days_after_today'] = 6
        b['intents'][3]['action']['transfer'] = 'support'
        spec, log = cs.resolve(a, b, cs.disagreements(a, b), decide=lambda todo: {t['id']: 'b' for t in todo})
        self.assertEqual(spec['bands'][1]['deadline']['business_days_after_today'], 6)
        human = next(i for i in spec['intents'] if i['id'] == 'human')
        self.assertEqual(human['action']['transfer'], 'support')
        self.assertEqual(cs.disagreements(spec, b), [])

    def test_model_failure_keeps_first_parse(self):
        a, b = base(), base()
        b['bands'][0]['deadline']['business_days_after_today'] = 9

        def boom(todo):
            raise RuntimeError('no backend')
        spec, log = cs.resolve(a, b, cs.disagreements(a, b), decide=boom)
        self.assertEqual(spec['bands'], a['bands'])
        self.assertIn('no backend', log[0]['model_error'])

    def test_unreadable_second_spec_is_a_kept_value(self):
        a = base()
        b = {'meta': {}}
        spec, log = cs.resolve(a, b, cs.disagreements(a, b), decide=lambda todo: {t['id']: 'b' for t in todo})
        self.assertEqual(spec['bands'], a['bands'])


class Decisions(unittest.TestCase):
    def diffs(self):
        return [{'id': 'bands', 'label': 'x', 'a': 1, 'b': 2}, {'id': 'holidays', 'label': 'y', 'a': 3, 'b': 4}]

    def test_options_alternate_and_map_back(self):
        items = cs.decision_prompt_items(self.diffs())
        self.assertEqual((items[0]['option_1'], items[1]['option_1']), (1, 4))
        raw = {'decisions': [
            {'id': 'bands', 'choice': 'option_2', 'unit': 'u1', 'quote': 'within 5 business days'},
            {'id': 'holidays', 'choice': 'option_1', 'unit': 'u1', 'quote': 'Holidays are 2026-11-20'}]}
        self.assertEqual(cs.read_decisions(raw, self.diffs(), UNITS), {'bands': 'b', 'holidays': 'b'})

    def test_quote_must_be_in_the_unit(self):
        raw = {'decisions': [{'id': 'bands', 'choice': 'option_1', 'unit': 'u1', 'quote': 'ten business days'},
                             {'id': 'holidays', 'choice': 'option_1', 'unit': 'nope', 'quote': 'Holidays are'},
                             {'id': 'zzz', 'choice': 'option_1', 'unit': 'u1', 'quote': 'Holidays are'}]}
        self.assertEqual(cs.read_decisions(raw, self.diffs(), UNITS), {})


class CrossCheck(unittest.TestCase):
    """spec_parser.cross_check with the model replaced: a second extraction that differs, then the arbiter."""

    def run_it(self, second_mut, arbiter):
        import tempfile
        a = base()
        a.pop('parser', None)
        with tempfile.TemporaryDirectory() as d:
            sp = os.path.join(d, 'spec.json')
            with open(sp, 'w', encoding='utf-8') as f:
                json.dump(a, f)
            sec = copy.deepcopy(a)
            second_mut(sec)
            groups = {'g1': {'sections': {k: sec[k] for k in ('meta', 'call_variables', 'opening', 'third_party', 'identity', 'debt_statement')}},
                      'g2': {'sections': {k: sec[k] for k in ('calendar', 'bands', 'dates', 'amounts', 'persuasion', 'confirmation')}},
                      'g3': {'sections': {k: sec[k] for k in ('intents', 'multi_product', 'closing')}}}
            orig = (spec_parser._extract_groups, spec_parser._call_json, spec_parser._system_prompt)
            spec_parser._extract_groups = lambda *a_, **k: (groups, '')
            spec_parser._call_json = lambda purpose, system, prompt, model, timeout, retries=2: arbiter(prompt)
            spec_parser._system_prompt = lambda: 'system'
            try:
                return spec_parser.cross_check(sp, [os.path.join(ROOT, 'test-briefs', 'brief-e.md')], os.path.join(ROOT, 'test-briefs', 'tools-e.openapi.json'), 100)
            finally:
                spec_parser._extract_groups, spec_parser._call_json, spec_parser._system_prompt = orig

    def test_agreement(self):
        out = self.run_it(lambda s: None, lambda p: self.fail('no arbiter call expected'))
        c = out['parser']['consistency']
        self.assertTrue(c['checked'])
        self.assertEqual(c['disagreements'], [])

    def test_disagreement_goes_to_the_arbiter_and_is_logged(self):
        seen = []

        def arbiter(prompt):
            seen.append(prompt)
            return {'decisions': []}
        out = self.run_it(lambda s: s['bands'][0]['deadline'].update(business_days_after_today=11), arbiter)
        c = out['parser']['consistency']
        self.assertEqual([d['id'] for d in c['disagreements']], ['bands'])
        self.assertEqual(c['disagreements'][0]['rule'], 'kept the first parse')
        self.assertEqual(out['bands'][0]['deadline']['business_days_after_today'], 10)
        self.assertIn('option_1', seen[0])

    def test_incomplete_second_extraction_is_skipped(self):
        import tempfile
        a = base()
        with tempfile.TemporaryDirectory() as d:
            sp = os.path.join(d, 'spec.json')
            with open(sp, 'w', encoding='utf-8') as f:
                json.dump(a, f)
            orig = (spec_parser._extract_groups, spec_parser._system_prompt)
            spec_parser._extract_groups = lambda *a_, **k: ({}, 'down')
            spec_parser._system_prompt = lambda: 'system'
            try:
                out = spec_parser.cross_check(sp, [os.path.join(ROOT, 'test-briefs', 'brief-e.md')], os.path.join(ROOT, 'test-briefs', 'tools-e.openapi.json'), 100)
            finally:
                spec_parser._extract_groups, spec_parser._system_prompt = orig
        self.assertFalse(out['parser']['consistency']['checked'])
        self.assertEqual(out['bands'], a['bands'])


if __name__ == '__main__':
    unittest.main()
