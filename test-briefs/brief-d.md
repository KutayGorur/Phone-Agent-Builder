Alpenbank AG is fictional. Every customer, debt and payment in this file is synthetic.
(Our own practice material in the style of raw bank documents: a mail, a policy extract, an amending memo and a code list. Four documents, pasted one after another.)

=====================================================================
DOCUMENT 1 of 4: MAIL
=====================================================================

From: Regula Brunner, Head of Early Collections
To: Voice project team
Subject: Re: Re: phone agent for the early arrears campaign - what you need from us
Date: Mon, 9 Nov 2026

Hi all,

thanks for the call on Friday. As promised, the attached policy extract (Document 2) is what the human agents work to today. Please do not build anything from the old script, it is out of date. Document 3 is the memo that Legal sent round after the extract was printed. Where the memo and the extract disagree, the memo wins. Document 4 is the list of codes that our ledger uses, so the phone agent can write to it.

A few things that are not in the extract and that I care about:

- On the phone we say "overdue amount". We never say "debt" and we never say "collections" to a customer. Only the word "arrears" is allowed, and only after the customer is identified.
- Never say the product name, the amount or why we call before the customer is identified. Not to a spouse either, however nice they are.
- After a promise has been recorded, the agent says: "We will send you a confirmation by post and by email." Nothing else is promised.
- Our customers can have up to three products with us that are overdue at the same time. The extract talks about "the product" in places, but the rules apply per product.
- The agent does not discuss fees, interest or settlements. If asked, it says it does not have that information.
- Be kind. If somebody tells you they lost their job or are ill, we do not push.

Kind regards,
Regula

PS. Last quarter we had too many calls that ended with the agent promising something we cannot do. If a customer asks for a payment holiday, a lower rate, or a new plan, that is a restructuring request and goes to the restructuring queue. No discussion.

=====================================================================
DOCUMENT 2 of 4: POLICY EXTRACT "EARLY ARREARS - OUTBOUND VOICE", version 4.1 (printed 28 Oct 2026)
=====================================================================

1. SCOPE
1.1 Outbound calls to retail customers with one to three products in arrears of 1 to 60 days.
1.2 The caller is Alpenbank's automated assistant.

2. OPENING
2.1 The first sentence says that the caller is Alpenbank's automated assistant and that the call is recorded.
2.2 Then ask: "Am I speaking with {first_name} {last_name}?" (use the full name, no title).
2.3 A clear yes, "speaking", or the customer repeating their own name is an acknowledgement. Anything else ("hello", "who's this", "what is it about") is not. If no acknowledgement after two asks, end the call with code NOREACH / UNCLEAR.
2.4 A customer who asks whether they are talking to a machine gets the answer "I am Alpenbank's automated assistant" and the call continues.

3. THIRD PARTIES
3.1 Anybody who is not the customer is told nothing beyond the sentence in 2.1.
3.2 Ask when the customer can be reached. A call back is possible on the same day or the next working day, between 10:00 and 19:00 inclusive, and must be later than the current time. Record it with the callback tool and end the call with NOREACH / CALLBK.
3.3 If the time named is outside the window, ask once more. If it is outside again, record nothing and end with NOREACH / NOCALL.
3.4 "Wrong number" ends the call with NOREACH / WRONGNO. A death ends the call with the words "I am very sorry" and NOREACH / DECEASED, no further questions.
3.5 Family members cannot be given any information and cannot pay on the customer's behalf through this channel.

4. IDENTIFICATION
4.1 Two questions, one at a time, in this order: (1) the year the account was opened, (2) the date of birth. Both are checked with the verification tool.
4.2 Dates are written YYYY-MM-DD in the tool. A date spoken only in numbers is read day first, then month, then year (European order).
4.3 Three wrong answers in total (any question) end the check. A hint from the tool that the day and the month are swapped is not a wrong answer: ask the customer to name the month.
4.4 After a failed check say nothing about the account. Tell the customer to call the number on their card or visit a branch. End with NOVER / FAILED.
4.5 A customer who refuses the questions gets one explanation (the questions protect the account). A second refusal, or asking what the call is about instead of answering, ends the call with NOVER / DECLINED.

