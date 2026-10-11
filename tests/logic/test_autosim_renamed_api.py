"""Generated local scenarios are skipped, with a note, when the tool API does not use the seven standard routes (brief K). Offline.

    python tests/logic/test_autosim_renamed_api.py
"""
import json
import os
import sys
import tempfile
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, ROOT)

from builder import build  # noqa: E402


class Notes:
    def __init__(self):
        self.lines = []

    def note(self, m):
        self.lines.append(m)

    def error(self, m):
        self.lines.append('ERROR ' + m)


class Skip(unittest.TestCase):
    def test_renamed_routes_are_skipped_not_reported_as_95_failures(self):
        with open(os.path.join(ROOT, 'tests', 'fixtures', 'spec-i-fresh.json'), encoding='utf-8') as f:
            spec = json.load(f)
        t = Notes()
        with tempfile.TemporaryDirectory() as d:
            build.local_scenarios(spec, os.path.join(ROOT, 'test-briefs', 'tools-k.openapi.json'), d, 'k', t, 30)
        self.assertEqual(len(t.lines), 1, t.lines)
        self.assertIn('skipped', t.lines[0])
        self.assertIn('/verify_identity', t.lines[0])

    def test_standard_routes_still_run(self):
        with open(os.path.join(ROOT, 'tests', 'fixtures', 'spec-i-fresh.json'), encoding='utf-8') as f:
            spec = json.load(f)
        t = Notes()
        with tempfile.TemporaryDirectory() as d:
            build.local_scenarios(spec, os.path.join(ROOT, 'test-briefs', 'tools-i.openapi.json'), d, 'i', t, 60)
        self.assertTrue(any('passed' in l for l in t.lines), t.lines)


if __name__ == '__main__':
    unittest.main()
