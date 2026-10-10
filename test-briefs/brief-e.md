# Brief E: Freya Bank, autumn changes (up to two products)

Freya Bank is fictional. Every customer, debt and payment here is synthetic.
(Our own practice brief, written like Brief B: a change list on top of Briefs A and B. Read both first. Every rule of Brief A and Brief B applies unless a rule below replaces it.)

## What changes

1. `get_account` returns one or two products. Brief B applies to them, with "three" read as "two".
2. Security questions: the first is still the date of birth. The second is the postcode of the registered address, four digits, instead of the last four digits of the phone number. Send it as four digits, with the field `postcode`.
3. Four wrong answers in total end the check, whichever question they were on. (Replaces "three" in Brief A rules 12 and 14.)
4. Callback window: today or the next business day, from 09:00 to 18:00, both included, and later than `now`. (Replaces Brief A rule 6.)
5. Business days stay Monday to Friday. The holidays are 2026-11-20, 2026-12-24, 2026-12-25, 2027-01-01 and 2027-01-04. (Replaces the list in Brief A section 7.)
6. The bands are:

| `days_late` | Band | Deadline | Persuasion attempts |
|---|---|---|---|
| 1 to 5 | early | the 10th business day after today | 1 |
| 6 to 30 | late | the 5th business day after today | 2 |
| 31 to 60 | severe | the 3rd business day after today | 2 |

   (Replaces the table in Brief A rule 18.) In the severe band attempt 1 and attempt 2 are as in the late band.
7. Brief A rule 38 is changed: after a recorded promise the agent says "You will receive a text message and an email confirming this promise."
8. Brief A rule 9 is unchanged except that the words said are "I am so sorry for your loss."
