import unittest
from builder.folder_build import apply_audit_patch


class AuditPatchTests(unittest.TestCase):
    def test_focused_patch_preserves_original_and_unaffected_nodes(self):
        original={'workflow':{'nodes':{'a/b':{'prompt':'old'},'keep':{'prompt':'same'}}},'tests':[{'name':'old'}],'coverage':[]}
        result=apply_audit_patch(original,[{'op':'replace','path':'/workflow/nodes/a~1b/prompt','value':'new'},{'op':'add','path':'/tests/-','value':{'name':'new'}}])
        self.assertEqual(result['workflow']['nodes']['a/b']['prompt'],'new')
        self.assertEqual(result['workflow']['nodes']['keep'],original['workflow']['nodes']['keep'])
        self.assertEqual(original['workflow']['nodes']['a/b']['prompt'],'old')
        self.assertEqual(len(original['tests']),1)
        self.assertEqual(len(result['tests']),2)

    def test_invalid_or_out_of_range_patch_is_rejected(self):
        for operation in ({'op':'replace','path':'/workflow/missing','value':0},{'op':'remove','path':'/tests/2'},{'op':'add','path':'/credentials','value':'x'},{'op':'move','path':'/workflow/nodes'}):
            with self.subTest(operation=operation),self.assertRaises(ValueError):
                apply_audit_patch({'workflow':{'nodes':{}},'tests':[]},[operation])


if __name__=='__main__':
    unittest.main()
