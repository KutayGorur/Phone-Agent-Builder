"""brief file(s) + tool API file -> spec.json (shape: builder/SPEC_CONTRACT.md).

Pipeline (about 3 to 6 minutes):
  1. split the briefs into addressable units (units.py), read the tool API (tools_api.py)
  2. three model calls in parallel, one per group of spec sections (prompts.py), each citing unit ids
  3. deterministic validation (validate.py): every unit covered, values inside the tool API's enums, dates and numbers grounded
  4. one model audit call (missing / wrong / unsupported / overridden), then one repair call for what 3 and 4 found
  5. add the tool block from the API file, a `parser` block (models, warnings, open questions), and return
If a model is unreachable the spec degrades gracefully: every brief unit becomes an extra_rules sentence, so the generator still sees all rules.
"""
import concurrent.futures
import copy
import json
import os
import pathlib
import re
import time

from . import llm, prompts, units as units_mod, validate as validate_mod
from .tools_api import tools_from_openapi

try:
    from builder import trace
except ImportError:
    trace = None

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
EXAMPLE_BRIEF = ROOT / "briefs" / "brief-a.md"
EXAMPLE_SPEC = ROOT / "builder" / "specs" / "brief-a.spec.json"
DEBUG_DIR = ROOT / "out" / "parse"

EXTRACT_MODEL = os.environ.get("PARSER_MODEL", llm.DEFAULT_MODEL)
AUDIT_MODEL = os.environ.get("PARSER_AUDIT_MODEL", EXTRACT_MODEL)
PARSE_BUDGET_S = float(os.environ.get("PARSER_BUDGET_S", "480"))


def _note(msg):
    if trace is not None:
        trace.note("parse: " + msg)


def _debug(name, text):
    try:
        DEBUG_DIR.mkdir(parents=True, exist_ok=True)
        (DEBUG_DIR / name).write_text(text if isinstance(text, str) else json.dumps(text, indent=1, ensure_ascii=False), encoding="utf-8")
    except OSError:
        pass


def _tools_summary(tools):
    """Compact text of the tool API: names, fields, enums. This is what the model may take enums from."""
    lines = []
    for name, t in tools.items():
        req = ", ".join(f"{f}{'*' if d.get('required') else ''}" + (f" in {d['enum']}" if d.get("enum") else "") + (f" ({d['description']})" if d.get("description") else "")
                        for f, d in t["fields"].items())
        resp = []
        for f, d in t["response_fields"].items():
            if d.get("items"):
                inner = ", ".join(f"{k}" + (f" in {v['enum']}" if v.get("enum") else "") + (f" ({v['description']})" if v.get("description") else "")
                                  for k, v in d["items"].items() if k != "required")
                resp.append(f"{f}[{inner}]")
            else:
                resp.append(f + (f" in {d['enum']}" if d.get("enum") else ""))
        lines.append(f"- {name}: {t.get('summary')}\n    request: {req}\n    response: {', '.join(resp)}")
    return "\n".join(lines)


def _system_prompt():
    contract = (ROOT / "builder" / "SPEC_CONTRACT.md").read_text(encoding="utf-8")
    parts = [prompts.SYSTEM, "\n\n=== SPEC CONTRACT (the shape you must follow) ===\n" + contract]
    if EXAMPLE_BRIEF.exists() and EXAMPLE_SPEC.exists():
        ex_units, _ = units_mod.load_briefs([EXAMPLE_BRIEF])
        ex_spec = json.loads(EXAMPLE_SPEC.read_text(encoding="utf-8"))
        for k in ("tools", "tools_server"):
            ex_spec.pop(k, None)
        parts.append("\n\n=== " + prompts.EXAMPLE_INTRO + " ===\n--- example brief units ---\n" + units_mod.render_units(ex_units)
                     + "\n--- example spec ---\n" + json.dumps(ex_spec, ensure_ascii=False, separators=(",", ":")))
    return "".join(parts)


def _call_json(purpose, system, prompt, model, timeout, retries=1):
    last = None
    for attempt in range(retries + 1):
        try:
            text = llm.complete(purpose if attempt == 0 else purpose + " (retry)", system, prompt, model=model, timeout=timeout)
            _debug(re.sub(r"\W+", "_", purpose)[:50] + (f"_{attempt}" if attempt else "") + ".txt", text)
            return llm.extract_json(text)
        except Exception as e:  # noqa: BLE001 - network, auth, bad JSON: retry once, then give up on this call
            last = e
            _note(f"model call failed ({purpose}): {str(e)[:200]}")
    raise RuntimeError(f"model call failed twice: {purpose}: {last}")


