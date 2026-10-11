"""Regenerates cases-j.json (practice brief J). python3 test-briefs/make_cases_j.py"""
import json, os
ID = dict(date_of_birth='1985-04-09', mobile_last4='0482')
V = lambda now: dict(family_name='Hayashi', given_name='Rin', now=now)
CARD = lambda o, d, m, l='7301': dict(type='card_revolving', outstanding_jpy=o, overdue_days=d, card_last4=l, minimum_due=m)
AUTO = lambda o, d, i: dict(type='auto_loan', outstanding_jpy=o, overdue_days=d, instalment_jpy=i)
def case(id, fam, title, prods, script, out, reason, prom=(), notes=(), cbs=(), trs=(), checks=(), now='2027-04-27T14:10', **kw):
    c = dict(id=id, brief='J', family=fam, level='hard', title=title, variables=V(now), identity=dict(ID), products=prods, script=script,
             expected=dict(outcome=out, reason=reason, promises=[dict(product_id=p, amount=a, date=d) for p, a, d in prom],
                           notes=[dict(product_id=p, reason=r) for p, r in notes], callbacks=[dict(date=d, time=t) for d, t in cbs],
                           transfers=[dict(queue=q) for q in trs]), checks=list(checks), bank=dict(max_wrong=3))
    c.update(kw); return c
cs = [
 case('TJ-01', 'Dates and amounts', 'Card floor is max(minimum, 10%) rounded up to 100', [CARD(184300, 20, 5000)],
  'Verified. Cannot pay today. Offers 10000 on Saturday 1 May; accepts the agent floor of 18500 on that Saturday and confirms.',
  'PTP', 'RECORDED', [('p1', 18500, '2027-05-01')],
  checks=['10% of 184300 = 18430 > minimum 5000; round UP to 18500', 'late band: 27 Apr + 6 = Mon 3 May (holiday) -> back to Sat 1 May, which is a working day (Mon-Sat week)']),
 case('TJ-02', 'Dates and amounts', 'Showa day holiday inside a Mon-Sat week', [AUTO(520000, 6, 38000)],
  'Verified. Cannot pay today. Wants to pay in full on Thursday 29 April; accepts the next working day.',
  'PTP', 'RECORDED', [('p1', 520000, '2027-04-30')], checks=['29 April holiday; next working day Fri 30 April; early deadline 7 May']),
 case('TJ-03', 'Dates and amounts', 'Sunday inside Golden Week rolls to Thursday 6 May', [AUTO(300000, 3, 20000)],
  'Verified. Cannot pay today. Wants to pay in full on Sunday 2 May; accepts the next working day.',
  'PTP', 'RECORDED', [('p1', 300000, '2027-05-06')], checks=['Sun 2 May not working; 3, 4, 5 May holidays; Thu 6 May is the next working day and is within 7 May']),
 case('TJ-04', 'Third party', 'Callback: third working day refused, then Friday 19:00 (memo B end of window)', [CARD(184300, 20, 5000)],
  'A housemate answers. Proposes Saturday 1 May at 10:00, then Friday 30 April at 19:00.',
  'NO_CONTACT', 'CALLBACK', cbs=[('2027-04-30', '19:00')],
  checks=['next two working days after Tue 27 April: Wed 28 April, Fri 30 April (29 April holiday); Saturday 1 May is the third', 'window 09:00-19:00 inclusive (memo B)']),
 case('TJ-05', 'Identity', 'Three wrong answers end the check', [CARD(184300, 20, 5000)],
  'Gives wrong mobile endings three times.', 'NO_ID', 'FAILED'),
 case('TJ-06', 'Persuasion', 'Late band: refusal, then floor on the deadline', [CARD(90000, 40, 5000)],
  'Verified. Refuses the first offer flatly, refuses again when the full is offered for the next working day, accepts the floor on the deadline.',
  'PTP', 'RECORDED', [('p1', 9000, '2027-05-01')], checks=['floor max(5000, 9000) = 9000 exactly; second attempt on deadline Sat 1 May']),
 case('TJ-07', 'Multi-product', 'Shared date beyond the loan deadline', [CARD(60000, 5, 3000), AUTO(250000, 30, 25000)],
  'Verified. Cannot pay today. Wants to pay both on Friday 7 May; accepts the loan moving to its deadline.',
  'PTP', 'RECORDED', [('p1', 60000, '2027-05-07'), ('p2', 250000, '2027-05-01')],
  checks=['card early band deadline 7 May; loan late band (30 days) deadline 1 May']),
 case('TJ-08', 'Persuasion', 'Refuses everything on both products', [CARD(60000, 5, 3000), AUTO(250000, 30, 25000)],
  'Verified. Flatly refuses every offer.', 'NO_PTP', 'DECLINED_OFFER', notes=[('p1', 'DECLINED_OFFER'), ('p2', 'DECLINED_OFFER')]),
 case('TJ-09', 'Restructuring', 'Plan request', [CARD(60000, 5, 3000), AUTO(250000, 30, 25000)],
  'Verified. Asks for a lower-payment plan.', 'XFER', 'RESTRUCTURE', trs=['Q-RESTRUCTURE']),
 case('TJ-10', 'Happy path', 'Pays everything today (reason still required)', [CARD(60000, 5, 3000), AUTO(250000, 30, 25000)],
  'Verified. Pays both in full today.', 'PTP', 'RECORDED', [('p1', 60000, '2027-04-27'), ('p2', 250000, '2027-04-27')]),
 case('TJ-11', 'Multi-product', 'Already paid the card, pays the loan today', [CARD(60000, 5, 3000), AUTO(250000, 30, 25000)],
  'Verified. Says the card was paid on Friday. Pays the loan in full today.', 'PTP', 'RECORDED', [('p2', 250000, '2027-04-27')], notes=[('p1', 'PAID')]),
 case('TJ-12', 'Multi-product', 'Both already paid', [CARD(60000, 5, 3000), AUTO(250000, 30, 25000)],
  'Verified. Says both were paid on Friday.', 'PAID_CLAIMED', 'CUSTOMER_STATED', notes=[('p1', 'PAID'), ('p2', 'PAID')]),
]
json.dump(cs, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cases-j.json'), 'w'), indent=1)
