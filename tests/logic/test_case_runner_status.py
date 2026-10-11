"""Exercise runner aggregation and artifact writing without any platform calls."""
import contextlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from tools import run_cases as runner

CASES = runner.ROOT / 'public-test-set.json'


class RunnerStatus(unittest.TestCase):
    def run_mocked(self, outcomes):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            result = root / 'result.json'
            rounds = [([{'id': 'PUB-01', 'pass': ok, 'failed': [] if ok else ['missing promise']}],
                       'sim', 'iteration', 'completed', 1, 1) for ok in outcomes]
            args = ['run_cases.py', 'agent', '--cases', str(CASES), '--only', 'PUB-01',
                    '--reps', str(len(rounds)), '--out', str(result)]
            with patch.object(runner, 'ROOT', root), patch.object(sys, 'argv', args), \
                 patch.object(runner.freya, 'create_personas', return_value={'personas': [{'id': 'persona'}]}), \
                 patch.object(runner, 'run_once', side_effect=rounds), contextlib.redirect_stdout(io.StringIO()):
                status = runner.main()
            return status, json.loads(result.read_text()), (root / 'results/log.jsonl').read_text()

    def test_failed_case_returns_failure_and_preserves_results(self):
        status, result, log = self.run_mocked([False])
        self.assertEqual(status, 1)
        self.assertEqual(result['passed'], 0)
        self.assertEqual(result['rows'][0]['failed'], ['missing promise'])
        self.assertEqual(json.loads(log)['failed'], ['PUB-01'])

    def test_final_rep_pass_does_not_hide_an_earlier_failure(self):
        status, result, _ = self.run_mocked([True, False, True])
        self.assertEqual(status, 1)
        self.assertEqual(result['final'][0]['passes'], 2)
        self.assertFalse(result['final'][0]['pass'])
        self.assertTrue(result['rows'][0]['pass'])

    def test_three_of_three_returns_success(self):
        status, result, _ = self.run_mocked([True, True, True])
        self.assertEqual(status, 0)
        self.assertEqual(result['passed'], 1)

    def test_invalid_selection_and_rep_count_never_make_platform_calls(self):
        for args in [('--only', 'DOES-NOT-EXIST'), ('--reps', '0')]:
            with self.subTest(args=args), patch.object(sys, 'argv', ['run_cases.py', 'agent', '--cases', str(CASES), *args]), \
                 patch.object(runner.freya, 'create_personas') as create, \
                 patch.object(runner, 'run_once') as simulate, contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as error:
                    runner.main()
                self.assertEqual(error.exception.code, 2)
                create.assert_not_called()
                simulate.assert_not_called()


if __name__ == '__main__':
    unittest.main()
