import unittest
from builder.folder_build import choose_documents, origin, validate_plan, workflow_problems, code_problems, run_vectors,platform_compatible_workflow


class FolderCompilerTests(unittest.TestCase):
    def test_platform_loop_compatibility_preserves_both_prompts_and_original(self):
        original={'nodes':{'choose':{'task_message':'Initial question','loop_prompt':'Short retry'}},'global_nodes':{'guard':{'task_message':'Initial guard','loop_prompt':'Repeat guard'}}}
        result=platform_compatible_workflow(original)
        for collection,name in (('nodes','choose'),('global_nodes','guard')):
            self.assertNotIn('loop_prompt',result[collection][name])
            self.assertIn(original[collection][name]['task_message'],result[collection][name]['task_message'])
            self.assertIn(original[collection][name]['loop_prompt'],result[collection][name]['task_message'])
            self.assertIn('{{'+name+'.current_turns}}',result[collection][name]['task_message'])
        self.assertIn('loop_prompt',original['nodes']['choose'])

    def test_generated_semantics_are_executed_and_wrong_answer_fails(self):
        tool={'type':'function','function':{'handler':'__function__:code_exec','parameters':{'properties':{'code':{'default':"vars['result'] = max(0, vars['amount'] - vars['paid'])"}}}}}
        result={'workflow':{'nodes':{'compute':{'pre_actions':[tool]}}},'tests':[{'name':'credit is not debt','node':'compute','vars':{'amount':10,'paid':15},'expect_vars':{'result':0}}]}
        self.assertIn('PASS 1',run_vectors(result))
        result['tests'][0]['expect_vars']['result']=5
        with self.assertRaises(ValueError):
            run_vectors(result)

    def test_standard_character_builtin_is_supported_in_semantic_harness(self):
        tool={'type':'function','function':{'handler':'__function__:code_exec','parameters':{'properties':{'code':{'default':"vars['result'] = chr(65)"}}}}}
        result={'workflow':{'nodes':{'compute':{'pre_actions':[tool]}}},'tests':[{'name':'standard character conversion','node':'compute','vars':{},'expect_vars':{'result':'A'}}]}
        self.assertIn('PASS 1',run_vectors(result))

    def test_global_guard_vectors_are_executed(self):
        tool={'type':'function','function':{'handler':'__function__:code_exec','parameters':{'properties':{'code':{'default':"vars['count'] = int(vars.get('count', 0)) + 1"}}}}}
        result={'workflow':{'nodes':{},'global_nodes':{'guard':{'pre_actions':[tool]}}},'tests':[{'name':'global counter','node':'guard','vars':{'count':1},'expect_vars':{'count':2}}]}
        self.assertIn('PASS 1',run_vectors(result))

    def test_unsupported_generated_code_is_rejected_without_execution(self):
        self.assertTrue(code_problems("import os\nvars['result']=os.environ"))
        self.assertTrue(code_problems("vars['result']=open('credentials').read()"))
        self.assertEqual(code_problems("import decimal\nvars['result']=str(decimal.Decimal('1.20'))"),[])

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
        f = {'type':'function','config':{'timeoutMs':30000,'maxRetries':0},'function':{'name':'send','handler':'__function__:api_call','parameters':{'properties':{'url':{'default':'https://other.example/send'},'method':{'default':'POST'},'body':{'properties':{'data':{'properties':{'wrong':{'default':'x'}}}}}}}}}
        wf = {'initial_node':'start','nodes':{'start':{'node_type':'conversation','tools':[f],'transitions':[]}}}
        plan = {'services':[{'path':'/send','method':'POST','required_request_fields':['data.item']}]}
        errors,_ = workflow_problems(wf,plan,'https://bank.example')
        self.assertTrue(any('origin' in e for e in errors))
        self.assertTrue(any('data.item' in e for e in errors))
        f['function']['parameters']['properties']['url']['default'] = 'https://bank.example/send'
        f['function']['parameters']['properties']['body']['properties']['data']['properties']['item'] = {'default':'{{selected}}'}
        self.assertEqual(workflow_problems(wf,plan,'https://bank.example')[0], [])
        f['function']['config']=f.pop('config')
        self.assertTrue(any('timeout' in e for e in workflow_problems(wf,plan,'https://bank.example')[0]))


if __name__ == '__main__':
    unittest.main()
