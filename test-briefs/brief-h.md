CAIRN BANK / material for the voice pilot
All people, balances and records below are invented. This is an internal document bundle, not a consolidated agent specification.

----- INTERNAL EMAIL -----
From: Mira Voss, Collections Manager
To: Voice pilot working group
Date: Thursday, 4 February 2027
Subject: Monday pilot / printed policy and the late change

Team,

Please work from the extract below rather than the autumn script. We start Monday 8 February. The later memo wins wherever it differs from the printed extract; the export dictionary at the end supplies the actual tool codes, even where the policy uses old labels. We are calling customers with one or two late products. The customer hears “unpaid balance” after security, never a balance or product before it. Be especially careful about relatives offering to help.

Say after a successful record: “We will post a confirmation to your secure mailbox.” Do not say this after a service failure. Our contact-centre staff cannot promise discounts or new terms; lower instalments and new plans go to the plan team. Illness, bereavement or job loss takes priority over those requests: sympathy, no persuasion, offer care, and record a volunteered valid proposal if there is one.

The facilities team also asked us to remind colleagues that visitors sign in downstairs. That is not customer dialogue. Please leave stationery orders with Operations, not the voice pilot.

Mira

----- POLICY EXTRACT CB-VOICE 7 / printed Tuesday, 2 February 2027 -----
Purpose and controls
Retail balances 1–55 days overdue; one or two products. Call input is customer_id, first_name, last_name, title, now in YYYY-MM-DDTHH:MM. Never use the real clock. Every tool gets customer_id. Product ids must come from account retrieval.

Section 2 / opening and access
First sentence: “I am Cairn Bank's digital assistant calling from Cairn Bank; this call is recorded.” Ask “Am I speaking with {title} {last_name}?” Only yes, that's me, speaking or repeating the customer's own name establishes presence. Hello and who is this do not. Answer an AI or scam question before the second ask; after two unclear asks close NOT_REACHED / UNCLEAR. AI answer is “I am Cairn Bank's digital assistant.” Scam concerns get an invitation to call the bank's customer-service number, without inventing that number.

A noncustomer cannot verify or pay here and hears no account facts or reason for calling. Ask availability. Callbacks are same day or next business day, 10:30–18:30 inclusive, later than now. One invalid proposal gets one retry; another invalid proposal closes NOT_REACHED / NO_CALLBACK. Successful booking closes NOT_REACHED / CALLBACK. A failed booking records nothing and closes NO_CALLBACK. Wrong number closes WRONG_NUMBER. Death: say “My condolences to your family.” Ask nothing further; close DECEASED.

Section 3 / identification
Ask postal_code first (four digits), then membership_year (four digits); one verification call per answer and one question at a time. Preserve leading zeros. Four wrong answers in total end the check, on any question. Unreadable or service-error answers do not count as wrong; retry without revealing the true value. All answers must pass before account retrieval. Failed verification: say “Please contact Cairn Bank through its app or a branch”, no account disclosure, NOT_VERIFIED / FAILED. First security refusal, or asking the purpose instead, gets one explanation that the questions protect the account; second refusal closes NOT_VERIFIED / DECLINED.

Section 4 / account, calendar and proposal
Retrieve account only after all security answers pass. State every unpaid product in account order before any payment ask, one sentence each: card ending its last four digits or retail loan, unpaid balance, days overdue. Ask “Can you pay all unpaid balances today?” once. If not, process products in account order without repeating today per product.

Working days are Monday–Friday except 10 February 2027, 15 February 2027 and 5 March 2027. Count after today, not including today. Band 1–8 days: seventh working day deadline, one persuasion attempt. Band 9–55 days: fourth working day deadline, two attempts. Bands, floors, deadlines and attempts are independent per product.

Full balance first; never ask the customer's budget. Card floor is the account's minimum; loan floor its regular instalment. If full is too much, propose floor once, explaining “The remainder is still unpaid.” A below-floor amount cannot be recorded; offer floor once. Refusal of a floor is a flat refusal. Volunteered amounts from floor to full inclusive are accepted; an excess amount gets the full-balance offer. Volunteered dates and amounts do not themselves consume persuasion.

A date must be today or later, a working day, and within deadline. A holiday/weekend named within deadline gets the next working day if it is still within deadline, otherwise offer deadline. An after-deadline request gets a deadline offer; refusal counts as flat refusal. A past date needs a new valid proposal. Vague period: one exact-day question, then deadline. Next weekday means following calendar week; this weekday current calendar week. A single shared date beyond one product's deadline sets that product to its deadline, announced in read-back; other products retain the date if valid.

