"""Enum guard: values the spec would send to the bank that the supplied tool API does not allow.

    problems = enum_problems(spec)            # close_call outcomes, transfer queues, add_note reasons, verify_identity fields, tool names
    spec, changes = auto_repair(spec)         # model-free: only a unique spelling variant of an allowed value is renamed

A close_call whose outcome is outside the API enum is refused by the bank on every call, so the guard runs before the
generator. Renames are limited to spelling variants (case, separators, plural, a prefix such as "not_" kept intact);
a meaning change is never guessed: what stays unresolved goes to one targeted model repair (spec_parser.guard_enums).
"""
import copy
import difflib
import re

SKIP = ("rule_coverage", "extra_rules", "tools", "tools_server", "parser")


def _tools(spec):
    t = spec.get("tools") or {}
    t = t.get("tools") if isinstance(t.get("tools"), dict) else t
    return {k: v for k, v in t.items() if isinstance(v, dict)}


def _enum(tools, tool, field):
    return (((tools.get(tool) or {}).get("fields") or {}).get(field) or {}).get("enum")


def allowed_sets(spec):
    tools = _tools(spec)
    return {"outcome": _enum(tools, "close_call", "outcome"), "queue": _enum(tools, "transfer_to_agent", "queue"),
            "note_reason": _enum(tools, "add_note", "reason"), "id_field": _enum(tools, "verify_identity", "field"),
            "tool": sorted(tools) or None}


def _walk(node, path=()):
    if isinstance(node, dict):
        for k, v in node.items():
            yield path + (k,), k, v
            yield from _walk(v, path + (k,))
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from _walk(v, path + (i,))


def enum_problems(spec):
    """-> list of {path, value, kind, allowed}. Empty when the tool API block is missing (nothing to compare with)."""
    al = allowed_sets(spec)
    body = {k: v for k, v in spec.items() if k not in SKIP}
    out = []

    def bad(path, value, kind):
        if isinstance(value, str) and al.get(kind) and value not in al[kind]:
            out.append({"path": path, "value": value, "kind": kind, "allowed": list(al[kind])})
    for path, key, val in _walk(body):
        if key == "outcome":
            bad(path, val, "outcome")
        elif key in ("transfer", "queue", "offer_transfer"):
            bad(path, val, "queue")
        elif key == "note_reasons" and isinstance(val, list):
            for i, r in enumerate(val):
                bad(path + (i,), r, "note_reason")
        elif key in ("note", "add_note"):
            if isinstance(val, dict):
                bad(path + ("reason",), val.get("reason"), "note_reason")
            elif isinstance(val, str):
                bad(path, val, "note_reason")
        elif key in ("tool", "close_tool", "note_tool"):
            bad(path, val, "tool")
    for i, q in enumerate(((spec.get("identity") or {}).get("questions")) or []):
        if isinstance(q, dict):
            bad(("identity", "questions", i, "field"), q.get("field"), "id_field")
    return out


def _norm(s):
    return re.sub(r"[^a-z0-9]", "", str(s).lower())


def closest(value, allowed):
    """The one allowed value that is a spelling variant of value (case, separators, trailing s / ed), else None."""
    n = _norm(value)
    if not n:
        return None
    exact = [a for a in allowed if _norm(a) == n]
    if len(exact) == 1:
        return exact[0]
    stem = lambda x: re.sub(r"(ed|s)$", "", _norm(x))
    same = [a for a in allowed if stem(a) == stem(value)]
    if len(same) == 1:
        return same[0]
    close = difflib.get_close_matches(n, [_norm(a) for a in allowed], n=2, cutoff=0.88)
    if len(close) == 1:
        hit = [a for a in allowed if _norm(a) == close[0]]
        if len(hit) == 1 and not (n.startswith("not") != close[0].startswith("not")):
            return hit[0]
    return None


def _set(spec, path, value):
    cur = spec
    for p in path[:-1]:
        cur = cur[p]
    cur[path[-1]] = value


def auto_repair(spec):
    """-> (new spec, [change text]). Renames a value to its allowed spelling variant, everywhere that exact value is used
    in the same kind of position. Anything without a unique variant is left alone."""
    spec = copy.deepcopy(spec)
    changes, renamed = [], {}
    for p in enum_problems(spec):
        key = (p["kind"], p["value"])
        if key not in renamed:
            renamed[key] = closest(p["value"], p["allowed"])
        new = renamed[key]
        if new is not None:
            _set(spec, p["path"], new)
            changes.append("%s: %r -> %r" % (".".join(str(x) for x in p["path"]), p["value"], new))
    return spec, changes


def describe(problems):
    return ["%s = %r is not allowed by the tool API (%s: %s)" % (".".join(str(x) for x in p["path"]), p["value"], p["kind"], p["allowed"])
            for p in problems]