def _merge_extract(results, unit_ids):
    spec, extra, cov, questions = {}, [], {}, []
    for res in results:
        if not isinstance(res, dict):
            continue
        for k, v in (res.get("sections") or {}).items():
            spec[k] = v
        for r in res.get("extra_rules") or []:
            if isinstance(r, dict) and r.get("text"):
                extra.append({"source": str(r.get("source")), "text": r["text"]})
        for uid, val in (res.get("rule_coverage") or {}).items():
            uid = str(uid)
            if val is None:
                continue
            cov[uid] = (cov[uid] + "; " + str(val)) if uid in cov and str(val) not in cov[uid] else str(val)
        questions += [q for q in (res.get("open_questions") or []) if isinstance(q, str)]
    return spec, _dedupe_rules(extra), cov, questions


def _dedupe_rules(rules):
    seen, out = set(), []
    for r in rules:
        key = (r["source"], " ".join(r["text"].lower().split()))
        if key not in seen:
            seen.add(key)
            out.append(r)
    return out


def _assemble(sections, extra, cov, questions):
    spec = {k: sections.get(k) for k in validate_mod.TOP_KEYS if k not in ("extra_rules", "rule_coverage")}
    for k, v in sections.items():
        if k not in spec and k not in ("tools", "tools_server", "extra_rules", "rule_coverage"):
            spec[k] = v
    spec["extra_rules"] = extra
    spec["rule_coverage"] = cov
    spec["_open_questions"] = questions
    return spec


def _apply_patch(spec, patch):
    spec = copy.deepcopy(spec)
    for k, v in (patch.get("sections") or {}).items():
        if k not in ("tools", "tools_server", "rule_coverage", "extra_rules"):
            spec[k] = v
    drop = [d for d in (patch.get("remove_extra_rules") or []) if isinstance(d, str)]
    if drop:
        spec["extra_rules"] = [r for r in spec["extra_rules"] if not any((r["source"] + " " + r["text"]).startswith(d) or r["text"].startswith(d) for d in drop)]
    adds = [{"source": str(r.get("source")), "text": r["text"]} for r in (patch.get("extra_rules") or []) if isinstance(r, dict) and r.get("text")]
    spec["extra_rules"] = _dedupe_rules(spec["extra_rules"] + adds)
    for uid, val in (patch.get("rule_coverage") or {}).items():
        if val:
            spec["rule_coverage"][str(uid)] = str(val)
    spec["_open_questions"] = list(spec.get("_open_questions") or []) + [q for q in (patch.get("open_questions") or []) if isinstance(q, str)]
    return spec


def _degraded(units, sources, tools_block, reason):
    """No model available: keep every brief unit as an extra rule so nothing is lost."""
    _note(f"DEGRADED spec: {reason}")
    spec = {k: None for k in validate_mod.TOP_KEYS}
    spec["meta"] = {"bank_name": None, "language": None, "multi_product": None, "max_products": None}
    spec["extra_rules"] = [{"source": u["id"], "text": u["text"]} for u in units]
    spec["rule_coverage"] = {u["id"]: f"extra_rules[{u['id']}]" for u in units}
    spec["tools_server"] = tools_block["server"]
    spec["tools"] = tools_block["tools"]
    spec["parser"] = {"degraded": True, "reason": reason, "briefs": sources, "models": [], "warnings": [], "open_questions": []}
    return spec


