"""Offline checks on a generated workflow before it is allowed near a simulation.

python ci/lint_workflow.py out/gen-a.workflow.json [--openapi tools/openapi.json] [--dry-run]

Exit code 0 = clean. --dry-run also asks Freya to validate it (POST /api/v2/workflow?dryRun=true, stores nothing).
"""
import argparse, json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

VAR = re.compile(r"\{\{\s*([A-Za-z_][\w.]*)\s*\}\}")


def lint(wf, openapi=None):
    errs, warns = [], []
    nodes = wf.get("nodes") or {}
    gnodes = wf.get("global_nodes") or {}
    allnodes = {**nodes, **gnodes}
    if "agent_config" in wf:
        errs.append("agent_config must be left out")
    if wf.get("initial_node") not in nodes:
        errs.append(f"initial_node {wf.get('initial_node')!r} is not a node")

    # transitions point at real nodes; every node reachable; every non-end node has a way out
    edges = {}
    for name, n in allnodes.items():
        tgts = []
        for t in n.get("transitions") or []:
            tg = t.get("target_node")
            if tg != "__previous__" and tg not in allnodes:
                errs.append(f"{name}: transition to unknown node {tg!r}")
            tgts.append(tg)
            c = t.get("condition") or {}
            for cc in c.get("conditions", [c]):
                op = cc.get("operator")
                if op in ("equals", "not_equals", "greater_than", "less_than", "contains") and "operand" not in cc:
                    errs.append(f"{name}: {op} condition without operand")
        edges[name] = tgts
        if n.get("node_type") != "end_call" and not tgts:
            warns.append(f"{name}: no transitions and not an end_call node (ok only if a tool ends the call)")
    seen, todo = set(), [wf.get("initial_node")] + list(gnodes)
    while todo:
        x = todo.pop()
        if x in seen or x not in allnodes:
            continue
        seen.add(x)
        todo += edges.get(x, [])
    for name in nodes:
        if name not in seen:
            warns.append(f"{name}: unreachable from initial_node")
    if not any(n.get("node_type") == "end_call" for n in allnodes.values()):
        warns.append("no end_call node (ok only if a tool ends the call)")

    # {{vars}} used in text must be produced somewhere (call vars, test vars, extraction, code, mappings)
    blob = json.dumps(wf)
    produced = set(wf.get("test_variables") or {})
    produced |= set(re.findall(r"vars\[['\"]([\w.]+)['\"]\]", blob))
    produced |= set(re.findall(r"\"([\w.]+)\"\s*:\s*\{\s*\"type\"", blob))  # extraction schema properties
    for n in allnodes.values():
        for v in (n.get("response_mapping") or {}).values() if isinstance(n.get("response_mapping"), dict) else []:
            produced.add(str(v))
    used = set(VAR.findall(blob))
    for v in sorted(used - produced):
        if not v.endswith("_response") and "_response." not in v:
            warns.append(f"{{{{{v}}}}} used but no producer found (check it is a call variable)")

    # tool enums must come from the tool API file
    if openapi:
        enums = {}
        for path, ops in openapi.get("paths", {}).items():
            for op in ops.values():
                sch = (((op.get("requestBody") or {}).get("content") or {}).get("application/json") or {}).get("schema") or {}
                for f, p in (sch.get("properties") or {}).items():
                    if "enum" in p:
                        enums[(path.strip("/"), f)] = set(map(str, p["enum"]))
        for (tool, field), allowed in enums.items():
            for m in re.finditer(r'\\?"%s\\?"\s*:\s*\\?"([^"\\{]+)\\?"' % re.escape(field), blob):
                val = m.group(1)
                if val not in allowed and tool in blob:
                    warns.append(f"{tool}.{field} = {val!r} not in tool API enum {sorted(allowed)}")
    return errs, sorted(set(warns))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("workflow")
    ap.add_argument("--openapi", default=str(ROOT / "tools/openapi.json"))
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    wf = json.load(open(a.workflow, encoding="utf-8"))
    if set(wf) == {"workflow"}:  # export / dry-run envelope
        wf = wf["workflow"]
    errs, warns = lint(wf, json.load(open(a.openapi, encoding="utf-8")) if a.openapi else None)
    for w in warns:
        print("WARN", w)
    for e in errs:
        print("ERROR", e)
    if a.dry_run and not errs:
        import freya
        try:
            freya.api("POST", "/api/v2/workflow", {"name": "lint-dry-run", "workflow": wf}, dryRun="true")
            print("dry run: accepted by Freya")
        except Exception as e:  # any HTTP error is a failure, as in the reference client
            errs.append(f"dry run rejected: {str(e)[:400]}")
            print("ERROR", errs[-1])
    print(f"{len(errs)} error(s), {len(warns)} warning(s)")
    sys.exit(1 if errs else 0)


if __name__ == "__main__":
    main()
