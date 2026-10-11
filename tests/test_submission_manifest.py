import unittest
from ci.prepare_submission import source_manifest


class SubmissionManifestTests(unittest.TestCase):
    def test_manifest_uses_run_revision_and_requires_matching_export(self):
        text='[START] build_commit='+('a'*40)+'\n[FREYA] workflow_id=agent-wf\n[END] status=ok workflow_id=agent-wf'
        args=['Team',[{'name':'A Person','email':'a@example.com'}],'https://github.com/example/builder','python builder/build.py {case_folder} --mock-url https://mock.example','https://mock.example',{'workflow_id':'agent-wf','workflow':{}},text,'submission/agent.json','submission/trace.log']
        self.assertEqual(source_manifest(*args)['commit'],'a'*40)
        args[5]['workflow_id']='other'
        with self.assertRaises(ValueError):source_manifest(*args)

    def test_failed_run_cannot_be_packaged_as_ready(self):
        with self.assertRaises(ValueError):
            source_manifest('Team',[{'name':'Person','email':'a@example.com'}],'repo','python {case_folder}','https://mock.example',{'workflow_id':'wf','workflow':{}},'[START] build_commit='+('a'*40)+'\n[END] status=failed','wf.json','trace.log')


if __name__=='__main__':unittest.main()
