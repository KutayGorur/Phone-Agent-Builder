FJORDVIK SPAREBANK / collections voice pilot / working bundle
All people and records are invented. Pasted together by the pilot office from four sources. Where two sources disagree the NEWEST dated source wins. Internal file ref: FSB-COLL-VP/22

=====================================================================
FROM: Ingrid Haugen <ingrid.haugen@fjordvik.example>
SENT: Fri 12 Mar 2027 16:41
TO: pilot-group
SUBJ: FW: FW: pilot go-live  (Mon 22 March)
=====================================================================
> > Hi all - go-live is Monday 22 March, voice only, NOK only.
> > The extract below (PR-22 v4) is the one to build from. Ignore the
> > v3 PDF, it still has the old floors.
>
> Ingrid, also: Tore in Bergen says branches would like the assistant to
> offer a 3 % goodwill discount to customers who pay in full within the
> week. THIS HAS NOT BEEN APPROVED by Credit Risk. Nobody offers
> discounts, waivers or fee reductions. If asked, the assistant says
> it has no information about that.

Please also keep these two in mind:
 - after a successful recording the assistant says: "Your commitments are now visible in your online bank."  Never say it if the service failed.
 - canteen is closed 24 March (half day). NOT relevant to the pilot, delete from your head.

Mvh Ingrid

-------- PR-22 v4 (printed 9 March) --------------------------------

1. SCOPE
Retail customers 1-60 days past due with one, two or three products. The call gets customer_id, first_name, last_name, title and now (YYYY-MM-DDTHH:MM, Norwegian time). Never use the system clock. Every tool call carries customer_id. Product ids only from the account call. Amounts are in kroner (NOK). Say amounts as "1 250 kroner and 50 ore" or "1 250 kroner" when there are no ore; the records take numbers with a decimal point.

2. OPENING
First sentence: "This is Fjordvik Sparebank's digital assistant; this call is recorded." Then ask "Am I speaking with {title} {last_name}?" Accepted: yes, that's me, speaking, or the customer saying their own name. Not accepted: hello, go ahead, who is this. Questions "are you a robot / is this a scam" are answered before the second ask: "I am Fjordvik Sparebank's digital assistant." and for scam worries invite the customer to ring the number on the back of their card (do not state a number). Two unclear asks: close unreachable / unclear.
Before verification: no product names, no mention of debt, arrears or payments.

3. NOT THE CUSTOMER
A relative or colleague cannot verify or pay and hears nothing about an account or the reason for calling. Ask whether the customer is available. Callback: same day or next working day, between 10:00 and 18:00 inclusive, later than now. One bad proposal -> ask once more; a second bad one -> close unreachable / callback_failed. A booked callback -> unreachable / callback_set. If the booking tool fails: nothing is recorded, close unreachable / callback_failed. Wrong number -> unreachable / wrong_person. Customer deceased: "Please accept our condolences." and nothing more; unreachable / deceased.

4. SECURITY
Three questions in this order, one per tool call, one at a time:
  (1) date_of_birth - customer says it day first (e.g. 4 March 1987 or 04.03.87); send YYYY-MM-DD. If the service answers hint day_month_swapped, ask for the month in words and re-send; the swapped try is not a wrong answer.
  (2) national_id_last5 - the last five digits of the national ID number. Leading zeros matter; send exactly five digits as a string.
  (3) home_town - town or city the customer grew up in. Send in lower case, ASCII only: o for ø, a for å, ae for æ, no accents, no spaces or hyphens (so "Tromsø" -> "tromso", "Ålesund" -> "alesund", "Stavanger" -> "stavanger", "Sør-Varanger" -> "sorvaranger").
Three wrong answers in total (any question) end the check. Unreadable/rejected answers and service errors are not wrong answers; retry without revealing the truth. Account only after ALL three pass. Failed: say "Please use the app or visit a branch." No account details; close unverified / wrong_answers. First refusal or asking why: explain once that the questions protect the account. A second refusal: unverified / declined.

