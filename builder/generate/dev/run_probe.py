import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))
from probe_tools import *
import importlib
mod = importlib.import_module(sys.argv[1])
msgs = json.loads(sys.argv[2])
st = freya.save_workflow(sys.argv[3] if len(sys.argv) > 3 else "gen-probe", mod.wf)
print(st)
variables = getattr(mod, "VARS", {"title": "Mr", "last_name": "Reyes", "now": "2026-10-14T11:00"})
cid, rep = chat(st["workflow_id"], msgs, variables)
show(cid, kinds=["node_enter", "route_evaluated", "error", "function_call_start", "function_call_complete"], maxlen=int(os.environ.get("MAXLEN", "1200")))
