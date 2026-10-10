"""Malformed model output per section must give path-specific errors (never an exception) and degrade one section only.

    python tests/parse/test_malformed.py
"""
import copy
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from builder.parse import llm, prompts, spec_parser, units as units_mod, validate  # noqa: E402
from builder.parse.tools_api import tools_from_openapi  # noqa: E402

GOLD = json.loads((ROOT / "builder" / "specs" / "brief-a.spec.json").read_text(encoding="utf-8"))
UNITS, _ = units_mod.load_briefs([ROOT / "briefs" / "brief-a.md"])
TOOLS = tools_from_openapi(ROOT / "tools" / "openapi.json")["tools"]


def mutate(fn):
    s = copy.deepcopy(GOLD)
    fn(s)
    return s


def set_path(s, key, value):
    s[key] = value


# (name, mutation, substring expected in an error)
CASES = [
    ("reasons as dicts", lambda s: s["closing"]["outcomes"][0].__setitem__("reasons", [{"x": 1}]), "closing.outcomes[0].reasons"),
    ("reasons as string", lambda s: s["closing"]["outcomes"][0].__setitem__("reasons", "A"), "closing.outcomes[0].reasons"),
    ("outcome as dict", lambda s: s["closing"]["outcomes"][0].__setitem__("outcome", {"a": 1}), "closing.outcomes[0].outcome"),
    ("outcomes as dict", lambda s: s["closing"].__setitem__("outcomes", {"a": 1}), "closing.outcomes"),
    ("outcomes holding strings", lambda s: s["closing"].__setitem__("outcomes", ["PTP"]), "closing.outcomes"),
    ("closing as list", lambda s: set_path(s, "closing", ["x"]), "closing must be"),
    ("identity.questions strings", lambda s: s["identity"].__setitem__("questions", ["dob"]), "identity.questions"),
    ("identity question field dict", lambda s: s["identity"]["questions"][0].__setitem__("field", {"a": 1}), "identity.questions[0].field"),
    ("holidays dicts", lambda s: s["calendar"].__setitem__("holidays", [{"date": "2026-01-01"}]), "calendar.holidays"),
    ("business_days dicts", lambda s: s["calendar"].__setitem__("business_days", [{"d": "Mon"}]), "calendar.business_days"),
    ("bands as dict", lambda s: set_path(s, "bands", {"a": 1}), "bands"),
    ("band deadline string", lambda s: s["bands"][0].__setitem__("deadline", "next day"), "bands[0].deadline"),
    ("intents as dict", lambda s: set_path(s, "intents", {"a": 1}), "intents"),
    ("product_names list", lambda s: s["debt_statement"].__setitem__("product_names", ["x"]), "debt_statement.product_names"),
    ("floor_field list", lambda s: s["amounts"].__setitem__("floor_field_by_product", ["x"]), "amounts.floor_field_by_product"),
]


def check_validate():
    bad = 0
    for name, fn, want in CASES:
        spec = mutate(fn)
        try:
            errors, _ = validate.validate(spec, UNITS, TOOLS)
        except Exception as e:  # noqa: BLE001
            print(f"FAIL {name}: validate raised {type(e).__name__}: {e}")
            bad += 1
            continue
        if not any(want in e for e in errors):
            print(f"FAIL {name}: no error mentioning '{want}' in {errors[:3]}")
            bad += 1
        else:
            print(f"ok   {name}")
    return bad


def check_degrade_one_section():
    """Fake model keeps returning a malformed closing: the parse must end non-degraded, closing nulled, other sections intact."""
    bad_closing = copy.deepcopy(GOLD["closing"])
    bad_closing["outcomes"][0]["reasons"] = [{"x": 1}]

    def fake(purpose, system, prompt, model=None, **kw):
        for g, (names, _) in prompts.SECTION_HELP.items():
            if purpose.endswith(f"sections {names}"):
                secs = {k: GOLD[k] for k in validate.SECTION_GROUPS[g]}
                if g == "g3":
                    secs["closing"] = bad_closing
                return json.dumps({"sections": secs, "extra_rules": GOLD["extra_rules"] if g == "g1" else [],
                                   "rule_coverage": GOLD["rule_coverage"], "open_questions": []})
        if purpose.startswith("audit"):
            return json.dumps({"issues": []})
        if purpose.startswith("repair"):
            return json.dumps({"sections": {"closing": bad_closing}})   # the model fails to fix it
        raise AssertionError(purpose)

    old = llm.complete
    llm.complete = fake
    spec_parser.DEBUG_DIR = ROOT / "out" / "parse-selftest"
    try:
        out = spec_parser.parse([ROOT / "briefs" / "brief-a.md"], ROOT / "tools" / "openapi.json")
    finally:
        llm.complete = old
    ok = True
    if out["parser"]["degraded"]:
        print("FAIL whole spec degraded:", out["parser"].get("reason"))
        ok = False
    if out.get("closing") is not None:
        print("FAIL closing not nulled")
        ok = False
    if out.get("identity") != GOLD["identity"] or out.get("calendar") != GOLD["calendar"]:
        print("FAIL identity/calendar not preserved")
        ok = False
    if any("closing" in str(e) and "does not exist" in str(e) for e in out["parser"]["unresolved_errors"]):
        print("FAIL dangling coverage:", out["parser"]["unresolved_errors"][:3])
        ok = False
    if ok:
        print("ok   one malformed section degrades only that section")
    return 0 if ok else 1


if __name__ == "__main__":
    n = check_validate() + check_degrade_one_section()
    print("FAILED" if n else "all passed")
    sys.exit(1 if n else 0)
