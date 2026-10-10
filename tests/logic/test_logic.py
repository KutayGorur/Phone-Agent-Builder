"""Unit tests for builder.logic. Run from the repo root:

    python tests/logic/test_logic.py
"""
import datetime
import os
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from builder.logic import config_from_spec, render_all, render_snippet, run_snippet, snippet_lib as L  # noqa: E402

D = datetime.date

# Values copied from briefs/brief-a.md (via builder/SPEC_CONTRACT.md example).
SPEC_A = {
    'calendar': {
        'business_days': ['Mon', 'Tue', 'Wed', 'Thu', 'Fri'],
        'holidays': ['2026-10-26', '2026-11-11', '2026-11-26', '2026-12-25', '2027-01-01'],
    },
    'bands': [
        {'name': 'early', 'days_late_min': 1, 'days_late_max': 7,
         'deadline': {'business_days_after_today': 12}, 'persuasion_attempts': 1},
        {'name': 'late', 'days_late_min': 8, 'days_late_max': 45,
         'deadline': {'business_days_after_today': 7}, 'persuasion_attempts': 2},
    ],
    'third_party': {'callback': {
        'allowed_days': 'today_or_next_business_day', 'window_start': '10:00', 'window_end': '19:00',
        'inclusive': True, 'must_be_after_now': True}},
    'identity': {'questions': [
        {'field': 'date_of_birth', 'numeric_date_order': 'DMY'}, {'field': 'phone_last4'}]},
}

# A different calendar: Sun-Thu week, Sunday week start, other holiday, three bands,
# exclusive window, MDY dates, callback only on the next business day.
SPEC_V = {
    'calendar': {'business_days': ['Sun', 'Mon', 'Tue', 'Wed', 'Thu'], 'holidays': ['2026-10-19'],
                 'week_start': 'Sun'},
    'bands': [
        {'name': 'a', 'days_late_min': 1, 'days_late_max': 10, 'deadline': {'business_days_after_today': 5}},
        {'name': 'b', 'days_late_min': 11, 'days_late_max': 30, 'deadline': {'business_days_after_today': 3}},
        {'name': 'c', 'days_late_min': 31, 'days_late_max': None, 'deadline': {'business_days_after_today': 2}},
    ],
    'third_party': {'callback': {
        'allowed_days': 'next_business_day', 'window_start': '09:00', 'window_end': '17:00',
        'inclusive': False, 'must_be_after_now': False}},
    'identity': {'questions': [{'field': 'date_of_birth', 'numeric_date_order': 'MDY'}]},
}

CA = config_from_spec(SPEC_A)
CV = config_from_spec(SPEC_V)
TODAY = D(2026, 10, 14)  # Wednesday


def run(name, spec, **v):
    return run_snippet(render_snippet(name, spec), dict(v))


class TestCalendarA(unittest.TestCase):
    def test_today_is_wednesday(self):
        self.assertEqual(TODAY.weekday(), 2)

    def test_business_days(self):
        self.assertTrue(L.is_bd(D(2026, 10, 14), CA))
        self.assertFalse(L.is_bd(D(2026, 10, 17), CA))   # Saturday
        self.assertFalse(L.is_bd(D(2026, 10, 26), CA))   # holiday Monday

    def test_next_bd_skips_weekend_and_holiday(self):
        self.assertEqual(L.next_bd(D(2026, 10, 16), CA), D(2026, 10, 19))
        self.assertEqual(L.next_bd(D(2026, 10, 23), CA), D(2026, 10, 27))

    def test_deadlines(self):
        early = L.band_for(3, CA)
        late = L.band_for('8', CA)
        self.assertEqual(early['name'], 'early')
        self.assertEqual(late['name'], 'late')
        self.assertEqual(L.deadline_for(TODAY, late, CA), D(2026, 10, 23))
        # 12 business days, 2026-10-26 is a holiday
        self.assertEqual(L.deadline_for(TODAY, early, CA), D(2026, 11, 2))

    def test_band_edges(self):
        self.assertEqual(L.band_for(7, CA)['name'], 'early')
        self.assertEqual(L.band_for(8, CA)['name'], 'late')
        self.assertEqual(L.band_for(45, CA)['name'], 'late')
        self.assertIsNone(L.band_for(46, CA))
        self.assertIsNone(L.band_for(0, CA))
        self.assertIsNone(L.band_for('x', CA))

    def test_last_bd_of_week(self):
        self.assertEqual(L.persuasion_date(D(2026, 10, 14), CA), D(2026, 10, 16))
        # today is that day -> next week's
        self.assertEqual(L.persuasion_date(D(2026, 10, 16), CA), D(2026, 10, 23))
        # Saturday: this week's last bd is past -> next week
        self.assertEqual(L.persuasion_date(D(2026, 10, 17), CA), D(2026, 10, 23))
        # week of the holiday Monday: Friday is still the last
        self.assertEqual(L.persuasion_date(D(2026, 10, 26), CA), D(2026, 10, 30))

    def test_last_bd_when_friday_is_holiday(self):
        cfg = config_from_spec({'calendar': {'business_days': ['Mon', 'Tue', 'Wed', 'Thu', 'Fri'],
                                             'holidays': ['2026-10-16']}})
        self.assertEqual(L.persuasion_date(D(2026, 10, 14), cfg), D(2026, 10, 15))


