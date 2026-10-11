import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from builder.folder_build import source_answer_cache,validated_compiler_cache


class SourceCacheTests(unittest.TestCase):
    def test_only_exact_source_requests_are_reused_with_provenance(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'old.model.jsonl'
            request={'type':'request','purpose':'derive source requirements','instructions':'rules','prompt':'hashed source contents'}
            response={'type':'response','purpose':request['purpose'],'text':'{"requirements":[]}'}
            path.write_text(json.dumps(request)+'\n'+json.dumps(response)+'\n',encoding='utf-8')
            current=Path(folder)/'current.model.jsonl'
            result=source_answer_cache(folder,request['purpose'],'rules',request['prompt'],current)
            self.assertEqual(result['text'],response['text'])
            self.assertEqual(result['reused_from'],str(path))
            self.assertEqual(len(result['answer_sha256']),64)
            self.assertIsNone(source_answer_cache(folder,request['purpose'],'rules','changed source',current))
            self.assertIsNone(source_answer_cache(folder,request['purpose'],'changed instructions',request['prompt'],current))
            self.assertIsNone(source_answer_cache(folder,'compile document workflow','rules',request['prompt'],current))

    def test_current_session_and_incomplete_answers_are_not_reused(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'current.model.jsonl'
            request={'type':'request','purpose':'classify document roles','instructions':'rules','prompt':'source'}
            path.write_text(json.dumps(request)+'\n',encoding='utf-8')
            self.assertIsNone(source_answer_cache(folder,request['purpose'],'rules','source',path))
            self.assertIsNone(source_answer_cache(folder,request['purpose'],'rules','source',Path(folder)/'new.model.jsonl'))

    def test_compiler_resume_requires_current_contract_coverage_and_semantics(self):
        result={'workflow':{'nodes':{}},'coverage':[{'requirement_id':'R1'}],'tests':[]}
        found={'text':json.dumps(result),'reused_from':'old','answer_sha256':'hash'}
        payload=json.dumps({'specification':{'requirements':[{'id':'R1'}]},'deployment_origin':'https://mock.example'})
        with patch('builder.folder_build._recorded_answer_cache',return_value=found), patch('builder.folder_build.workflow_problems',return_value=([],[])), patch('builder.folder_build.run_vectors',return_value='PASS') as vectors:
            self.assertEqual(validated_compiler_cache('.', 'compile document workflow','rules',payload,Path('current')),found)
            vectors.assert_called_once_with(result)
        with patch('builder.folder_build._recorded_answer_cache',return_value=found), patch('builder.folder_build.workflow_problems',return_value=(['invalid contract'],[])), patch('builder.folder_build.run_vectors') as vectors:
            self.assertIsNone(validated_compiler_cache('.', 'compile document workflow','rules',payload,Path('current')))
            vectors.assert_not_called()
        with patch('builder.folder_build._recorded_answer_cache',return_value=found), patch('builder.folder_build.workflow_problems',return_value=([],[])), patch('builder.folder_build.run_vectors',side_effect=ValueError('wrong result')):
            self.assertIsNone(validated_compiler_cache('.', 'compile document workflow','rules',payload,Path('current')))


if __name__=='__main__':
    unittest.main()
