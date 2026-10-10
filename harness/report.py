"""Turn several `run_cases.py --out` files into a pass-rate table with the failure reasons per case.

    python harness/report.py results/c-rep1.json results/c-rep2.json results/c-rep3.json
    python harness/report.py "results/c-*.json" --md results/c-report.md --json results/c-report.json
    python harness/report.py results/ --family            # a directory takes every *.json in it; --family adds a table per family

Every run of every file counts as one repetition (a file made with --reps 3 counts three). For each customer:
  passes/runs, the pass rate, STRICT (the final's rule: it counts only when every run passes), and the failure reasons
  with how often each one happened and a call id to open with freya.get_call(...)["messages"].
The headline numbers are the mean pass rate per run and the strict score (share of customers that passed every run).
Files that are not run_cases outputs (no "all_rows"/"rows") are skipped with a note. Standard library only.
"""
import argparse, collections, glob, json, os, re, sys


def load(paths):
    files = []
    for p in paths:
        if os.path.isdir(p): files += sorted(glob.glob(os.path.join(p, "*.json")))
        else: files += sorted(glob.glob(p)) or [p]
    return files


def runs_of(doc):
    """The list of repetitions in one run_cases output: each is a list of rows."""
    if isinstance(doc, dict):
        if doc.get("all_rows"): return doc["all_rows"]
        if doc.get("rows"): return [doc["rows"]]
    return []


def shorten(reason, n=170):
    reason = " ".join(str(reason).split())
    return reason if len(reason) <= n else reason[: n - 3] + "..."


def kind(reason):
    """A short label for a failure reason, so reasons of one kind can be counted together."""
    for k in ("outcome", "promises", "notes", "callbacks", "transfers"):
        if reason.startswith(k + " "): return k
    if reason.startswith("conversation:"): return "conversation"
    if "close_call" in reason: return "not closed"
    if "before identity" in reason: return "tool before identity"
    if reason.startswith("identity or account tools"): return "identity tools on third party"
    return "other"


def aggregate(files):
    cases, used, skipped = collections.OrderedDict(), [], []
    for f in files:
        try: doc = json.load(open(f, encoding="utf-8"))
        except Exception as e: skipped.append((f, str(e)[:60])); continue
        reps = runs_of(doc)
        if not reps: skipped.append((f, "no rows")); continue
        used.append((f, len(reps), doc.get("agent_id")))
        for ri, rows in enumerate(reps):
            for r in rows:
                c = cases.setdefault(r["id"], {"id": r["id"], "family": r.get("family", ""), "level": r.get("level", ""), "runs": 0, "passes": 0, "fails": [], "slowest": []})
                c["runs"] += 1; c["passes"] += bool(r["pass"])
                if r.get("slowest_turn_s") is not None: c["slowest"].append(r["slowest_turn_s"])
                if not r["pass"]: c["fails"].append({"file": os.path.basename(f), "rep": ri + 1, "call_id": r.get("call_id"), "reasons": r.get("failed") or ["(no reason recorded)"], "ended": r.get("ended"), "tools": r.get("tools")})
    return cases, used, skipped


def summarize(cases):
    out = []
    for c in cases.values():
        counts = collections.Counter()
        first_call = {}
        for fl in c["fails"]:
            for reason in fl["reasons"]:
                key = shorten(reason); counts[key] += 1; first_call.setdefault(key, fl["call_id"])
        out.append({**c, "rate": c["passes"] / c["runs"] if c["runs"] else 0.0, "strict": c["passes"] == c["runs"] and c["runs"] > 0,
                    "reasons": [{"text": t, "count": n, "kind": kind(t), "call_id": first_call[t]} for t, n in counts.most_common()]})
    return out


def pct(x): return f"{100 * x:.0f}%"


