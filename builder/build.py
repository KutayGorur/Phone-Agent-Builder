"""Build a Freya phone agent from bank brief(s) and a tool API file.

    python3 builder/build.py <brief> [<brief2> ...] <tool_api> [--selftest] [--out-dir out] [--budget-min 27]

Pipeline: parse -> generate -> freya.save_workflow -> optional self-test/fix loop -> freya.export_workflow.
Everything runs inside a hard time budget (the event allows 30 minutes per brief). The last brief file names
the output (out/<stem>.workflow.json) and the Freya slot. A trace goes to traces/<stem>-<time>.trace.txt.
Needs FREYA_API_KEY and FREYA_BANK_TEAM_KEY (source env.sh).
"""
import argparse, json, os, pathlib, re, subprocess, sys, tempfile, threading, time, traceback

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
    return {"meta": {"stub": True}, "raw_briefs": [pathlib.Path(p).read_text(encoding="utf-8-sig") for p in brief_paths],
            "tools": json.loads(pathlib.Path(tool_api_path).read_text(encoding="utf-8-sig")), "extra_rules": []}


def stub_generate(spec):
    tr.note("generate: STUB (builder.generate not available), using examples/base-agent.json")
    return json.loads(FALLBACK_WORKFLOW.read_text(encoding="utf-8"))


def _run_limited(fn, args, seconds, what):
    """Run fn(*args) in a daemon thread and stop waiting after `seconds`. The thread cannot be killed, but being a
    daemon it never keeps the interpreter alive; main() ends with os._exit."""
    box = {}
    def work():
        try:
            box["v"] = fn(*args)
        except BaseException as e:  # noqa: BLE001
            box["e"] = e
    th = threading.Thread(target=work, daemon=True, name=what)
    th.start()
    th.join(max(seconds, 1))
    if th.is_alive():
        raise TimeoutError(f"{what} exceeded its time slice of {seconds:.0f}s")
    if "e" in box:
        raise box["e"]
    return box["v"]


_CHILD = """
import json, sys, traceback
for _s in (sys.stdout, sys.stderr):
    try: _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass
sys.path.insert(0, sys.argv[1])
from builder import trace as tr
tr.set_current(tr.Trace(sys.argv[5] or None, echo=True))
mod, _, name = sys.argv[2].partition(":")
out = sys.argv[4]
try:
    fn = getattr(__import__(mod, fromlist=[name]), name)
    spec = fn(*json.loads(sys.argv[3]))
    open(out, "w", encoding="utf-8").write(json.dumps({"spec": spec}, ensure_ascii=False))
except BaseException as e:
    open(out, "w", encoding="utf-8").write(json.dumps({"error": repr(e), "tb": traceback.format_exc()}))
    sys.exit(1)
"""


def run_parse_subprocess(target, args, seconds, trace_path=None):
    """Run `module:function` in a child process that is killed when the time slice ends."""
    fd, out = tempfile.mkstemp(suffix=".json", prefix="parse-"); os.close(fd)
    p = subprocess.Popen([sys.executable, "-c", _CHILD, str(ROOT), target, json.dumps(args), out, str(trace_path or "")], cwd=ROOT)
    try:
        try:
            p.wait(timeout=max(seconds, 1))
        except subprocess.TimeoutExpired:
            p.kill(); p.wait()
            raise TimeoutError(f"parse exceeded its time slice of {seconds:.0f}s; child process killed") from None
        try:
            res = json.loads(pathlib.Path(out).read_text(encoding="utf-8"))
        except Exception:
            raise RuntimeError(f"parse child exited with code {p.returncode} and no result") from None
        if "error" in res:
            raise RuntimeError(f"parse failed: {res['error']}")
        return res["spec"]
    finally:
        try: os.unlink(out)
        except OSError: pass


