import os
import subprocess
import unittest
from unittest.mock import patch
from builder.parse import llm


class CliEffortTests(unittest.TestCase):
    def test_selected_effort_reaches_cli_without_enabling_tools(self):
        response = subprocess.CompletedProcess([],0,'{"result":"ok"}','')
        with patch.dict(os.environ,{'PARSER_EFFORT':'medium'}), patch.object(llm.shutil,'which',return_value='claude'), patch.object(llm.subprocess,'run',return_value=response) as run:
            self.assertEqual(llm._call_cli('model','system','prompt',10),'ok')
        command = run.call_args.args[0]
        self.assertEqual(command[command.index('--effort')+1],'medium')
        self.assertEqual(command[command.index('--tools')+1],'')

    def test_invalid_effort_fails_before_starting_process(self):
        with patch.dict(os.environ,{'PARSER_EFFORT':'invalid'}), patch.object(llm.shutil,'which',return_value='claude'), patch.object(llm.subprocess,'run') as run:
            with self.assertRaises(ValueError):
                llm._call_cli('model','system','prompt',10)
        run.assert_not_called()

    def test_cli_failure_reports_reason_instead_of_usage_metadata(self):
        response = subprocess.CompletedProcess([],1,'{"usage":{"input_tokens":0},"result":"Usage limit reached"}','')
        with patch.object(llm.shutil,'which',return_value='claude'), patch.object(llm.subprocess,'run',return_value=response):
            with self.assertRaisesRegex(RuntimeError,'Usage limit reached'):
                llm._call_cli('model','system','prompt',10)


if __name__ == '__main__':
    unittest.main()
