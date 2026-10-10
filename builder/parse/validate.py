"""Deterministic checks of a parsed spec against the brief units and the tool API. No model, no brief-specific values.

validate(spec, units, tools) -> (errors, warnings)
  errors   = things the repair step must fix (missing coverage, values outside the tool API's enums, broken paths)
  warnings = things worth a second look (a date or number in the spec that the brief text does not contain)
"""
import re

TOP_KEYS = ["meta", "call_variables", "opening", "third_party", "identity", "debt_statement", "calendar", "bands",
            "dates", "amounts", "persuasion", "confirmation", "intents", "multi_product", "closing", "extra_rules",
            "rule_coverage"]
# top-level sections that are always present in the output (null when the brief does not define them)
SECTION_GROUPS = {
    "g1": ["meta", "call_variables", "opening", "third_party", "identity", "debt_statement"],
    "g2": ["calendar", "bands", "dates", "amounts", "persuasion", "confirmation"],
    "g3": ["intents", "multi_product", "closing"],
}
NUMBER_WORDS = ("zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen "
                "seventeen eighteen nineteen twenty").split()
ORDINALS = ("zeroth first second third fourth fifth sixth seventh eighth ninth tenth eleventh twelfth thirteenth "
            "fourteenth fifteenth sixteenth seventeenth eighteenth nineteenth twentieth").split()
WEEKDAYS = {"Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"}


def _walk(node, path=""):
    """Yield (path, key, value) for every dict entry in the tree."""
    if isinstance(node, dict):
        for k, v in node.items():
            p = f"{path}.{k}" if path else k
            yield p, k, v
            yield from _walk(v, p)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from _walk(v, f"{path}[{i}]")


def _tokens(path):
    """'intents[hardship].on_accept' -> ['intents', ('sel','hardship'), 'on_accept']"""
    out = []
    for part in re.findall(r"[^.\[\]]+|\[[^\]]*\]", path.strip()):
        out.append(("sel", part[1:-1]) if part.startswith("[") else part)
    return out


def path_exists(spec, path):
    cur = spec
    for tok in _tokens(path):
        if isinstance(tok, tuple):
            sel = tok[1]
            if not isinstance(cur, list):
                return False
            if sel.isdigit() and int(sel) < len(cur) and not any(isinstance(x, dict) and str(x.get("source")) == sel for x in cur):
                cur = cur[int(sel)]
                continue
            hit = next((x for x in cur if isinstance(x, dict) and sel in (str(x.get("id")), str(x.get("source")),
                                                                         str(x.get("name")), str(x.get("outcome")),
                                                                         str(x.get("field")))), None)
            if hit is None:
                return False
            cur = hit
        else:
            if not isinstance(cur, dict) or tok not in cur:
                return False
            cur = cur[tok]
    return True


def split_coverage(value):
    return [p.strip() for p in re.split(r";|\n", str(value)) if p.strip()]


def _enum(tools, tool, field, response=False):
    t = tools.get(tool) or {}
    f = (t.get("response_fields" if response else "fields") or {}).get(field) or {}
    return f.get("enum")


def number_in_text(n, text):
    n = int(n)
    low = text.lower()
    if re.search(rf"(?<![\d.]){n}(?:st|nd|rd|th)?(?![\d])", low):
        return True
    if n < len(NUMBER_WORDS) and re.search(rf"\b({NUMBER_WORDS[n]}|{ORDINALS[n]})\b", low):
        return True
    return False


def _is_str_list(v):
    return isinstance(v, list) and all(isinstance(x, str) for x in v)


def _is_dict_list(v):
    return isinstance(v, list) and all(isinstance(x, dict) for x in v)


def _branch_reason_or_outcome(br):
    """True when the generator can read an outcome or a reason from this branch (same shapes as ecfg._oc)."""
    if not isinstance(br, dict):
        return False
    for k in ("close", "base"):
        if isinstance(br.get(k), dict) and _branch_reason_or_outcome(br[k]):
            return True
    if br.get("outcome") or br.get("reason"):
        return True
    n = br.get("note") or br.get("add_note")
    return bool(isinstance(n, str) and n or isinstance(n, dict) and n.get("reason") or isinstance(br.get("note_products_without_promise"), str))


