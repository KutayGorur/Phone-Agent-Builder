"""Dev helper: talk to a workflow through the chat route and print the events of the call."""
import json, sys, os, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
import freya

def chat(workflow_id, messages, variables, call_id=None, verbose=True):
    """Send user messages one by one. Returns (call_id, replies)."""
    replies = []
    for m in messages:
        body = {"workflowId": workflow_id, "message": m, "customerVariables": variables}
        if call_id: body["callId"] = call_id
        try:
            r = freya.api("POST", "/api/v2/chat/message", body)
        except RuntimeError as e:
            print("USER:", m, "ERROR:", str(e)[:300]); replies.append(None); continue
        call_id = r.get("callId") or call_id
        replies.append(r.get("response"))
        if verbose: print("USER:", m, "\nAGENT:", r.get("response"), "\n")
    return call_id, replies

def events(call_id, kinds=None, full=False):
    c = freya.get_call(call_id)
    out = []
    for m in c.get("messages", []):
        role = m.get("role"); msg = m.get("message")
        if role == "system":
            try: e = json.loads(msg)
            except Exception: e = {"raw": msg}
            if kinds and e.get("event") not in kinds: continue
            out.append(("SYS", m.get("nodeId"), e))
        else:
            out.append((role.upper(), m.get("nodeId"), msg))
    return c, out

def show(call_id, kinds=None, maxlen=900):
    c, ev = events(call_id, kinds)
    for role, node, e in ev:
        s = json.dumps(e) if not isinstance(e, str) else e
        print(f"[{role}] ({node}) {s[:maxlen]}")
    print("endedReason:", c.get("endedReason"))
    return c