def render(rows, used, skipped, by_family):
    L = []
    total_runs = sum(r["runs"] for r in rows); total_pass = sum(r["passes"] for r in rows)
    strict = sum(r["strict"] for r in rows)
    L.append(f"# Pass-rate report: {len(rows)} customers, {sum(n for _, n, _ in used)} run(s) from {len(used)} file(s)\n")
    L.append(f"- Mean pass rate per customer-run: **{pct(total_pass / total_runs) if total_runs else 'n/a'}** ({total_pass} of {total_runs})")
    L.append(f"- Strict score (customer counts only when every run passes): **{strict} / {len(rows)}** ({pct(strict / len(rows)) if rows else 'n/a'})")
    unstable = [r for r in rows if 0 < r["passes"] < r["runs"]]
    L.append(f"- Flaky (passed some runs, failed others): {len(unstable)}" + (": " + ", ".join(r["id"] for r in unstable) if unstable else ""))
    never = [r for r in rows if r["passes"] == 0]
    L.append(f"- Never passed: {len(never)}" + (": " + ", ".join(r["id"] for r in never) if never else ""))
    L.append("")
    L.append("Files: " + "; ".join(f"{os.path.basename(f)} ({n} run{'s' if n != 1 else ''})" for f, n, _ in used))
    for f, why in skipped: L.append(f"Skipped {f}: {why}")
    L.append("")
    L.append("| Customer | Family | Level | Passes | Rate | Strict | Main failure |")
    L.append("|---|---|---|---|---|---|---|")
    for r in rows:
        main = f"{r['reasons'][0]['kind']} x{r['reasons'][0]['count']}" if r["reasons"] else ""
        L.append(f"| {r['id']} | {r['family']} | {r['level']} | {r['passes']}/{r['runs']} | {pct(r['rate'])} | {'PASS' if r['strict'] else 'FAIL'} | {main} |")
    if by_family:
        L.append("\n## By family\n")
        L.append("| Family | Customers | Mean rate | Strict |")
        L.append("|---|---|---|---|")
        fam = collections.OrderedDict()
        for r in rows: fam.setdefault(r["family"], []).append(r)
        for k, g in fam.items():
            L.append(f"| {k} | {len(g)} | {pct(sum(x['passes'] for x in g) / max(1, sum(x['runs'] for x in g)))} | {sum(x['strict'] for x in g)}/{len(g)} |")
    kinds = collections.Counter()
    for r in rows:
        for x in r["reasons"]: kinds[x["kind"]] += x["count"]
    if kinds:
        L.append("\n## Failure kinds\n")
        L.append(", ".join(f"{k}: {n}" for k, n in kinds.most_common()))
    failing = [r for r in rows if r["reasons"]]
    if failing:
        L.append("\n## Failure reasons per customer\n")
        for r in failing:
            L.append(f"**{r['id']}** {r['passes']}/{r['runs']} - {r['family']}")
            for x in r["reasons"]:
                L.append(f"- x{x['count']} [{x['kind']}] {x['text']}" + (f"  (call {x['call_id']})" if x["call_id"] else ""))
            ended = collections.Counter(f.get("ended") for f in r["fails"] if f.get("ended"))
            if ended.get("customer-ended-call"): L.append(f"- note: the customer hung up in {ended['customer-ended-call']} failed run(s); check agent speed before changing the agent")
            L.append("")
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("inputs", nargs="+", help="run_cases --out files, globs or directories")
    ap.add_argument("--md", help="also write the report to this Markdown file"); ap.add_argument("--json", help="also write the aggregate as JSON")
    ap.add_argument("--family", action="store_true", help="add a table per family")
    a = ap.parse_args()
    files = load(a.inputs)
    if not files: sys.exit("no input files")
    cases, used, skipped = aggregate(files)
    if not cases: sys.exit("no usable run_cases output in: " + ", ".join(files))
    rows = summarize(cases)
    text = render(rows, used, skipped, a.family)
    sys.stdout.buffer.write((text + "\n").encode("utf-8", "replace")); sys.stdout.flush()
    if a.md: open(a.md, "w", encoding="utf-8").write(text + "\n")
    if a.json: json.dump({"files": [f for f, _, _ in used], "customers": rows}, open(a.json, "w", encoding="utf-8"), indent=1)


if __name__ == "__main__": main()
