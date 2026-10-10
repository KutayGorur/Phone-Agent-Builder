"""Local pre-flight for a generated workflow. No Freya call, no simulation, no credits.

    python harness/preflight.py <workflow.json> <tools.openapi.json> [--base tools/openapi.json] [--strict]

Checks the workflow file against the tool API file it was built for:
  ERROR  a tool URL whose path is not one of the API's seven calls, or is not POST
  ERROR  a body field the API does not have, or a required API field the tool never sends
  ERROR  a fixed value (default / enum) for an enum field that is not in the API's enum
  ERROR  a stale literal: an enum value of the base API (tools/openapi.json) that the new API does not allow,
         found quoted ('x', "x" or `x`) in a prompt or code string of the workflow (a name carried over from another brief)
  WARN   a tool of the API that the workflow never calls
  WARN   an enum value of the API (outcome, reason, queue, note reason, verify field) that appears nowhere in the workflow text
  WARN   a tool URL host different from the API's server
Exit code 1 when there are errors (or warnings with --strict). Standard library only.
Run it on every generated workflow before the first simulation; it takes under a second.
"""
import argparse, json, pathlib, re, sys
from urllib.parse import urlparse

ROOT = pathlib.Path(__file__).resolve().parent.parent


def enums_of(api):
    """{(tool, field): [values]} for every enum in a request body, plus the hint enum of verify_identity."""
    out = {}
    for path, item in api["paths"].items():
        t = path.strip("/")
        for k, v in item["post"]["requestBody"]["content"]["application/json"]["schema"]["properties"].items():
            if "enum" in v: out[(t, k)] = v["enum"]
    return out


def body_schema(api, tool):
    s = api["paths"]["/" + tool]["post"]["requestBody"]["content"]["application/json"]["schema"]
    return s["properties"], set(s.get("required", []))


def api_tools(node, found):
    """Collect every api_call tool function as (location, function dict)."""
    if isinstance(node, dict):
        if node.get("handler") == "__function__:api_call" and "parameters" in node:
            found.append(node)
        for v in node.values(): api_tools(v, found)
    elif isinstance(node, list):
        for v in node: api_tools(v, found)


def strings(node, out):
    if isinstance(node, str): out.append(node)
    elif isinstance(node, dict):
        for v in node.values(): strings(v, out)
    elif isinstance(node, list):
        for v in node: strings(v, out)


def check(workflow, api, base, strict=False):
    errors, warns = [], []
    funcs = []; api_tools(workflow, funcs)
    tools_api = {p.strip("/") for p in api["paths"]}
    server = api["servers"][0]["url"]
    en = enums_of(api)
    called = set()
    for f in funcs:
        props = f["parameters"].get("properties", {})
        url = (props.get("url") or {}).get("default", "")
        method = (props.get("method") or {}).get("default", "POST")
        name = f.get("name", "?")
        m = re.fullmatch(r"(https?://[^/]+)(/.*)/(\w+)", url or "")
        tool = m.group(3) if m else None
        if tool not in tools_api:
            errors.append(f"tool '{name}': URL {url!r} does not end in one of {sorted(tools_api)}"); continue
        called.add(tool)
        if method.upper() != "POST": errors.append(f"tool '{name}': method {method}, the API uses POST")
        if urlparse(url).netloc != urlparse(server).netloc: warns.append(f"tool '{name}': host {urlparse(url).netloc} differs from the API server {urlparse(server).netloc}")
        sprops, required = body_schema(api, tool)
        body = (props.get("body") or {}).get("properties", {})
        for k, v in body.items():
            if k not in sprops: errors.append(f"tool '{name}': body field '{k}' is not in the API ({sorted(sprops)})"); continue
            vals = ([v["default"]] if isinstance(v.get("default"), str) and "{{" not in v["default"] else []) + list(v.get("enum", []))
            for x in vals:
                if (tool, k) in en and x not in en[(tool, k)]: errors.append(f"tool '{name}': {k}={x!r} is not allowed, the API says {en[(tool, k)]}")
        sent = set(body) | {k for k, v in body.items() if "default" in v}
        for r in required - sent:
            errors.append(f"tool '{name}': required field '{r}' is never sent")
    for t in sorted(tools_api - called): warns.append(f"the workflow never calls {t}")
    # literals
    texts = []; strings(workflow, texts)
    blob = "\n".join(texts)
    def present(v): return re.search(r"(?<![A-Za-z0-9_])" + re.escape(v) + r"(?![A-Za-z0-9_])", blob) is not None
    new_vals = {v for vs in en.values() for v in vs}
    for (t, k), vs in sorted(en.items()):
        for v in vs:
            if not present(v): warns.append(f"{t}.{k}: value {v!r} appears nowhere in the workflow text")
    if base is not None:
        stale = {v for vs in enums_of(base).values() for v in vs} - new_vals
        # words that are also ordinary English or call-variable names are not reported
        for v in sorted(stale):
            if len(v) >= 5 and re.search(r"""['"`]""" + re.escape(v) + r"""['"`]""", blob): errors.append(f"stale literal {v!r}: allowed by the base API but not by this one")
    return errors, warns


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("workflow"); ap.add_argument("api"); ap.add_argument("--base", default=str(ROOT / "tools" / "openapi.json"), help="the base API whose names must not leak (default tools/openapi.json; 'none' to skip)")
    ap.add_argument("--strict", action="store_true")
    a = ap.parse_args()
    wf = json.load(open(a.workflow, encoding="utf-8")); wf = wf.get("workflow", wf)
    api = json.load(open(a.api, encoding="utf-8"))
    base = None if a.base == "none" else json.load(open(a.base, encoding="utf-8"))
    errors, warns = check(wf, api, base)
    for e in errors: print("ERROR", e)
    for w in warns: print("WARN ", w)
    print(f"{len(errors)} error(s), {len(warns)} warning(s)")
    sys.exit(1 if errors or (a.strict and warns) else 0)


if __name__ == "__main__": main()