class TestWeekdayPhrases(unittest.TestCase):
    def r(self, text, today=TODAY, cfg=CA):
        st, d = L.resolve_phrase(text, today, cfg)
        return d if st == 'ok' else st

    def test_next_and_this(self):
        self.assertEqual(self.r('next Friday'), D(2026, 10, 23))
        self.assertEqual(self.r('this Friday'), D(2026, 10, 16))
        self.assertEqual(self.r('next Monday'), D(2026, 10, 19))
        self.assertEqual(self.r('this Monday'), D(2026, 10, 12))  # before today
        self.assertEqual(self.r('next wed'), D(2026, 10, 21))

    def test_next_friday_said_on_friday(self):
        fri = D(2026, 10, 16)
        self.assertEqual(self.r('next Friday', fri), D(2026, 10, 23))
        self.assertEqual(self.r('this Friday', fri), fri)

    def test_bare_weekday(self):
        self.assertEqual(self.r('Friday'), D(2026, 10, 16))
        self.assertEqual(self.r('on monday please'), D(2026, 10, 19))

    def test_today_tomorrow_and_junk(self):
        self.assertEqual(self.r('tomorrow'), D(2026, 10, 15))
        self.assertEqual(self.r('today'), TODAY)
        self.assertEqual(self.r('when my salary comes'), 'no_match')
        self.assertEqual(self.r('end of the month'), 'no_match')

    def test_sunday_is_end_of_monday_week(self):
        sun = D(2026, 10, 18)
        self.assertEqual(self.r('this Sunday', sun), sun)
        self.assertEqual(self.r('next Monday', sun), D(2026, 10, 19))  # Sunday still in the week of Mon 10-12
        self.assertEqual(self.r('next Sunday', sun), D(2026, 10, 25))


class TestPromiseDate(unittest.TestCase):
    late_dl = D(2026, 10, 23)

    def c(self, d, dl=None, today=TODAY, cfg=CA):
        return L.check_promise_date(d, today, dl or self.late_dl, cfg)

    def test_ok(self):
        self.assertEqual(self.c(D(2026, 10, 14)), ('ok', D(2026, 10, 14)))      # today
        self.assertEqual(self.c(D(2026, 10, 23)), ('ok', D(2026, 10, 23)))      # deadline itself

    def test_past(self):
        self.assertEqual(self.c(D(2026, 10, 13)), ('in_past', None))

    def test_weekend_moves_to_monday(self):
        self.assertEqual(self.c(D(2026, 10, 17)), ('moved_to_next_business_day', D(2026, 10, 19)))
        self.assertEqual(self.c(D(2026, 10, 18)), ('moved_to_next_business_day', D(2026, 10, 19)))

    def test_holiday_moves_to_next_bd(self):
        self.assertEqual(self.c(D(2026, 10, 26), D(2026, 11, 2)), ('moved_to_next_business_day', D(2026, 10, 27)))

    def test_after_deadline_capped(self):
        self.assertEqual(self.c(D(2026, 10, 28)), ('after_deadline', self.late_dl))
        # weekend right after the deadline: still after
        self.assertEqual(self.c(D(2026, 10, 24)), ('after_deadline', self.late_dl))

    def test_today_on_weekend(self):
        sat = D(2026, 10, 17)
        self.assertEqual(self.c(sat, D(2026, 10, 28), today=sat), ('moved_to_next_business_day', D(2026, 10, 19)))

    def test_no_deadline_means_no_cap(self):
        self.assertEqual(L.check_promise_date(D(2027, 1, 4), TODAY, None, CA), ('ok', D(2027, 1, 4)))