def bundle_stem(briefs, out_dir):
    """Name of the output files and the Freya slot. One file: its stem. Several: all stems joined, so a bundle is told
    apart from another that ends in a file of the same name. A rerun of the same bundle keeps its name (the slot is
    updated in place); a different bundle that would take an existing name gets a short hash of its paths."""
    import hashlib
    stems = [pathlib.Path(b).stem for b in briefs]
    stem = "-".join(stems) if len(stems) > 1 else stems[0]
    stem = re.sub(r"[^\w.-]+", "_", stem)[:60]
    src = chr(10).join(str(pathlib.Path(b).resolve()) for b in briefs)
    side = pathlib.Path(out_dir) / f"{stem}.source.txt"
    try:
        if side.exists() and side.read_text(encoding="utf-8") != src:
            stem = f"{stem[:50]}-{hashlib.sha1(src.encode('utf-8')).hexdigest()[:6]}"
            side = pathlib.Path(out_dir) / f"{stem}.source.txt"
        pathlib.Path(out_dir).mkdir(parents=True, exist_ok=True)
        side.write_text(src, encoding="utf-8")
    except OSError:
        pass
    return stem


def save_with_recovery(freya, stem, workflow, state_file, t):
    """freya.save_workflow; a slot whose workflow no longer exists (other workspace or key, deleted) is forgotten once
    and created again. Any other error is raised."""
    try:
        return freya.save_workflow(stem, workflow, state_file=state_file)
    except Exception as e:  # noqa: BLE001
        if "-> 404" not in str(e):
            raise
        f = pathlib.Path(state_file)
        state = json.loads(f.read_text()) if f.exists() else {}
        if stem not in state:
            raise
        t.error(f"saved workflow for slot {stem} not found on the platform (404); creating it again")
        state.pop(stem)
        f.write_text(json.dumps(state, indent=1))
        return freya.save_workflow(stem, workflow, state_file=state_file)


def readiness_problems(spec):
    """Reasons a spec is not trustworthy: parser flags plus minimum content (identity questions, closing outcomes, calendar)."""
    probs, par = [], spec.get("parser") or {}
    if par.get("degraded"):
        probs.append("parser degraded: " + str(par.get("reason", "no reason given"))[:200])
    if par.get("unresolved_errors"):
        probs.append(f"{len(par['unresolved_errors'])} unresolved parser error(s)")
    ident, closing, cal = spec.get("identity"), spec.get("closing"), spec.get("calendar")
    if not (isinstance(ident, dict) and ident.get("questions")):
        probs.append("no identity questions")
    if not (isinstance(closing, dict) and closing.get("outcomes")):
        probs.append("no closing outcomes")
    if not (isinstance(cal, dict) and cal):
        probs.append("no calendar")
    return probs


def enum_guard(spec, briefs, tool_api, out_dir, stem, left, t, parse_target, spec_file):
    """Before generating: any outcome, queue, note reason, identity field or tool the spec would send that the tool API does
    not allow is repaired (spelling variants for free, then one targeted model call in a child process). What cannot be
    repaired is listed in the trace and keeps the build labelled degraded through the parser's unresolved errors."""
    er = _load("parse.enum_repair", "enum_problems")
    if er is None or not isinstance(spec, dict) or (spec.get("parser") or {}).get("degraded"):
        return spec
    try:
        probs = er(spec)
    except Exception as e:  # noqa: BLE001
        t.note(f"enum guard skipped: {e!r}"); return spec
    if not probs:
        t.note("enum guard: every outcome, queue, note reason and identity field in the spec is allowed by the tool API"); return spec
    describe = _load("parse.enum_repair", "describe")
    t.error(f"enum guard: {len(probs)} value(s) in the spec are not allowed by the tool API: " + " | ".join(describe(probs)[:6]))
    if a_parse_is_fake(parse_target, spec_file):
        return spec
    fd, tmp = tempfile.mkstemp(suffix=".json", prefix="spec-"); os.close(fd)
    try:
        pathlib.Path(tmp).write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
        new = run_parse_subprocess("builder.parse.spec_parser:guard_enums", [tmp, list(briefs), tool_api, left() > 8 * 60],
                                   min(300, max(left() * 0.2, 30)), t.path)
    except Exception as e:  # noqa: BLE001
        t.error(f"enum guard repair failed: {e!r}; keeping the spec as parsed"); return spec
    finally:
        try: os.unlink(tmp)
        except OSError: pass
    rest = er(new)
    for line in (new.get("parser") or {}).get("enum_repair") or []:
        t.note("enum guard: " + line)
    if rest:
        t.error(f"enum guard: {len(rest)} value(s) still not allowed by the tool API: " + " | ".join(describe(rest)[:6]))
    else:
        t.note("enum guard: repaired, the spec now matches the tool API enums")
    return new if len(rest) <= len(probs) else spec


