"""Identity schemes: detection from the brief's format and the tool API's wording, and the pre_process hook's behaviour. Offline.

    python tests/logic/test_identity_schemes.py
"""
import json
import os
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, ROOT)

from builder.generate import identity as IDN  # noqa: E402
from builder.generate.generate import verify_pre  # noqa: E402

E = {'cal': {'dob_order': 'DMY'}}


def send(q, answers, hint='', now='2026-10-14T11:00'):
    hook = verify_pre(q, E, hint)
    v, out = {'now': now}, []
    for a in answers:
        cfg = {'body': {'answer': a}}
        exec(hook, {'config': cfg, 'vars': v})
        out.append(cfg['body']['answer'])
    return out


def kind(q, hint=''):
    return IDN.scheme(q, hint)


class Detect(unittest.TestCase):
    def test_dates(self):
        self.assertEqual(kind({'field': 'date_of_birth', 'format': 'YYYY-MM-DD'})['kind'], 'date')
        self.assertEqual(kind({'field': 'dob', 'format': ''})['kind'], 'date')

    def test_year_fields_are_digits_not_dates(self):
        for f in ('membership_year', 'account_open_year'):
            s = kind({'field': f, 'ask': 'the year', 'format': 'YYYY'})
            self.assertEqual((s['kind'], s['n']), ('digits', 4), f)

    def test_digit_counts(self):
        cases = [({'field': 'phone_last4', 'format': '4 digits'}, 4), ({'field': 'national_id_last5', 'format': 'exactly five digits as a string'}, 5),
                 ({'field': 'security_pin_last2', 'format': ''}, 2), ({'field': 'card', 'ask': 'the last 6 digits of your card'}, 6),
                 ({'field': 'postal_code', 'format': 'four digits'}, 4), ({'field': 'x', 'format': '4-digit string, keep leading zeros'}, 4)]
        for q, n in cases:
            s = kind(q)
            self.assertEqual((s['kind'], s['n']), ('digits', n), q)

    def test_tool_api_hint_decides(self):
        s = kind({'field': 'postcode', 'ask': 'the postcode of your registered address', 'format': ''}, 'four digits')
        self.assertEqual((s['kind'], s['n']), ('digits', 4))
        s = kind({'field': 'home_town', 'ask': 'where you grew up', 'format': ''}, 'lower case ASCII')
        self.assertEqual((s['kind'], s.get('case'), s.get('ascii')), ('text', 'lower', True))

    def test_postcode_with_letters_keeps_a_space_before_the_inward_part(self):
        s = kind({'field': 'postcode', 'ask': 'your postcode', 'format': 'letters and digits, like SW1A 1AA'})
        self.assertEqual((s['kind'], s['case'], s['tail']), ('alnum', 'upper', 3))

    def test_free_text_stays_free(self):
        s = kind({'field': 'maiden_name', 'ask': "your mother's maiden name", 'format': ''})
        self.assertEqual(s, {'kind': 'text'})

    def test_hint_for_one_field_is_cut_out_of_the_description(self):
        d = 'date_of_birth: YYYY-MM-DD. national_id_last5: five digits as a string. home_town: lower case ASCII. An unreadable value is rejected.'
        self.assertEqual(IDN.field_hint(d, 'home_town'), 'lower case ASCII')
        self.assertEqual(IDN.field_hint(d, 'national_id_last5'), 'five digits as a string')
        self.assertEqual(IDN.field_hint('For postcode: four digits.', 'postcode'), 'four digits')


class Hooks(unittest.TestCase):
    def test_spoken_digits(self):
        q = {'field': 'national_id_last5', 'format': 'five digits'}
        self.assertEqual(send(q, ['zero zero four one seven'])[0], '00417')
        self.assertEqual(send(q, ['oh oh four one seven'])[0], '00417')
        self.assertEqual(send(q, ['it is 0 0 4 1 7'])[0], '00417')
        self.assertEqual(send(q, ['double four one seven oh'])[0], '44170')

    def test_parts_and_long_numbers_still_work_with_words(self):
        q = {'field': 'phone_last4', 'format': '4 digits'}
        self.assertEqual(send(q, ['two two', 'one nine'])[-1], '2219')
        self.assertEqual(send(q, ['0555 123 4471'])[0], '4471')

    def test_year_field_is_not_parsed_as_a_date(self):
        self.assertEqual(send({'field': 'membership_year', 'format': 'YYYY'}, ['2014', 'twenty fourteen'])[0], '2014')

    def test_years_spoken_in_words(self):
        q = {'field': 'membership_year', 'format': 'YYYY'}
        got = send(q, ['nineteen eighty four', 'twenty fourteen', 'two thousand and five', 'nineteen oh five', 'in 2014', 'one nine eight four'])
        self.assertEqual(got, ['1984', '2014', '2005', '1905', '2014', '1984'])

    def test_text_ascii_lower(self):
        q = {'field': 'home_town', 'ask': 'where you grew up', 'format': 'lower case ASCII: o for ø, a for å; no spaces or hyphens'}
        self.assertEqual(send(q, ['Tromsø', 'Ålesund', 'Sør-Varanger', 'S o r  Varanger', 'Tønsberg', 'Ærø', 'Straße', 'São Paulo', 'Zürich'])[:9],
                         ['tromso', 'alesund', 'sorvaranger', 'sorvaranger', 'tonsberg', 'aeroe'.replace('oe', 'o'), 'strasse', 'saopaulo', 'zurich'])

    def test_text_keeps_case_and_accents_when_the_brief_does_not_say(self):
        q = {'field': 'maiden_name', 'ask': "your mother's maiden name", 'format': ''}
        self.assertEqual(send(q, ["  Ó  Brien ", "Müller"]), ["Ó Brien", "Müller"])

    def test_spelled_text_is_joined(self):
        q = {'field': 'town', 'ask': 'town', 'format': 'lower case ASCII'}
        self.assertEqual(send(q, ['O S L O'])[0], 'oslo')

    def test_postcode_with_letters(self):
        q = {'field': 'postcode', 'ask': 'your postcode', 'format': 'letters and digits, like SW1A 1AA'}
        self.assertEqual(send(q, ['sw1a1aa', 'S W one A, one A A', 'sierra whiskey one alpha one alpha alpha', 'sw1a 1aa'])[:4], ['SW1A 1AA'] * 4)
        q2 = {'field': 'postcode', 'ask': 'your postcode', 'format': 'letters and digits, no spaces'}
        self.assertEqual(send(q2, ['sw1a 1aa'])[0], 'SW1A1AA')

    def test_date_hook_unchanged(self):
        q = {'field': 'date_of_birth', 'format': 'YYYY-MM-DD', 'numeric_date_order': 'DMY'}
        self.assertEqual(send(q, ['4 March 1987', '04.03.87'])[:2], ['1987-03-04', '1987-03-04'])

    def test_hook_never_raises_and_leaves_empty_answers(self):
        for q in ({'field': 'a_last4', 'format': '4 digits'}, {'field': 'town', 'format': 'lower case ASCII'}, {'field': 'p', 'format': 'letters and digits postcode'}):
            self.assertEqual(send(q, [''])[0], '')


if __name__ == '__main__':
    unittest.main()
