import json, sys
sys.path.insert(0, '.')
import freya
r = json.load(open(sys.argv[1]))
row = [x for x in r['rows'] if x['id'] == sys.argv[2]][0]
c = freya.get_call(row['call_id'])
n = int(sys.argv[3]) if len(sys.argv) > 3 else 40
for m in c['messages'][:n]:
    s = m['message']
    if m['role'] == 'system':
        try:
            e = json.loads(s)
            ev = e.get('event')
            if ev == 'route_evaluated': s = 'ROUTE ' + json.dumps({k: e.get(k) for k in ('from_node', 'target', 'reason')})
            elif ev == 'variable_extracted': s = 'EXTRACT %s=%s' % (e.get('name'), e.get('value'))
            else:
                e.pop('variable_table', None); s = json.dumps(e)
        except Exception: pass
    print(m['role'], m.get('nodeId'), s[:600])
print('ended', c.get('endedReason'))
