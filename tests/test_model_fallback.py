"""Offline checks for the parser's fallback model: used only after every backend failed on the requested model."""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from builder import trace
from builder.parse import llm


class ModelFallback(unittest.TestCase):
    def setUp(self):
        previous = trace.get()
        self.trace = trace.Trace(echo=False)
        trace.set_current(self.trace)
        self.addCleanup(trace.set_current, previous)
        env = patch.dict(llm.os.environ, {"ANTHROPIC_API_KEY": "test"})
        env.start(); self.addCleanup(env.stop)
        llm.os.environ.pop("PARSER_REPLAY_DIR", None)
        which = patch.object(llm.shutil, "which", return_value="claude")
        which.start(); self.addCleanup(which.stop)

    def run_call(self, api, cli, fallback="small-model"):
        self.seen = []
        def rec(backend, fn):
            def call(model, *a):
                self.seen.append((backend, model))
                return fn(model)
            return call
        with patch.object(llm, "_call_api", rec("api", api)), patch.object(llm, "_call_cli", rec("cli", cli)), \
             patch.object(llm, "FALLBACK_MODEL", fallback):
            return llm.complete("test", "system", "prompt", model="big-model")

    @staticmethod
    def fail(model):
        raise RuntimeError(f"usage limit reached for {model}")

    def test_working_model_never_touches_fallback(self):
        self.assertEqual(self.run_call(lambda m: "ok", self.fail), "ok")
        self.assertEqual(self.seen, [("api", "big-model")])

    def test_other_backend_is_tried_before_the_fallback_model(self):
        self.assertEqual(self.run_call(self.fail, lambda m: "ok"), "ok")
        self.assertEqual(self.seen, [("api", "big-model"), ("cli", "big-model")])

    def test_fallback_model_after_every_backend_failed(self):
        def cli(model):
            if model == "big-model":
                self.fail(model)
            return "from small"
        self.assertEqual(self.run_call(self.fail, cli), "from small")
        self.assertEqual(self.seen, [("api", "big-model"), ("cli", "big-model"), ("api", "small-model"), ("cli", "small-model")])

    def test_all_failed_raises_and_empty_fallback_is_off(self):
        with self.assertRaises(RuntimeError):
            self.run_call(self.fail, self.fail)
        self.assertEqual(len(self.seen), 4)
        with self.assertRaises(RuntimeError):
            self.run_call(self.fail, self.fail, fallback="")
        self.assertEqual(len(self.seen), 2)


if __name__ == "__main__":
    unittest.main()
