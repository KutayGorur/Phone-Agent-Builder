"""Parse twice, compare the critical facts, resolve the disagreements.

    facts = critical_facts(spec)                          # {fact id: normalised value}, read the way the compiler reads the spec
    diffs = disagreements(spec_a, spec_b)                 # [{id, label, a, b}]
    spec, log = resolve(spec_a, spec_b, diffs, decide)    # decide(diffs) -> {id: {"choice": "A"|"B", "unit": ..., "quote": ...}}

The second spec comes from a plain second extraction (no audit, no repair); the first spec is the repaired one and is the
base. Facts are compared after compiling (builder/generate/ecfg.build_E_warn), so two specs that spell a key differently
but mean the same thing do not count as a disagreement. A disagreement is settled by, in order:
  1. a rule for the safer value (holidays: union, business days: intersection, identity wrong-answer limit: the larger
     one because the bank enforces the real limit);
  2. a targeted model call that must name the brief unit and quote its words; a choice whose quote is not in that unit
     is ignored;
  3. the first spec's value.
Every change is re-compiled and kept only if the fact then equals the chosen value and no other fact moved.
"""
import copy
import re

DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def _compiled(spec):
    """The compiler's reading of the spec. A spec the full compile rejects (an unrepaired second parse may) still gives the
    parts that can be read on their own: calendar, bands, callback, floors, intents."""
    from builder.generate import ecfg
    s = copy.deepcopy(spec)
    try:
        E, _ = ecfg.build_E_warn(s)
        return E
    except Exception:  # noqa: BLE001
        pass
    s = copy.deepcopy(spec)
    E = {"cal": ecfg.config_from_spec(s)}
    for name, fn in (("floors", lambda: ecfg.floor_rules((s.get("amounts") or {}), "past_due", None)),
                     ("intents", lambda: ecfg.normalize_intents(s))):
        try:
            v = fn()
            if name == "floors":
                E["floor_field"], E["formula"] = v
            else:
                E["intents"] = v
        except Exception:  # noqa: BLE001
            pass
    return E


def _qs(spec):
    return [q for q in ((spec.get("identity") or {}).get("questions") or []) if isinstance(q, dict)]


def _f_business_days(E, spec):
    return sorted(E["cal"]["bd"])


def _f_holidays(E, spec):
    return sorted(E["cal"]["holidays"])


def _f_bands(E, spec):
    return [[b.get("min"), b.get("max"), b.get("deadline_bd"), b.get("attempts")] for b in E["cal"]["bands"]]


def _f_floors(E, spec):
    out = {t: ["field", f] for t, f in (E["floor_field"] or {}).items() if f}
    for t, fm in (E["formula"] or {}).items():
        if isinstance(fm, dict):
            out[t] = ["pct", fm.get("field"), fm.get("percent_of_field")]
    return out


def _f_id_fields(E, spec):
    return [q.get("field") for q in _qs(spec)]


def _f_id_limit(E, spec):
    v = (spec.get("identity") or {}).get("max_wrong_answers_total")
    return v if isinstance(v, int) and not isinstance(v, bool) else None


def _f_outcomes(E, spec):
    out = {}
    for o in ((spec.get("closing") or {}).get("outcomes") or []):
        if isinstance(o, dict) and o.get("outcome"):
            out[str(o["outcome"])] = sorted(str(r) for r in (o.get("reasons") or []))
    return out


def _f_queues(E, spec):
    out = {}
    for it in E["intents"].values():
        if not isinstance(it, dict):
            continue
        q = it.get("queue") or ((it.get("on_accept") or {}).get("queue"))
        if q:
            out[str(it.get("id"))] = q
    return out


def _f_persuasion(E, spec):
    return [[p.get("n"), p.get("amt"), p.get("date"), p.get("bands")] for p in E["pers"]]


def _f_callback(E, spec):
    c = E["cal"]
    return [c.get("cb_days"), c.get("cb_start"), c.get("cb_end"), c.get("cb_inclusive"), c.get("cb_after_now")]


def _f_dob_order(E, spec):
    return E["cal"].get("dob_order")


def _f_multi(E, spec):
    m = spec.get("multi_product")
    return [bool(m), (spec.get("meta") or {}).get("max_products")]


# ---------------------------------------------------------------- how a chosen value is written into the base spec

def _copy_path(dst, src, path):
    """dst[path] = copy of src[path]; a path missing in src is removed from dst."""
    d, s = dst, src
    for k in path[:-1]:
        if not isinstance(s, dict) or k not in s:
            s = None
            break
        s = s[k]
        d = d.setdefault(k, {}) if isinstance(d.get(k), (dict, type(None))) else d[k]
    if isinstance(s, dict) and path[-1] in s:
        d[path[-1]] = copy.deepcopy(s[path[-1]])
    else:
        d.pop(path[-1], None)


