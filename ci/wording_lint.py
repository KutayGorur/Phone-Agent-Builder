"""Offline wording lint for a built workflow: flags phrases a judge would mark down. No Freya or model calls.

python ci/wording_lint.py out/gen-a.workflow.json [--brief briefs/brief-a.md ...] [--spec builder/specs/brief-a.spec.json] [--json]

Checks (rule ids in output):
  W1 forbidden phrase     a phrase the brief forbids (Never ask/say "...") or a budget question, in a line the agent can say
  W2 pre-id disclosure    debt, product, amount or "collections" wording in a node reachable before account retrieval
  W3 unkeepable promise   discount, waiver, guarantee, plan, "cancel/change it now" and similar, said as an offer
  W4 false success        a failure line that says recorded/saved/confirmed, or "recorded" in a line spoken before create
  W5 repeated line        the same spoken sentence in several nodes, or an instruction repeated in the system prompt
  W6 missing disclosure   opening lacks assistant/bank/recording words, or a sentence the brief says to say word for word is nowhere in the workflow
Exit 1 when any ERROR is found. WARN and INFO are advice.
"""
import argparse, ast, json, re, sys
from pathlib import Path

SENT = re.compile(r"(?<=[.!?])\s+")
NEG = re.compile(r"\b(never|do not|don't|not|no|without|cannot|can't|must not|nothing)\b", re.I)
DISCLOSE = re.compile(r"collections?|\bdebts?\b|\bowe[sd]?\b|overdue|past[- ]due|late payment|\bpayment|\bbalance|credit card|\bloan|instalment|\bamount|[£$€]\s?\d|\bdays late", re.I)
BUDGET = re.compile(r"how much (can|could|would|are) you|what (can|could) you (pay|afford)|can you afford|your budget|what amount (can|would|do) you|how much do you want to pay", re.I)
PROMISE = re.compile(r"guarantee|waive|waiver|discount|forgive|write[- ]off|no (extra )?fees|(won't|will not|not) (be )?report|credit (score|file|rating)|interest (will|won't|is)|freeze|settle(ment)?\b|payment plan|instalment plan|lower (instalment|payment)s?|new plan|I promise|(cancel|change|undo|reverse) (it|that|the promise)( now| today| later)?|extend (the|your) deadline|stop (the )?(calls|reminders)", re.I)
FAILWORDS = re.compile(r"\b(recorded|saved|booked|scheduled|confirmed|all set|success)\b", re.I)
FAILKEY = re.compile(r"fail|error|unable|problem", re.I)
SAYQ = re.compile(r"""(?:say|says|said|sentence|exactly|word for word)[^"“\n]{0,60}["“]([^"”\n]{8,220})["”]""", re.I)
FORBID_Q = re.compile(r"""(?:never|do not|don't) (?:ask|say|use|tell)[^"“\n.]{0,40}["“]([^"”\n]{6,120})["”]""", re.I)


def norm(s):
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9£$€ ]", " ", s.lower())).strip()


def sentences(t):
    return [s.strip() for s in SENT.split(t.replace("\n", " ")) if s.strip()]


def code_literals(code):
    """String constants of 4+ words from a code snippet, docstrings and comments excluded."""
    out = []
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return [("", m) for m in re.findall(r"""['"]([A-Z][^'"\n]{20,200})['"]""", code)]
    docs = {id(n.value) for n in ast.walk(tree) if isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant)}
    for n in ast.walk(tree):
        if isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in docs and id(n.value) not in docs:
            v = n.value.strip()
            if v.startswith("{"):   # the engine config is a JSON literal: keep each string with its key path
                try:
                    out += json_strings(json.loads(v))
                    continue
                except ValueError:
                    pass
            if len(v.split()) >= 4 and re.search(r"[A-Za-z]{3}", v) and not v.startswith(("def ", "import ")) and "\n" not in v[:200]:
                out.append(("", v))
    return out


def json_strings(o, path=""):
    if isinstance(o, dict):
        return [x for k, v in o.items() for x in json_strings(v, path + "." + k if path else k)]
    if isinstance(o, list):
        return [x for i, v in enumerate(o) for x in json_strings(v, f"{path}[{i}]")]
    if isinstance(o, str) and len(o.split()) >= 3 and re.search(r"[A-Za-z]{3}", o) and not re.search(r"^[a-z_]+( [a-z_]+)*$", o) or (isinstance(o, str) and re.search(r"(say|say_text|_text|explain)$", path)):
        return [(path, o)]
    return []