def cross_check_parse(spec, briefs, tool_api, left, t, parse_target, spec_file):
    """Parse twice (builder/parse/consistency.py): a second extraction in a child process, the critical facts (calendar, bands,
    floors, identity, outcomes, queues, callback, multi-product) compared, disagreements settled by the safer value, one
    model re-ask that must quote the brief, or the first parse. Disagreements go to the trace and spec.parser.consistency.
    Skipped when the parser is swapped, the spec is degraded, or less than 12 minutes are left. Any failure keeps the first spec."""
    if not isinstance(spec, dict) or (spec.get("parser") or {}).get("degraded") or a_parse_is_fake(parse_target, spec_file):
        return spec
    if left() < 12 * 60:
        t.note(f"parse cross-check skipped: only {left():.0f}s left in budget"); return spec
    fd, tmp = tempfile.mkstemp(suffix=".json", prefix="spec-"); os.close(fd)
    secs = min(420, max(left() * 0.25, 60))
    try:
        pathlib.Path(tmp).write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
        new = run_parse_subprocess("builder.parse.spec_parser:cross_check", [tmp, list(briefs), tool_api, secs - 20], secs, t.path)
    except Exception as e:  # noqa: BLE001
        t.error(f"parse cross-check failed: {e!r}; keeping the first parse"); return spec
    finally:
        try: os.unlink(tmp)
        except OSError: pass
    block = (new.get("parser") or {}).get("consistency") or {}
    if not block.get("checked"):
        t.note("parse cross-check did not run: " + str(block.get("skipped", "no result"))); return spec
    dis = block.get("disagreements") or []
    if not dis:
        t.note(f"parse cross-check: the second parse agrees on all {block.get('facts')} critical facts")
    for d in dis:
        t.error(f"parse cross-check: {d['id']} differs: first={json.dumps(d['a'], ensure_ascii=False)[:160]} second={json.dumps(d['b'], ensure_ascii=False)[:160]} "
                f"-> {d.get('rule')}: {json.dumps(d.get('chosen'), ensure_ascii=False)[:160]}" + ("" if d.get("applied") else f" (not applied: {d.get('problem', 'n/a')})"))
    return new


def shape_guard(spec, t):
    """Spec sections of the wrong type (builder/generate/sanitize.py) are coerced or dropped before anything reads the spec, so one
    malformed section cannot stop generate or the generated scenarios. Every change goes to the trace; a drop labels the build
    degraded (the caller reads the second value)."""
    san = _load("generate.sanitize", "sanitize_spec")
    if san is None or not isinstance(spec, dict):
        return spec, 0
    try:
        clean, notes = san(spec)
    except Exception as e:  # noqa: BLE001
        t.note(f"shape guard skipped: {e!r}"); return spec, 0
    for n in notes:
        (t.error if n["action"] == "dropped" else t.note)(f"shape guard: spec {n['path']} {n['action']}: {n['detail']}")
    return clean, sum(1 for n in notes if n["action"] == "dropped")


def a_parse_is_fake(parse_target, spec_file):
    """Tests and development runs swap the parser; the guard's child process needs the real one (and a model for the rest)."""
    return bool(spec_file) or parse_target != "builder.parse:parse"