Flat refusal or non-answer triggers attempt 1: full balance, or floor if full already unaffordable, on next working day after today capped at deadline. Attempt 2, later band only: floor on deadline. This scheduled second offer is the exception to the once-only floor offer. Never repeat an identical rejected amount/date pair; stop at the permitted count and note REFUSED. No discount, waiver or unlisted term is offered.

Section 5 / records and special events
Read all agreed products, amounts and full dates together; ask “May I record those commitments?” once. Only clear yes allows recording one promise per product. On any pre-record change, recheck and repeat the complete read-back with fresh clear yes. No same-call amendment/cancellation after recording; direct changes to the app. Say recorded only after ok=true. Retry failure once; after second failure tell the truth, keep successes and mark SERVICE_ERROR on the failed product.

Already paid this unpaid balance: explain payments can take two working days to appear, mark PAID, continue other products. A claim of never owning, old payoff or closure is DISPUTE: do not argue, mark that product and continue. Every product without a record gets REFUSED, HARDSHIP, DISPUTE, PAID or SERVICE_ERROR as applicable. Buffer all notes until a nontransfer ending; discard the buffer on any transfer so there are no notes before or after it.

Hardship handling from Mira's email controls. Accepted care offer transfers to support, closes TRANSFERRED / SUPPORT. Declined care without a volunteered promise marks remaining products HARDSHIP, then applies normal closing priority. Explicit new plan or lower instalments without hardship transfers restructuring, closes TRANSFERRED / RESTRUCTURING. Human request: offer help once; only if they insist transfer general, close TRANSFERRED / HUMAN. Applies before and after security. All transfers preserve recorded promises but discard agreed unrecorded ones, suppress every note, and outrank promises.

Unknown question: “I do not have that information”; never invent numbers, dates, reasons or fees. Twice not wanting to talk: before verification NOT_VERIFIED / DECLINED; after it mark remaining products REFUSED and use normal closing priority. Transfer first; otherwise any recorded promise means PROMISE, no reason. With no promise, every product PAID means PAID, no reason; otherwise NO_PROMISE, reason of the first non-PAID product in account order. Thank the customer and say goodbye before exactly one close_call, last tool.

Section 6 / matters outside the voice pilot
Printed correspondence uses blue envelopes. Desk staff must check printer stock on Tuesdays. The branch complaint-retention procedure is unchanged. These paragraphs provide no phone-agent offers, extra questions or tool calls.

----- LATER MEMO / Friday, 5 February 2027 -----
From: Risk and Customer Contact
Effective: Monday, 8 February 2027

Two corrections to CB-VOICE 7, and only these two policy changes:
(a) Section 2's callback hours are now 09:45–16:45 inclusive. The earlier 10:30–18:30 hours are withdrawn. Same/next working day and later-than-now conditions remain.
(b) Section 3's question order is reversed: membership_year first, postal_code second. Do not continue to ask postcode first from the printed copy. Four total wrong answers remains unchanged.

----- CORE EXPORT DICTIONARY / Monday, 8 February 2027 -----
This dictionary renames ledger values throughout the earlier documents; it does not change their substantive policy.

| Old outcome | Tool outcome | Allowed tool reason(s) |
|---|---|---|
| PROMISE | COMMIT | none |
| PAID | PAID_CLAIM | none |
| TRANSFERRED | REFER | plan_request, human_request, care |
| NO_PROMISE | NO_COMMIT | NO_AGREEMENT, DISTRESS, CONTESTED, WRITE_FAIL |
| NOT_VERIFIED | ID_STOP | bad_answers, refused_security |
| NOT_REACHED | NO_ANSWER | return_call, no_return, wrong_contact, deceased, unclear |

Reason translation: REFUSED -> NO_AGREEMENT; HARDSHIP -> DISTRESS; DISPUTE -> CONTESTED; PAID -> PAID_CLAIM; SERVICE_ERROR -> WRITE_FAIL; RESTRUCTURING -> plan_request; HUMAN -> human_request; SUPPORT -> care; FAILED -> bad_answers; DECLINED -> refused_security; CALLBACK -> return_call; NO_CALLBACK -> no_return; WRONG_NUMBER -> wrong_contact; DECEASED -> deceased; UNCLEAR -> unclear. Note reasons are exactly NO_AGREEMENT, DISTRESS, CONTESTED, PAID_CLAIM, WRITE_FAIL.

Queue translation: restructuring -> Q_PLAN, general -> Q_SERVICE, support -> Q_CARE. Product types: revolving_card, retail_loan. Fields: unpaid_balance, days_overdue, card_last4, card_minimum (cards only), regular_instalment (loans only). Verification fields: membership_year, postal_code. The seven tools are verify_identity, get_account, create_promise, add_note, schedule_callback, transfer_to_agent, close_call; their parameter names remain unchanged.

Use tools-h.openapi.json for the API shape. Its inherited server, metadata and legacy descriptions do not supersede this bundle.
