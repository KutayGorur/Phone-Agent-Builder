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


class ToolContract(unittest.TestCase):
    def _spec(self):
        return json.load(open(os.path.join(ROOT, 'builder', 'specs', 'brief-a.spec.json'), encoding='utf-8'))

    def test_gap04_shipped_specs_match(self):
        import glob
        from builder.generate.generate import generate, tool_contract_problems
        for f in glob.glob(os.path.join(ROOT, 'builder', 'specs', '*.json')):
            s = json.load(open(f, encoding='utf-8'))
            self.assertEqual(tool_contract_problems(s, generate(s)), [], f)

    def test_gap04_renamed_field_new_required_field_and_renamed_response_are_found(self):
        from builder.generate.generate import generate, tool_contract_problems
        s = self._spec()
        wf = generate(s)                                   # built from the old contract
        cp = s['tools']['create_promise']
        cp['fields']['promise_date'] = cp['fields'].pop('date')
        cp['fields']['channel'] = {'type': 'string', 'required': True}
        cp['response_fields']['success'] = cp['response_fields'].pop('ok')
        text = ' | '.join(tool_contract_problems(s, wf))
        self.assertIn('request field date is not a field of create_promise', text)
        self.assertIn('required field promise_date of create_promise is not sent', text)
        self.assertIn('required field channel of create_promise is not sent', text)
        self.assertIn('reads data.ok', text)

    def test_gap04_value_outside_an_enum_and_changed_path(self):
        from builder.generate.generate import generate, tool_contract_problems
        s = self._spec()
        wf = generate(s)
        s['tools']['close_call']['path'] = '/finish'
        add = s['tools']['add_note']['fields']['reason']
        add['enum'] = ['only_this']
        text = ' | '.join(tool_contract_problems(s, wf))
        self.assertIn('does not end with the API path /finish', text)


class Backends(unittest.TestCase):
    def test_gap02_failing_api_falls_back_to_the_cli(self):
        calls = []
        old = (llm._call_api, llm._call_cli, os.environ.get('ANTHROPIC_API_KEY'), os.environ.get('PARSER_REPLAY_DIR'), llm.shutil.which)
        os.environ.pop('PARSER_REPLAY_DIR', None)
        os.environ['ANTHROPIC_API_KEY'] = 'sk-test-not-real-0000'
        llm.shutil.which = lambda n: 'claude' if n == 'claude' else None
        def bad_api(*a):
            calls.append('api'); raise RuntimeError('Anthropic API 401')
        def good_cli(*a):
            calls.append('cli'); return 'ok'
        llm._call_api, llm._call_cli = bad_api, good_cli
        try:
            self.assertEqual(llm.complete('p', 's', 'x'), 'ok')
            self.assertEqual(calls, ['api', 'cli'])
            llm._call_cli = lambda *a: (_ for _ in ()).throw(RuntimeError('cli down'))
            with self.assertRaises(RuntimeError):
                llm.complete('p', 's', 'x')
        finally:
            llm._call_api, llm._call_cli, key, rd, llm.shutil.which = old
            if key is None:
                os.environ.pop('ANTHROPIC_API_KEY', None)
            else:
                os.environ['ANTHROPIC_API_KEY'] = key


class BundleIdentity(unittest.TestCase):
    def test_gap11_same_final_name_in_two_bundles_does_not_collide(self):
        from builder.build import bundle_stem
        with tempfile.TemporaryDirectory() as d:
            out = pathlib.Path(d) / 'out'
            a, b = pathlib.Path(d) / 'bank-a' / 'memo.txt', pathlib.Path(d) / 'bank-b' / 'memo.txt'
            s1 = bundle_stem([str(a)], out)
            self.assertEqual(s1, 'memo')
            self.assertEqual(bundle_stem([str(a)], out), 'memo')              # a rerun keeps its slot
            s2 = bundle_stem([str(b)], out)
            self.assertNotEqual(s2, 'memo')
            self.assertEqual(bundle_stem([str(b)], out), s2)
            self.assertEqual(bundle_stem([str(a), str(b)], out), 'memo-memo')

    def test_gap11_stale_slot_is_created_again_only_on_404(self):
        from builder.build import save_with_recovery
        with tempfile.TemporaryDirectory() as d:
            st = pathlib.Path(d) / 's.json'
            st.write_text(json.dumps({'x': {'workflow_id': 'w1'}}))
            class F:
                n = 0
                def save_workflow(self, slot, wf, state_file):
                    F.n += 1
                    state = json.loads(pathlib.Path(state_file).read_text())
                    if slot in state:
                        raise RuntimeError('PUT /api/v2/workflow/w1 -> 404: not found')
                    state[slot] = {'workflow_id': 'w2'}
                    pathlib.Path(state_file).write_text(json.dumps(state))
                    return state[slot]
            class T:
                def error(self, m): pass
            self.assertEqual(save_with_recovery(F(), 'x', {}, str(st), T())['workflow_id'], 'w2')
            class G(F):
                def save_workflow(self, slot, wf, state_file):
                    raise RuntimeError('PUT /api/v2/workflow/w1 -> 401: bad key')
            with self.assertRaises(RuntimeError):
                save_with_recovery(G(), 'x', {}, str(st), T())


if __name__ == '__main__':
    unittest.main()
