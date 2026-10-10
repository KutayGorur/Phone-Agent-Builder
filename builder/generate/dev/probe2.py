import json, sys, os
sys.path.insert(0, os.path.dirname(__file__))
from probe_tools import *
from probe1 import code_node, ALW

def cond(var, op, operand=None):
    c = {"variable": var, "operator": op}
    if operand is not None: c["operand"] = operand
    return {"logic": "or", "conditions": [c]}

tests = [("e", "is_set", None), ("e", "is_not_set", None), ("e", "equals", ""), ("e", "not_equals", ""),
         ("u", "is_set", None), ("u", "is_not_set", None), ("u", "equals", ""), ("u", "not_equals", ""),
         ("s", "equals", "x"), ("n", "greater_than", 0), ("n", "equals", "3"), ("start.total_turns", "greater_than", 0), ("lst", "contains", "p1")]
nodes = {}
INIT = r'''
vars['e'] = ''
vars['s'] = 'x'
vars['n'] = 3
vars['lst'] = '[{"product_id": "p1"} ]'
'''
nodes["start"] = {"name": "start", "node_type": "conversation", "on_enter": {"type": "tts", "text": "Say anything."},
   "task_message": "Reply briefly. No tool calls.", "max_node_turns": 10,
   "transitions": [{"target_node": "init", "description": "always", "condition": {"operator": "always"}}]}
nodes["init"] = code_node("init", INIT, [ALW("t0")])
for i, (v, op, od) in enumerate(tests):
    nxt = f"t{i+1}" if i + 1 < len(tests) else "fin"
    nodes[f"t{i}"] = {"name": f"t{i}", "node_type": "code", "passthrough": True, "passthrough_default_transition": nxt, "on_enter": {"type": "silent"},
        "pre_actions": [{"type": "function", "function": {"name": "code_exec", "handler": "__function__:code_exec", "parameters": {"type": "object", "properties": {"code": {"type": "string", "default": "x = 1"}}}}}],
        "transitions": [{"target_node": f"hit{i}", "description": f"{v} {op} {od}", "condition": cond(v, op, od)}, ALW(nxt)]}
    nodes[f"hit{i}"] = {"name": f"hit{i}", "node_type": "code", "passthrough": True, "passthrough_default_transition": nxt, "on_enter": {"type": "silent"},
        "pre_actions": [{"type": "function", "function": {"name": "code_exec", "handler": "__function__:code_exec", "parameters": {"type": "object", "properties": {"code": {"type": "string", "default": f"vars['hit{i}'] = 'yes'"}}}}}],
        "transitions": [ALW(nxt)]}
nodes["fin"] = {"name": "fin", "node_type": "end_call", "on_enter": {"type": "silent"}, "disable_inactivity_monitor": True, "transitions": [],
          "terminal": {"type": "function", "function": {"name": "done", "handler": "__function__:end_call",
            "parameters": {"type": "object", "properties": {"message_mode": {"type": "string", "default": "custom"}, "spoken_message": {"type": "string", "default": "done"}}}}}}
wf = {"initial_node": "start", "system_prompt": "test", "nodes": nodes}
TESTS = tests
