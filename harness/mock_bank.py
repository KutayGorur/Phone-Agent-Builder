"""A stand-in for the organisers' mock bank, so the variant cases in test-briefs/ can be run.

The organisers' mock answers `POST /v1/practice/sessions` only for its own case ids (PUB-01 ...). It answers
"unknown practice case" for ours. This server speaks the same protocol and reads the customers from our case files:

    POST /v1/practice/sessions   {"case": "TC-01"}   -> {"ok": true, "variables": {customer_id, first_name, ...}}
    GET  /v1/practice/ledger/<customer_id>           -> outcome, reason, promises, notes, callbacks, transfers, calls
    POST /v1/<tool>              the seven tool calls of the tool API file (enums are checked against that file)

Like the real mock it does not enforce the brief. It only refuses what the real one refuses: a tool call before both
questions are passed ("identity not verified"), an unknown product id, a value outside an enum, anything after close_call.
A case may carry {"bank": {"max_wrong": N}} (wrong answers that end the check, default 3) and "faults"
[{"tool": ..., "fail_first_n": n}] (the first n calls to that tool for the customer answer HTTP 500).

Use (the phone agent runs on Freya's cloud, so it needs a public URL: put a tunnel such as cloudflared or ngrok in front):

    python harness/mock_bank.py --api test-briefs/tools-c.openapi.json --cases test-briefs/cases-c.json --port 8787
    cloudflared tunnel --url http://localhost:8787            # prints https://<name>.trycloudflare.com
    python harness/make_testset.py --server https://<name>.trycloudflare.com    # rewrites the tool API files with that URL
    export FREYA_BANK_HOST=http://localhost:8787 FREYA_BANK_TEAM_KEY=anything-16-chars-long
    python tools/run_cases.py <agent_id> --cases test-briefs/cases-c.json --out results/c-rep1.json

    python harness/mock_bank.py --selftest        # replays the expected ledger of every case through the server and scores it
"""
import argparse, datetime as dt, json, pathlib, re, sys, threading, uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = pathlib.Path(__file__).resolve().parent.parent
TOOLS = ["verify_identity", "get_account", "create_promise", "add_note", "schedule_callback", "transfer_to_agent", "close_call"]