class TestCallback(unittest.TestCase):
    NOW = 11 * 60

    def c(self, d, t, today=TODAY, now=NOW, cfg=CA):
        st, dd, mm = L.check_callback(d, t, today, now, cfg)
        return st

    def test_ok_today_and_tomorrow(self):
        self.assertEqual(self.c('2026-10-14', '14:00'), 'ok')
        self.assertEqual(self.c('2026-10-15', '10:00'), 'ok')
        self.assertEqual(self.c('tomorrow', '3pm'), 'ok')

    def test_window_inclusive(self):
        self.assertEqual(self.c('2026-10-15', '19:00'), 'ok')
        self.assertEqual(self.c('2026-10-15', '19:01'), 'out_of_window')
        self.assertEqual(self.c('2026-10-15', '09:59'), 'out_of_window')

    def test_must_be_after_now(self):
        self.assertEqual(self.c('2026-10-14', '10:30'), 'not_after_now')
        self.assertEqual(self.c('2026-10-14', '11:00'), 'not_after_now')
        self.assertEqual(self.c('2026-10-14', '11:01'), 'ok')

    def test_bad_day(self):
        self.assertEqual(self.c('2026-10-16', '12:00'), 'bad_day')
        self.assertEqual(self.c('2026-10-13', '12:00'), 'bad_day')

    def test_friday_next_business_day_is_monday(self):
        fri = D(2026, 10, 16)
        self.assertEqual(self.c('2026-10-19', '12:00', today=fri), 'ok')
        self.assertEqual(self.c('2026-10-17', '12:00', today=fri), 'bad_day')

    def test_holiday_skipped(self):
        fri = D(2026, 10, 23)
        self.assertEqual(self.c('2026-10-27', '12:00', today=fri), 'ok')
        self.assertEqual(self.c('2026-10-26', '12:00', today=fri), 'bad_day')

    def test_invalid_and_ambiguous(self):
        self.assertEqual(self.c('whenever', '12:00'), 'invalid_date')
        self.assertEqual(self.c('2026-10-15', 'later'), 'invalid_time')
        self.assertEqual(self.c('2026-10-15', '3'), 'ambiguous_time')
        self.assertEqual(self.c('2026-10-15', '25:00'), 'invalid_time')

    def test_time_parsing(self):
        for text, mins in (('3pm', 900), ('3:30 pm', 930), ('12am', 0), ('12pm', 720), ('noon', 720),
                           ('15:45', 945), ('10:00', 600), ('09:00', 540), ('7 p.m.', 1140)):
            self.assertEqual(L.parse_time(text), (mins, 'ok'), text)

    def test_variant_calendar(self):
        now = 600
        thu = D(2026, 10, 15)
        self.assertEqual(L.check_callback('2026-10-14', '12:00', TODAY, now, CV)[0], 'bad_day')  # next bd only
        self.assertEqual(L.check_callback('2026-10-15', '09:00', TODAY, now, CV)[0], 'out_of_window')  # exclusive
        self.assertEqual(L.check_callback('2026-10-15', '09:01', TODAY, now, CV)[0], 'ok')
        self.assertEqual(L.check_callback('2026-10-15', '17:00', TODAY, now, CV)[0], 'out_of_window')
        # Thursday: next business day skips Fri/Sat -> Sunday 18th
        self.assertEqual(L.check_callback('2026-10-18', '12:00', thu, now, CV)[0], 'ok')
        # must_be_after_now false: a same-day time before now is not checked
        self.assertEqual(L.check_callback('2026-10-14', '12:00', TODAY, now, config_from_spec(
            {'calendar': SPEC_V['calendar'], 'third_party': {'callback': dict(
                SPEC_V['third_party']['callback'], allowed_days='today_or_next_business_day')}}))[0], 'ok')


