"""Band deadlines in calendar days (brief J): rolled back (or forward) to a business day; unreadable deadlines are blocking. Offline.

    python tests/logic/test_calendar_deadlines.py
"""
import copy
import datetime as dt
import json
import os
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, ROOT)

from builder.generate import auto_sim  # noqa: E402
from builder.generate.ecfg import blocking_warnings, build_E_warn  # noqa: E402
from builder.logic import snippet_lib as sl  # noqa: E402
from builder.logic.config import read_deadline  # noqa: E402
from builder.parse import validate  # noqa: E402


def spec():
    with open(os.path.join(ROOT, 'tests', 'fixtures', 'spec-j-fresh.json'), encoding='utf-8') as f:
        return json.load(f)


class Read(unittest.TestCase):
    def test_shapes(self):
        self.assertEqual(read_deadline({'business_days_after_today': 5}), (5, None, 'back'))
        self.assertEqual(read_deadline({'calendar_days_after_today': 10, 'if_non_business_day': 'move back to the previous working day'}), (None, 10, 'back'))
        self.assertEqual(read_deadline({'calendar_days': 6, 'if_non_business_day': 'move forward to the next business day'}), (None, 6, 'forward'))
        self.assertEqual(read_deadline({'calendar_days_after_today': '7'})[1], 7)
        self.assertEqual(read_deadline({'text': 'soon'})[:2], (None, None))
        self.assertEqual(read_deadline(None)[:2], (None, None))


class Deadline(unittest.TestCase):
    def setUp(self):
        self.E, self.warns = build_E_warn(spec())
        self.cal = self.E['cal']

    def band(self, name):
        return next(b for b in self.cal['bands'] if b['name'] == name)

    def test_compiled_bands_carry_calendar_days(self):
        self.assertEqual((self.band('early')['deadline_cd'], self.band('late')['deadline_cd']), (10, 6))
        self.assertEqual(blocking_warnings(self.warns), [])

    def test_rolls_back_over_a_sunday_and_a_holiday(self):
        # Thursday 22 April 2027 + 10 calendar days = Sunday 2 May -> Saturday 1 May is a working day (Mon-Sat week)
        today = dt.date(2027, 4, 22)
        d = sl.deadline_for(today, self.band('early'), self.cal)
        self.assertTrue(sl.is_bd(d, self.cal))
        self.assertLessEqual(d, today + dt.timedelta(days=10))
        self.assertGreater(d, today + dt.timedelta(days=7))
        # a closed day exactly at the deadline: move back to the last open day
        cal2 = dict(self.cal, holidays=sorted(set(self.cal['holidays']) | {(today + dt.timedelta(days=6)).isoformat()}))
        d2 = sl.deadline_for(today, self.band('late'), cal2)
        self.assertEqual(d2, today + dt.timedelta(days=5))

    def test_forward_roll(self):
        today = dt.date(2027, 5, 9)              # Sunday; +6 = Saturday 15 May (made a holiday here), Sunday 16 is closed anyway
        b = dict(self.band('late'), deadline_roll='forward')
        cal2 = dict(self.cal, holidays=sorted(set(self.cal['holidays']) | {'2027-05-15'}))
        self.assertEqual(sl.deadline_for(today, b, cal2), dt.date(2027, 5, 17))
        self.assertEqual(sl.deadline_for(today, dict(b, deadline_roll='back'), cal2), dt.date(2027, 5, 14))

    def test_business_day_count_for_the_midpoint(self):
        today = dt.date(2027, 4, 22)
        n = sl.deadline_bd_count(today, self.band('early'), self.cal)
        self.assertTrue(5 <= n <= 9)
        self.assertEqual(sl.deadline_bd_count(today, {'deadline_bd': 7}, self.cal), 7)


class Blocking(unittest.TestCase):
    def test_band_without_any_readable_deadline_is_blocking(self):
        s = spec()
        s['bands'][0]['deadline'] = {'when': 'soon'}
        _, warns = build_E_warn(s)
        self.assertTrue([w for w in blocking_warnings(warns) if 'no deadline' in w])

    def test_parser_validation_flags_it(self):
        s = spec()
        s['bands'][0]['deadline'] = {'when': 'soon'}
        errs, warns = [], []
        validate._check_calendar_bands(s, [], {}, errs, warns, False)
        self.assertTrue([e for e in errs if 'no readable number' in e], errs)
        errs = []
        validate._check_calendar_bands(spec(), [], {}, errs, warns, False)
        self.assertEqual(errs, [])


class Generated(unittest.TestCase):
    def test_shared_date_beyond_the_deadline_is_capped(self):
        with open(os.path.join(ROOT, 'test-briefs', 'tools-j.openapi.json'), encoding='utf-8') as f:
            api = json.load(f)
        res = auto_sim.run(spec(), api, echo=False)
        self.assertEqual(res['failed'], [])


if __name__ == '__main__':
    unittest.main()