def shape_errors(spec):
    """Path-specific errors for malformed nested shapes. Every later check can then rely on these types."""
    errs = []

    def need(path, ok, what, val):
        if not ok:
            errs.append(f"{path} must be {what}, got {str(val)[:80]!r}")
        return ok

    def sec(key, kind=dict):
        v = spec.get(key)
        if v is None:
            return None
        return v if need(key, isinstance(v, kind), "an object" if kind is dict else "a list", v) else None

    closing = sec("closing")
    if closing is not None:
        outs = closing.get("outcomes")
        if outs is not None and need("closing.outcomes", _is_dict_list(outs), "a list of objects", outs):
            for i, o in enumerate(outs):
                if o.get("outcome") is not None:
                    need(f"closing.outcomes[{i}].outcome", isinstance(o["outcome"], str), "a string", o["outcome"])
                if o.get("reasons") is not None:
                    need(f"closing.outcomes[{i}].reasons", _is_str_list(o["reasons"]), "a list of strings", o["reasons"])
        if closing.get("reason_required_except") is not None:
            need("closing.reason_required_except", _is_str_list(closing["reason_required_except"]), "a list of strings", closing["reason_required_except"])
    ident = sec("identity")
    if ident is not None and ident.get("questions") is not None:
        qs = ident["questions"]
        if need("identity.questions", _is_dict_list(qs), "a list of objects", qs):
            for i, q in enumerate(qs):
                if q.get("field") is not None:
                    need(f"identity.questions[{i}].field", isinstance(q["field"], str), "a string", q["field"])
    cal = sec("calendar")
    if cal is not None:
        for key in ("holidays", "business_days"):
            if cal.get(key) is not None:
                need(f"calendar.{key}", _is_str_list(cal[key]), "a list of strings", cal[key])
    bands = spec.get("bands")
    if bands is not None and need("bands", _is_dict_list(bands), "a list of objects", bands):
        for i, b in enumerate(bands):
            if b.get("deadline") is not None:
                need(f"bands[{i}].deadline", isinstance(b["deadline"], dict), "an object", b["deadline"])
    intents = spec.get("intents")
    if intents is not None:
        need("intents", _is_dict_list(intents), "a list of objects", intents)
    for i, it in enumerate(intents if _is_dict_list(intents) else []):
        for key in ("on_accept", "on_decline"):
            br = it.get(key)
            if br is None:
                continue
            if not isinstance(br, dict):
                errs.append(f"intents[{i}].{key} must be an object, got {str(br)[:80]!r}")
            elif not _branch_reason_or_outcome(br):
                errs.append(f"intents[{i}].{key} has no readable outcome, reason or note: give it close {{outcome, reason}} or note {{reason}} (found keys {sorted(br)})")
        if "max" in it and it.get("max"):
            for key in ("close_verified", "close_unverified"):
                br = it.get(key)
                if br is not None and not (isinstance(br, dict) and _branch_reason_or_outcome(br)):
                    errs.append(f"intents[{i}].{key} has no readable outcome, reason or note: give it close {{outcome, reason}} or note {{reason}}")
    for key in ("debt_statement", "amounts"):
        sec(key)
    ds = spec.get("debt_statement")
    if isinstance(ds, dict) and ds.get("product_names") is not None:
        need("debt_statement.product_names", isinstance(ds["product_names"], dict), "an object", ds["product_names"])
    am = spec.get("amounts")
    if isinstance(am, dict) and am.get("floor_field_by_product") is not None:
        need("amounts.floor_field_by_product", isinstance(am["floor_field_by_product"], dict), "an object", am["floor_field_by_product"])
    return errs


def validate(spec, units, tools):
    """Run every check independently: a crash in one check becomes one error, never a lost spec."""
    errors, warnings = [], []
    if not isinstance(spec, dict):
        return [f"spec must be an object, got {type(spec).__name__}"], []
    shape = shape_errors(spec)
    errors.extend(shape)
    for name, fn in (("coverage", _check_coverage), ("tool enums", _check_enums), ("calendar and bands", _check_calendar_bands),
                     ("grounding", _check_grounding)):
        try:
            fn(spec, units, tools, errors, warnings, bool(shape))
        except Exception as e:  # noqa: BLE001 - malformed nested model output must be repairable, not fatal
            if not shape:   # with shape errors listed the repair loop already knows what to fix
                errors.append(f"internal check '{name}' could not run on this spec ({type(e).__name__}: {str(e)[:120]}); fix the malformed shapes first")
    return errors, warnings


def _body(spec):
    return {k: v for k, v in spec.items() if k not in ("rule_coverage", "extra_rules", "tools", "tools_server", "parser")}


