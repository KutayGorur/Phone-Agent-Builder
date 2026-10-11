import unittest
from ci.lint_workflow import lint,workflow_definition


class ExportLintTests(unittest.TestCase):
    def test_export_metadata_and_platform_configuration_do_not_hide_graph_checks(self):
        graph={'initial_node':'start','agent_config':{'llmConfig':{}},'nodes':{'start':{'node_type':'conversation','transitions':[{'target_node':'missing'}]}}}
        document={'workflow_id':'published','agent_id':'agent','workflow':graph}
        checked=workflow_definition(document)
        errors,_=lint(checked)
        self.assertTrue(any('missing' in e for e in errors))
        self.assertFalse(any('agent_config' in e for e in errors))
        self.assertIn('agent_config',graph)

    def test_raw_generated_config_still_fails(self):
        graph={'initial_node':'end','agent_config':{},'nodes':{'end':{'node_type':'end_call'}}}
        self.assertTrue(any('agent_config' in e for e in lint(workflow_definition(graph))[0]))


if __name__=='__main__':
    unittest.main()
