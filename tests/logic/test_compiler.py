"""Spec compiler: date tokens, outcome roles, defaults, tools server, transfer fail-safe (Task 11)."""
import copy
import json
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

import importlib  # noqa: E402

G = importlib.import_module('builder.generate.generate')
from builder.generate.ecfg import build_E, build_E_warn, _date_tok, ignored_fields  # noqa: E402


def spec(name):
    with open(os.path.join(ROOT, 'builder', 'specs', 'brief-%s.spec.json' % name), encoding='utf-8') as f:
        return json.load(f)


class DateTokens(unittest.TestCase):
    def test_explicit_tokens_pass_through(self):
        for t in ('next_business_day', 'capped_next_business_day', 'deadline', 'midpoint', 'week_end', 'today'):
            self.assertEqual(_date_tok(t), t)

    def test_real_briefs(self):
        a = [p['date'] for p in build_E(spec('a'))['pers']]
        self.assertEqual(a, ['week_end', 'deadline'])
        for b in ('f', 'g'):
            toks = [p['date'] for p in build_E(spec(b))['pers']]
            self.assertEqual(toks[0], 'capped_next_business_day', b)
            self.assertEqual(toks[1], 'deadline', b)
        g = build_E(spec('g'))['pers']
        self.assertEqual(g[2]['date'], 'midpoint')
        self.assertEqual(g[2]['bd'], 3)

    def test_deadline_word_inside_other_rule_is_not_the_deadline(self):
        self.assertNotEqual(_date_tok('next business day after today, capped at the deadline'), 'deadline')
        self.assertNotEqual(_date_tok('business day at index ceiling(deadline count / 2)'), 'deadline')

    def test_unknown_text_is_not_guessed(self):
        w = []
        self.assertEqual(_date_tok('the second Tuesday after payday', w), 'unknown')
        self.assertEqual(len(w), 1)
        s = copy.deepcopy(spec('a'))
        s['persuasion']['attempts'][1]['date'] = 'whenever suits'
        E, warns = build_E_warn(s)
        self.assertEqual(E['pers'][1]['date'], 'unknown')
        self.assertTrue(any('whenever suits' in x for x in warns))

    def test_explicit_date_token_field_wins(self):
        s = copy.deepcopy(spec('a'))
        s['persuasion']['attempts'][0]['date_token'] = 'today'
        self.assertEqual(build_E(s)['pers'][0]['date'], 'today')


class OutcomeRoles(unittest.TestCase):
    def roles(self, name, mutate=None):
        s = copy.deepcopy(spec(name))
        if mutate:
            mutate(s)
        E, w = build_E_warn(s)
        return E['out'], w

    def test_baseline(self):
        for b in ('a', 'f', 'g'):
            out, _ = self.roles(b)
            self.assertTrue(all(out.values()), (b, out))

    def test_without_when_and_reordered(self):
        for b in ('a', 'f', 'g'):
            ref, _ = self.roles(b)

            def mut(s):
                outs = s['closing']['outcomes']
                for o in outs:
                    o.pop('when', None)
                outs.reverse()
            out, w = self.roles(b, mut)
            self.assertEqual(out, ref, b)
            self.assertFalse([x for x in w if 'outcome' in x and 'when' in x], (b, w))

    def test_ambiguous_promise_warns(self):
        def mut(s):
            s['intents'] = [i for i in s['intents'] if i['id'] != 'already_paid']
            for o in s['closing']['outcomes']:
                o.pop('when', None)
                if o['outcome'] == 'paid':
                    o['outcome'] = 'settled'
        out, w = self.roles('a', mut)
        self.assertTrue(any('could be the promise outcome' in x for x in w), w)

    def test_two_roles_one_outcome_warns(self):
        def mut(s):
            s['persuasion']['on_exhausted'] = {'outcome': 'promise', 'reason': None}
        out, w = self.roles('a', mut)
        self.assertTrue(any('two roles' in x for x in w), (out, w))


class Defaults(unittest.TestCase):
    def test_max_tries_zero_stays_zero(self):
        s = copy.deepcopy(spec('a'))
        s['confirmation']['create_promise_max_tries'] = 0
        self.assertEqual(build_E(s)['max_tries'], 0)
        s['confirmation'].pop('create_promise_max_tries')
        self.assertEqual(build_E(s)['max_tries'], 2)

    def test_ack_scope(self):
        self.assertEqual(build_E(spec('a'))['ack_scope'], 'per_call')
        self.assertEqual(build_E(spec('g'))['ack_scope'], 'per_record')
        s = copy.deepcopy(spec('a'))
        s['confirmation']['acknowledgement_scope'] = 'per_record'
        self.assertEqual(build_E(s)['ack_scope'], 'per_record')
        s['confirmation']['acknowledgement_scope'] = 'sometimes'
        E, w = build_E_warn(s)
        self.assertEqual(E['ack_scope'], 'per_call')
        self.assertTrue(any('acknowledgement_scope' in x for x in w))

    def test_ignored_fields_reported(self):
        s = copy.deepcopy(spec('a'))
        s['persuasion']['brand_new_rule'] = 'x'
        s['brand_new_section'] = {'a': 1}
        w = ignored_fields(s)
        self.assertTrue(any('persuasion.brand_new_rule' in x for x in w))
        self.assertTrue(any('brand_new_section' in x for x in w))
        self.assertTrue(any('identity.max_wrong_answers_total' in x for x in w))


class Workflow(unittest.TestCase):
    def urls(self, wf):
        out = set()
        for n in wf['nodes'].values():
            for a in n.get('pre_actions') or []:
                u = a.get('function', {}).get('parameters', {}).get('properties', {}).get('url')
                if u:
                    out.add(u['default'])
        return out

    def test_tools_server(self):
        s = copy.deepcopy(spec('a'))
        s['tools_server'] = 'https://example.test/api/'
        urls = self.urls(G.generate(s))
        self.assertTrue(urls and all(u.startswith('https://example.test/api/') for u in urls), urls)
        s['tools_server'] = 'not a url'
        urls = self.urls(G.generate(s))
        self.assertTrue(all(u.startswith(G.DEFAULT_BASE) for u in urls))
        self.assertTrue(any('tools_server' in x for x in G.LAST_WARNINGS))
        del s['tools_server']
        self.assertTrue(all(u.startswith(G.DEFAULT_BASE) for u in self.urls(G.generate(s))))

    def test_failed_transfer_does_not_close_as_transferred(self):
        wf = G.generate(spec('a'))
        nodes = wf['nodes']
        t = nodes['do_transfer']['transitions']
        self.assertEqual(t[0]['target_node'], 'transfer_failed')
        self.assertEqual(t[0]['condition']['conditions'][0]['operator'], 'not_equals')
        self.assertEqual(t[-1]['target_node'], 'engine')
        code = nodes['transfer_failed']['pre_actions'][0]['function']['parameters']['properties']['code']['default']
        for cp, want in (('true', 'promise'), ('false', 'no_promise')):
            v = {'cp_ok': cp}
            exec(code, {'vars': v})
            self.assertEqual(v['close_outcome'], want)
        self.assertEqual(nodes['do_close']['pre_actions'][0]['config']['maxRetries'], 1)


if __name__ == '__main__':
    unittest.main()