5. THE ARREARS STATEMENT
5.1 After both answers are correct, retrieve the account. Before asking for anything, say for every overdue product, one short sentence each: the product in words ("Alpencard ending 1234", "consumer loan", "overdraft"), the overdue amount and the number of days.

6. TIME LIMITS FOR A PROMISE (see Document 3, which replaces table 6.2)
6.1 A promise date must not be in the past, must be a working day and must not be later than the deadline of that product.
6.2 [REPLACED BY THE MEMO]
    days past due 1-14: deadline = 10th working day after today; one persuasion attempt.
    days past due 15-60: deadline = 6th working day after today; two persuasion attempts.
6.3 Working days are Monday to Friday except the bank holidays 2026-12-08, 2026-12-24, 2026-12-25, 2026-12-31 and 2027-01-01.
6.4 A weekend day or a bank holiday named by the customer: if it is not later than the deadline offer the next working day. If it is later, treat it as in 6.6.
6.5 Vague answers ("soon", "next month", "when I get paid"): ask once for the exact day, then propose the deadline.
6.6 If the customer wants a date after the deadline, tell them the latest date that can be recorded and offer it. If they decline, that is a flat refusal.
6.7 "Next Monday" etc. is that weekday in the following calendar week; "this Friday" is the Friday of the current week.

7. AMOUNTS
7.1 Always propose the full overdue amount of the product first. The agent never asks how much the customer could pay.
7.2 Minimum amount ("floor"): credit card: the minimum payment shown on the account. Consumer loan: the monthly instalment shown on the account. Overdraft: there is no figure on the account; the floor is 25 % of the overdue amount (no rounding needed, all overdue amounts are multiples of 4).
7.3 If the customer says the full amount is too much, offer the floor once and say that the remainder stays overdue. A customer who proposes an amount between the floor and the full amount (both inclusive) gets it. Below the floor: say it cannot be recorded, offer the floor once. If the floor is declined, that is a flat refusal.
7.4 Offering anything else (discount, waiver, plan, holiday) is forbidden.

8. SEVERAL PRODUCTS
8.1 First ask whether the customer can pay everything today. If not, go through the products one at a time in the order of the account response, without asking about today again.
8.2 Bands, deadlines and persuasion attempts are per product and start from zero for each product.
8.3 If the customer gives a single date for all products and it is later than the deadline of one of them, that product gets its own deadline and the agent says so when reading back. The other products keep the customer's date.
8.4 Read all the promises back together, ask "Is that correct?" once, and only after a clear yes record one promise per product.
8.5 If a product has no promise at the end, add a note for it using the note tool: REFUSED, HARDSHIP, DISPUTE, PAID or SVCERR (see Document 4). A dispute or "I have already paid" for one product does not end the call; carry on with the other products.
8.6 If recording a promise fails, try once more. If it fails again, keep what is recorded, add the note SVCERR for the failed product, and continue.

9. GETTING A PROMISE
9.1 A flat refusal, a "no" to today without a date or an amount, or a non-answer uses up one persuasion attempt for the current product.
9.2 First attempt: offer the full amount tomorrow (the next working day after today). Second attempt (where allowed): offer the floor on the deadline.
9.3 When the attempts are used, stop, make no offer again, and go to the next product. The product gets the note REFUSED.
9.4 Illness, a death in the family or loss of a job: one sentence of sympathy, no persuasion attempt, offer a transfer to the support team. If accepted: transfer to the support queue and end with XFER / SUPP. If declined: the products without a promise get the note HARDSHIP and the call ends with NOPTP / HARDSHIP (unless a promise exists). A date or an amount that the customer names themselves is still recorded.
9.5 "Already paid" (for this overdue amount): say that payments can take one working day to be visible, take no promise for that product, note PAID.
9.6 "It is not mine" / "I never had this": do not argue, no promise for that product, note DISPUTE.
9.7 Restructuring (new plan, lower instalments, payment holiday, lower rate): transfer to the restructuring queue. Promises recorded earlier stay; promises agreed but not yet recorded are dropped. No notes on a transfer, before or after. End with XFER / RESTR.
9.8 A request for a person: ask once whether you can help. If the customer insists, transfer to the general queue, no notes, end with XFER / HUMAN.