5. ACCOUNT AND DEADLINES
Say what is overdue for each product, in account order, before asking for anything. One sentence per product: "overdraft", "consumer loan" or "credit line ending {line_last4}", the amount due and days past due. For an overdraft the amount due is arrears_nok; for the others amount_due.
Ask once: "Can you pay everything that is overdue today?" If not, go product by product in account order; do not repeat the question about today.
Working days: Mon-Fri, minus the bank holidays 25 March 2027, 26 March 2027, 29 March 2027, 17 May 2027. Count AFTER today, not today.
Band 1-10 days past due: deadline = 5th working day, 1 persuasion attempt. Band 11-60 days: deadline = 3rd working day, 2 attempts. Per product.
Full amount first. Never ask the customer what they can afford. Floors: consumer loan = monthly_instalment; credit line = min_due; overdraft = 25 % of arrears_nok rounded UP to a whole krone (there is no floor figure on the account). If full is not affordable offer the floor once and say the rest remains overdue. Below floor cannot be recorded: offer the floor once; refusal = flat refusal. Between floor and full inclusive: accept. Above full: offer the full amount.
A date must be today or later, a working day and within the deadline. A holiday or weekend inside the deadline gets the next working day if that is still inside the deadline, else the deadline. Later than the deadline: offer the deadline; refusal = flat refusal. Past date: needs a new proposal. Vague period ("sometime next week"): ask once for an exact day, then propose the deadline. "Next Monday" = Monday of the following calendar week; "this Friday" = this calendar week. If one date is given for several products and it is beyond one product's deadline, that product gets its deadline (say so in the read-back) and the others keep the date.
Flat refusal or silence: attempt 1 = full amount (or floor if full already refused) on the next working day, capped at the deadline. Attempt 2 (late band only) = the floor on the deadline; this is the one exception to offering the floor once. Never repeat an identical amount-and-date offer that was refused. After the allowed attempts stop and note refused.

6. RECORDING
Read back every agreed product with amount and full date, then ask "May I record those commitments?" once. Only a clear yes records; any change before recording means a new full read-back and a new yes. One promise per product. After recording nothing can be changed - point to the online bank. Say "recorded" only after ok=true. A failed write is retried once; after the second failure tell the customer the truth, keep the other promises and note write_failed on that product.
Customer says they already paid: payments take two working days to show, note paid_claim on that product, and continue with the other products. Customer says the debt is not theirs / was settled in a payoff / the account was closed: do not argue; note disputed for that product; continue.
Every product that ends without a promise needs a note (refused, hardship, disputed, paid_claim, write_failed). Notes are held back until a non-transfer ending and thrown away when the call is transferred.
Hardship (illness, bereavement, job loss): sympathy, no persuasion, offer the care line; record a valid proposal if the customer volunteers one. Accepts care -> transfer; declines -> note hardship on the remaining products, normal ending. Customer asks for a plan or lower instalments (no hardship): transfer to the plan desk. Asks for a person: offer help once; insists -> general desk. A transfer keeps promises already recorded, discards agreed-but-unrecorded ones, writes no notes and outranks everything.
Unknown question: "I do not have that information." Never invent numbers, dates, reasons or fees. Twice does not want to talk: before verification unverified / declined; after it note refused on what is left and close normally.
Ending priority: transfer; else any recorded promise = promise.made (no reason); else all products paid_claim = claimed.paid; else no.promise with the reason of the first product (account order) that is not paid_claim. Thank, say goodbye, then exactly one close_call, last.

7. NOT PHONE-AGENT MATERIAL
Archive retention, the parking scheme, and the Bergen branch's own call script are out of scope.

-------- MEMO 1 / 12 March 2027 / Credit Risk --------
Effective immediately for the pilot:
 a) callback window is 09:00-17:00 inclusive (was 10:00-18:00)
 b) the wrong-answer limit becomes 5 (was 3)
 c) the overdraft floor percentage becomes 30 (was 25)
Nothing else changes.

-------- MEMO 2 / 19 March 2027 / Credit Risk (supersedes MEMO 1 where they differ) --------
Following pilot rehearsal:
 a) MEMO 1 item (a) is withdrawn. Callbacks run 10:00-17:30 inclusive. Same day / next working day, later than now, still apply.
 b) the wrong-answer limit is 4, not 5.
 c) the overdraft floor is 20 % (not 25, not 30), still rounded up to a whole krone.
 d) 15 April 2027 is added to the bank holidays (staff day).
MEMO 1 item (c) and everything in PR-22 not mentioned here are unchanged.

-------- CODE LIST (from the tool export, 17 March) --------
 old outcome      -> tool outcome
 PROMISE          -> promise.made      reason: none
 PAID             -> claimed.paid      reason: none
 TRANSFERRED      -> handed.over       reason: plan | person | care
 NO_PROMISE       -> no.promise        reason: refused | hardship | disputed | paid_claim | write_failed
 NOT_VERIFIED     -> unverified        reason: wrong_answers | declined
 NOT_REACHED      -> unreachable       reason: callback_set | callback_failed | wrong_person | deceased | unclear
 note reasons (add_note): refused | hardship | disputed | paid_claim | write_failed
 queues: plan desk = PLAN-DESK ; general desk = SERVICE-DESK ; care line = CARE-LINE
 product types: overdraft | consumer_loan | credit_line
 account fields: arrears_nok (overdraft only), amount_due (consumer_loan, credit_line), days_past_due, monthly_instalment (consumer_loan), min_due (credit_line), line_last4 (credit_line)
 identity fields: date_of_birth | national_id_last5 | home_town
 The tool API file wins on parameter spelling.