class Bank:
    def __init__(self, api, cases):
        self.api, self.cases = api, {c["id"]: c for c in cases}
        self.sessions, self.lock = {}, threading.Lock()
        self.enums = {}
        for t in TOOLS:
            props = api["paths"]["/" + t]["post"]["requestBody"]["content"]["application/json"]["schema"]["properties"]
            self.enums[t] = {k: v["enum"] for k, v in props.items() if "enum" in v}
        resp = api["paths"]["/verify_identity"]["post"]["responses"]["200"]["content"]["application/json"]["schema"]["properties"]
        self.hints = resp["hint"]["enum"]

    def new_session(self, cid):
        c = self.cases.get(cid)
        if not c: return {"ok": False, "error": "unknown practice case"}
        customer_id = "c_" + uuid.uuid4().hex[:16]
        s = {"case": c, "wrong": 0, "verified": set(), "closed": False, "faults": {}, "led": {"outcome": None, "reason": None, "promises": [], "notes": [], "callbacks": [], "transfers": [], "calls": []}}
        with self.lock: self.sessions[customer_id] = s
        return {"ok": True, "variables": {"customer_id": customer_id, **c["variables"]}}

    def ledger(self, customer_id):
        s = self.sessions.get(customer_id)
        return {"ok": False, "error": "unknown customer"} if not s else {"ok": True, **s["led"]}

    def tool(self, name, body):
        """Returns (http_status, result)."""
        s = self.sessions.get(body.get("customer_id"))
        if not s: return 200, {"ok": False, "error": "unknown customer"}
        with self.lock:
            f = next((f for f in s["case"].get("faults", []) if f["tool"] == name), None)
            if f and not s["closed"]:
                s["faults"][name] = s["faults"].get(name, 0) + 1
                if s["faults"][name] <= f["fail_first_n"]:
                    res = {"ok": False, "error": "service unavailable"}
                    s["led"]["calls"].append({"tool": name, "args": body, "result": res, "status": 500}); return 500, res
            res = self._do(s, name, body)
            s["led"]["calls"].append({"tool": name, "args": body, "result": res})
            return 200, res

    def _do(self, s, name, b):
        c, led = s["case"], s["led"]
        if s["closed"]: return {"ok": False, "error": "call closed"}
        for k, allowed in self.enums[name].items():
            if b.get(k) not in allowed: return {"ok": False, "error": f"invalid {k}: {b.get(k)!r}, allowed {allowed}"}
        required = list(c["identity"])
        if name == "verify_identity":
            field, ans = b["field"], str(b.get("answer", "")).strip()
            if s["wrong"] >= c.get("bank", {}).get("max_wrong", 3): return {"ok": False, "error": "check closed after too many wrong answers"}
            truth = str(c["identity"].get(field, ""))
            if field == "date_of_birth":
                if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", ans): return {"ok": False, "error": "unreadable date, send YYYY-MM-DD"}
                try: d = dt.date.fromisoformat(ans)
                except ValueError: return {"ok": False, "error": "unreadable date, send YYYY-MM-DD"}
                if d.year < 100 and "year_two_digits" in self.hints: return {"ok": True, "verified": False, "hint": "year_two_digits", "wrong_answers_left": self._left(s), "all_verified": False}
                t = dt.date.fromisoformat(truth)
                if ans != truth and "day_month_swapped" in self.hints and d.day <= 12 and (d.year, d.day, d.month) == (t.year, t.month, t.day):
                    return {"ok": True, "verified": False, "hint": "day_month_swapped", "wrong_answers_left": self._left(s), "all_verified": False}
            elif field not in c["identity"]:
                s["wrong"] += 1; return {"ok": True, "verified": False, "wrong_answers_left": self._left(s), "all_verified": False}
            if ans == truth:
                s["verified"].add(field)
                return {"ok": True, "verified": True, "wrong_answers_left": self._left(s), "all_verified": all(f in s["verified"] for f in required)}
            s["wrong"] += 1
            return {"ok": True, "verified": False, "wrong_answers_left": self._left(s), "all_verified": False}
        if name in ("get_account", "create_promise") and not all(f in s["verified"] for f in required):
            return {"ok": False, "error": "identity not verified"}
        pids = {f"p{i + 1}": p for i, p in enumerate(c["products"])}
        if name == "get_account":
            return {"ok": True, "products": [{"product_id": k, **p} for k, p in pids.items()]}
        if name in ("create_promise", "add_note") and b.get("product_id") not in pids: return {"ok": False, "error": "unknown product_id"}
        if name == "create_promise":
            try: dt.date.fromisoformat(str(b["date"])); amount = float(b["amount"])
            except (KeyError, ValueError, TypeError): return {"ok": False, "error": "bad amount or date"}
            led["promises"].append({"product_id": b["product_id"], "amount": amount, "date": b["date"]})
            return {"ok": True, "promise_id": "pr_" + uuid.uuid4().hex[:8]}
        if name == "add_note":
            led["notes"].append({"product_id": b["product_id"], "reason": b["reason"], "text": b.get("text")}); return {"ok": True}
        if name == "schedule_callback":
            led["callbacks"].append({"date": b.get("date"), "time": b.get("time")}); return {"ok": True}
        if name == "transfer_to_agent":
            led["transfers"].append({"queue": b["queue"]}); return {"ok": True}
        if name == "close_call":
            led["outcome"], led["reason"] = b["outcome"], b.get("reason"); s["closed"] = True; return {"ok": True}

    def _left(self, s): return max(0, s["case"].get("bank", {}).get("max_wrong", 3) - s["wrong"])


