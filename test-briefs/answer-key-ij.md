# Answer key: tricky practice briefs I and J (keep separate from the raw briefs)

## Brief I (Fjordvik Sparebank, NOK, up to 3 products)
Newest source wins. Final values after MEMO 2 (19 Mar): callback window 10:00-17:30 inclusive (printed 10:00-18:00, memo 1 09:00-17:00); wrong-answer limit 4 (printed 3, memo 1 5); overdraft floor 20 % of arrears_nok rounded UP to whole krone (printed 25, memo 1 30); holidays 2027-03-25, 03-26, 03-29, 04-15 (added by memo 2), 05-17.
Outcome table: promise.made, claimed.paid (no reason); handed.over (plan|person|care); no.promise (refused|hardship|disputed|paid_claim|write_failed); unverified (wrong_answers|declined); unreachable (callback_set|callback_failed|wrong_person|deceased|unclear). Queues PLAN-DESK, SERVICE-DESK, CARE-LINE.
Traps: overdraft amount lives in `arrears_nok` (others `amount_due`); three identity questions, home_town sent as lower-case ASCII; unapproved 3 % discount (never offered); canteen/parking text is noise.
From Mon 2027-03-22: working days after today 1=03-23, 2=03-24, 3=03-30, 4=03-31, 5=04-01. Late band (11-60 d) deadline 03-30, early (1-10 d) 04-01. From Mon 2027-04-12: 1=04-13, 2=04-14, 3=04-16, 4=04-19, 5=04-20.

## Brief J (Sakuraba Credit, JPY, 2 products)
Working week Mon-Sat; Sundays and 2027-04-29, 05-03, 05-04, 05-05 are not working days. Deadlines are CALENDAR based: today + 10 days (1-14 d overdue, 1 attempt) or + 6 days (15-90 d, 2 attempts), rolled BACK to the previous working day. From Tue 2027-04-27: early deadline Fri 05-07, late deadline Sat 05-01 (05-03 holiday, 05-02 Sunday).
Card floor = greater of minimum_due and 10 % of outstanding_jpy, rounded up to 100 yen; loan floor instalment_jpy. Whole yen only.
Callback: same day or either of the next TWO working days (Wed 04-28, Fri 04-30), 09:00-19:00 inclusive (memo B; memo A is retracted: attempts stay 2).
EVERY outcome carries a reason: PTP/RECORDED, PAID_CLAIMED/CUSTOMER_STATED, XFER/(RESTRUCTURE|AGENT|WELFARE), NO_PTP/(DECLINED_OFFER|HARDSHIP|DISPUTE|PAID|SYSTEM), NO_ID/(FAILED|REFUSED), NO_CONTACT/(CALLBACK|NO_CALLBACK|WRONG_PARTY|DECEASED|UNCLEAR). Queues Q-RESTRUCTURE, Q-GENERAL, Q-WELFARE. No title variable (family_name, given_name). Hint code year_two_digits.

## Brief K = brief I with a v2 tool API (renamed endpoints and parameters, amounts in ore, DD-MM-YYYY, HHMM). Generator-only check; the stand-in bank cannot serve it.
