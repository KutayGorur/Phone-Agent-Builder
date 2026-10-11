"""Offline regression checks for model outages after extraction and exported builds."""
import copy
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from builder import build, trace
from builder.parse import prompts, spec_parser


class ModelFailureStatus(unittest.TestCase):
    def setUp(self):
        previous = trace.get()
        trace.set_current(trace.Trace(echo=False))
        self.addCleanup(trace.set_current, previous)

    def parse_with_calls(self, calls):
        golden = json.loads((ROOT / "builder/specs/brief-a.spec.json").read_text())
        extraction = {g: {"sections": golden if i == 0 else {}, "extra_rules": [],
                          "rule_coverage": {}, "open_questions": []}
                      for i, g in enumerate(prompts.SECTION_HELP)}
        with patch.object(spec_parser, "_extract_groups", return_value=(extraction, "")), \
             patch.object(spec_parser, "_call_json", side_effect=calls), \
             patch.object(spec_parser.validate_mod, "validate", return_value=([], [])), \
             patch.object(spec_parser.validate_mod, "shape_errors", return_value=[]), \
             patch.object(spec_parser, "_debug"):
            return spec_parser.parse([ROOT / "briefs/brief-a.md"], ROOT / "tools/openapi.json")

    def test_audit_auth_failure_keeps_extracted_spec_but_marks_degraded(self):
        spec = self.parse_with_calls(RuntimeError("Anthropic API 401: invalid API key"))
        self.assertTrue(spec["parser"]["degraded"])
        self.assertIn("401", spec["parser"]["reason"])
        self.assertTrue(spec["identity"]["questions"])
        self.assertTrue(build.readiness_problems(spec))

    def test_repair_usage_limit_cannot_disappear_when_validation_is_clean(self):
        spec = self.parse_with_calls([{"issues": [{"type": "wrong", "detail": "wrong policy"}]},
                                      RuntimeError("usage limit reached")])
        self.assertTrue(spec["parser"]["degraded"])
        self.assertIn("repair model call failed", spec["parser"]["reason"])

    def test_successful_audit_stays_ready(self):
        spec = self.parse_with_calls([{"issues": []}])
        self.assertFalse(spec["parser"]["degraded"])
        self.assertEqual(build.readiness_problems(spec), [])

    def test_degraded_freya_export_returns_nonzero(self):
        spec = self.parse_with_calls(RuntimeError("usage limit reached"))
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            exported = []
            def export(wid, path):
                Path(path).write_text(json.dumps({"workflow_id": wid, "workflow": {}}))
                exported.append(path)
                return path
            freya = SimpleNamespace(validate_workflow=lambda *a: None,
                                    save_workflow=lambda *a, **k: {"workflow_id": "existing", "agent_id": "agent"},
                                    export_workflow=export)
            def load(module, name):
                return (lambda *a: {"nodes": {}}) if module == "generate" else None
            with patch.dict(sys.modules, {"freya": freya}), \
                 patch.object(build, "STATE_FILE", str(tmp / "state.json")), \
                 patch.object(build, "run_parse_subprocess", return_value=copy.deepcopy(spec)), \
                 patch.object(build, "_load", side_effect=load):
                rc = build.main([str(ROOT / "briefs/brief-a.md"), str(ROOT / "tools/openapi.json"),
                                 "--parse-target", "fake:parse", "--out-dir", str(tmp / "out"),
                                 "--trace-dir", str(tmp / "traces")])
            self.assertEqual(rc, 2)
            self.assertEqual(len(exported), 1)
            self.assertTrue(Path(exported[0]).exists())
            trace = next((tmp / "traces").glob("*.txt")).read_text()
            self.assertIn("[END] status=degraded", trace)


if __name__ == "__main__":
    unittest.main()
