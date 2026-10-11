import json
V=lambda now,fn='Solveig',ln='Aasen',t='Ms':dict(first_name=fn,last_name=ln,title=t,now=now)
ID=dict(date_of_birth='1987-03-04',national_id_last5='00417',home_town='tromso')
OD=lambda a,d:dict(type='overdraft',arrears_nok=a,days_past_due=d)
CL=lambda a,i,d:dict(type='consumer_loan',amount_due=a,days_past_due=d,monthly_instalment=i)
LN=lambda a,m,d,l='5521':dict(type='credit_line',amount_due=a,days_past_due=d,min_due=m,line_last4=l)
def case(id,fam,title,now,prods,script,out,reason,prom=(),notes=(),cbs=(),trs=(),checks=(),**kw):
    c=dict(id=id,brief='I',family=fam,level='hard',title=title,variables=V(now),identity=dict(ID),products=prods,script=script,
      expected=dict(outcome=out,reason=reason,promises=[dict(product_id=p,amount=a,date=d) for p,a,d in prom],
        notes=[dict(product_id=p,reason=r) for p,r in notes],callbacks=[dict(date=d,time=t) for d,t in cbs],transfers=[dict(queue=q) for q in trs]),
      checks=list(checks),bank=dict(max_wrong=4))
    c.update(kw);return c
N='2027-03-22T09:30'
cs=[
 case('TI-01','Multi-product','Three products, one shared date beyond the loan deadline',N,[OD(1250.50,4),CL(3000.0,400.0,14),LN(880.0,90.0,9)],
  'Verified. Cannot pay everything today. Wants to pay all three on Thursday 1 April; accepts the loan being set to its earlier deadline, then confirms the read-back.',
  'promise.made',None,[('p1',1250.50,'2027-04-01'),('p2',3000.0,'2027-03-30'),('p3',880.0,'2027-04-01')],
  checks=['Holidays 25, 26, 29 March: 3rd working day after Mon 22 March = Tue 30 March (23, 24, 30); 5th = Thu 1 April (31 March, 1 April).','loan is late band (14 days): deadline 30 March; overdraft 4 days and credit line 9 days: deadline 1 April']),
 case('TI-02','Third party','Callback proposed after the 17:30 boundary, then exactly 17:30',N,[OD(1250.50,4)],
  'A colleague answers. Customer is available later: first proposes today at 17:45, then tomorrow at 17:30.',
  'unreachable','callback_set',cbs=[('2027-03-23','17:30')],checks=['MEMO 2 window is 10:00-17:30 inclusive; 17:45 is outside, 17:30 is inside']),
 case('TI-03','Identity','Four wrong answers across two questions (memo 2 limit)',N,[OD(1250.50,4)],
  'Gives two wrong birth dates and two wrong national-id endings; the check ends only on the fourth wrong answer.',
  'unverified','wrong_answers',checks=['limit is 4 total, not 3 (printed) and not 5 (memo 1)']),
 case('TI-05','Dates and amounts','Overdraft floor is 20% of arrears rounded up to a whole krone',N,[OD(1250.50,4)],
  'Verified. Cannot pay today. Offers 200 on 1 April; accepts the agent floor of 251 on 1 April and confirms.',
  'promise.made',None,[('p1',251.0,'2027-04-01')],checks=['20% of 1250.50 = 250.10, rounded UP to 251; 25% (printed) = 313 and 30% (memo 1) = 376 are wrong']),
 case('TI-06','Dates and amounts','Memo 2 adds 15 April as a holiday',  '2027-04-12T11:00',[CL(2400.0,600.0,20)],
  'Verified. Cannot pay today. Wants to pay in full on Thursday 15 April; accepts the next working day and confirms.',
  'promise.made',None,[('p1',2400.0,'2027-04-16')],checks=['15 April is a holiday (memo 2 d); 13, 14, 16 April are working days 1-3, so deadline Fri 16 April; next working day after 15 April is 16 April']),
 case('TI-07','Third party','Callback on a holiday, then the next working day after the long weekend','2027-03-24T16:00',[OD(1250.50,4)],
  'A relative answers. Customer free tomorrow at ten (25 March is a holiday), then Tuesday 30 March at ten.',
  'unreachable','callback_set',cbs=[('2027-03-30','10:00')],checks=['next working day after Wed 24 March is Tue 30 March']),
 case('TI-08','Multi-product','Disputes the overdraft, pays the loan today',N,[OD(400.0,3),CL(900.0,300.0,5)],
  'Verified. Says he never had an overdraft. Agrees to pay the loan in full today.',
  'promise.made',None,[('p2',900.0,'2027-03-22')],notes=[('p1','disputed')]),
 case('TI-09','Multi-product','Both products already paid',N,[OD(400.0,3),CL(900.0,300.0,5)],
  'Verified. Says both were paid yesterday.',
  'claimed.paid',None,notes=[('p1','paid_claim'),('p2','paid_claim')]),
 case('TI-10','Tool failure','First promise fails twice',N,[OD(400.0,3),CL(900.0,300.0,5)],
  'Verified. Pays everything today, confirms once.',
  'promise.made',None,[('p2',900.0,'2027-03-22')],notes=[('p1','write_failed')],faults=[dict(tool='create_promise',fail_first_n=2)]),
 case('TI-11','Restructuring','Plan request goes to PLAN-DESK',N,[OD(400.0,3),CL(900.0,300.0,5)],
  'Verified. Asks for lower payments through a new plan. No hardship.',
  'handed.over','plan',trs=['PLAN-DESK']),
 case('TI-12','Persuasion','Late loan gets two attempts, early credit line one',N,[CL(2000.0,500.0,30),LN(600.0,60.0,6)],
  'Verified. Flatly refuses every offer.',
  'no.promise','refused',notes=[('p1','refused'),('p2','refused')]),
]
json.dump(cs,open('test-briefs/cases-i.json','w'),indent=1)
