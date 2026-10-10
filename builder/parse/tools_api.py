"""Turn the bank's OpenAPI tool file into the spec's `tools` block. No model involved: enums and fields come only from this file."""
import json
import pathlib


def _fields(props, required):
    out = {}
    for name, p in (props or {}).items():
        f = {k: p[k] for k in ("type", "enum", "format", "description") if k in p}
        if p.get("type") == "array" and isinstance(p.get("items"), dict):
            it = p["items"]
            if it.get("type") == "object":
                f["items"] = _fields(it.get("properties"), it.get("required", []))
            else:
                f["items"] = {k: it[k] for k in ("type", "enum") if k in it}
        if p.get("type") == "object" and p.get("properties"):
            f["fields"] = _fields(p["properties"], p.get("required", []))
        f["required"] = name in (required or [])
        out[name] = f
    return out


def tools_from_openapi(path):
    api = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    tools = {}
    for route, methods in api.get("paths", {}).items():
        for method, op in methods.items():
            req = (op.get("requestBody", {}).get("content", {}).get("application/json", {}).get("schema", {}))
            resp = (op.get("responses", {}).get("200", {}).get("content", {}).get("application/json", {}).get("schema", {}))
            name = route.strip("/")
            tools[name] = {
                "summary": op.get("summary"),
                "method": method.upper(),
                "path": route,
                "fields": _fields(req.get("properties"), req.get("required")),
                "response_fields": _fields(resp.get("properties"), resp.get("required")),
            }
    return {"server": (api.get("servers") or [{}])[0].get("url"), "tools": tools}


if __name__ == "__main__":
    import sys
    print(json.dumps(tools_from_openapi(sys.argv[1]), indent=1))