def find_code(o):
    if isinstance(o, dict):
        for k, v in o.items():
            if k == "default" and isinstance(v, str) and "def " in v and len(v) > 500:
                yield v
            else:
                yield from find_code(v)
    elif isinstance(o, list):
        for v in o:
            yield from find_code(v)


PRE_PATH = re.compile(r":(tp|unclear_say|idv)\b")


def pre_verify_nodes(wf):
    """Nodes reachable from initial_node without crossing the account-retrieval node."""
    nodes = {**(wf.get("nodes") or {}), **(wf.get("global_nodes") or {})}
    seen, todo = set(), [wf.get("initial_node")]
    while todo:
        x = todo.pop()
        if x in seen or x not in nodes or re.search(r"get_account|engine", x):
            continue
        seen.add(x)
        todo += [t.get("target_node") for t in nodes[x].get("transitions") or []]
    return seen


def collect(wf):
    """(source, kind, text) with kind spoken | instruction | code."""
    units = []
    if wf.get("system_prompt"):
        for s in sentences(wf["system_prompt"].replace("\n- ", "\n")):
            units.append(("system_prompt", "instruction", s))
    for name, n in {**(wf.get("nodes") or {}), **(wf.get("global_nodes") or {})}.items():
        oe = n.get("on_enter") or {}
        if oe.get("type") == "tts" and oe.get("text"):
            for s in sentences(oe["text"]):
                units.append((name, "spoken", s))
        if n.get("task_message"):
            for s in sentences(n["task_message"]):
                units.append((name, "instruction", s))
        seen = set()
        for code in find_code(n.get("pre_actions") or []):
            for path, lit in code_literals(code):
                if (path, lit) not in seen and not path.endswith((".desc", "desc")):
                    seen.add((path, lit))
                    for s in re.split(r"(?<=[.!?])['\"]?,?\s+['\"]?|', '", lit.replace("\n", " ")):
                        if s.strip():
                            units.append((f"{name}:{path}" if path else name, "code", s.strip()))
    return units


def spec_phrases(spec):
    out = []

    def walk(o, p):
        if isinstance(o, dict):
            for k, v in o.items():
                if k in ("raw_briefs", "tools", "rule_coverage", "meta"):
                    continue
                walk(v, p + "." + k)
        elif isinstance(o, list):
            for i, v in enumerate(o):
                walk(v, p + f"[{i}]")
        elif isinstance(o, str) and len(o.split()) >= 3 and re.search(r"(^|\.)(say|[a-z_]*_say|explain_once|first_sentence)$", p.split("[")[0]):
            out.append((p, o))
    walk(spec, "")
    return out


