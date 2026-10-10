import json, sys, os
sys.path.insert(0, os.path.dirname(__file__))
from probe_tools import *
from probe1 import code_node, ALW
BASE = "https://freya-bank-mock.freyavoice.workers.dev/v1/"

def api_node(name, tool, body_props, nxt, mapping=None, pre=None, post=None, retries=0, on_enter=None):
    props = {"customer_id": {"type": "string", "default": "{{customer_id}}"}}
    for k, (typ, default) in body_props.items():
        props[k] = {"type": typ, "default": default}
    fn = {"type": "function", "config": {"timeoutMs": 12000, "maxRetries": retries},
          "function": {"name": tool, "handler": "__function__:api_call", "description": tool,
            "parameters": {"type": "object", "properties": {
                "url": {"type": "string", "default": BASE + tool}, "method": {"type": "string", "default": "POST"},
                "headers": {"type": "object", "properties": {"Content-Type": {"type": "string", "default": "application/json"}}},
                "body": {"type": "object", "properties": props, "required": []}}}}}
    if pre: fn["pre_process_code"] = pre
    if post: fn["post_process_code"] = post
    return {"name": name, "node_type": "api_request", "passthrough": True, "passthrough_default_transition": nxt,
            "on_enter": on_enter or {"type": "silent"}, "disable_inactivity_monitor": True, "pre_actions": [fn],
            "response_mapping": mapping or [], "transitions": [ALW(nxt)]}

SHOW = r'''
import json
p = vars.get('products')
vars['dbg_type'] = type(p).__name__
vars['dbg_val'] = str(p)[:400]
ks = [k for k in vars.keys() if 'get_account' in str(k) or 'products' in str(k)]
vars['dbg_keys'] = json.dumps(ks)[:600]
vars['dbg_ok'] = str(vars.get('ga_ok'))
'''
PRE = r'''
try:
    b = config.get('body')
    if isinstance(b, dict) and 'answer' in b:
        b['answer'] = str(b['answer']).strip()
    vars['pre_ran'] = 'yes'
except Exception:
    vars['pre_ran'] = 'err'
'''
POST = r'''
try:
    d = result.get('data') if isinstance(result, dict) else None
    if isinstance(d, dict):
        d['state'] = 'passed' if d.get('verified') else 'failed'
        d['what_to_do_next'] = 'x'
    result.pop('header', None)
    vars['post_ran'] = 'yes'
except Exception:
    vars['post_ran'] = 'err'
'''
nodes = {
 "start": {"name": "start", "node_type": "conversation", "on_enter": {"type": "tts", "text": "Say anything."}, "task_message": "Reply briefly.", "max_node_turns": 10,
           "transitions": [ALW("v1")]},
 "v1": api_node("v1", "verify_identity", {"field": ("string", "date_of_birth"), "answer": ("string", "{{dob}}")}, "v2", mapping=[{"path": "data.state", "variable": "v1_state"}], pre=PRE, post=POST),
 "v2": api_node("v2", "verify_identity", {"field": ("string", "phone_last4"), "answer": ("string", "{{ph}}")}, "ga", mapping=[{"path": "data.all_verified", "variable": "all_ver"}], pre=PRE),
 "ga": api_node("ga", "get_account", {}, "show", mapping=[{"path": "data.products", "variable": "products"}, {"path": "data.ok", "variable": "ga_ok"}], retries=2),
 "show": code_node("show", SHOW, [ALW("cp")]),
 "cp": api_node("cp", "create_promise", {"product_id": ("string", "p1"), "amount": ("number", "{{amt}}"), "date": ("string", "2026-10-16")}, "fin", mapping=[{"path": "data.ok", "variable": "cp_ok"}],
        pre="try:\n    b = config.get('body')\n    vars['body_type'] = type(b.get('amount')).__name__ + ':' + str(b.get('amount'))\n    b['amount'] = float(b['amount'])\nexcept Exception as e:\n    vars['body_type'] = 'err ' + str(e)\n"),
 "fin": {"name": "fin", "node_type": "end_call", "on_enter": {"type": "silent"}, "disable_inactivity_monitor": True, "transitions": [],
          "terminal": {"type": "function", "function": {"name": "done", "handler": "__function__:end_call",
            "parameters": {"type": "object", "properties": {"message_mode": {"type": "string", "default": "custom"}, "spoken_message": {"type": "string", "default": "done {{dbg_type}} {{cp_ok}} {{v1_state}} {{pre_ran}} {{post_ran}} {{body_type}}"}}}}}},
}
wf = {"initial_node": "start", "system_prompt": "test", "nodes": nodes}
