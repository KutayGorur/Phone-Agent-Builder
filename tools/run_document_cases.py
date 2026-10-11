"""Run source-derived personas with arbitrary live call variables.

Use through ci/sim.py --runner document so lint, dry run and credits are logged.
Conversation verdicts and actual API dispatch constraints are reported
separately; a static mock cannot supply a bank ledger.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import freya
from tools.run_cases import call_waits


def api_dispatches(call):
    found = []
    for message in call.get('messages', []):
        if message.get('role') != 'system':
            continue
        event = message.get('message') or message.get('content') or ''
        if isinstance(event, str):
            try:
                event = json.loads(event)
            except (ValueError, TypeError):
                continue
        if not isinstance(event, dict) or event.get('event') != 'function_call_start':
            continue
        args = event.get('args') or {}
        if isinstance(args, dict) and args.get('url'):
            found.append({'path':urlsplit(args['url']).path, 'body':args.get('body'), 'seconds':message.get('secondsFromStart')})
    return found


def dispatch_problems(case, calls):
    problems = []
    for check in case.get('tool_checks', []):
        matches = [c for c in calls if c['path'] == check['path']]
        if len(matches) < check.get('min', 0) or len(matches) > check.get('max', float('inf')):
            problems.append('%s dispatched %s times, expected %s..%s' % (check['path'], len(matches), check.get('min',0), check.get('max','unbounded')))
        for match in matches:
            for field, expected in check.get('body_equals', {}).items():
                value = match.get('body') or {}
                for part in field.split('.'):
                    value = value.get(part) if isinstance(value, dict) else None
                if str(value) != str(expected):
                    problems.append('%s request field %s does not match expected value' % (check['path'], field))
    return problems


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('agent_id')
    parser.add_argument('--cases', required=True)
    parser.add_argument('--only')
    parser.add_argument('--brief')
    parser.add_argument('--reps', type=int, default=1)
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    cases = [c for c in json.loads(Path(args.cases).read_text(encoding='utf-8-sig'))
             if (not args.only or c['id'] in args.only.split(',')) and (not args.brief or c.get('brief') == args.brief)]
    if not cases or args.reps < 1:
        parser.error('select at least one case and a positive repetition count')
    if len({c['id'] for c in cases}) != len(cases):
        parser.error('case IDs must be unique')
    cache_path = ROOT / 'out' / 'document-personas.json'
    cache = json.loads(cache_path.read_text(encoding='utf-8')) if cache_path.exists() else {}
    keys = {c['id']:hashlib.sha256(json.dumps(c['persona'],sort_keys=True).encode()).hexdigest() for c in cases}
    for case in cases:
        if keys[case['id']] not in cache:
            persona = dict(case['persona'])
            if isinstance(persona.get('successCriteria'), list):
                persona['successCriteria'] = 'All of these must hold:\n- ' + '\n- '.join(persona['successCriteria'])
            cache[keys[case['id']]] = freya.create_personas([persona])['personas'][0]['id']
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(cache,indent=2),encoding='utf-8')
    ids = {c['id']:cache[keys[c['id']]] for c in cases}
    all_rows = []
    t0 = time.monotonic()
    for rep in range(args.reps):
        sim, iteration, status = freya.run_simulation(args.agent_id, 'document cases '+time.strftime('%H:%M:%S'),
            {ids[c['id']]:c['variables'] for c in cases})
        runs = {r['personaId']:r for r in freya.get_iteration(sim,iteration)['runs']}
        rows = []
        for case in cases:
            run = runs.get(ids[case['id']], {})
            failed = []
            if run.get('outcome') != 'pass':
                failed.append('conversation: '+str(run.get('reason') or 'no verdict'))
            call = freya.get_call(run['callId']) if run.get('callId') else {}
            if not call:
                failed.append('missing call transcript')
            dispatches = api_dispatches(call)
            failed += dispatch_problems(case, dispatches)
            slow, unanswered = call_waits(call)
            rows.append({'id':case['id'],'pass':not failed,'failed':failed,'call_id':run.get('callId'),
                'dispatches':dispatches,'slowest_turn_s':slow,'unanswered_wait_s':unanswered,'ended':call.get('endedReason'),
                'simulation_id':sim,'iteration_id':iteration,'status':status})
            if call:
                destination = ROOT/'results'/'document-calls'/(str(run['callId'])+'.json')
                destination.parent.mkdir(parents=True,exist_ok=True)
                destination.write_text(json.dumps(call,ensure_ascii=False,indent=1),encoding='utf-8')
            print(('PASS' if not failed else 'FAIL'),case['id'], ' | '.join(failed)[:700],flush=True)
        all_rows.append(rows)
        destination = Path(args.out)
        destination.parent.mkdir(parents=True,exist_ok=True)
        destination.write_text(json.dumps({'agent_id':args.agent_id,'rows':rows,'all_rows':all_rows},ensure_ascii=False,indent=2),encoding='utf-8')
    passed = sum(all(rows[i]['pass'] for rows in all_rows) for i in range(len(cases)))
    print('%s / %s passed %s/%s reps; conversation and transcript dispatch checks; %.0f seconds' % (passed,len(cases),args.reps,args.reps,time.monotonic()-t0))
    return 0 if passed == len(cases) else 1


if __name__ == '__main__':
    sys.exit(main())
