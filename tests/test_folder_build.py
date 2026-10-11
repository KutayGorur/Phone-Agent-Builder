import unittest
from builder.folder_build import choose_documents, origin, validate_plan, workflow_problems


class FolderCompilerTests(unittest.TestCase):
    def test_origin_rejects_credentials_and_non_origin_urls(self):
        self.assertEqual(origin('https://bank.example/'), 'https://bank.example')
        for value in ('http://bank.example', 'https://user:secret@bank.example', 'https://bank.example/path', 'https://bank.example?token=secret'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                origin(value)

    def test_all_sources_classified_and_fixture_not_sent_to_compiler(self):
        pack = {'documents':[{'source':s,'text':'data'} for s in ('rules.md','api.md','customers.json')]}
        classification = {'documents':[{'source':'rules.md','role':'policy'}, {'source':'api.md','role':'integration'}, {'source':'customers.json','role':'fixture'}]}
        self.assertEqual([d['source'] for d in choose_documents(pack,classification)], ['rules.md','api.md'])
        classification['documents'].pop()
        with self.assertRaises(ValueError):
            choose_documents(pack,classification)

    def test_requirement_evidence_cannot_cite_nonexistent_source(self):
        plan = {'authority':[{}], 'call_variables':[{'name':'caller'}], 'requirements':[{'id':'R1','rule':'ask consent','sources':['invented.md']}], 'services':[{'path':'/preview','method':'POST','required_request_fields':['data.item']}]}
        with self.assertRaises(ValueError):
            validate_plan(plan,[{'source':'rules.md'}])

    def test_missing_nested_request_field_and_wrong_origin_are_blocked(self):
        f = {'type':'function','function':{'name':'send','handler':'__function__:api_call','config':{'timeoutMs':30000,'maxRetries':0},'parameters':{'properties':{'url':{'default':'https://other.example/send'},'method':{'default':'POST'},'body':{'properties':{'data':{'properties':{'wrong':{'default':'x'}}}}}}}}}
        wf = {'initial_node':'start','nodes':{'start':{'node_type':'conversation','tools':[f],'transitions':[]}}}
        plan = {'services':[{'path':'/send','method':'POST','required_request_fields':['data.item']}]}
        errors,_ = workflow_problems(wf,plan,'https://bank.example')
        self.assertTrue(any('origin' in e for e in errors))
        self.assertTrue(any('data.item' in e for e in errors))
        f['function']['parameters']['properties']['url']['default'] = 'https://bank.example/send'
        f['function']['parameters']['properties']['body']['properties']['data']['properties']['item'] = {'default':'{{selected}}'}
        self.assertEqual(workflow_problems(wf,plan,'https://bank.example')[0], [])


if __name__ == '__main__':
    unittest.main()
