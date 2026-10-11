"""Latency must count unanswered customer turns, not system events as replies."""
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from tools.run_cases import call_waits


class CaseLatency(unittest.TestCase):
    def test_system_events_do_not_end_the_wait_for_a_spoken_reply(self):
        call = {'messages': [{'role': 'user', 'secondsFromStart': 1},
                             {'role': 'system', 'secondsFromStart': 6},
                             {'role': 'assistant', 'secondsFromStart': 14}]}
        self.assertEqual(call_waits(call), (13.0, None))

    def test_hangup_before_reply_counts_the_final_silence(self):
        call = {'startedAt': '2026-10-11T12:00:00Z', 'endedAt': '2026-10-11T12:01:28Z',
                'messages': [{'role': 'assistant', 'secondsFromStart': 18},
                             {'role': 'user', 'secondsFromStart': 28},
                             {'role': 'system', 'secondsFromStart': 51}]}
        self.assertEqual(call_waits(call), (60.0, 60.0))

    def test_hangup_after_only_opening_does_not_report_zero(self):
        call = {'startedAt': '2026-10-11T12:00:00+00:00', 'endedAt': '2026-10-11T12:01:01+00:00',
                'messages': [{'role': 'assistant', 'secondsFromStart': 0},
                             {'role': 'user', 'secondsFromStart': 1}]}
        self.assertEqual(call_waits(call), (60.0, 60.0))

    def test_missing_end_timestamp_is_unknown_instead_of_zero(self):
        self.assertEqual(call_waits({'messages': [{'role': 'user', 'secondsFromStart': 1}]}), (None, None))


if __name__ == '__main__':
    unittest.main()