def lint(wf, briefs=(), spec=None):
    F = []

    def add(sev, rule, where, text, why):
        F.append({"sev": sev, "rule": rule, "node": where, "text": text[:220], "why": why})

    units = collect(wf)
    pre = pre_verify_nodes(wf)
    brief_text = "\n".join(briefs)
    allnorm = norm(" ".join(t for _, _, t in units) + " " + " ".join(p for _, p in (spec_phrases(spec) if spec else [])))

    # W1 forbidden phrases
    forb = {norm(m) for m in FORBID_Q.findall(brief_text) if " " in m.strip()}
    for src, kind, t in units:
        neg = bool(NEG.search(t))
        if BUDGET.search(t) and not neg:
            add("ERROR", "W1", src, t, "asks the customer's budget; the agent must propose every amount")
        n = norm(t)
        for f in forb:
            if f and f in n and not neg:
                add("ERROR", "W1", src, t, f"brief forbids: {f!r}")

    # W2 disclosure before identity
    for src, kind, t in units:
        if (src in pre or PRE_PATH.search(src)) and kind in ("spoken", "instruction", "code") and not NEG.search(t) and DISCLOSE.search(t):
            add("ERROR" if kind != "instruction" else "WARN", "W2", src, t, "debt/product wording in a node reachable before verification")
    if spec:
        for p, t in spec_phrases(spec):
            if re.search(r"opening|third_party|identity|unclear", p) and DISCLOSE.search(t) and not NEG.search(t):
                add("ERROR", "W2", "spec" + p, t, "spec line spoken before verification mentions debt or product")

    # W3 promises the bank cannot keep
    for src, kind, t in units:
        if kind != "instruction" or src == "system_prompt":
            if PROMISE.search(t) and not NEG.search(t):
                add("ERROR" if kind == "spoken" else "WARN", "W3", src, t, "possible term outside the brief")
        elif PROMISE.search(t) and not NEG.search(t) and not re.search(r"\bnot (in|part)", t):
            add("WARN", "W3", src, t, "possible term outside the brief")
    for p, t in (spec_phrases(spec) if spec else []):
        if PROMISE.search(t) and not NEG.search(t):
            add("ERROR", "W3", "spec" + p, t, "spec line promises something outside the brief")

    # W4 false success claims
    for p, t in (spec_phrases(spec) if spec else []):
        if FAILKEY.search(p) and FAILWORDS.search(t) and not NEG.search(t):
            add("ERROR", "W4", "spec" + p, t, "failure line claims success")
    for src, kind, t in units:
        if kind == "spoken" and re.search(r"\brecorded\b", t, re.I) and src in pre:
            sev = "INFO" if norm(t) in norm(brief_text) else "WARN"   # the brief itself dictates the word
            add(sev, "W4", src, t, "'recorded' spoken before any promise exists (PUB-10's judge matched the word)")
        if kind in ("spoken", "code") and FAILKEY.search(src) and FAILWORDS.search(t) and not NEG.search(t):
            add("ERROR", "W4", src, t, "failure node claims success")

    # W5 repeats
    spoken = {}
    for src, kind, t in units:
        if kind in ("spoken", "code") and len(t.split()) >= 4:
            spoken.setdefault(norm(t), []).append((src, t))
    for n, lst in spoken.items():
        srcs = sorted({s for s, _ in lst})
        if len(srcs) >= 3:
            add("INFO", "W5", ",".join(srcs[:5]), lst[0][1], f"same sentence in {len(srcs)} nodes")
    sp = {}
    for src, kind, t in units:
        if src == "system_prompt" and len(t.split()) >= 6:
            sp.setdefault(norm(t), []).append(t)
    for n, lst in sp.items():
        if len(lst) > 1:
            add("WARN", "W5", "system_prompt", lst[0], f"instruction repeated {len(lst)}x in the system prompt")
    # near-duplicate instructions (same words, different order of clauses)
    keys = [(norm(t), t) for _, k, t in units if _ == "system_prompt" and len(t.split()) >= 8]
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            a, b = set(keys[i][0].split()), set(keys[j][0].split())
            if keys[i][0] != keys[j][0] and len(a & b) / max(1, len(a | b)) > 0.75:
                add("WARN", "W5", "system_prompt", keys[i][1], "near-duplicate of: " + keys[j][1][:100])

    # W6 required disclosures
    op = wf.get("nodes", {}).get(wf.get("initial_node"), {})
    oe = (op.get("on_enter") or {}).get("text", "")
    if not oe:
        add("WARN", "W6", wf.get("initial_node"), "", "opening is not a fixed tts line; the first sentence is left to the model")
    else:
        for need, rx in (("digital assistant", r"digital assistant"), ("recording notice", r"record"), ("bank name", r"\bBank\b")):
            if not re.search(rx, oe, re.I):
                add("ERROR", "W6", wf.get("initial_node"), oe, f"opening lacks {need}")
    for q in SAYQ.findall(brief_text):
        if "{" in q or "<" in q:
            continue
        if norm(q) not in allnorm:
            add("WARN", "W6", "workflow", q, "brief gives this sentence to say, not found in any line of the workflow")
    return F


TOOLS = ("verify_identity", "verify_date_of_birth", "verify_phone_last4", "get_account", "create_promise", "add_note", "schedule_callback", "transfer_to_agent", "close_call")
MONEY = re.compile(r"[£$€]\s?\d[\d,]*(?:\.\d+)?|\b\d[\d,]*(?:\.\d+)?\s?(?:pounds|dollars|euros)\b", re.I)


def call_turns(call):
    """[(index, role, text, tools)] from a Freya call object (messages with role/content/tool calls); tolerant of key names."""
    out = []
    for i, m in enumerate(call.get("messages") or []):
        role = m.get("role") or ""
        text = next((m[k] for k in ("content", "text", "message", "transcript") if isinstance(m.get(k), str)), "")
        blob = json.dumps({k: v for k, v in m.items() if k not in ("content", "text", "message", "transcript")})
        tools = [t for t in TOOLS if t in blob]
        out.append((i, role, text, tools))
    return out


