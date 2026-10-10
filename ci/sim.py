"""Credit-guarded wrapper around tools/run_cases.py. Every Freya simulation goes through this.

python ci/sim.py <agent_id> --workflow out/gen-a.workflow.json --only PUB-01,PUB-04 --brief A --why "check floor path"
python ci/sim.py <agent_id> --workflow ... --brief A --full --why "milestone: full A"          # all cases
python ci/sim.py --ledger                                                                       # show spend so far

- Lints the workflow file first (ci/lint_workflow.py, incl. Freya dry run); refuses to simulate if it fails.
- Without --full you must pass --only (a few cases). --reps > 1 also needs --full.
- Appends every run to results/sim-ledger.csv (shared folder, not committed) so all threads see the spend.
Extra arguments after `--` go to run_cases.py unchanged (e.g. -- --style pieces --out results/x.json).
"""
import argparse, csv, json, subprocess, sys, time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LEDGER = ROOT / "results" / "sim-ledger.csv"
FIELDS = ["utc", "agent_id", "brief", "cases", "reps", "calls", "style", "why", "result", "seconds"]


def show_ledger():
    if not LEDGER.exists():
        print("no simulations logged yet"); return
    rows = list(csv.DictReader(open(LEDGER, encoding="utf-8")))
    for r in rows:
        print(f"{r['utc']}  {r['calls']:>3} calls  brief={r['brief']:<3} {r['result']:<14} {r['why']}")
    print(f"total: {len(rows)} simulations, {sum(int(r['calls'] or 0) for r in rows)} customer calls")


def main():
    argv = sys.argv[1:]
    extra = argv[argv.index("--") + 1:] if "--" in argv else []
    argv = argv[:argv.index("--")] if "--" in argv else argv
    ap = argparse.ArgumentParser()
    ap.add_argument("agent_id", nargs="?")
    ap.add_argument("--workflow", help="the workflow file that was saved for this agent")
    ap.add_argument("--brief")
    ap.add_argument("--cases", default=str(ROOT / "public-test-set.json"))
    ap.add_argument("--only")
    ap.add_argument("--reps", type=int, default=1)
    ap.add_argument("--full", action="store_true")
    ap.add_argument("--why", default="")
    ap.add_argument("--ledger", action="store_true")
    a = ap.parse_args(argv)
    if a.ledger:
        show_ledger(); return
    if not a.agent_id or not a.workflow or not a.why:
        sys.exit("need agent_id, --workflow and --why")
    if not a.full and not a.only:
        sys.exit("refusing: pass --only <ids> for a small run, or --full for a milestone run")
    if a.reps > 1 and not a.full:
        sys.exit("refusing: --reps > 1 is for milestone runs, add --full")

    lint = subprocess.run([sys.executable, str(ROOT / "ci/lint_workflow.py"), a.workflow, "--dry-run"])
    if lint.returncode:
        sys.exit("refusing: workflow lint failed")

    cases = [c for c in json.load(open(a.cases, encoding="utf-8"))
             if (not a.brief or c["brief"] == a.brief) and (not a.only or c["id"] in a.only.split(","))]
    calls = len(cases) * a.reps
    print(f"simulating {len(cases)} case(s) x {a.reps} rep(s) = {calls} calls", flush=True)

    cmd = [sys.executable, str(ROOT / "tools/run_cases.py"), a.agent_id, "--cases", a.cases, "--reps", str(a.reps)]
    if a.brief: cmd += ["--brief", a.brief]
    if a.only: cmd += ["--only", a.only]
    cmd += extra
    t0 = time.time()
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
    print(p.stdout)
    summary = next((l.strip() for l in reversed(p.stdout.splitlines()) if "passed" in l), f"exit {p.returncode}")
    style = extra[extra.index("--style") + 1] if "--style" in extra else ""
    LEDGER.parent.mkdir(exist_ok=True)
    new = not LEDGER.exists()
    with open(LEDGER, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, FIELDS)
        if new: w.writeheader()
        w.writerow({"utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M"), "agent_id": a.agent_id,
                    "brief": a.brief or "", "cases": a.only or "all", "reps": a.reps, "calls": calls,
                    "style": style, "why": a.why, "result": summary[:60], "seconds": int(time.time() - t0)})
    sys.exit(p.returncode)


if __name__ == "__main__":
    main()
