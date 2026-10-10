"""spec.json -> Freya workflow dict. See HANDOFF.md for the architecture.

    python -m builder.generate.generate builder/specs/brief-a.spec.json out/gen-a.workflow.json
"""
import inspect
import json
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(_HERE)))

from builder.logic import snippet_lib as SL  # noqa: E402
from builder.generate.ecfg import build_E, first_sentence  # noqa: E402

BASE = 'https://freya-bank-mock.freyavoice.workers.dev/v1/'


def _braces(s):
    """Make JSON text free of double braces (whitespace between braces is still valid JSON)."""
    s = re.sub(r'\{(?=\{)', '{ ', s)
    return re.sub(r'\}(?=\})', '} ', s)


def check_code(code, what):
    if '{{' in code or '}}' in code:
        i = code.find('{{') if '{{' in code else code.find('}}')
        raise ValueError('double brace in code of %s near %r' % (what, code[max(0, i - 40):i + 40]))
    return code


def engine_code(E):
    lib = open(os.path.join(os.path.dirname(SL.__file__), 'snippet_lib.py'), encoding='utf-8').read()
    eng = open(os.path.join(_HERE, 'engine_lib.py'), encoding='utf-8').read()
    lit = json.dumps(_braces(json.dumps(E, separators=(', ', ': '))))
    eng = eng.replace('__E__', lit)
    return check_code(lib.rstrip('\n') + '\n\n\n' + eng, 'engine')


# ------------------------------------------------------------------ node helpers

def cond(var, op, operand=None):
    c = {'variable': var, 'operator': op}
    if operand is not None:
        c['operand'] = operand
    return {'logic': 'or', 'conditions': [c]}


def tr(target, var=None, op='equals', operand=None, desc=None):
    if var is None:
        return {'target_node': target, 'description': desc or 'always', 'condition': {'operator': 'always'}}
    return {'target_node': target, 'description': desc or '%s %s %s' % (var, op, operand), 'condition': cond(var, op, operand)}


def code_node(name, code, transitions):
    check_code(code, name)
    return {'name': name, 'node_type': 'code', 'passthrough': True,
            'passthrough_default_transition': transitions[-1]['target_node'], 'on_enter': {'type': 'silent'},
            'disable_inactivity_monitor': True,
            'pre_actions': [{'type': 'function', 'function': {'name': 'code_exec', 'handler': '__function__:code_exec',
                             'parameters': {'type': 'object', 'properties': {
                                 'code': {'type': 'string', 'default': code},
                                 'timeout_ms': {'type': 'number', 'default': 20000}}}}}],
            'transitions': transitions}


def api_fn(tool, body, pre=None, post=None, retries=0, description=None, path=None):
    props = {'customer_id': {'type': 'string', 'default': '{{customer_id}}'}}
    for k, (typ, default) in body.items():
        props[k] = {'type': typ, 'default': default}
    fn = {'type': 'function', 'config': {'timeoutMs': 12000, 'maxRetries': retries},
          'function': {'name': tool, 'handler': '__function__:api_call', 'description': description or tool,
                       'parameters': {'type': 'object', 'properties': {
                           'url': {'type': 'string', 'default': BASE + (path or tool)}, 'method': {'type': 'string', 'default': 'POST'},
                           'headers': {'type': 'object', 'properties': {'Content-Type': {'type': 'string', 'default': 'application/json'}}},
                           'body': {'type': 'object', 'properties': props, 'required': []}}}}}
    if pre:
        fn['pre_process_code'] = pre
    if post:
        fn['post_process_code'] = post
    return fn


def api_node(name, tool, body, nxt, mapping=None, pre=None, retries=0, on_enter=None, node_tool=None):
    return {'name': name, 'node_type': 'api_request', 'passthrough': True, 'passthrough_default_transition': nxt,
            'on_enter': on_enter or {'type': 'silent'}, 'disable_inactivity_monitor': True,
            'pre_actions': [api_fn(node_tool or tool, body, pre=pre, retries=retries)],
            'response_mapping': mapping or [], 'transitions': [tr(nxt)]}


