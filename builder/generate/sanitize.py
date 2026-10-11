"""Shape guard for the compiler: a spec section of the wrong type is coerced when its meaning is clear and dropped (with a
warning) when it is not, so one malformed section never kills `generate`.

    spec, notes = sanitize_spec(spec)     # notes: [{"path", "action": "coerced" | "dropped", "detail"}]

The parser's own shape check (parse/validate.shape_errors) normally repairs these; this is the second line of defence
for specs that reach the compiler anyway (a section the repair rounds could not fix, a hand-edited spec). Nothing is
invented: a string becomes {note: {reason}} / {outcome, reason} only when the words in it match values the tool API allows.
"""
import copy
import re

DICT_TOP = ("meta", "opening", "third_party", "identity", "debt_statement", "amounts", "persuasion", "confirmation",
            "multi_product", "closing", "calendar", "dates")
LIST_OF_DICTS_TOP = ("bands", "intents")
NESTED_DICT = {                     # path -> kind of value a bare string may be turned into
    ("opening", "on_unclear"): "outcome",
    ("third_party", "callback"): None, ("third_party", "wrong_number"): "outcome", ("third_party", "deceased"): "outcome",
    ("identity", "on_failed"): "outcome", ("identity", "on_declined"): "outcome",
    ("confirmation", "on_create_failed"): "outcome", ("persuasion", "on_exhausted"): "outcome",
    ("multi_product", "create_promise_failure"): "note",
    ("debt_statement", "product_names"): None, ("amounts", "floor_field_by_product"): None,
    ("amounts", "floor_formula_by_product"): None, ("amounts", "floor_percent_by_product"): None,
}
NESTED_LIST_OF_DICTS = (("identity", "questions"), ("persuasion", "attempts"), ("closing", "outcomes"), ("identity", "hints"))


def _tools(spec):
    t = spec.get("tools") or {}
    t = t.get("tools") if isinstance(t.get("tools"), dict) else t
    return t if isinstance(t, dict) else {}


def _enum(spec, tool, field):
    f = (((_tools(spec).get(tool) or {}).get("fields") or {}).get(field) or {})
    e = f.get("enum") if isinstance(f, dict) else None
    return [str(x) for x in e] if isinstance(e, list) else []


def _tokens_in(text, allowed):
    """Allowed values that appear in the text as whole words (underscores count as word characters)."""
    low = str(text).lower()
    return [a for a in allowed if re.search(r"(?<![a-z0-9_])" + re.escape(a.lower()) + r"(?![a-z0-9_])", low)]


def _coerce(spec, kind, text):
    """A bare string where an object belongs -> the object, or None when the words do not name an allowed value."""
    if kind == "note":
        reasons = _tokens_in(text, _enum(spec, "add_note", "reason"))
        mp = spec.get("multi_product") if isinstance(spec.get("multi_product"), dict) else {}
        if not reasons:
            reasons = _tokens_in(text, [str(r) for r in (mp.get("note_reasons") or []) if isinstance(r, str)])
        if reasons:          # the last named reason is the one the sentence ends on ("... note write_failed on that product")
            last = max(reasons, key=lambda r: str(text).lower().rfind(r.lower()))
            return {"note": {"reason": last}}
        return None
    if kind == "outcome":
        outs = _tokens_in(text, _enum(spec, "close_call", "outcome"))
        reasons = _tokens_in(text, _enum(spec, "close_call", "reason"))
        if len(outs) == 1:
            d = {"outcome": outs[0]}
            if len(reasons) == 1:
                d["reason"] = reasons[0]
            return d
    return None


def _note(notes, path, action, detail):
    notes.append({"path": ".".join(str(p) for p in path), "action": action, "detail": detail})


def sanitize_spec(spec):
    """-> (clean copy, notes). A spec that is not an object comes back unchanged."""
    if not isinstance(spec, dict):
        return spec, []
    s, notes = copy.deepcopy(spec), []

    def drop(path, parent, key, what):
        _note(notes, path, "dropped", "expected %s, got %s: %r" % (what, type(parent[key]).__name__, str(parent[key])[:80]))
        parent[key] = None

    for key in DICT_TOP:
        if key in s and s[key] is not None and not isinstance(s[key], dict):
            drop((key,), s, key, "an object")
    for key in LIST_OF_DICTS_TOP:
        v = s.get(key)
        if v is None:
            continue
        if not isinstance(v, list):
            drop((key,), s, key, "a list of objects")
        else:
            bad = [i for i, x in enumerate(v) if not isinstance(x, dict)]
            if bad:
                s[key] = [x for x in v if isinstance(x, dict)]
                _note(notes, (key,), "dropped", "%d entr%s not an object" % (len(bad), "y is" if len(bad) == 1 else "ies are"))
    for (sec, key), kind in NESTED_DICT.items():
        d = s.get(sec)
        if not isinstance(d, dict) or d.get(key) is None or isinstance(d[key], dict):
            continue
        v = d[key]
        c = _coerce(s, kind, v) if isinstance(v, str) and kind else None
        if c is not None:
            d[key] = c
            _note(notes, (sec, key), "coerced", "text %r read as %s" % (v[:60], c))
        else:
            drop((sec, key), d, key, "an object")
    for sec, key in NESTED_LIST_OF_DICTS:
        d = s.get(sec)
        if not isinstance(d, dict) or d.get(key) is None:
            continue
        v = d[key]
        if not isinstance(v, list):
            drop((sec, key), d, key, "a list of objects")
        elif any(not isinstance(x, dict) for x in v):
            n = sum(1 for x in v if not isinstance(x, dict))
            d[key] = [x for x in v if isinstance(x, dict)]
            _note(notes, (sec, key), "dropped", "%d entr%s not an object" % (n, "y is" if n == 1 else "ies are"))
    for it in s.get("intents") or []:                       # branches inside intents
        for key in ("on_accept", "on_decline", "close_verified", "close_unverified", "action"):
            if key in it and it[key] is not None and not isinstance(it[key], dict):
                c = _coerce(s, "outcome", it[key]) if isinstance(it[key], str) else None
                if c is not None:
                    _note(notes, ("intents", it.get("id"), key), "coerced", "text %r read as %s" % (it[key][:60], c))
                    it[key] = c
                else:
                    drop(("intents", it.get("id"), key), it, key, "an object")
    return s, notes


def describe_notes(notes):
    """Warning lines for generate.LAST_WARNINGS; ecfg.BLOCKING_MARKS makes ' dropped: ' ones label the build degraded."""
    return ["malformed spec section %s %s: %s" % (n["path"], n["action"], n["detail"]) for n in notes]
