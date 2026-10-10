"""Build a Freya phone agent from bank brief(s) and a tool API file.

    python3 builder/build.py <brief> [<brief2> ...] <tool_api> [--selftest] [--out-dir out] [--budget-min 27]

Pipeline: parse -> generate -> freya.save_workflow -> optional self-test/fix loop -> freya.export_workflow.
Everything runs inside a hard time budget (the event allows 30 minutes per brief). The last brief file names
the output (out/<stem>.workflow.json) and the Freya slot. A trace goes to traces/<stem>-<time>.trace.txt.
Needs FREYA_API_KEY and FREYA_BANK_TEAM_KEY (source env.sh).
"""
import argparse, concurrent.futures, json, pathlib, re, subprocess, sys, time, traceback

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from builder import trace as tr  # noqa: E402

HARD_LIMIT_S = 30 * 60
FALLBACK_WORKFLOW = ROOT / "examples" / "base-agent.json"
STATE_FILE = str(ROOT / ".freya-agents.json")


def _load(module, name):
    """Import builder.<module>.<name>; None while that thread's work has not landed."""
    try:
        return getattr(__import__(f"builder.{module}", fromlist=[name]), name)
    except (ImportError, AttributeError):
        return None


def stub_parse(brief_paths, tool_api_path):
    tr.note("parse: STUB (builder.parse not available), spec carries only raw inputs")
    return {"meta": {"stub": True}, "raw_briefs": [pathlib.Path(p).read_text(encoding="utf-8") for p in brief_paths],
            "tools": json.loads(pathlib.Path(tool_api_path).read_text(encoding="utf-8")), "extra_rules": []}


def stub_generate(spec):
    tr.note("generate: STUB (builder.generate not available), using examples/base-agent.json")
    return json.loads(FALLBACK_WORKFLOW.read_text(encoding="utf-8"))


def _run_limited(fn, args, seconds, what):
    """Run fn(*args) but stop waiting after `seconds`; a timed-out call is abandoned."""
    ex = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    fut = ex.submit(fn, *args)
    try:
        return fut.result(timeout=max(seconds, 1))
    except concurrent.futures.TimeoutError:
        raise TimeoutError(f"{what} exceeded its time slice of {seconds:.0f}s") from None
    finally:
        ex.shutdown(wait=False, cancel_futures=True)


def parse_results(text):
    m = re.search(r"(\d+)\s*/\s*(\d+)\s+passed", text)
    failed = re.findall(r"^FAIL\s+(\S+)", text, re.M)
    return ((int(m.group(1)), int(m.group(2))) if m else None), failed


def pick_cases(cases_file, brief, limit):
    """Frugal default: one customer per family (hardest level first), at most `limit`. Every simulated call costs credits."""
    cases = [c for c in json.loads(pathlib.Path(cases_file).read_text(encoding="utf-8")) if not brief or c.get("brief") == brief]
    rank = {"hard": 0, "medium": 1, "easy": 2}
    seen, picked = set(), []
    for c in sorted(cases, key=lambda c: rank.get(c.get("level"), 3)):
        if c.get("family") not in seen:
            seen.add(c.get("family")); picked.append(c["id"])
    return picked[:limit] if limit else [c["id"] for c in cases]