def serve(bank, port):
    class H(BaseHTTPRequestHandler):
        def _send(self, code, obj):
            data = json.dumps(obj).encode(); self.send_response(code); self.send_header("content-type", "application/json"); self.send_header("content-length", str(len(data))); self.end_headers(); self.wfile.write(data)
        def do_GET(self):
            m = re.fullmatch(r"/v1/practice/ledger/(\w+)", self.path)
            self._send(200, bank.ledger(m.group(1)) if m else {"ok": False, "error": "not found"})
        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers.get("content-length", 0))) or b"{}")
            if self.path == "/v1/practice/sessions": return self._send(200, bank.new_session(body.get("case")))
            m = re.fullmatch(r"/v1/(\w+)", self.path)
            if m and m.group(1) in TOOLS: return self._send(*bank.tool(m.group(1), body))
            self._send(404, {"ok": False, "error": "not found"})
        def log_message(self, *a): pass
    print(f"mock bank on http://localhost:{port}  ({len(bank.cases)} cases)", flush=True)
    ThreadingHTTPServer(("0.0.0.0", port), H).serve_forever()


def selftest():
    """Replay the expected ledger of each case through the server's own logic and score it with tools/score.py."""
    sys.path.insert(0, str(ROOT / "tools"))
    import os; os.environ.setdefault("FREYA_BANK_TEAM_KEY", "selftest-selftest-1")
    from score import score_ledger
    bad = 0
    for tag in "cde":
        cases = json.load(open(ROOT / "test-briefs" / f"cases-{tag}.json"))
        bank = Bank(json.load(open(ROOT / "test-briefs" / f"tools-{tag}.openapi.json")), cases)
        for c in cases:
            v = bank.new_session(c["id"])["variables"]; cid = v["customer_id"]; call = lambda t, **a: bank.tool(t, {"customer_id": cid, **a})[1]
            e = c["expected"]
            if c["family"] not in ("Third party",) and e["outcome"] not in ("not_verified", "NOVER"):
                for f, x in c["identity"].items(): call("verify_identity", field=f, answer=x)
                call("get_account")
            for f in c.get("faults", []):                       # the agent's own failed attempts come first
                for _ in range(f["fail_first_n"]): call(f["tool"], product_id="p1", amount=1.0, date="2026-01-01")
            for p in e["promises"]: call("create_promise", **p)
            for n in e["notes"]: call("add_note", **n)
            for cb in e["callbacks"]: call("schedule_callback", **cb)
            for t in e["transfers"]: call("transfer_to_agent", **t)
            r = call("close_call", outcome=e["outcome"], **({"reason": e["reason"]} if e["reason"] else {}))
            res = score_ledger(c, bank.ledger(cid)) if r.get("ok") else {"pass": False, "failed": ["close_call refused: " + str(r)]}
            print("ok  " if res["pass"] else "FAIL", c["id"], *res["failed"]); bad += not res["pass"]
    # the checks that must fail: a wrong answer closes the check, tools refuse before verification
    c = json.load(open(ROOT / "test-briefs" / "cases-c.json"))[0]; bank = Bank(json.load(open(ROOT / "test-briefs" / "tools-c.openapi.json")), [c])
    cid = bank.new_session(c["id"])["variables"]["customer_id"]
    assert bank.tool("get_account", {"customer_id": cid})[1]["error"] == "identity not verified"
    assert bank.tool("verify_identity", {"customer_id": cid, "field": "date_of_birth", "answer": "1984-12-09"})[1]["hint"] == "day_month_swapped"
    assert bank.tool("verify_identity", {"customer_id": cid, "field": "date_of_birth", "answer": "0084-09-12"})[1]["hint"] == "year_two_digits"
    assert bank.tool("close_call", {"customer_id": cid, "outcome": "paid"})[1]["ok"] is False        # not in this variant's enum
    print("server checks ok" if not bad else f"{bad} cases failed"); sys.exit(1 if bad else 0)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--api"); ap.add_argument("--cases", nargs="+"); ap.add_argument("--port", type=int, default=8787); ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest: selftest()
    if not a.api or not a.cases: ap.error("--api and --cases are required")
    serve(Bank(json.load(open(a.api)), [c for f in a.cases for c in json.load(open(f))]), a.port)