def _check_coverage(spec, units, tools, errors, warnings, shaky):
    spec = dict(spec, tools=tools)   # coverage may point into the tool block, which the program adds itself
    unit_ids = [u["id"] for u in units]
    # 1. shape
    for k in TOP_KEYS:
        if k not in spec:
            errors.append(f"top-level key '{k}' is missing (use null when the brief does not define it)")

    # 2. coverage of every brief unit
    cov = spec.get("rule_coverage") or {}
    for uid in unit_ids:
        if uid not in cov or not str(cov[uid]).strip():
            errors.append(f"brief unit [{uid}] has no rule_coverage entry (map it to spec paths, extra_rules[...] or 'context: why nothing is needed')")
    for uid in cov:
        if uid not in unit_ids:
            errors.append(f"rule_coverage cites unknown unit id '{uid}'")
    for uid, val in cov.items():
        for part in split_coverage(val):
            low = part.lower()
            if low.startswith(("context", "superseded", "overridden", "replaced", "open_questions")):   # open questions live in spec.parser, not in the spec body
                for ref in re.findall(r"\b[a-z0-9]+:(?:p|t)?\d+\b|\b(?:p|t)\d+\b", part):
                    pass
                continue
            if re.search(r"\s", part) and not re.fullmatch(r"[\w.\[\]:\-]+(\s*,\s*[\w.\[\]:\-]+)*", part) and not path_exists(spec, part):
                warnings.append(f"rule_coverage[{uid}] = '{part}' is prose, not a spec path; treated as context")
                continue
            if not path_exists(spec, part):
                errors.append(f"rule_coverage[{uid}] points to '{part}', which does not exist in the spec")

    # 3. extra_rules
    for i, r in enumerate(spec.get("extra_rules") or []):
        if not isinstance(r, dict) or not str(r.get("text", "")).strip():
            errors.append(f"extra_rules[{i}] needs a 'text'")
        elif str(r.get("source")) not in unit_ids:
            warnings.append(f"extra_rules[{i}] cites source '{r.get('source')}', not a brief unit id")



def _check_enums(spec, units, tools, errors, warnings, shaky):
    body = _body(spec)
    # 4. consistency with the tool API enums
    close_outcomes = _enum(tools, "close_call", "outcome")
    queues = _enum(tools, "transfer_to_agent", "queue")
    note_reasons = _enum(tools, "add_note", "reason")
    id_fields = _enum(tools, "verify_identity", "field")
    table = {}
    closing = spec.get("closing") or {}
    for o in (closing.get("outcomes") or []):
        if isinstance(o, dict) and o.get("outcome"):
            reasons = o.get("reasons") or []
            if not isinstance(reasons, list) or not all(isinstance(x, str) for x in reasons):
                errors.append(f"closing.outcomes '{o['outcome']}': reasons must be a list of strings, got {reasons!r}")
                reasons = [x for x in reasons if isinstance(x, str)] if isinstance(reasons, list) else []
            table[o["outcome"]] = set(reasons)
            if close_outcomes and o["outcome"] not in close_outcomes:
                errors.append(f"closing.outcomes has outcome '{o['outcome']}', not in the tool API close_call enum {close_outcomes}")
    if close_outcomes and table:
        for oc in close_outcomes:
            if oc not in table:
                warnings.append(f"close_call allows outcome '{oc}' but closing.outcomes does not list it")
    for p, k, v in _walk(body):
        if k == "outcome" and isinstance(v, str) and close_outcomes and v not in close_outcomes:
            errors.append(f"{p} = '{v}' is not a close_call outcome {close_outcomes}")
        if k == "reason" and v and isinstance(v, str):
            parent_path = p.rsplit(".", 1)[0]
            parent = None
            try:
                cur = spec
                for tok in _tokens(parent_path):
                    cur = cur[int(tok[1])] if isinstance(tok, tuple) and tok[1].isdigit() else cur[tok]
                parent = cur
            except Exception:
                pass
            oc = parent.get("outcome") if isinstance(parent, dict) else None
            if oc in table and table[oc] and v not in table[oc]:
                errors.append(f"{p} = '{v}' is not a reason listed for outcome '{oc}' in closing.outcomes {sorted(table[oc])}")
        if k in ("transfer", "queue") and isinstance(v, str) and queues and v not in queues:
            errors.append(f"{p} = '{v}' is not a transfer_to_agent queue {queues}")
        if k == "note_reasons" and isinstance(v, list) and note_reasons:
            for r in v:
                if r not in note_reasons:
                    errors.append(f"{p} has '{r}', not an add_note reason {note_reasons}")
        if k in ("tool", "close_tool", "note_tool") and isinstance(v, str) and v not in tools:
            errors.append(f"{p} = '{v}' is not a tool in the tool API {sorted(tools)}")
    for q in ((spec.get("identity") or {}).get("questions") or []):
        if isinstance(q, dict) and id_fields and q.get("field") not in id_fields:
            errors.append(f"identity.questions field '{q.get('field')}' is not a verify_identity field {id_fields}")
    types = ((tools.get("get_account") or {}).get("response_fields") or {}).get("products", {}).get("items", {}).get("type", {}).get("enum")
    for name, val in ((spec.get("debt_statement") or {}).get("product_names") or {}).items():
        if types and name not in types:
            errors.append(f"debt_statement.product_names key '{name}' is not a product type {types}")
    for name, val in ((spec.get("amounts") or {}).get("floor_field_by_product") or {}).items():
        if types and name not in types:
            errors.append(f"amounts.floor_field_by_product key '{name}' is not a product type {types}")
        items = ((tools.get("get_account") or {}).get("response_fields") or {}).get("products", {}).get("items", {})
        if isinstance(val, str) and items and val not in items:
            errors.append(f"amounts.floor_field_by_product['{name}'] = '{val}' is not a get_account product field {sorted(items)}")



