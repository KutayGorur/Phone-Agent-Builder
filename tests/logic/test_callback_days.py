"""Callback day rules: today, next business day, 'today or the next N working days' (brief J). Offline.

    python tests/logic/test_callback_days.py
"""
import datetime as dt
import json
import os
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, ROOT)

from builder.generate import auto_sim  # noqa: E402
from builder.generate.ecfg import blocking_warnings, build_E_warn, canon_cb_days  # noqa: E402
from builder.generate.generate import engine_code  # noqa: E402


def spec():
    with open(os.path.join(ROOT, 'tests', 'fixtures', 'spec-j-fresh.json'), encoding='utf-8') as f:
        return json.load(f)


class Canon(unittest.TestCase):
    def test_spellings(self):
        table = {
            'today_or_next_two_working_days': 'today_or_next_2_business_days', 'today or the next 3 business days': 'today_or_next_3_business_days',
            'next_two_business_days': 'next_2_business_days', 'today_or_next_business_day': 'today_or_next_business_day',
            'next business day': 'next_business_day', 'today': 'today', 'any_business_day': 'any_business_day',
            'next working day': 'next_business_day',
        }
        for k, v in table.items():
            self.assertEqual(canon_cb_days(k), v, k)

    def test_unknown_text_warns_and_blocks(self):
        s = spec()
        s['third_party']['callback']['allowed_days'] = 'whenever suits'
        E, warns = build_E_warn(s)
        self.assertEqual(E['cal']['cb_days'], 'today_or_next_business_day')
        self.assertTrue(blocking_warnings(warns))


class Engine(unittest.TestCase):
    def check(self, day, hhmm='10:00', today='2027-04-27', now='11:00'):
        E, _ = build_E_warn(spec())
        ns = {'vars': {'now': today + 'T' + now, 'st': ''}}
        exec(compile(engine_code(E), 'engine', 'exec'), ns)
        d = dt.date.fromisoformat(day)
        return ns['cb_check'](d, ns['parse_time'](hhmm)[0] if 'parse_time' in ns else 600, dt.date.fromisoformat(today))[0]

    def test_second_working_day_is_allowed_third_is_not(self):
        # Tuesday 27 April 2027: Wed 28 = 1st, Thu 29 = 2nd (a holiday, see the spec calendar) -> check against the spec's own days
        E, _ = build_E_warn(spec())
        ns = {'vars': {'now': '2027-04-27T11:00', 'st': ''}}
        exec(compile(engine_code(E), 'engine', 'exec'), ns)
        add_bd, is_bd = ns['add_bd'], ns['is_bd']
        today = dt.date(2027, 4, 27)
        second = add_bd(today, 2, ns['CAL'])
        third = add_bd(today, 3, ns['CAL'])
        self.assertEqual(ns['cb_check'](second, 600, today)[0], 'ok')
        self.assertEqual(ns['cb_check'](third, 600, today)[0], 'bad_day')
        self.assertEqual(ns['cb_check'](today, 20 * 60, today)[0], 'out_of_window')        # today is allowed, the window is not
        sunday = next(today + dt.timedelta(days=i) for i in range(1, 8) if not is_bd(today + dt.timedelta(days=i), ns['CAL']))
        self.assertEqual(ns['cb_check'](sunday, 600, today)[0], 'bad_day')

    def test_generated_customers_all_pass(self):
        with open(os.path.join(ROOT, 'test-briefs', 'tools-j.openapi.json'), encoding='utf-8') as f:
            api = json.load(f)
        res = auto_sim.run(spec(), api, echo=False)
        self.assertEqual(res['failed'], [])


if __name__ == '__main__':
    unittest.main()
