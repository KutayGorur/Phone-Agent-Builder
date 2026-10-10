"""Generated local scenarios (builder/generate/auto_sim.py): green on the saved specs, and they catch a spec that
closes with something the tool API or the outcome table does not allow. No Freya calls, no model calls."""
import copy
import json
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

from builder.generate import auto_sim  # noqa: E402


def load(path):
    with open(os.path.join(ROOT, path), encoding='utf-8') as f:
        return json.load(f)


API = load('tools/openapi.json')


class AutoSim(unittest.TestCase):
    def test_brief_a_green(self):
        r = auto_sim.run(load('builder/specs/brief-a.spec.json'), API, echo=False, only='early/')
        self.assertGreater(r['total'], 20)
        self.assertEqual(r['failed'], [])

    def test_variant_brief_green(self):
        r = auto_sim.run(load('builder/specs/brief-f.spec.json'), load('test-briefs/tools-f.openapi.json'), echo=False)
        self.assertGreater(r['total'], 30)
        self.assertEqual(r['failed'], [])

    def test_outcome_table_gap_is_reported(self):
        spec = copy.deepcopy(load('builder/specs/brief-a.spec.json'))
        spec['closing']['outcomes'] = [o for o in spec['closing']['outcomes'] if o['outcome'] != 'no_promise']
        r = auto_sim.run(spec, API, echo=False, only='early/credit_card:refuse_all')
        self.assertEqual(len(r['failed']), 1)
        self.assertIn('not in the spec outcome table', r['failed'][0][1][0])

    def test_outcome_the_api_rejects_is_reported(self):
        spec = copy.deepcopy(load('builder/specs/brief-a.spec.json'))
        spec['persuasion']['on_exhausted']['outcome'] = 'declined'          # not a close_call enum value
        r = auto_sim.run(spec, API, echo=False, only='early/credit_card:refuse_all')
        self.assertEqual(len(r['failed']), 1)
        self.assertTrue(any('close_call' in p for p in r['failed'][0][1]), r['failed'])

    def test_bad_tool_api_does_not_raise_in_build(self):
        sys.path.insert(0, os.path.join(ROOT, 'builder'))
        from builder import build, trace
        t = trace.Trace(echo=False)
        build.local_scenarios(load('builder/specs/brief-a.spec.json'), os.path.join(ROOT, 'builder', 'SPEC_CONTRACT.md'), '/tmp', 'x', t, 5)
        build.local_scenarios({}, os.path.join(ROOT, 'tools', 'openapi.json'), '/tmp', 'x', t, 5)


if __name__ == '__main__':
    unittest.main()