def lint_call(call, briefs=(), label=""):
    """Wording checks over what the agent actually said in one real call. Same rules as the workflow lint plus transcript-only ones."""
    F = []

    def add(sev, rule, i, text, why):
        F.append({"sev": sev, "rule": rule, "node": f"{label}#{i}", "text": text[:220], "why": why})

    brief_text = "\n".join(briefs)
    forb = {norm(m) for m in FORBID_Q.findall(brief_text) if " " in m.strip()}
    turns = call_turns(call)
    verified, promised, seen_say, offers = False, False, {}, []
    for i, role, text, tools in turns:
        if "verify" in " ".join(tools) and "get_account" not in tools:
            pass
        if "get_account" in tools:
            verified = True
        if "create_promise" in tools:
            promised = True
        if role != "assistant" or not text:
            continue
        for sent in sentences(text):
            n = norm(sent)
            if BUDGET.search(sent):
                add("ERROR", "W1", i, sent, "asks the customer's budget")
            for f in forb:
                if f and f in n:
                    add("ERROR", "W1", i, sent, f"brief forbids: {f!r}")
            if not verified and DISCLOSE.search(sent) and not NEG.search(sent):
                add("ERROR", "W2", i, sent, "debt/product wording before get_account (identity not yet verified)")
            if PROMISE.search(sent) and not NEG.search(sent):
                add("WARN", "W3", i, sent, "possible term outside the brief")
            if re.search(r"\brecorded\b|\ball set\b", sent, re.I) and not promised and not re.search(r"call is recorded|recording", sent, re.I):
                add("ERROR", "W4", i, sent, "claims a record before create_promise ran")
            if len(n.split()) >= 5:
                seen_say.setdefault(n, []).append(i)
            for amt in MONEY.findall(sent):
                if re.search(r"minimum|instalment|at least|lowest|floor|could you do|can you do|how about", sent, re.I):
                    offers.append((i, amt.strip(), sent))
    for n, idx in seen_say.items():
        if len(idx) >= 2:
            add("WARN", "W5", idx[1], n, f"agent said the same sentence {len(idx)}x (turns {idx})")
    by_amt = {}
    for i, amt, sent in offers:
        by_amt.setdefault(norm(amt), []).append((i, sent))
    for amt, lst in by_amt.items():
        if len(lst) >= 2:
            add("WARN", "T1", lst[1][0], lst[1][1], f"amount {amt!r} offered/named {len(lst)}x as a floor-type offer (turns {[i for i, _ in lst]}); a judge may count a second offer")
    return F


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("workflow", help="workflow JSON, or with --calls a call JSON / folder of call JSON files (a results/run.json lists call_ids, fetch each with freya.get_call and save)")
    ap.add_argument("--calls", action="store_true")
    ap.add_argument("--brief", action="append", default=[])
    ap.add_argument("--spec")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    if a.calls:
        files = sorted(Path(a.workflow).glob("*.json")) if Path(a.workflow).is_dir() else [Path(a.workflow)]
        bad = 0
        for fp in files:
            c = json.loads(fp.read_text(encoding="utf-8-sig"))
            c = c.get("call", c)
            F = lint_call(c, [Path(b).read_text(encoding="utf-8-sig") for b in a.brief], fp.stem)
            for f in F:
                print(f"{f['sev']:5} {f['rule']} [{f['node']}] {f['why']}\n        {f['text']}")
            bad += any(f["sev"] == "ERROR" for f in F)
        print(f"{len(files)} calls, {bad} with errors")
        return 1 if bad else 0
    wf = json.loads(Path(a.workflow).read_text(encoding="utf-8-sig"))
    briefs = [Path(b).read_text(encoding="utf-8-sig") for b in a.brief]
    spec = json.loads(Path(a.spec).read_text(encoding="utf-8-sig")) if a.spec else None
    F = lint(wf, briefs, spec)
    if a.json:
        print(json.dumps(F, indent=1))
    else:
        for f in sorted(F, key=lambda f: ("ERROR", "WARN", "INFO").index(f["sev"])):
            print(f"{f['sev']:5} {f['rule']} [{f['node']}] {f['why']}\n        {f['text']}")
        print(f"{sum(f['sev']=='ERROR' for f in F)} error, {sum(f['sev']=='WARN' for f in F)} warn, {sum(f['sev']=='INFO' for f in F)} info")
    return 1 if any(f["sev"] == "ERROR" for f in F) else 0


if __name__ == "__main__":
    sys.exit(main())
