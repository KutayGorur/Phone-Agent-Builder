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
''' % (json.dumps(GOOD), json.dumps(GOOD))


def run(tmp, target, budget_min=27, extra=()):
    (tmp / "fakeparse.py").write_text(FAKE, encoding="utf-8")
    (tmp / "b.md").write_text("brief", encoding="utf-8"); (tmp / "t.json").write_text("{}", encoding="utf-8")
    env = dict(os.environ, PYTHONPATH=str(tmp), PYTHONIOENCODING="utf-8")
    t0 = time.time()
    p = subprocess.run([sys.executable, str(BUILD), str(tmp / "b.md"), str(tmp / "t.json"), "--dry-run", "--parse-target", target,
                        "--out-dir", str(tmp / "out"), "--trace-dir", str(tmp / "tr"), "--budget-min", str(budget_min), *extra],
                       env=env, capture_output=True, text=True, encoding="utf-8", timeout=120)
    trace = "".join(f.read_text(encoding="utf-8") for f in (tmp / "tr").glob("*.trace.txt"))
    return p.returncode, trace, time.time() - t0


def end_status(trace):
    return [l for l in trace.splitlines() if "[END]" in l][-1].split("status=")[1].split()[0]


def main():
    with tempfile.TemporaryDirectory() as d:
        tmp = pathlib.Path(d)
        rc, tr, _ = run(tmp, "fakeparse:good"); assert rc == 0 and end_status(tr) == "ok", (rc, tr)
    with tempfile.TemporaryDirectory() as d:
        rc, tr, _ = run(pathlib.Path(d), "fakeparse:degraded"); assert rc == 0 and end_status(tr) == "degraded", (rc, tr)
    with tempfile.TemporaryDirectory() as d:   # parse sleeps 600s; slice is 35% of ~6s, so it must be killed quickly
        rc, tr, el = run(pathlib.Path(d), "fakeparse:sleeper", budget_min=0.1)
        assert el < 30 and "time slice" in tr and end_status(tr) != "ok", (rc, el, tr)
    print("ok")


if __name__ == "__main__":
    main()
