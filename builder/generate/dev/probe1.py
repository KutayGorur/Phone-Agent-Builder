import json, sys, os
sys.path.insert(0, os.path.dirname(__file__))
from probe_tools import *

def code_node(name, code, trans, default=None):
    return {"name": name, "node_type": "code", "passthrough": True, "passthrough_default_transition": default or trans[-1]["target_node"],
            "on_enter": {"type": "silent"}, "disable_inactivity_monitor": True,
            "pre_actions": [{"type": "function", "function": {"name": "code_exec", "handler": "__function__:code_exec",
              "parameters": {"type": "object", "properties": {"code": {"type": "string", "default": code}, "timeout_ms": {"type": "number", "default": 10000}}}}}],
            "transitions": trans}

def eq(var, val, target, desc=""):
    return {"target_node": target, "description": desc or f"{var}={val}", "condition": {"logic": "or", "conditions": [{"variable": var, "operator": "equals", "operand": val}]}}
def isset(var, target):
    return {"target_node": target, "description": f"{var} set", "condition": {"logic": "or", "conditions": [{"variable": var, "operator": "is_set"}]}}
ALW = lambda t: {"target_node": t, "description": "always", "condition": {"operator": "always"}}

ENG = r'''
import json
w = vars.get('word')
n = int(vars.get('n') or 0) + 1
vars['n'] = n
vars['seen_word'] = str(w)
vars['instruction'] = 'You said ' + str(w) + ' (turn ' + str(n) + '). Ask for another word.'
vars['word'] = ''
vars['st'] = json.dumps({'a': {'b': n}})
vars['route'] = 'end' if str(w).lower() == 'stop' else 'say'
'''

wf = {
 "initial_node": "start",
 "system_prompt": "You are a test assistant. English. One short sentence.",
 "test_variables": {"title": "Mr", "last_name": "Reyes", "now": "2026-10-14T11:00"},
 "nodes": {
  "start": {"name": "start", "node_type": "conversation", "on_enter": {"type": "tts", "text": "Hello {{title}} {{last_name}}, say any word, or say stop."},
            "task_message": "Reply briefly. No tool calls.",
            "extraction_schema": [{"name": "word", "type": "string", "description": "A single word the user says. Empty if none.", "min_confidence": 0.5}],
            "max_node_turns": 10,
            "transitions": [isset("word", "eng"), ALW("start")]},
  "eng": code_node("eng", ENG, [eq("route", "end", "fin"), eq("route", "say", "say"), ALW("say")]),
  "say": {"name": "say", "node_type": "conversation", "on_enter": {"type": "llm"},
          "task_message": "Say this to the customer, in your own words: {{instruction}}. Do not call tools.",
          "extraction_schema": [{"name": "word", "type": "string", "description": "A single word the user says. Empty if none.", "min_confidence": 0.5}],
          "max_node_turns": 10,
          "transitions": [isset("word", "eng"), ALW("say")]},
  "fin": {"name": "fin", "node_type": "end_call", "on_enter": {"type": "silent"}, "disable_inactivity_monitor": True, "transitions": [],
          "terminal": {"type": "function", "function": {"name": "done", "handler": "__function__:end_call",
            "parameters": {"type": "object", "properties": {"message_mode": {"type": "string", "default": "custom"}, "spoken_message": {"type": "string", "default": "Bye {{seen_word}} n={{n}}"}}}}}}
 }
}

if __name__ == "__main__":
    st = freya.save_workflow("gen-probe", wf)
    print(st)
    cid, rep = chat(st["workflow_id"], ["Hello", "banana", "...", "stop"], {"title": "Mr", "last_name": "Reyes", "now": "2026-10-14T11:00"})
    show(cid, kinds=["node_enter", "route_evaluated", "error", "function_call_start", "function_call_complete"], maxlen=1500)
