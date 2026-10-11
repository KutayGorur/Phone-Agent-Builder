import unittest
from tools.run_document_cases import api_dispatches, dispatch_problems


class DocumentCaseRunnerTests(unittest.TestCase):
    def test_actual_dispatches_only_and_nested_request_checks(self):
        call = {'messages':[
            {'role':'assistant','message':'I will send it'},
            {'role':'system','message':'{"event":"function_call_start","args":{"url":"https://bank.example/send","body":{"data":{"item":"selected"}}}}'},
            {'role':'system','message':'{"event":"function_call_complete","result":{"ok":true}}'},
        ]}
        calls=api_dispatches(call)
        self.assertEqual(len(calls),1)
        case={'tool_checks':[{'path':'/send','min':1,'max':1,'body_equals':{'data.item':'selected'}}]}
        self.assertEqual(dispatch_problems(case,calls),[])
        self.assertTrue(dispatch_problems(case,calls+calls))
        case['tool_checks'][0]['body_equals']['data.item']='other'
        self.assertTrue(dispatch_problems(case,calls))

    def test_claim_is_not_evidence_of_a_completed_tool_call(self):
        calls=api_dispatches({'messages':[{'role':'assistant','message':'Sent successfully'}]})
        self.assertTrue(dispatch_problems({'tool_checks':[{'path':'/send','min':1,'max':1}]},calls))


if __name__=='__main__':
    unittest.main()
