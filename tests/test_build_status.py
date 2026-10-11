"""Offline tests for build.py status labelling and the hard deadline. No Freya, no model calls.
Run: python tests/test_build_status.py"""
import json, os, pathlib, subprocess, sys, tempfile, time

ROOT = pathlib.Path(__file__).resolve().parent.parent
BUILD = ROOT / "builder" / "build.py"
GOOD = {"parser": {"degraded": False, "unresolved_errors": []}, "identity": {"questions": [{"field": "x"}]},
        "closing": {"outcomes": [{"outcome": "promise"}]}, "calendar": {"business_days": ["Mon"]}, "tools": {}, "extra_rules": []}
FAKE = '''import json, time
def good(briefs, api): return json.loads(%r)
def degraded(briefs, api):
    s = json.loads(%r); s["parser"] = {"degraded": True, "reason": "fake"}; s["identity"] = None; return s
def sleeper(briefs, api): time.sleep(600)
def auth_failure(briefs, api):
    s = sound(briefs, api); s["parser"] = {"degraded": True, "reason": "Anthropic API 401: invalid API key"}; return s
def limit_failure(briefs, api):
    s = sound(briefs, api); s["parser"] = {"degraded": True, "reason": "claude CLI error: usage limit reached"}; return s
def guessy(briefs, api):
    s = json.load(open(%r, encoding="utf-8")); s["persuasion"]["attempts"][0]["date"] = "two business days after today"; return s
def flaky(briefs, api):
    import pathlib
    m = pathlib.Path(__file__).with_name("flaky.mark")
    if m.exists(): return json.loads(%r)
    m.write_text("1"); s = json.loads(%r); s["parser"] = {"degraded": True, "reason": "first try"}; s["identity"] = None; return s
def sound(briefs, api): return json.load(open(%r, encoding="utf-8"))
def reader(briefs, api): open(briefs[0]).read(); open(api).read(); return json.loads(%r)
''' % (json.dumps(GOOD), json.dumps(GOOD), str(ROOT / "builder" / "specs" / "brief-a.spec.json"), json.dumps(GOOD), json.dumps(GOOD), str(ROOT / "builder" / "specs" / "brief-a.spec.json"), json.dumps(GOOD))


def run(tmp, target, budget_min=27, extra=(), relative=False):
    (tmp / "fakeparse.py").write_text(FAKE, encoding="utf-8")
    (tmp / "b.md").write_text("brief", encoding="utf-8"); (tmp / "t.json").write_text("{}", encoding="utf-8")
    env = dict(os.environ, PYTHONPATH=str(tmp), PYTHONIOENCODING="utf-8")
    t0 = time.time()
    files = ["b.md", "t.json"] if relative else [str(tmp / "b.md"), str(tmp / "t.json")]
    p = subprocess.run([sys.executable, str(BUILD), *files, "--dry-run", "--parse-target", target,
                        "--out-dir", str(tmp / "out"), "--trace-dir", str(tmp / "tr"), "--budget-min", str(budget_min), *extra],
                       env=env, cwd=str(tmp) if relative else None, capture_output=True, text=True, encoding="utf-8", timeout=120)
    trace = "".join(f.read_text(encoding="utf-8") for f in (tmp / "tr").glob("*.trace.txt"))
    return p.returncode, trace, time.time() - t0


def end_status(trace):
    return [l for l in trace.splitlines() if "[END]" in l][-1].split("status=")[1].split()[0]


def main():
    with tempfile.TemporaryDirectory() as d:
        tmp = pathlib.Path(d)
        rc, tr, _ = run(tmp, "fakeparse:good"); assert rc == 0 and end_status(tr) == "ok", (rc, tr)
    with tempfile.TemporaryDirectory() as d:
        rc, tr, _ = run(pathlib.Path(d), "fakeparse:degraded"); assert rc == 2 and end_status(tr) == "degraded", (rc, tr)
    for failure in ("auth_failure", "limit_failure"):
        with tempfile.TemporaryDirectory() as d:
            tmp = pathlib.Path(d)
            rc, tr, _ = run(tmp, "fakeparse:" + failure)
            assert rc == 2 and end_status(tr) == "degraded" and "parser degraded" in tr, (rc, tr)
            assert (tmp / "out" / "b.workflow.json").exists(), "degraded diagnostic export must survive"
    with tempfile.TemporaryDirectory() as d:   # parse sleeps 600s; slice is 35% of ~6s, so it must be killed quickly
        rc, tr, el = run(pathlib.Path(d), "fakeparse:sleeper", budget_min=0.1)
        assert el < 30 and "time slice" in tr and end_status(tr) != "ok", (rc, el, tr)
    with tempfile.TemporaryDirectory() as d:   # the compiler had to guess a date rule: labelled degraded, and the warning is in the trace
        rc, tr, _ = run(pathlib.Path(d), "fakeparse:guessy"); assert rc == 2 and end_status(tr) == "degraded" and "compiler guessed" in tr, (rc, tr)
    with tempfile.TemporaryDirectory() as d:   # a real spec with only ignored-field warnings stays ok
        rc, tr, _ = run(pathlib.Path(d), "fakeparse:sound"); assert rc == 0 and end_status(tr) == "ok" and "compiler guessed" not in tr, (rc, tr)
    with tempfile.TemporaryDirectory() as d:   # first parse not ready, second is: the second one is used, status ok
        rc, tr, _ = run(pathlib.Path(d), "fakeparse:flaky"); assert rc == 0 and end_status(tr) == "ok" and "second parse is ready" in tr, (rc, tr)
    with tempfile.TemporaryDirectory() as d:   # started from another directory with relative paths: the parse child still finds the files
        rc, tr, _ = run(pathlib.Path(d), "fakeparse:reader", relative=True); assert rc == 0 and end_status(tr) == "ok", (rc, tr)
    print("ok")


if __name__ == "__main__":
    main()
