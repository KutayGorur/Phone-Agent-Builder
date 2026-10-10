"""Offline plumbing test for the parser: a fake model returns the hand-checked golden spec, so no credentials are needed.

    python builder/parse/selftest.py
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from builder.parse import llm, spec_parser, validate, prompts  # noqa: E402


def run(name, briefs):
    golden = json.loads((ROOT / "builder" / "specs" / f"{name}.spec.json").read_text(encoding="utf-8"))

    def fake(purpose, system, prompt, model=None, **kw):
        for g, (names, _) in prompts.SECTION_HELP.items():
            if purpose.endswith(f"sections {names}"):
                secs = {k: golden[k] for k in validate.SECTION_GROUPS[g]}
                return json.dumps({"sections": secs, "extra_rules": golden["extra_rules"] if g == "g1" else [],
                                   "rule_coverage": golden["rule_coverage"], "open_questions": []})
        if purpose.startswith("audit"):
            return json.dumps({"issues": []})
        raise AssertionError(purpose)

    llm.complete = fake
    spec_parser.DEBUG_DIR = ROOT / "out" / "parse-selftest"
    out = spec_parser.parse([ROOT / b for b in briefs], ROOT / "tools" / "openapi.json")
    gold = {k: v for k, v in golden.items()}
    diff = [k for k in gold if gold[k] != out.get(k)]
    print(name, "parser errors:", out["parser"]["unresolved_errors"], "warnings:", len(out["parser"]["warnings"]), "differs from golden in:", diff)
    return not out["parser"]["unresolved_errors"] and not diff


if __name__ == "__main__":
    ok = run("brief-a", ["briefs/brief-a.md"]) & run("brief-ab", ["briefs/brief-a.md", "briefs/brief-b.md"])
    sys.exit(0 if ok else 1)