class TestAmounts(unittest.TestCase):
    def c(self, a, floor=100, past=500):
        return L.check_amount(a, floor, past)[0]

    def test_range(self):
        self.assertEqual(self.c(100), 'ok')
        self.assertEqual(self.c(500), 'ok')
        self.assertEqual(self.c(250.5), 'ok')
        self.assertEqual(self.c(99.99), 'below_floor')
        self.assertEqual(self.c(500.01), 'above_past_due')

    def test_formats(self):
        self.assertEqual(L.check_amount('$1,200.50', '100', '2000'), ('ok', '1200.50'))
        self.assertEqual(L.check_amount('1.200,50', 100, 2000), ('ok', '1200.50'))
        self.assertEqual(L.check_amount('300 dollars', 100.0, 500.0), ('ok', '300.00'))
        self.assertEqual(L.check_amount('1,200', 100, 2000), ('ok', '1200.00'))

    def test_invalid(self):
        for bad in ('', None, 'a lot', 0, -5, True):
            self.assertEqual(L.check_amount(bad, 100, 500)[0], 'invalid', repr(bad))

    def test_float_edge(self):
        self.assertEqual(L.check_amount(0.1 + 0.2, 0.3, 0.3)[0], 'ok')


class TestDob(unittest.TestCase):
    def n(self, s, cfg=CA, today=TODAY):
        return L.normalize_dob(s, cfg, today)

    def test_iso_and_words(self):
        self.assertEqual(self.n('1985-03-15'), ('ok', '1985-03-15', False))
        self.assertEqual(self.n('15 March 1985'), ('ok', '1985-03-15', False))
        self.assertEqual(self.n('March 15th, 1985'), ('ok', '1985-03-15', False))
        self.assertEqual(self.n('the 5th of May 1990'), ('ok', '1990-05-05', False))
        self.assertEqual(self.n('1 Sept 1971'), ('ok', '1971-09-01', False))

    def test_numeric_defaults_to_dmy(self):
        self.assertEqual(self.n('03/04/1985'), ('ok', '1985-04-03', True))
        self.assertEqual(self.n('15.03.1985'), ('ok', '1985-03-15', False))
        self.assertEqual(self.n('15-3-85'), ('ok', '1985-03-15', False))
        self.assertEqual(self.n('15031985'), ('ok', '1985-03-15', False))
        self.assertEqual(self.n('12/12/1990'), ('ok', '1990-12-12', False))

    def test_dmy_invalid_not_guessed(self):
        self.assertEqual(self.n('03/15/1985'), ('invalid', '', False))
        self.assertEqual(self.n('31/02/1990')[0], 'invalid')

    def test_two_digit_year_pivot(self):
        self.assertEqual(self.n('1/1/05')[1], '2005-01-01')
        self.assertEqual(self.n('1/1/30')[1], '1930-01-01')

    def test_range_and_junk(self):
        self.assertEqual(self.n('2030-01-01')[0], 'invalid')      # future
        self.assertEqual(self.n('1850-01-01')[0], 'invalid')
        for bad in ('', None, 'yesterday', 'March 1985', '1985'):
            self.assertEqual(self.n(bad)[0], 'invalid', repr(bad))

    def test_variant_order_mdy(self):
        self.assertEqual(self.n('03/15/1985', CV), ('ok', '1985-03-15', False))
        self.assertEqual(self.n('03/04/1985', CV), ('ok', '1985-03-04', True))
        self.assertEqual(self.n('15 March 1985', CV)[1], '1985-03-15')


class TestVariantCalendar(unittest.TestCase):
    def test_deadlines_per_band(self):
        self.assertEqual(L.deadline_for(TODAY, L.band_for(5, CV), CV), D(2026, 10, 22))   # holiday 19th skipped
        self.assertEqual(L.deadline_for(TODAY, L.band_for(20, CV), CV), D(2026, 10, 20))
        self.assertEqual(L.deadline_for(TODAY, L.band_for(99, CV), CV), D(2026, 10, 18))  # Sunday is a business day
        self.assertEqual(L.band_for(99, CV)['name'], 'c')

    def test_weekend_is_fri_sat(self):
        self.assertFalse(L.is_bd(D(2026, 10, 16), CV))
        self.assertFalse(L.is_bd(D(2026, 10, 17), CV))
        self.assertEqual(L.check_promise_date(D(2026, 10, 16), TODAY, D(2026, 10, 22), CV),
                         ('moved_to_next_business_day', D(2026, 10, 18)))

    def test_sunday_week_start(self):
        self.assertEqual(L.persuasion_date(D(2026, 10, 14), CV), D(2026, 10, 15))
        self.assertEqual(L.persuasion_date(D(2026, 10, 15), CV), D(2026, 10, 22))
        self.assertEqual(L.resolve_phrase('next sunday', TODAY, CV), ('ok', D(2026, 10, 18)))
        self.assertEqual(L.resolve_phrase('this sunday', TODAY, CV), ('ok', D(2026, 10, 11)))
        self.assertEqual(L.resolve_phrase('sunday', TODAY, CV), ('ok', D(2026, 10, 18)))

    def test_empty_calendar_does_not_hang(self):
        cfg = dict(CA, bd=[])
        self.assertIsNone(L.next_bd(TODAY, cfg))
        self.assertIsNone(L.add_bd(TODAY, 3, cfg))
        self.assertIsNone(L.persuasion_date(TODAY, cfg))