def _check_calendar_bands(spec, units, tools, errors, warnings, shaky):
    # 5. calendar and bands
    cal = spec.get("calendar") or {}
    for h in cal.get("holidays") or []:
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(h)):
            errors.append(f"calendar.holidays entry '{h}' is not YYYY-MM-DD")
    for d in cal.get("business_days") or []:
        if d not in WEEKDAYS:
            errors.append(f"calendar.business_days entry '{d}' must be one of {sorted(WEEKDAYS)}")
    bands = spec.get("bands") or []
    spans = []
    for b in bands:
        if not isinstance(b, dict):
            continue
        lo, hi = b.get("days_late_min"), b.get("days_late_max")
        if not isinstance(lo, int) or (hi is not None and not isinstance(hi, int)):
            errors.append(f"band '{b.get('name')}' needs integer days_late_min / days_late_max (null max = open ended)")
            continue
        spans.append((lo, hi if hi is not None else 10 ** 9, b.get("name")))
        if not isinstance(b.get("deadline"), dict) or not b["deadline"]:
            errors.append(f"band '{b.get('name')}' needs a structured deadline object, e.g. {{\"business_days_after_today\": N}}")
        if not isinstance(b.get("persuasion_attempts"), int):
            warnings.append(f"band '{b.get('name')}' has no integer persuasion_attempts")
    spans.sort()
    for (a_lo, a_hi, an), (b_lo, b_hi, bn) in zip(spans, spans[1:]):
        if b_lo <= a_hi:
            errors.append(f"bands '{an}' and '{bn}' overlap")
        elif b_lo > a_hi + 1:
            warnings.append(f"bands '{an}' and '{bn}' leave days {a_hi + 1}..{b_lo - 1} without a band")



def _check_grounding(spec, units, tools, errors, warnings, shaky):
    body = _body(spec)
    brief_text = "\n".join(u["text"] for u in units)
    cal = spec.get("calendar") or {}
    bands = spec.get("bands") or []
    # 6. grounding: concrete dates, times and band numbers must be findable in the brief text
    for p, k, v in _walk(body):
        if isinstance(v, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", v) and v not in brief_text:
            warnings.append(f"{p} = '{v}' does not appear in the brief text; check it was not invented")
        if isinstance(v, str) and re.fullmatch(r"\d{1,2}:\d{2}", v) and v not in brief_text:
            hh = int(v.split(":")[0])
            if not number_in_text(hh, brief_text):
                warnings.append(f"{p} = '{v}' does not appear in the brief text; check it was not invented")
    for h in cal.get("holidays") or []:
        if str(h) not in brief_text:
            warnings.append(f"calendar.holidays '{h}' does not appear verbatim in the brief text")
    for b in bands:
        if not isinstance(b, dict):
            continue
        nums = [b.get("days_late_min"), b.get("days_late_max"), b.get("persuasion_attempts")]
        nums += [x for x in (b.get("deadline") or {}).values() if isinstance(x, int)]
        for n in nums:
            if isinstance(n, int) and not isinstance(n, bool) and n >= 0 and not number_in_text(n, brief_text):
                warnings.append(f"band '{b.get('name')}' uses the number {n}, which the brief text does not contain")
    return errors, warnings
