"""The graph leaves the engine node by a code-free path when the engine run failed.

    python tests/logic/test_engine_guard.py

A failed sandbox run leaves `route` and `say_text` as they were, so without a guard the agent repeats its
last line. This test walks the engine node's transitions the way the platform does (first match wins).
"""
import glob
import json
import os
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from builder.generate import generate  # noqa: E402

SPECS = sorted(glob.glob(os.path.join(ROOT, 'builder', 'specs', '*.spec.json')))


def holds(c, v):
    if c.get('operator') == 'always':
        return True
    if 'conditions' in c:
        rs = [holds(x, v) for x in c['conditions']]
        return all(rs) if c.get('logic') == 'and' else any(rs)
    val, op, operand = v.get(c['variable']), c['operator'], c.get('operand')
    if op == 'equals':
        return val is not None and str(val) == str(operand)
    if op == 'not_equals':
        return val is None or str(val) != str(operand)      # true for an unset variable (PLATFORM_NOTES.md)
    if op == 'greater_than':
        try:
            return float(val) > float(operand)
        except (TypeError, ValueError):
            return False
    raise AssertionError('operator not modelled: ' + op)


def leave_engine(wf, v):
    for t in wf['nodes']['engine']['transitions']:
        if holds(t['condition'], v):
            return t['target_node']
    return None


STALE = {'route': 'say', 'say_text': 'Can you make this payment today?', 'x_intent': 'agree'}


class EngineGuard(unittest.TestCase):
    def each(self):
        for path in SPECS:
            yield os.path.basename(path), generate(json.load(open(path, encoding='utf-8')))

    def test_healthy_run_is_untouched(self):
        for name, wf in self.each():
            ok = {'engine_response.status': 'success', 'engine_success_count': 3}
            self.assertEqual(leave_engine(wf, dict(STALE, **ok)), 'say_fixed', name)
            self.assertEqual(leave_engine(wf, STALE), 'say_fixed', name + ': no counters at all must behave as before')
            # an old failure followed by a good run does not trigger the guard again
            self.assertEqual(leave_engine(wf, dict(STALE, engine_failure_count=1, **{'engine_response.status': 'success'})), 'say_fixed', name)

    def test_first_failure_asks_to_repeat(self):
        for name, wf in self.each():
            v = dict(STALE, engine_failure_count=1, **{'engine_response.status': 'error'})
            self.assertEqual(leave_engine(wf, v), 'eng_retry', name)
            n = wf['nodes']['eng_retry']
            self.assertEqual(n['on_enter']['type'], 'tts')
            self.assertNotIn(STALE['say_text'], n['on_enter']['text'])
            self.assertEqual([t['target_node'] for t in n['transitions']], ['security_eng_retry', 'engine'])
            self.assertEqual(n['transitions'][0]['condition']['variable'], 'x_security')

    def test_second_failure_closes_once_without_code(self):
        for name, wf in self.each():
            v = dict(STALE, engine_failure_count=2, **{'engine_response.status': 'error'})
            for extra, want in (({}, 'eng_fail_close'), ({'cp_ok': 'true'}, 'eng_fail_promise'), ({'cp_ok': 'pending'}, 'eng_fail_close')):
                tgt = leave_engine(wf, dict(v, **extra))
                self.assertEqual(tgt, want, name)
                n = wf['nodes'][tgt]
                fn = n['pre_actions'][0]['function']
                self.assertEqual(fn['name'], 'close_call')
                self.assertNotIn('code_exec', json.dumps(n))
                self.assertNotIn('pre_process_code', json.dumps(n))
                self.assertEqual([t['target_node'] for t in n['transitions']], ['hangup'])
                text = n['on_enter']['text'].lower()
                self.assertTrue('thank' in text and 'goodbye' in text and 'recorded' not in text, text)
                body = fn['parameters']['properties']['body']['properties']
                self.assertNotIn('{', body['outcome']['default'], 'the outcome is baked, not a variable')

    def test_close_outcomes_come_from_the_spec(self):
        for path in SPECS:
            spec = json.load(open(path, encoding='utf-8'))
            wf = generate(spec)
            table = {o['outcome']: (o.get('reasons') or []) for o in spec['closing']['outcomes']}
            for key in ('eng_fail_close', 'eng_fail_promise'):
                body = wf['nodes'][key]['pre_actions'][0]['function']['parameters']['properties']['body']['properties']
                out = body['outcome']['default']
                self.assertIn(out, table, os.path.basename(path))
                if 'reason' in body:
                    self.assertIn(body['reason']['default'], table[out], os.path.basename(path))


if __name__ == '__main__':
    unittest.main()