def end_node(name, fname):
    return {'name': name, 'node_type': 'end_call', 'on_enter': {'type': 'silent'}, 'disable_inactivity_monitor': True,
            'transitions': [], 'terminal': {'type': 'function', 'function': {
                'name': fname, 'handler': '__function__:end_call',
                'parameters': {'type': 'object', 'properties': {'message_mode': {'type': 'string', 'default': 'none'}}}}}}


def conv(name, task, extraction=None, transitions=None, on_enter=None, tools=None, first_only=False):
    n = {'name': name, 'node_type': 'conversation', 'task_message': task, 'on_enter': on_enter or {'type': 'llm'},
         'max_node_turns': 60, 'transitions': transitions or []}
    if extraction:
        n['extraction_schema'] = extraction
    if tools:
        n['tools'] = tools
    if first_only:
        n['on_enter_first_entry_only'] = True
    return n


def ext(name, desc, enum=None, typ='string'):
    d = {'name': name, 'type': typ, 'description': desc, 'min_confidence': 0.3}
    if enum:
        d['enum_values'] = enum
    return d


def lit(x):
    return json.dumps(x)


# ------------------------------------------------------------------ hooks for identity tools

def verify_pre(q, E):
    fmt = (q.get('format') or '').lower()
    field = (q.get('field') or '').lower()
    dob = 'yyyy' in fmt or 'birth' in field or 'date' in field
    digits = None
    m = re.search(r'(\d+)\s*digit', fmt) or re.search(r'last(\d+)', field)
    if m:
        digits = int(m.group(1))
    funcs = ''
    if dob:
        funcs = '\n'.join(inspect.getsource(f) for f in (SL.parse_now, SL._expand_year, SL._build_dob, SL.normalize_dob))
        funcs = 'import re\nimport datetime\n' + 'MONTH_ALIASES = ' + repr(SL.MONTH_ALIASES) + '\n' + funcs
    body = ("\ntry:\n    b = config.get('body')\n    if isinstance(b, dict):\n        a = str(b.get('answer') or '').strip()\n")
    if dob:
        body += ("        today, _m = parse_now(vars.get('now'))\n"
                 "        s, val, amb = normalize_dob(a, %s, today)\n"
                 "        if s == 'ok' and val:\n            a = val\n" % repr({'dob_order': E['cal'].get('dob_order')}))
    elif digits:
        body += "        dg = re.sub(r'[^0-9]', '', a)\n        if len(dg) >= %d:\n            a = dg[-%d:]\n" % (digits, digits)
    body += "        b['answer'] = a\nexcept Exception:\n    pass\n"
    if not dob:
        funcs = 'import re\n'
    return check_code(funcs + body, 'verify_pre')


def verify_post(q, idx, n):
    ask = q.get('ask') or 'the answer'
    return check_code(
        "\ntry:\n"
        "    def _t(x):\n        return x is True or str(x).lower() == 'true'\n"
        "    if isinstance(result, dict):\n        result.pop('header', None)\n"
        "        d = result.get('data')\n"
        "        if not isinstance(d, dict):\n            d = dict()\n            result['data'] = d\n"
        "        left = d.get('wrong_answers_left')\n"
        "        if _t(d.get('verified')):\n            state = 'passed'\n"
        "            nxt = 'The answer is correct. Say thank you in two words.'\n"
        "        elif d.get('hint') == 'day_month_swapped':\n            state = 'swapped'\n"
        "            nxt = 'Day and month may be swapped. Ask the customer to say the month as a word, then call this tool again with the date.'\n"
        "        elif d.get('ok') is not None and not _t(d.get('ok')):\n            state = 'error'\n"
        "            nxt = 'The answer could not be read or the service failed. Ask for the answer again, then call this tool again.'\n"
        "        elif left is not None and str(left).isdigit() and int(left) <= 0:\n            state = 'locked'\n"
        "            nxt = 'The check has ended. Do not say anything about why.'\n"
        "        elif d.get('verified') is None:\n            state = 'error'\n"
        "            nxt = 'The service failed. Ask for the answer again, then call this tool again.'\n"
        "        else:\n            state = 'failed'\n"
        "            nxt = 'The answer did not match. Tell the customer it did not match, do not say what was wrong, and ask for %s again.'\n"
        "        d['state'] = state\n        d['what_to_do_next'] = nxt\n"
        "except Exception:\n    pass\n" % ask.replace("'", ' '), 'verify_post')