def parse(brief_paths, tool_api_path):
    t0 = time.time()
    left = lambda: PARSE_BUDGET_S - (time.time() - t0)  # noqa: E731
    all_units, sources = units_mod.load_briefs(brief_paths)
    tools_block = tools_from_openapi(tool_api_path)
    tools = tools_block["tools"]
    unit_ids = [u["id"] for u in all_units]
    _note(f"{len(all_units)} units from {len(sources)} file(s); tool API has {len(tools)} tools")
    models_used = set()

    try:
        system = _system_prompt()
        units_text = units_mod.render_units(all_units)
        tools_text = _tools_summary(tools)

        # ---- 1. extraction: three calls in parallel, one per group of sections
        def extract(group):
            names, guide = prompts.SECTION_HELP[group]
            prompt = prompts.EXTRACT_TASK.format(sections=names, guide=guide, section_list=names, tools=tools_text, units=units_text)
            return _call_json(f"parse brief: spec sections {names}", system, prompt, EXTRACT_MODEL, timeout=min(420, max(left() - 30, 60)))

        results = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as ex:
            futs = {ex.submit(extract, g): g for g in prompts.SECTION_HELP}
            for f in concurrent.futures.as_completed(futs):
                try:
                    results[futs[f]] = f.result()
                except Exception as e:  # noqa: BLE001
                    _note(f"extraction group {futs[f]} failed: {str(e)[:200]}")
        models_used.add(EXTRACT_MODEL)
        if len(results) < len(prompts.SECTION_HELP):
            missing = sorted(set(prompts.SECTION_HELP) - set(results))
            if not results:
                return _degraded(all_units, sources, tools_block, f"all extraction calls failed ({missing})")
            _note(f"extraction groups missing: {missing}; their sections stay null and are repaired below")
        sections, extra, cov, questions = _merge_extract(list(results.values()), unit_ids)
        spec = normalize_intents(_assemble(sections, extra, cov, questions))
        _debug("spec.after_extract.json", spec)

        # ---- 2-4. validate, audit, repair (at most two rounds, only while there is time)
        for rnd in (1, 2):
            errors, warnings = validate_mod.validate(spec, all_units, tools)
            _note(f"validation round {rnd}: {len(errors)} errors, {len(warnings)} warnings")
            issues = []
            if left() > 150 and rnd == 1:
                try:
                    audit = _call_json("audit parsed spec against the brief", system,
                                       prompts.AUDIT_TASK.format(tools=tools_text, flags="\n".join(f"- {x}" for x in (errors + warnings)[:40]) or "(none)",
                                                                 units=units_text, spec=json.dumps(_for_prompt(spec), ensure_ascii=False, separators=(",", ":"))),
                                       AUDIT_MODEL, timeout=min(300, max(left() - 60, 60)))
                    models_used.add(AUDIT_MODEL)
                    issues = [i for i in (audit.get("issues") or []) if isinstance(i, dict)]
                    _note(f"audit found {len(issues)} issues")
                except Exception as e:  # noqa: BLE001
                    _note(f"audit skipped: {str(e)[:200]}")
            problems = [f"[validation error] {e}" for e in errors] + [f"[automatic warning] {w}" for w in warnings[:25]] + \
                       [f"[audit {i.get('type')}] unit {i.get('unit')}: {i.get('detail')} -> {i.get('fix')}" for i in issues]
            if not errors and not issues:
                break
            if left() < 90:
                _note("repair skipped: out of parse time budget")
                break
            try:
                patch = _call_json("repair spec: fix validation errors and audit findings", system,
                                   prompts.REPAIR_TASK.format(tools=tools_text, problems="\n".join(problems), units=units_text,
                                                              spec=json.dumps(_for_prompt(spec), ensure_ascii=False, separators=(",", ":"))),
                                   EXTRACT_MODEL, timeout=min(360, max(left() - 20, 60)))
                models_used.add(EXTRACT_MODEL)
                spec = normalize_intents(_apply_patch(spec, patch))
                _debug(f"spec.after_repair{rnd}.json", spec)
            except Exception as e:  # noqa: BLE001
                _note(f"repair failed: {str(e)[:200]}")
                break

        errors, warnings = validate_mod.validate(spec, all_units, tools)
        spec, quarantined = _quarantine(spec, all_units, validate_mod.shape_errors(spec))
        if quarantined:
            _note(f"sections degraded to extra_rules: {quarantined}")
            errors, warnings = validate_mod.validate(spec, all_units, tools)
            warnings = [f"section '{q}' stayed malformed after repair; its brief rules are kept as extra_rules" for q in quarantined] + warnings
        # uncovered units that survived every repair: keep their text verbatim as extra rules, never drop a rule
        cov = spec["rule_coverage"]
        for u in all_units:
            if u["id"] not in cov or not str(cov[u["id"]]).strip():
                spec["extra_rules"].append({"source": u["id"], "text": u["text"]})
                cov[u["id"]] = f"extra_rules[{u['id']}]"
        errors, warnings = validate_mod.validate(spec, all_units, tools)
    except Exception as e:  # noqa: BLE001
        return _degraded(all_units, sources, tools_block, f"parser failed: {str(e)[:300]}")

    questions = spec.pop("_open_questions", [])
    spec["tools_server"] = tools_block["server"]
    spec["tools"] = tools
    spec["parser"] = {"degraded": False, "briefs": sources, "models": sorted(models_used),
                      "seconds": round(time.time() - t0), "unresolved_errors": errors, "warnings": warnings, "open_questions": questions}
    order = [k for k in spec if k not in ("tools_server", "tools", "extra_rules", "rule_coverage", "parser")] + ["tools_server", "tools", "extra_rules", "rule_coverage", "parser"]
    return {k: spec[k] for k in order}


