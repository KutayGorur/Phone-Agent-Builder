"""Merge harder customer-script overlays (harness/scripts/scripts-*.json) into case files.
Usage: python harness/apply_scripts.py   -> writes out/hard/{public-test-set,cases-c,cases-d,cases-e}.json
Only `script` is replaced and `extra_checks` appended to `checks`; facts and `expected` are untouched.
The scripts are free text for the Freya customer simulator; builder/generate/local_sim.py uses its own
scripted extractions (VARIANTS) and does not read them."""
import json, os
R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
J = lambda *p: os.path.join(R, *p)
os.makedirs(J('out', 'hard'), exist_ok=True)
for src, ov, dst in [('public-test-set.json', 'pub', 'public-test-set.json')] + [
        ('test-briefs/cases-%s.json' % k, k, 'cases-%s.json' % k) for k in 'cde']:
    cases = json.load(open(J(src), encoding='utf-8'))
    over = {o['id']: o for o in json.load(open(J('harness', 'scripts', 'scripts-%s.json' % ov), encoding='utf-8'))}
    for c in cases:
        o = over.get(c['id'])
        if o:
            c['script'] = o['script']
            c['checks'] = list(c.get('checks', [])) + o.get('extra_checks', [])
    json.dump(cases, open(J('out', 'hard', dst), 'w', encoding='utf-8'), indent=2, ensure_ascii=False)
    print(dst, len(cases), 'cases,', sum(c['id'] in over for c in cases), 'overlaid')