def local_scenarios(spec, tool_api, out_dir, stem, t, seconds):
    """Generated customers (builder/generate/auto_sim.py) through the compiled engine and the in-process stand-in bank. Free:
    no Freya calls, no model calls. Findings are compiler gaps; they go to the trace and out/<stem>.autosim.txt and do not
    change the build status. Skipped (with a note) when the spec is not ready or the tool API is not an OpenAPI file."""
    run = _load("generate.auto_sim", "run")
    if run is None:
        t.note("generated local scenarios skipped: builder.generate.auto_sim not available"); return
    if readiness_problems(spec):
        t.note("generated local scenarios skipped: spec not ready"); return
    try:
        api = json.loads(pathlib.Path(tool_api).read_text(encoding="utf-8-sig"))
    except Exception as e:  # noqa: BLE001
        t.note(f"generated local scenarios skipped: tool API unreadable ({e!r})"); return
    if not isinstance(api, dict) or not api.get("paths"):
        t.note("generated local scenarios skipped: tool API has no paths"); return
    canon = ("verify_identity", "get_account", "create_promise", "add_note", "schedule_callback", "transfer_to_agent", "close_call")
    missing = [c for c in canon if "/" + c not in api["paths"]]
    if missing:
        t.note("generated local scenarios skipped: the stand-in bank speaks the seven standard tool routes and this tool API has no route "
               + ", ".join("/" + m for m in missing[:4]) + " (the README says the seven tool names stay the same)"); return
    try:
        res = _run_limited(lambda s, a: run(s, a, deadline=time.time() + seconds - 2, echo=False), (spec, api), seconds, "generated local scenarios")
    except Exception as e:  # noqa: BLE001
        t.note(f"generated local scenarios could not run: {e!r}"); return
    lines = [f"{n}: {'; '.join(p)}" for n, p in res["failed"]]
    try:
        (pathlib.Path(out_dir) / f"{stem}.autosim.txt").write_text("\n".join(lines + res["errors"]) + "\n", encoding="utf-8")
    except OSError:
        pass
    if res["failed"]:
        t.error(f"generated local scenarios: {len(res['failed'])} of {res['total']} failed (compiler gaps for this brief; full list in {stem}.autosim.txt)")
        for ln in lines[:10]:
            t.error("  autosim " + ln[:300])
    else:
        t.note(f"generated local scenarios: all {res['total']} passed (identity, dates, amounts, intents, third party, tool failure)")
    for e in res["errors"]:
        t.note("generated local scenarios: " + e)


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