def run_selftest(agent_id, brief, timeout_s, t, label, cases_file=None, only=None, runner=None):
    out_file = ROOT / "results" / f"selftest-{label}.json"
    cmd = [sys.executable, str(runner or ROOT / "tools" / "run_cases.py"), agent_id, "--out", str(out_file)]
    if brief:
        cmd += ["--brief", brief]
    if cases_file:
        cmd += ["--cases", str(cases_file)]
    if only:
        cmd += ["--only", ",".join(only)]
    t.selftest(f"run_cases start: {' '.join(cmd[2:])} (timeout {timeout_s:.0f}s)")
    try:
        p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout_s)
        out = p.stdout + p.stderr
    except subprocess.TimeoutExpired:
        t.selftest("run_cases TIMED OUT, result discarded")
        return None, []
    res, failed = parse_results(out)
    for line in out.splitlines():
        if line.startswith(("PASS", "FAIL", "       -")) or "passed" in line:
            t.selftest(line[:300])
    t.selftest(f"result passed={res[0] if res else '?'} total={res[1] if res else '?'} failed={','.join(failed) or '-'}")
    return res, failed


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="+", help="brief file(s) followed by the tool API file")
    ap.add_argument("--out-dir", default=str(ROOT / "out"))
    ap.add_argument("--trace-dir", default=str(ROOT / "traces"))
    ap.add_argument("--budget-min", type=float, default=27, help="soft budget in minutes (hard cap is 30)")
    ap.add_argument("--selftest", action="store_true", help="run practice customers on the built agent and try fixes")
    ap.add_argument("--selftest-brief", default=None, help="run_cases --brief value (A or B); default all practice cases")
    ap.add_argument("--selftest-cases", default=str(ROOT / "public-test-set.json"), help="case file for the self-test")
    ap.add_argument("--selftest-max", type=int, default=4, help="max customers per self-test run (0 = all); each costs Freya credits")
    ap.add_argument("--selftest-only", default=None, help="comma-separated case ids (overrides the automatic pick)")
    ap.add_argument("--max-fix-rounds", type=int, default=1)
    ap.add_argument("--spec-file", default=None, help="development: skip parse and use this spec.json")
    ap.add_argument("--dry-run", action="store_true", help="parse + generate only; no Freya calls, no credits; writes out/<stem>.workflow.json")
    ap.add_argument("--run-cases-cmd", default=None, help=argparse.SUPPRESS)
    a = ap.parse_args(argv)
    if len(a.files) < 2:
        ap.error("need at least one brief and the tool API file")
    briefs, tool_api = a.files[:-1], a.files[-1]
    stem = pathlib.Path(briefs[-1]).stem
    t = tr.Trace(pathlib.Path(a.trace_dir) / f"{stem}-{time.strftime('%Y%m%d-%H%M%S')}.trace.txt")
    tr.set_current(t)
    t0 = time.time()
    deadline = t0 + min(a.budget_min * 60, HARD_LIMIT_S - 60)
    left = lambda: deadline - time.time()
    t.start(briefs=",".join(briefs), tool_api=tool_api, budget_s=int(left()), selftest=a.selftest)
    status, workflow_id, out_path = "failed", None, None
    try:
        t.stage("parse")
        if a.spec_file:
            spec = json.loads(pathlib.Path(a.spec_file).read_text(encoding="utf-8"))
            t.note(f"parse skipped: spec loaded from {a.spec_file}")
        else:
            parse = _load("parse", "parse") or stub_parse
            spec = _run_limited(parse, (briefs, tool_api), left() * 0.35, "parse")
        out_dir = pathlib.Path(a.out_dir); out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / f"{stem}.spec.json").write_text(json.dumps(spec, indent=1, ensure_ascii=False), encoding="utf-8")
        t.note(f"spec written to {out_dir / (stem + '.spec.json')}")

        # generate; fall back to the example workflow so something valid is always exported
        t.stage("generate")
        generate = _load("generate", "generate") or stub_generate
        try:
            workflow = _run_limited(generate, (spec,), left() * 0.5, "generate")
        except Exception as e:
            t.error(f"generate failed: {e!r}; falling back to examples/base-agent.json")
            workflow, status = json.loads(FALLBACK_WORKFLOW.read_text(encoding="utf-8")), "degraded"

        if a.dry_run:
            out_path = str(out_dir / f"{stem}.workflow.json")
            pathlib.Path(out_path).write_text(json.dumps({"workflow": workflow}, indent=1, ensure_ascii=False), encoding="utf-8")
            t.note(f"dry run: no Freya calls; workflow written to {out_path}")
            if a.selftest:
                t.selftest(f"dry run: would run run_cases on {','.join(pick_cases(a.selftest_cases, a.selftest_brief, a.selftest_max))}")
            status = status if status == "degraded" else "ok"
            return 0
        import freya
        t.stage("freya save")
        try:
            freya.validate_workflow(f"{stem} dryrun", workflow)
            t.freya("validate_workflow dry-run ok")
        except Exception as e:
            t.error(f"validation failed: {e}")
            if status != "degraded":
                workflow, status = json.loads(FALLBACK_WORKFLOW.read_text(encoding="utf-8")), "degraded"
                t.error("using fallback workflow")
        state = pathlib.Path(STATE_FILE)
        existed = stem in (json.loads(state.read_text()) if state.exists() else {})
        info = freya.save_workflow(stem, workflow, state_file=STATE_FILE)
        workflow_id, agent_id = info["workflow_id"], info["agent_id"]
        t.freya("workflow " + ("updated" if existed else "created"), workflow_id=workflow_id, agent_id=agent_id, version=info.get("version"))

        if a.selftest:
            fix = _load("fix", "fix")
            only = a.selftest_only.split(",") if a.selftest_only else pick_cases(a.selftest_cases, a.selftest_brief, a.selftest_max)
            for rnd in range(a.max_fix_rounds + 1):
                if left() < 8 * 60:   # a small practice run takes a few minutes
                    t.selftest(f"skipped round {rnd}: only {left():.0f}s left in budget"); break
                res, failed = run_selftest(agent_id, a.selftest_brief, left() - 120, t, f"{stem}-{rnd}", a.selftest_cases, only, a.run_cases_cmd)
                if res is None or not failed or rnd == a.max_fix_rounds:
                    break
                if fix is None:
                    t.selftest("no fixer available (builder.fix.fix), stopping loop"); break
                t.stage(f"fix round {rnd + 1}")
                try:
                    workflow = _run_limited(fix, (spec, workflow, failed), max(left() - 8 * 60, 60), "fix")
                    freya.validate_workflow(f"{stem} dryrun", workflow)
                    info = freya.save_workflow(stem, workflow, state_file=STATE_FILE)
                    t.freya("workflow updated", workflow_id=workflow_id, version=info.get("version"))
                except Exception as e:
                    t.error(f"fix round failed: {e!r}; keeping previous workflow"); break

        t.stage("export")
        out_path = freya.export_workflow(workflow_id, str(out_dir / f"{stem}.workflow.json"))
        t.freya("exported workflow", path=out_path)
        if status == "failed":
            status = "ok"
    except Exception as e:
        t.error(f"{e!r}")
        t.error(traceback.format_exc().replace("\n", " | "))
    finally:
        t.end(status, workflow_id=workflow_id, output=out_path)
    return 0 if status in ("ok", "degraded") and out_path else 1


if __name__ == "__main__":
    sys.exit(main())