def _apply_paths(*paths):
    def apply(base, src, value):
        for p in paths:
            _copy_path(base, src, p)
    return apply


def _apply_queues(base, src, value):
    by_id = {i.get("id"): i for i in (src.get("intents") or []) if isinstance(i, dict)}
    for n, it in enumerate(base.get("intents") or []):
        if isinstance(it, dict) and it.get("id") in value and it.get("id") in by_id:
            base["intents"][n] = copy.deepcopy(by_id[it["id"]])


def _apply_multi(base, src, value):
    _copy_path(base, src, ("multi_product",))
    _copy_path(base, src, ("meta", "multi_product"))
    _copy_path(base, src, ("meta", "max_products"))


def _put_days(base, src, value):
    base.setdefault("calendar", {})["business_days"] = [DAYS[i] for i in value]


def _put_holidays(base, src, value):
    base.setdefault("calendar", {})["holidays"] = list(value)


def _put_outcomes(base, src, value):
    outs = (base.setdefault("closing", {})).get("outcomes")
    if not isinstance(outs, list):
        return
    for o in outs:
        if isinstance(o, dict) and o.get("outcome") in value:
            o["reasons"] = list(value[o["outcome"]])
    have = {o.get("outcome") for o in outs if isinstance(o, dict)}
    other = {o.get("outcome"): o for o in ((src.get("closing") or {}).get("outcomes") or []) if isinstance(o, dict)}
    for name, reasons in value.items():
        if name not in have and name in other:
            o = copy.deepcopy(other[name]); o["reasons"] = list(reasons); outs.append(o)


# ---------------------------------------------------------------- safer-value rules: (a, b) -> merged value or None

def _safer_days(a, b):
    both = sorted(set(a) & set(b))
    return both or None                       # fewer business days only ever makes a date refused, never a holiday accepted


def _safer_holidays(a, b):
    return sorted(set(a) | set(b))            # an extra holiday refuses a valid day; a missed one records a promise on a closed day


def _safer_limit(a, b):
    if a is None or b is None:
        return None
    return max(a, b)                          # the bank locks the check itself; a lower limit here would stop customers early


def _safer_outcomes(a, b):
    out = {}
    for k in sorted(set(a) | set(b)):
        out[k] = sorted(set(a.get(k, [])) | set(b.get(k, [])))
    return out


# id, label, getter, paths/apply, safer, put (writes a merged value)
FACTS = [
    ("business_days", "business days", _f_business_days, None, _safer_days, _put_days),
    ("holidays", "holidays", _f_holidays, None, _safer_holidays, _put_holidays),
    ("bands", "bands [days_late_min, days_late_max, deadline business days, persuasion attempts]", _f_bands, _apply_paths(("bands",)), None, None),
    ("floors", "floor per product type", _f_floors, _apply_paths(("amounts", "floor_field_by_product"), ("amounts", "floor_formula_by_product")), None, None),
    ("identity_fields", "identity questions in order", _f_id_fields, _apply_paths(("identity", "questions")), None, None),
    ("identity_limit", "wrong identity answers allowed in total", _f_id_limit, _apply_paths(("identity", "max_wrong_answers_total")), _safer_limit, None),
    ("outcomes", "closing outcome -> reasons", _f_outcomes, _apply_paths(("closing", "outcomes")), _safer_outcomes, _put_outcomes),
    ("queues", "transfer queue per intent", _f_queues, _apply_queues, None, None),
    ("persuasion", "persuasion attempts [n, amount, date, bands]", _f_persuasion, _apply_paths(("persuasion",)), None, None),
    ("callback", "callback rules [days, start, end, inclusive, after now]", _f_callback, _apply_paths(("third_party", "callback")), None, None),
    ("dob_order", "numeric date order", _f_dob_order, _apply_paths(("identity", "questions")), None, None),
    ("multi_product", "multi-product call [on, max products]", _f_multi, _apply_multi, None, None),
]
_BY_ID = {f[0]: f for f in FACTS}


def critical_facts(spec):
    """{fact id: value}; a fact the compiler cannot read from this spec is left out."""
    try:
        E = _compiled(spec)
    except Exception:  # noqa: BLE001
        return {}
    out = {}
    for fid, _label, get, *_ in FACTS:
        try:
            out[fid] = get(E, spec)
        except Exception:  # noqa: BLE001
            pass
    return out


def disagreements(spec_a, spec_b):
    fa, fb = critical_facts(spec_a), critical_facts(spec_b)
    out = []
    for fid, label, *_ in FACTS:
        if fid in fa and fid in fb:
            if fa[fid] != fb[fid]:
                d = {"id": fid, "label": label, "a": fa[fid], "b": fb[fid]}
                if _empty(fb[fid]) and not _empty(fa[fid]):
                    d["b_unreadable"] = True          # the second parse found nothing: that is a miss, not a rival value
                out.append(d)
        elif fid in fa and not _empty(fa[fid]):
            out.append({"id": fid, "label": label, "a": fa[fid], "b": None, "b_unreadable": True})
    return out