10. ENDING THE CALL
10.1 The call ends with exactly one end-call entry, as the last tool call, after saying goodbye.
10.2 At least one promise recorded: PTP (unless 9.7 or 9.4 applies and a transfer happened: then XFER with that reason).
10.3 No promise: if every product is noted PAID, end with PAID. Otherwise NOPTP with the reason of the first product (account order) whose note is not PAID.
10.4 If the customer says twice that they do not want to talk: NOPTP / REFUSED, or before identification NOVER / DECLINED.

=====================================================================
DOCUMENT 3 of 4: MEMO "Changes to the early arrears voice policy" (Legal & Collections), 2 Nov 2026
=====================================================================

To: all early collections teams
Re: Policy extract v4.1 - amendments with effect from 9 November 2026

Following the review on 30 October the following points change. Everything else in v4.1 stays as printed.

(a) Table 6.2 is replaced by:
      1 to 9 days past due: deadline = 10th working day after today; one persuasion attempt.
      10 to 60 days past due: deadline = 5th working day after today; two persuasion attempts.
(b) Section 3.2: the call-back window is 09:30 to 18:00, both inclusive. Same day or next working day, later than the current time, as before.
(c) Section 6.3: 2026-11-23 is a bank holiday (cantonal election day). 2026-12-31 is NOT a bank holiday any more; branches are open.
(d) Section 9.2: the first attempt is changed from "tomorrow" to the end of the current week: offer the full amount on the last working day of this week; if today is that day, on the last working day of next week. The second attempt is unchanged.
(e) Section 4.3: the check ends after three wrong answers in total as before, but a wrong answer given to the question about the account opening year counts the same as a wrong date of birth. No change to the hint rule.
(f) Section 2.3: "speaking" no longer counts as an acknowledgement on its own, because customers say it when they answer the phone. Only a clear yes, "that's me" or the customer repeating their own name counts.

Legal & Collections

=====================================================================
DOCUMENT 4 of 4: CODE LIST (ledger codes, Alpenbank core banking export)
=====================================================================

END-CALL OUTCOME CODES                     
  PTP      promise to pay recorded         (reason: none)
  PAID     customer says it is paid        (reason: none)
  XFER     call handed to a person         (reasons: RESTR, HUMAN, SUPP)
  NOPTP    contact made, no promise        (reasons: REFUSED, HARDSHIP, DISPUTE, SVCERR)
  NOVER    identity not established        (reasons: FAILED, DECLINED)
  NOREACH  customer not reached            (reasons: CALLBK, NOCALL, WRONGNO, DECEASED, UNCLEAR)

NOTE REASON CODES (note tool): REFUSED, HARDSHIP, DISPUTE, PAID, SVCERR

TRANSFER QUEUE CODES: Q_RESTR (restructuring), Q_GENERAL (a person), Q_SUPPORT (support team)

PRODUCT TYPE CODES (account response): credit_card, consumer_loan, overdraft
  Fields: arrears (overdue amount), days_past_due, minimum_payment (cards only), monthly_instalment (consumer loans only), card_last4 (cards only)

VERIFICATION FIELD CODES: account_open_year (4 digits), date_of_birth (YYYY-MM-DD)

CALL VARIABLES: customer_id, first_name, last_name, title, now (YYYY-MM-DDTHH:MM, use instead of the real clock)
