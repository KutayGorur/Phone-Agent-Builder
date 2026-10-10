"""Fixes for the validated gap analysis (team/comms/gap-fix-verdicts.md). Offline, no model, no Freya.

    python tests/logic/test_gap_fixes.py
"""
import io
import json
import os
import sys
import tempfile
import unittest
import pathlib

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from builder import trace  # noqa: E402
from builder.parse import llm, units  # noqa: E402


class Encoding(unittest.TestCase):
    def test_gap05_console_that_cannot_show_a_character_does_not_abort(self):
        buf = io.TextIOWrapper(io.BytesIO(), encoding='cp1252', errors='strict')
        old, sys.stdout = sys.stdout, buf
        try:
            with tempfile.TemporaryDirectory() as d:
                t = trace.Trace(pathlib.Path(d) / 'x.txt')
                t.note('lira ₺ and ş')
                self.assertIn('₺', (pathlib.Path(d) / 'x.txt').read_text(encoding='utf-8'))   # the file keeps it
        finally:
            sys.stdout = old

    def test_gap05_bom_brief_keeps_its_first_numbered_rule(self):
        with tempfile.TemporaryDirectory() as d:
            f = pathlib.Path(d) / 'b.md'
            f.write_bytes(b'\xef\xbb\xbf1. First rule.\n2. Second rule.\n')
            us, _ = units.load_briefs([f])
            self.assertEqual([u['id'] for u in us][:2], ['1', '2'])

    def test_gap05_other_encodings_and_binary_fail_clearly(self):
        with tempfile.TemporaryDirectory() as d:
            f = pathlib.Path(d) / 'b.md'
            f.write_bytes('1. pay £150\n'.encode('cp1252'))
            with self.assertRaises(ValueError) as c:
                units.load_briefs([f])
            self.assertIn('UTF-8', str(c.exception))
            g = pathlib.Path(d) / 'b.docx'
            g.write_bytes(b'PK\x03\x04rest')
            with self.assertRaises(ValueError) as c:
                units.load_briefs([g])
            self.assertIn('text briefs only', str(c.exception))


class JsonBoundary(unittest.TestCase):
    def test_gap12_commentary_with_braces_and_leading_brackets(self):
        self.assertEqual(llm.extract_json('{"a": {"b": 1}}\nI kept {draft} as is.'), {'a': {'b': 1}})
        self.assertEqual(llm.extract_json('[note] here you go {"a": 1}'), {'a': 1})
        self.assertEqual(llm.extract_json('x ```json\n{"a": "}"}\n``` y {z}'), {'a': '}'})

    def test_gap12_two_different_objects_are_ambiguous(self):
        with self.assertRaises(ValueError):
            llm.extract_json('{"a": 1} and then {"a": 2}')

    def test_gap12_same_object_twice_and_bare_array_and_nothing(self):
        self.assertEqual(llm.extract_json('{"a": 1}\n{"a": 1}'), {'a': 1})
        self.assertEqual(llm.extract_json('[1, 2]'), [1, 2])
        with self.assertRaises(ValueError):
            llm.extract_json('no json here')


class TraceCounts(unittest.TestCase):
    def test_gap09_end_counts_model_lines_written_by_a_child(self):
        with tempfile.TemporaryDirectory() as d:
            p = pathlib.Path(d) / 't.txt'
            parent = trace.Trace(p, echo=False)
            child = trace.Trace(p, echo=False)          # the parse subprocess writes to the same file
            child.model_call('m', 'parse'); child.model_call('m', 'audit')
            parent.end('ok')
            self.assertIn('model_calls=2', p.read_text(encoding='utf-8'))


class Sign(unittest.TestCase):
    def test_gap13_negative_with_any_currency_sign_is_unclear(self):
        from test_engine_state import ns_for
        ns = ns_for()
        for t in ('-₺150', '- £150', '-$150', 'minus 150'):
            self.assertEqual(ns['amount_check'](t)[0], 'unclear', t)
        self.assertEqual(ns['amount_check']('₺150'), ('ok', 150.0))


class Smoke(unittest.TestCase):
    def test_gap08_syntax_error_without_braces_is_caught(self):
        from builder.generate.generate import check_code
        with self.assertRaises(SyntaxError):
            check_code('x = (1 + 2 +', 'snippet')
        check_code('x = 1', 'snippet')

    def test_gap08_broken_engine_fails_the_smoke_check(self):
        from builder.generate.generate import smoke_engine
        with self.assertRaises(Exception):
            smoke_engine('raise RuntimeError("boom")')
        with self.assertRaises(ValueError):
            smoke_engine('vars["engine_err"] = "x"')
        with self.assertRaises(ValueError):
            smoke_engine('pass')

    def test_gap08_shipped_specs_pass(self):
        import glob
        from builder.generate.generate import generate
        for f in glob.glob(os.path.join(ROOT, 'builder', 'specs', '*.json')):
            generate(json.load(open(f, encoding='utf-8')))


if __name__ == '__main__':
    unittest.main()