CLOSE_PRE = ("\ntry:\n    b = config.get('body')\n    if isinstance(b, dict) and not str(b.get('reason') or '').strip():\n"
             "        b.pop('reason', None)\n    if isinstance(b, dict) and str(b.get('reason') or '').startswith('{'):\n        b.pop('reason', None)\n"
             "except Exception:\n    pass\n")
AMOUNT_PRE = ("\ntry:\n    b = config.get('body')\n    if isinstance(b, dict) and 'amount' in b:\n"
              "        b['amount'] = float(b['amount'])\nexcept Exception:\n    pass\n")


# ------------------------------------------------------------------ the workflow

def generate(spec):
    E = build_E(spec)
    meta = spec.get('meta') or {}
    bank = meta.get('bank_name') or 'the bank'
    op = spec.get('opening') or {}
    idn = spec.get('identity') or {}
    qs = idn.get('questions') or []
    n = len(qs)
    multi = bool(E['use_notes'] or meta.get('multi_product'))
    forb = ', '.join('"%s"' % w for w in (op.get('forbidden_words_before_verification') or []))
    nodes = {}

    # ---- system prompt
    rules = [
        'You are the digital assistant of %s on an outbound phone call. Speak %s.' % (bank, meta.get('language') or 'English'),
        'Keep every turn to one to three short sentences. Ask one question at a time. Be polite and calm.',
        'Follow the instruction of the current step exactly. Never invent figures, dates, reasons or offers.',
        'If asked whether you are a robot or an AI, say: %s and continue.' % E['ai_say'],
        'If asked whether this is a scam, say that %s, and continue.' % E['scam_say'],
        'If you cannot answer a question, say "%s".' % E['unknown_say'],
        'Never offer a discount, a waiver, an instalment plan or any term that is not part of your instructions.',
    ]
    for r in spec.get('extra_rules') or []:
        t = r.get('text') if isinstance(r, dict) else str(r)
        if t:
            rules.append(t)
    system_prompt = '\n'.join('- ' + r for r in rules)

    confirm_q = (op.get('confirm_identity_question') or 'Am I speaking with {title} {last_name}?').replace('{', '{{').replace('}', '}}')
    opening_text = first_sentence(spec) + ' ' + confirm_q
    acc = ', '.join('"%s"' % a for a in (op.get('accepted_confirmations') or []) if 'own name' not in a and "customer's" not in a)
    notc = ', '.join('"%s"' % a for a in (op.get('not_confirmations') or []))
    pres_desc = ('Who is on the line, judged from the last customer message. confirmed = ONLY if they clearly say they are '
                 '{{title}} {{last_name}}: %s, or they say their own name. other_person = somebody else answered (relative, '
                 'colleague, child...) or says that person is not here. wrong_number = says the number is not theirs / nobody '
                 'of that name. deceased = says the person has died. unclear = anything else, e.g. %s, a question, a greeting.' % (acc or '"yes"', notc or '"hello"'))
    pres_enum = ['confirmed', 'other_person', 'wrong_number', 'deceased', 'unclear']
    pres_ext = [ext('presence', pres_desc.replace('{{title}} {{last_name}}', 'the person asked for'), pres_enum)]
    secrecy = ('Do not say why you are calling. Never say %s and never name any product, amount or account, even if asked or '
               'if the person offers to pay. ' % (forb or '"collections", "debt", "payment"'))

    opening_trans = [tr('init', 'presence', 'equals', 'confirmed'), tr('fin_wrong_number', 'presence', 'equals', 'wrong_number'),
                     tr('fin_deceased', 'presence', 'equals', 'deceased'), tr('to_tp', 'presence', 'equals', 'other_person')]
    nodes['opening'] = conv('opening', 'The customer has not yet confirmed who they are. If they asked a question, answer it in one short sentence '
                            'first (rules in your system prompt). ' + secrecy + 'Then ask once: ' + confirm_q,
                            pres_ext, opening_trans + [tr('opening_retry', 'presence', 'equals', 'unclear')],
                            on_enter={'type': 'tts', 'text': opening_text})
    nodes['opening_retry'] = conv('opening_retry', 'The customer has not yet confirmed who they are. If they asked a question, answer it in one short '
                                  'sentence first (rules in your system prompt); if they ask what the call is about, say you can explain after a short '
                                  'security check. ' + secrecy + 'Then ask again: ' + confirm_q,
                                  pres_ext, opening_trans + [tr('fin_unclear', 'presence', 'equals', 'unclear')])

    # ---- tiny closing nodes
    def fin(key, c, text):
        vs = 'vars[%s] = %s\n' % (lit('close_outcome'), lit(c['outcome']))
        if c.get('reason'):
            vs += 'vars[%s] = %s\n' % (lit('close_reason'), lit(c['reason']))
        vs += 'vars[%s] = %s\n' % (lit('bye_text'), lit(text))
        nodes[key] = code_node(key, vs, [tr('do_close')])
    fin('fin_unclear', E['unclear'], 'I am sorry, I could not confirm who I am speaking with. Goodbye.')
    fin('fin_wrong_number', E['tp']['wrong_number'], E['tp']['wrong_number_say'])
    fin('fin_deceased', E['tp']['deceased'], E['tp']['deceased_say'])
    fin('fin_idv_failed', E['idv']['failed'], 'I am sorry, I could not verify your identity. Please ' + E['idv']['failed_say'] + '. ' + E['goodbye'])

    # ---- init / to_tp
    ivars = ['say_text', 'x_date', 'x_amount', 'x_product', 'tp_date', 'tp_time', 'idv_note',
             'instruction', 'route', 'bye_text', 'close_outcome', 'cp_ok', 'nt_ok', 'cb_ok', 'tr_queue', 'tr_text', 'st']
    ivars += ['idq%d_state' % (i + 1) for i in range(n)]
    enum_init = 'vars["x_intent"] = "none"\nvars["x_stance"] = "other"\nvars["tp_event"] = "other"\nvars["x_q"] = "no"\n'
    nodes['init'] = code_node('init', enum_init + ''.join('vars[%s] = \'\'\n' % lit(v) for v in ivars), [tr('idq_1' if n else 'get_account')])
    nodes['to_tp'] = code_node('to_tp', 'vars["tp_event"] = "other"\n' + ''.join('vars[%s] = \'\'\n' % lit(v) for v in ('tp_date', 'tp_time', 'instruction', 'route')) +
                               'vars["st"] = \'{"phase": "tp"}\'\n', [tr('third_party')])

    # ---- third party
    tp_ext = [ext('tp_event', 'What the person says. gives_time = names a day and/or a time when the customer can be reached or called back. '
                  'wrong_number = says this number does not belong to the customer. deceased = says the customer has died. '
                  'other = anything else (asks what it is about, offers to pay, says the customer is not available, does not know).',
                  ['gives_time', 'wrong_number', 'deceased', 'other']),
              ext('tp_date', 'The day the person names for reaching the customer, in their own words (e.g. "tomorrow", "Friday"). Empty if none.'),
              ext('tp_time', 'The time of day the person names, in their own words, with morning/afternoon if said (e.g. "eleven in the morning"). Empty if none.')]
    tp_task = ('You are speaking to somebody who is NOT the customer. ' + secrecy + 'You may only ask when the customer can be reached '
               '(a day and a time). ')
    nodes['third_party'] = conv('third_party', tp_task + 'Say that you can only speak to ' + E['who'] + ' and ask when they can be reached.',
                                tp_ext, [tr('engine')])
    nodes['tp_say'] = conv('tp_say', tp_task + '{{instruction}}', tp_ext, [tr('engine')])

    # ---- identity questions
    for i, q in enumerate(qs, 1):
        tool = 'verify_%s' % q.get('field')
        nxt = 'idq_%d' % (i + 1) if i < n else 'get_account'
        fn = api_fn(tool, {'field': ('string', q.get('field')), 'answer': ('string', '{{answer}}')},
                    pre=verify_pre(q, E), post=verify_post(q, i, n), retries=1, path=idn.get('tool') or 'verify_identity',
                    description='CALL this every time the customer gives %s. Pass exactly what the customer said (%s). Never call it without an answer '
                                'given in this call and never guess one.' % (q.get('ask'), q.get('format') or 'as said'))
        fn['function']['parameters']['properties']['body']['properties']['answer']['description'] = (
            'The customer\'s answer to: %s. Format: %s.' % (q.get('ask'), q.get('format') or 'as said'))
        fn['function']['parameters']['properties']['body']['required'] = ['answer']
        fn['response_mapping'] = [{'path': 'data.state', 'variable': 'idq%d_state' % i}]
        first = ('Briefly say that you need to ask %d security question%s first. ' % (n, '' if n == 1 else 's')) if i == 1 else 'Say thank you in two words. '
        task = ('Current step: security check, question %d of %d. %sThen ask for %s, only this one question, in one short sentence. {{idv_note}}\n'
                'When the customer gives an answer, CALL the tool %s with it. Never guess an answer. After a tool result, follow its what_to_do_next and '
                'speak. Do not mention any product, amount, debt, payment or collections, and say nothing about the reason for the call; if asked '
                'what the call is about, say you can only explain after the security check.' % (i, n, first, q.get('ask'), tool))
        stance_enum = ['declines', 'human', 'other'] if E['human'] else ['declines', 'other']
        stance = ext('x_stance', 'declines = the customer declines to answer, does not want to continue, or asks what the call is about / why they are '
                     'called instead of answering. %sother = anything else (an answer, a question about whether you are a robot, a scam question).' %
                     ('human = asks for a person or a human agent. ' if E['human'] else ''), stance_enum)
        trans = [tr('fin_idv_failed', 'idq%d_state' % i, 'equals', 'locked'), tr(nxt, 'idq%d_state' % i, 'equals', 'passed'),
                 tr('engine', 'x_stance', 'equals', 'declines')]
        if E['human']:
            trans.append(tr('engine', 'x_stance', 'equals', 'human'))
        nodes['idq_%d' % i] = conv('idq_%d' % i, task, [stance], trans, tools=[fn])

    # ---- account
    nodes['get_account'] = api_node('get_account', 'get_account', {}, 'engine', mapping=[{'path': 'data.ok', 'variable': 'ga_ok'}], retries=2)

    # ---- engine
    routes = ['say_main', 'create', 'note', 'transfer', 'callback', 'tp_say', 'fin']
    target = {'say': 'say_fixed', 'ask': 'say_main', 'create': 'do_create_promise', 'note': 'do_add_note', 'transfer': 'do_transfer', 'callback': 'do_callback',
              'tp_say': 'tp_say', 'fin': 'do_close'}
    et = [tr(t, 'route', 'equals', r) for r, t in target.items()]
    for i in range(1, n + 1):
        et.append(tr('idq_%d' % i, 'route', 'equals', 'idq_%d' % i))
    et.append(tr('say_main'))
    nodes['engine'] = code_node('engine', engine_code(E), et)

    # ---- speaking node after verification
    ids = ['agree', 'refuse', 'too_much', 'offer', 'evasive', 'question', 'none'] + list(E['intents'].keys())
    d = ['agree = accepts or confirms what the agent just proposed or read back (yes, ok, fine, that works, I confirm)',
         'refuse = flat no / will not or cannot pay, with no date and no amount offered (also silence-type refusals)',
         'too_much = says the full amount is too much / unaffordable, no figure given',
         'offer = names a date and/or an amount they can pay (also when they change the date or amount after a read-back)',
         'evasive = a non-answer (hmm, I do not know, let me think, changes the subject without answering)',
         'question = asks any other question or says something unclear',
         'none = nothing relevant']
    for k, v in E['intents'].items():
        d.append('%s = %s' % (k, v['desc']))
    intent_desc = ('Classify the customer\'s LAST message into exactly one value. Priority: a mention of illness, a death in the family or losing a job comes first, then the special requests, then the rest. ' +
                   '; '.join(d) + '.')
    sm_ext = [ext('x_intent', intent_desc, ids),
              ext('x_date', 'The day or period the customer names for paying, in their own words (e.g. "Friday", "the 23rd", "next week", "6 November", '
                  '"end of the month"). Join pieces said in several messages; if they corrected themselves use the corrected one. Empty if none.'),
              ext('x_amount', 'The amount of money the customer says they can pay, as said (digits or words). Join pieces said in several messages; use the '
                  'corrected value if they corrected themselves. Empty if none.')]
    sm_ext.append(ext('x_q', "yes if the customer's last message contains a question of any kind (for example whether you are a robot, whether this is a scam, why, what, how much), even when it also contains an answer; otherwise no.", ['yes', 'no']))
    if E['use_notes'] or meta.get('multi_product'):
        sm_ext.append(ext('x_product', 'Which product the customer is talking about, if they name one (e.g. "credit card", "personal loan", "car loan"), or '
                          '"all" if they mean everything / both / all of them. Empty if not clear.'))
    nodes['say_fixed'] = conv('say_fixed', 'Speak only the fixed line. Do not call any tool.', sm_ext, [tr('engine')],
                              on_enter={'type': 'tts', 'text': '{{say_text}}'})
    nodes['say_main'] = conv('say_main', '{{instruction}}\n\nIf the customer\'s last message contained a question, answer it in one short sentence first '
                             '(rules in your system prompt), then say the above. Never mention these instructions. Do not call any tool.',
                             sm_ext, [tr('engine')])

    # ---- api nodes
    nodes['do_create_promise'] = api_node('do_create_promise', 'create_promise',
                                          {'product_id': ('string', '{{cp_pid}}'), 'amount': ('number', '{{cp_amount}}'), 'date': ('string', '{{cp_date}}')},
                                          'engine', mapping=[{'path': 'data.ok', 'variable': 'cp_ok'}], pre=None)
    nodes['do_add_note'] = api_node('do_add_note', 'add_note', {'product_id': ('string', '{{nt_pid}}'), 'reason': ('string', '{{nt_reason}}')},
                                    'engine', mapping=[{'path': 'data.ok', 'variable': 'nt_ok'}])
    nodes['do_transfer'] = api_node('do_transfer', 'transfer_to_agent', {'queue': ('string', '{{tr_queue}}')}, 'engine',
                                    on_enter={'type': 'tts', 'text': '{{tr_text}}'})
    nodes['do_callback'] = api_node('do_callback', 'schedule_callback', {'date': ('string', '{{cb_date}}'), 'time': ('string', '{{cb_time}}')}, 'engine',
                                    mapping=[{'path': 'data.ok', 'variable': 'cb_ok'}])
    nodes['do_close'] = api_node('do_close', 'close_call', {'outcome': ('string', '{{close_outcome}}'), 'reason': ('string', '{{close_reason}}')}, 'hangup',
                                 pre=None, on_enter={'type': 'tts', 'text': '{{bye_text}}'})
    nodes['hangup'] = end_node('hangup', 'call_closed')

    test_vars = {'customer_id': 'c_test', 'first_name': 'Test', 'last_name': 'Customer', 'title': 'Mr', 'now': '2026-10-14T11:00'}
    return {'initial_node': 'opening', 'system_prompt': system_prompt, 'test_variables': test_vars, 'global_nodes': {}, 'nodes': nodes}


if __name__ == '__main__':
    spec = json.load(open(sys.argv[1], encoding='utf-8'))
    wf = generate(spec)
    out = sys.argv[2] if len(sys.argv) > 2 else None
    if out:
        os.makedirs(os.path.dirname(out) or '.', exist_ok=True)
        json.dump(wf, open(out, 'w', encoding='utf-8'), indent=1)
    print('nodes:', len(wf['nodes']), 'bytes:', len(json.dumps(wf)))
