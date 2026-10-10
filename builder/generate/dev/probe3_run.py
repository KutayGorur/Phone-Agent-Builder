import sys, os, json
sys.path.insert(0,'builder/generate/dev'); sys.path.insert(0,'tools')
from probe_tools import *
from score import http
import probe3
cases = {c["id"]: c for c in json.load(open("public-test-set.json"))}
c = cases["PUB-12"]
sess = http("/v1/practice/sessions", {"case": "PUB-12"})["variables"]
print(sess)
sess["dob"] = c["identity"]["date_of_birth"]; sess["ph"] = c["identity"]["phone_last4"]; sess["amt"] = "510.0"
st = freya.save_workflow("gen-probe3", probe3.wf)
cid, rep = chat(st["workflow_id"], ["hi", "ok"], sess)
show(cid, kinds=["node_enter","function_call_start","function_call_complete","error"], maxlen=1500)
print(http("/v1/practice/ledger/" + sess["customer_id"]))