def run_selftest(agent_id, brief, timeout_s, t, label, workflow_file, cases_file=None, only=None, full=False, runner=None):
    """Every simulation goes through ci/sim.py: it lints, dry-runs and logs to results/sim-ledger.csv."""
    cmd = [sys.executable, str(runner or ROOT / "ci" / "sim.py"), agent_id, "--workflow", str(workflow_file), "--why", f"builder self-test {label}"]
    if brief:
        cmd += ["--brief", brief]
    if cases_file:
        cmd += ["--cases", str(cases_file)]
    if full:
        cmd += ["--full"]
    elif only:
        cmd += ["--only", ",".join(only)]
    t.selftest(f"sim.py start: {' '.join(cmd[2:])} (timeout {timeout_s:.0f}s)")
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
    for _s in (sys.stdout, sys.stderr):    # a piped Windows console is cp1252: never let a character abort the build
        try: _s.reconfigure(encoding="utf-8", errors="replace")
        except Exception: pass
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
    ap.add_argument("--selftest-full", action="store_true", help="first self-test run uses every case of the brief (the one allowed full run)")
    ap.add_argument("--max-fix-rounds", type=int, default=1)
    ap.add_argument("--spec-file", default=None, help="development: skip parse and use this spec.json")
    ap.add_argument("--dry-run", action="store_true", help="parse + generate only; no Freya calls, no credits; writes out/<stem>.workflow.json")
    ap.add_argument("--run-cases-cmd", default=None, help=argparse.SUPPRESS)
    ap.add_argument("--parse-target", default="builder.parse:parse", help=argparse.SUPPRESS)
    a = ap.parse_args(argv)
    if len(a.files) < 2:
        ap.error("need at least one brief and the tool API file")
    briefs, tool_api = a.files[:-1], a.files[-1]
    shown = (",".join(briefs), tool_api)
    briefs, tool_api = [str(pathlib.Path(b).resolve()) for b in briefs], str(pathlib.Path(tool_api).resolve())   # the parse child runs in ROOT
    if a.selftest and not a.selftest_brief and len(briefs) == 1:
        m = re.fullmatch(r"brief[-_ ]?([a-z])", pathlib.Path(briefs[0]).stem, re.I)   # practice briefs: only their own customers make sense
        if m:
            a.selftest_brief = m.group(1).upper()
    stem = bundle_stem(briefs, a.out_dir)
    t = tr.Trace(pathlib.Path(a.trace_dir) / f"{stem}-{time.strftime('%Y%m%d-%H%M%S')}.trace.txt")
    tr.set_current(t)
    t0 = time.time()
    deadline = t0 + min(a.budget_min * 60, HARD_LIMIT_S - 60)
    left = lambda: deadline - time.time()
    hard = t0 + HARD_LIMIT_S - 15

    def watchdog():   # last resort: the process ends before the event's 30 minutes whatever is still running
        t.error("hard time limit reached, aborting process")
        t.end("timeout", workflow_id=workflow_id, output=out_path)
        os._exit(3)
    wd = threading.Timer(max(hard - time.time(), 1), watchdog); wd.daemon = True; wd.start()
    t.start(briefs=shown[0], tool_api=shown[1], budget_s=int(left()), selftest=a.selftest)
    status, workflow_id, out_path = "failed", None, None
    try:
        t.stage("parse")
        if a.spec_file:
            spec = json.loads(pathlib.Path(a.spec_file).read_text(encoding="utf-8-sig"))
            t.note(f"parse skipped: spec loaded from {a.spec_file}")
        else:
            if _load("parse", "parse") or a.parse_target != "builder.parse:parse":
                spec = run_parse_subprocess(a.parse_target, [list(briefs), tool_api], left() * 0.35, t.path)
                first_problems = readiness_problems(spec)
                if first_problems and left() > 0.5 * (deadline - t0):
                    # one more attempt while more than half the budget is left; kept only if it is fully ready
                    t.note("spec not ready after the first parse (" + "; ".join(first_problems) + "), parsing once more")
                    try:
                        again = run_parse_subprocess(a.parse_target, [list(briefs), tool_api], left() * 0.35, t.path)
                        if not readiness_problems(again):
                            spec = again
                            t.note("second parse is ready, using it")
                        else:
                            t.note("second parse is not ready either, keeping the first")
                    except Exception as e:  # noqa: BLE001
                        t.error(f"second parse failed: {e!r}; keeping the first")
            else:
                spec = stub_parse(briefs, tool_api)
        out_dir = pathlib.Path(a.out_dir); out_dir.mkdir(parents=True, exist_ok=True)
        spec = cross_check_parse(spec, briefs, tool_api, left, t, a.parse_target, a.spec_file)
        spec, n_dropped = shape_guard(spec, t)
        spec = enum_guard(spec, briefs, tool_api, out_dir, stem, left, t, a.parse_target, a.spec_file)
        (out_dir / f"{stem}.spec.json").write_text(json.dumps(spec, indent=1, ensure_ascii=False), encoding="utf-8")
        t.note(f"spec written to {out_dir / (stem + '.spec.json')}")
        problems = readiness_problems(spec) + ([f"{n_dropped} malformed spec section(s) dropped by the shape guard"] if n_dropped else [])
        if problems:
            status = "degraded"
            t.error("spec not ready, build will be labelled degraded: " + "; ".join(problems))

        # generate; fall back to the example workflow so something valid is always exported
        t.stage("generate")
        generate = _load("generate", "generate") or stub_generate
        try:
            workflow = _run_limited(generate, (spec,), left() * 0.5, "generate")
        except Exception as e:
            t.error(f"generate failed: {e!r}; falling back to examples/base-agent.json")
            workflow, status = json.loads(FALLBACK_WORKFLOW.read_text(encoding="utf-8")), "degraded"

        # compiler diagnostics: guessed meanings make the build degraded, the rest is only logged
        gm = sys.modules.get("builder.generate.generate")      # the package attribute `generate` is the function
        lw, bw = getattr(gm, "LAST_WARNINGS", None), getattr(gm, "blocking_warnings", None)
        if lw is not None and bw is not None:
            blocking = bw(lw)
            for w in lw:
                if w not in blocking and not w.startswith("spec field"):
                    t.note("compiler warning: " + w)
            n_ign = sum(1 for w in lw if w.startswith("spec field"))
            if n_ign:
                t.note(f"compiler: {n_ign} spec field(s) are not read by the compiler (see generate.LAST_WARNINGS)")
            if blocking:
                status = "degraded"
                t.error("compiler guessed a meaning, build will be labelled degraded: " + "; ".join(blocking))

        tcp = getattr(gm, "tool_contract_problems", None)
        if tcp is not None and isinstance(workflow, dict) and "nodes" in workflow and workflow is not stub_generate:
            try:
                cp = tcp(spec, workflow)
            except Exception as e:  # noqa: BLE001
                cp = []
                t.note(f"tool contract check skipped: {e!r}")
            if cp:
                status = "degraded"
                t.error("workflow does not match the supplied tool API, build will be labelled degraded: " + "; ".join(cp[:8]))
            else:
                t.note("tool contract check: every request field, path and response binding matches the supplied tool API")

        t.stage("local scenarios")
        local_scenarios(spec, tool_api, out_dir, stem, t, min(120, max(left() * 0.15, 20)))

        if a.dry_run:
            out_path = str(out_dir / f"{stem}.workflow.json")
            pathlib.Path(out_path).write_text(json.dumps({"workflow": workflow}, indent=1, ensure_ascii=False), encoding="utf-8")
            t.note(f"dry run: no Freya calls; workflow written to {out_path}")
            if a.selftest:
                t.selftest(f"dry run: would run run_cases on {','.join(pick_cases(a.selftest_cases, a.selftest_brief, a.selftest_max))}")
            status = status if status == "degraded" else "ok"
            return 0 if out_path else 1
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
        info = save_with_recovery(freya, stem, workflow, STATE_FILE, t)
        workflow_id, agent_id = info["workflow_id"], info["agent_id"]
        t.freya("workflow " + ("updated" if existed else "created"), workflow_id=workflow_id, agent_id=agent_id, version=info.get("version"))

        if a.selftest:
            fix = _load("fix", "fix")
            only = a.selftest_only.split(",") if a.selftest_only else pick_cases(a.selftest_cases, a.selftest_brief, a.selftest_max)
            for rnd in range(a.max_fix_rounds + 1):
                if left() < 8 * 60:   # a small practice run takes a few minutes
                    t.selftest(f"skipped round {rnd}: only {left():.0f}s left in budget"); break
                wf_file = out_dir / f"{stem}.selftest.workflow.json"
                wf_file.write_text(json.dumps(workflow, indent=1, ensure_ascii=False), encoding="utf-8")
                # one full run per brief at most: a run after a fix only repeats the customers that failed
                res, failed = run_selftest(agent_id, a.selftest_brief, left() - 120, t, f"{stem}-{rnd}", wf_file, a.selftest_cases,
                                           only if rnd == 0 else failed, a.selftest_full and rnd == 0, a.run_cases_cmd)
                if res is None or not failed or rnd == a.max_fix_rounds:
                    break
                if fix is None:
                    t.selftest("no fixer available (builder.fix.fix), stopping loop"); break
                t.stage(f"fix round {rnd + 1}")
                try:
                    workflow = _run_limited(fix, (spec, workflow, failed), max(left() - 8 * 60, 60), "fix")
                    freya.validate_workflow(f"{stem} dryrun", workflow)
                    info = save_with_recovery(freya, stem, workflow, STATE_FILE, t)
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
        wd.cancel()
        t.end(status, workflow_id=workflow_id, output=out_path)
    return 0 if status in ("ok", "degraded") and out_path else 1


if __name__ == "__main__":
    code = main()
    sys.stdout.flush(); sys.stderr.flush()
    os._exit(code)   # abandoned worker threads must not hold the process past the limit