def _empty(v):
    return v in (None, [], {}, "")


def _squash(s):
    return re.sub(r"[^a-z0-9]+", " ", str(s).lower()).strip()


def quote_ok(quote, unit_text):
    q = _squash(quote)
    return len(q) >= 6 and q in _squash(unit_text)


def decision_prompt_items(diffs):
    """Neutral labels: the arbiter sees option 1 and option 2, alternating which run is first."""
    items = []
    for n, d in enumerate(diffs):
        flip = n % 2 == 1
        first, second = (d["b"], d["a"]) if flip else (d["a"], d["b"])
        items.append({"id": d["id"], "what": d["label"], "option_1": first, "option_2": second, "_flip": flip})
    return items


def read_decisions(raw, diffs, unit_text):
    """The model's reply -> {fact id: 'a' | 'b'} for every decision that names a unit and quotes it correctly."""
    flip = {it["id"]: it["_flip"] for it in decision_prompt_items(diffs)}
    out = {}
    for d in (raw or {}).get("decisions") or []:
        if not isinstance(d, dict) or d.get("id") not in flip:
            continue
        ch = str(d.get("choice") or "").strip().lower().replace("option", "").replace("_", "").strip()
        if ch not in ("1", "2"):
            continue
        txt = unit_text.get(str(d.get("unit")))
        if not txt or not quote_ok(d.get("quote") or "", txt):
            continue
        pick_first = ch == "1"
        out[d["id"]] = ("b" if pick_first else "a") if flip[d["id"]] else ("a" if pick_first else "b")
    return out


def resolve(spec_a, spec_b, diffs, decide=None):
    """-> (spec, log). spec is spec_a with the resolved facts written in; log has one entry per disagreement."""
    spec = copy.deepcopy(spec_a)
    log = []
    todo, safer_done = [], set()
    for d in diffs:
        fid = d["id"]
        entry = {"id": fid, "a": d["a"], "b": d["b"]}
        log.append(entry)
        _, _, _, apply, safer, put = _BY_ID[fid]
        merged = safer(d["a"], d["b"]) if (safer and not d.get("b_unreadable")) else None
        if merged is not None:
            entry["rule"] = "safer value"
            entry["chosen"] = merged
            if _commit(spec, spec_b, fid, merged, apply, put, entry):
                safer_done.add(fid)
            continue
        if d.get("b_unreadable"):
            entry.update({"rule": "kept the first parse (the second found nothing)", "chosen": d["a"], "applied": True})
            continue
        todo.append(d)
    decisions = {}
    if todo and decide:
        try:
            decisions = decide(todo) or {}
        except Exception as e:  # noqa: BLE001
            for en in log:
                if en["id"] in {t["id"] for t in todo}:
                    en["model_error"] = str(e)[:150]
    by_id = {e["id"]: e for e in log}
    for d in todo:
        en, ch = by_id[d["id"]], decisions.get(d["id"])
        _, _, _, apply, _s, put = _BY_ID[d["id"]]
        if ch in ("a", "b") and not d.get("b_unreadable"):
            en["rule"] = "brief text decides (model re-ask)"
            en["chosen"] = d[ch]
            if ch == "a":
                en["applied"] = True                     # the base already holds it
                continue
            _commit(spec, spec_b, d["id"], d["b"], apply, put, en)
        else:
            en["rule"] = "kept the first parse"
            en["chosen"] = d["a"]
            en["applied"] = True
    return spec, log


def _commit(spec, spec_b, fid, value, apply, put, entry):
    """Write `value` into spec; verified by compiling again. A write that does not give exactly `value`, or that moves
    another fact, is undone."""
    before = critical_facts(spec)
    trial = copy.deepcopy(spec)
    try:
        if put is not None and entry.get("rule") == "safer value":
            put(trial, spec_b, value)
        elif apply is not None:
            apply(trial, spec_b, value)
        else:
            raise ValueError("no writer")
    except Exception as e:  # noqa: BLE001
        entry["applied"] = False; entry["problem"] = "could not write: " + str(e)[:100]
        return False
    after = critical_facts(trial)
    moved = [k for k in before if k != fid and after.get(k) != before[k]]
    if after.get(fid) != value or moved:
        entry["applied"] = False
        entry["problem"] = "kept the first parse: the change did not reproduce the chosen value" + (f" or moved {moved}" if moved else "")
        return False
    spec.clear(); spec.update(trial)
    entry["applied"] = True
    return True