_NOTE_ALIASES = ("note_remaining_products", "note_products_without_promise", "note_reason", "note_all_products")


def _normalize_branch(spec, br):
    if not isinstance(br, dict):
        return
    for alias in _NOTE_ALIASES:
        v = br.get(alias)
        if v is None or br.get("note"):
            continue
        reason = v.get("reason") if isinstance(v, dict) else v
        if isinstance(reason, str) and reason:
            br["note"] = {"reason": reason}
            br.pop(alias)
    n = br.get("note")
    reason = n.get("reason") if isinstance(n, dict) else n if isinstance(n, str) else None
    if reason and not br.get("outcome") and not isinstance(br.get("close"), dict) and not isinstance(br.get("base"), dict):
        # a note-only branch closes by the closing table: the one outcome that lists this reason
        hits = [o["outcome"] for o in ((spec.get("closing") or {}).get("outcomes") or [])
                if isinstance(o, dict) and o.get("outcome") and isinstance(o.get("reasons"), list) and reason in o["reasons"]]
        if len(hits) == 1:
            br["base"] = {"outcome": hits[0], "reason": reason}


def normalize_intents(spec):
    """Map the note-keys the model invents onto the contract shape the generator reads.

    on_decline / verified-style branches carry their note reason as `note: {reason}`; a bare string reason becomes that too.
    `verified` / `unverified` are aliases of close_verified / close_unverified. Nothing is invented: only existing values move."""
    intents = spec.get("intents")
    if not isinstance(intents, list):
        return spec
    for it in intents:
        if not isinstance(it, dict):
            continue
        if "close_unverified" in it or "close_verified" in it or "verified" in it or "unverified" in it:
            for src, dst in (("verified", "close_verified"), ("unverified", "close_unverified")):
                if isinstance(it.get(src), dict) and not it.get(dst):
                    it[dst] = it.pop(src)
        for key in ("on_accept", "on_decline", "close_verified", "close_unverified"):
            _normalize_branch(spec, it.get(key))
    pers = spec.get("persuasion")
    if isinstance(pers, dict):
        _normalize_branch(spec, pers.get("on_exhausted"))
    return spec


def _quarantine(spec, units, shape_errs):
    """A section whose nested shape is still malformed is nulled and its brief rules fall back to extra_rules; the rest of the spec survives."""
    bad = []
    for e in shape_errs:
        sec = re.split(r"[.\[ ]", e, maxsplit=1)[0]
        if sec in spec and sec not in ("extra_rules", "rule_coverage") and sec not in bad:
            bad.append(sec)
    if not bad:
        return spec, []
    spec = copy.deepcopy(spec)
    unit_text = {u["id"]: u["text"] for u in units}
    for sec in bad:
        spec[sec] = None
    for uid, val in list(spec["rule_coverage"].items()):
        parts = validate_mod.split_coverage(val)
        if any(re.split(r"[.\[]", p, maxsplit=1)[0].strip() in bad for p in parts):
            keep = [p for p in parts if re.split(r"[.\[]", p, maxsplit=1)[0].strip() not in bad]
            if uid in unit_text:
                spec["extra_rules"].append({"source": uid, "text": unit_text[uid]})
                keep.append(f"extra_rules[{uid}]")
            spec["rule_coverage"][uid] = "; ".join(keep) or f"extra_rules[{uid}]"
    spec["extra_rules"] = _dedupe_rules(spec["extra_rules"])
    return spec, bad


def _for_prompt(spec):
    s = {k: v for k, v in spec.items() if k not in ("tools", "tools_server", "parser", "_open_questions")}
    return s


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description="brief file(s) + tool API file -> spec.json")
    ap.add_argument("files", nargs="+", help="brief file(s) followed by the tool API file")
    ap.add_argument("--out", default=None, help="write the spec here (default: stdout)")
    a = ap.parse_args(argv)
    spec = parse(a.files[:-1], a.files[-1])
    text = json.dumps(spec, indent=1, ensure_ascii=False)
    if a.out:
        pathlib.Path(a.out).write_text(text, encoding="utf-8")
        p = spec["parser"]
        print(f"spec written to {a.out}: degraded={p['degraded']} unresolved_errors={len(p.get('unresolved_errors', []))} warnings={len(p.get('warnings', []))}")
    else:
        print(text)


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(ROOT))
    from builder.parse.spec_parser import main as _main
    _main()