class TestConfig(unittest.TestCase):
    def test_from_spec(self):
        self.assertEqual(CA['bd'], [0, 1, 2, 3, 4])
        self.assertEqual((CA['cb_start'], CA['cb_end']), (600, 1140))
        self.assertEqual(CA['dob_order'], 'DMY')
        self.assertEqual(CV['bd'], [0, 1, 2, 3, 6])
        self.assertEqual(CV['week_start'], 6)
        self.assertFalse(CV['cb_inclusive'])
        self.assertEqual(CV['dob_order'], 'MDY')

    def test_missing_sections_are_reported_not_fatal(self):
        cfg = config_from_spec({})
        self.assertTrue(cfg['warnings'])
        self.assertEqual(cfg['bands'], [])
        self.assertIsNone(cfg['cb_start'])


class TestRenderedSnippets(unittest.TestCase):
    """The shipped code strings, executed the way the platform does."""

    def test_no_braces_and_compiles(self):
        for spec in (SPEC_A, SPEC_V, {}):
            for name, code in render_all(spec).items():
                self.assertNotIn('{{', code, name)
                self.assertNotIn('}}', code, name)
                compile(code, name, 'exec')

    def test_date_facts(self):
        v = run('date_facts', SPEC_A, now='2026-10-14T11:00', days_late=3)
        self.assertEqual(v['date_facts_status'], 'known')
        self.assertEqual(v['today'], '2026-10-14')
        self.assertEqual(v['today_weekday'], 'Wednesday')
        self.assertEqual(v['band'], 'early')
        self.assertEqual(v['deadline'], '2026-11-02')
        self.assertEqual(v['persuasion_date'], '2026-10-16')
        self.assertEqual(v['next_business_day'], '2026-10-15')
        self.assertIn('Saturday 2026-10-17 (not a business day)', v['date_facts'])
        self.assertIn('2026-10-26', v['date_facts'])
        self.assertIsInstance(v['date_facts'], str)

    def test_date_facts_fallbacks(self):
        v = run('date_facts', SPEC_A)  # no now, no days_late
        self.assertEqual(v['date_facts_status'], 'unknown')
        self.assertEqual(v['deadline'], '')
        v = run('date_facts', SPEC_A, now='2026-10-14T11:00', days_late='n/a')
        self.assertEqual(v['date_facts_status'], 'known')
        self.assertEqual(v['deadline'], '')
        self.assertEqual(v['band'], '')

    def test_check_promise_date(self):
        base = dict(now='2026-10-14T11:00', days_late=10)
        v = run('check_promise_date', SPEC_A, promise_date_input='2026-10-17', **base)
        self.assertEqual((v['promise_date_status'], v['promise_date_final']), ('moved_to_next_business_day', '2026-10-19'))
        self.assertEqual(v['promise_date_deadline'], '2026-10-23')
        v = run('check_promise_date', SPEC_A, promise_date_input='next Friday', **base)
        self.assertEqual((v['promise_date_status'], v['promise_date_final']), ('ok', '2026-10-23'))
        v = run('check_promise_date', SPEC_A, promise_date_input='2026-11-03', **base)
        self.assertEqual((v['promise_date_status'], v['promise_date_final']), ('after_deadline', '2026-10-23'))
        v = run('check_promise_date', SPEC_A, promise_date_input='end of the month', **base)
        self.assertEqual(v['promise_date_status'], 'invalid')
        v = run('check_promise_date', SPEC_A, promise_date_input='2026-10-01', **base)
        self.assertEqual(v['promise_date_status'], 'in_past')

    def test_check_promise_date_uses_given_deadline(self):
        v = run('check_promise_date', SPEC_A, now='2026-10-14T11:00', deadline='2026-10-20',
                promise_date_input='2026-10-21')
        self.assertEqual((v['promise_date_status'], v['promise_date_final']), ('after_deadline', '2026-10-20'))

    def test_var_map_and_prefix(self):
        code = render_snippet('check_promise_date', SPEC_A, var_map={'days_late': 'p1_days_late'}, out_prefix='p1_')
        v = run_snippet(code, {'now': '2026-10-14T11:00', 'p1_days_late': 3, 'promise_date_input': '2026-10-15'})
        self.assertEqual(v['p1_promise_date_final'], '2026-10-15')
        self.assertEqual(v['p1_promise_date_deadline'], '2026-11-02')
        self.assertNotIn('promise_date_final', v)
        with self.assertRaises(KeyError):
            render_snippet('check_promise_date', SPEC_A, var_map={'nope': 'x'})

    def test_check_callback(self):
        v = run('check_callback', SPEC_A, now='2026-10-14T11:00', callback_date_input='tomorrow',
                callback_time_input='3pm')
        self.assertEqual((v['callback_status'], v['callback_date'], v['callback_time']), ('ok', '2026-10-15', '15:00'))
        v = run('check_callback', SPEC_A, now='2026-10-14T11:00', callback_date_input='2026-10-14',
                callback_time_input='19:30')
        self.assertEqual(v['callback_status'], 'out_of_window')
        self.assertEqual(v['callback_next_business_day'], '2026-10-15')

    def test_check_amount(self):
        v = run('check_amount', SPEC_A, amount_input='250', floor_amount=100, past_due='500.00')
        self.assertEqual((v['amount_status'], v['amount_value']), ('ok', '250.00'))
        v = run('check_amount', SPEC_A, amount_input='50', floor_amount=100, past_due=500)
        self.assertEqual(v['amount_status'], 'below_floor')

    def test_normalize_dob(self):
        v = run('normalize_dob', SPEC_A, now='2026-10-14T11:00', dob_input='3rd of April 1985')
        self.assertEqual((v['dob_status'], v['dob_value'], v['dob_ambiguous']), ('ok', '1985-04-03', 'false'))
        v = run('normalize_dob', SPEC_A, now='2026-10-14T11:00', dob_input='03/04/1985')
        self.assertEqual((v['dob_value'], v['dob_ambiguous']), ('1985-04-03', 'true'))
        v = run('normalize_dob', SPEC_V, now='2026-10-14T11:00', dob_input='03/04/1985')
        self.assertEqual(v['dob_value'], '1985-03-04')
        v = run('normalize_dob', SPEC_A, dob_input='garbage')
        self.assertEqual((v['dob_status'], v['dob_value']), ('invalid', ''))

    def test_resolve_weekday(self):
        v = run('resolve_weekday', SPEC_A, now='2026-10-14T11:00', weekday_phrase='next Friday')
        self.assertEqual((v['weekday_status'], v['weekday_date']), ('ok', '2026-10-23'))
        v = run('resolve_weekday', SPEC_A, now='2026-10-14T11:00', weekday_phrase='soon')
        self.assertEqual(v['weekday_status'], 'no_match')

    def test_never_raises_on_garbage_vars(self):
        garbage = {'now': object(), 'days_late': [1], 'deadline': {}, 'promise_date_input': 5,
                   'callback_date_input': None, 'callback_time_input': 3.5, 'amount_input': {},
                   'floor_amount': 'x', 'past_due': None, 'dob_input': 12, 'weekday_phrase': 7}
        for spec in (SPEC_A, {}):
            for name, code in render_all(spec).items():
                v = run_snippet(code, dict(garbage))
                self.assertTrue(any(isinstance(x, str) for x in v.values()), name)

    def test_variant_snippet(self):
        v = run('date_facts', SPEC_V, now='2026-10-14T11:00', days_late=20)
        self.assertEqual(v['deadline'], '2026-10-20')
        self.assertEqual(v['band'], 'b')
        self.assertEqual(v['persuasion_date'], '2026-10-15')
        self.assertIn('Friday 2026-10-16 (not a business day)', v['date_facts'])


if __name__ == '__main__':
    unittest.main()
