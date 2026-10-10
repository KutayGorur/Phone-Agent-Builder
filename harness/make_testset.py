"""Generate our own unseen-style test material: tool API files and case files for the variant briefs C, D and E.

    python harness/make_testset.py [--server https://my-tunnel.example]

Writes into test-briefs/:
    tools-c.openapi.json  cases-c.json     (brief-c.md: clean spec, one product, renamed outcomes and fields)
    tools-d.openapi.json  cases-d.json     (brief-d.md: raw material, three products, coded outcomes)
    tools-e.openapi.json  cases-e.json     (brief-e.md: change list on top of A and B)

Every expected date is computed from the variant's own calendar below, not typed by hand. The case files have the
format of public-test-set.json, so tools/run_cases.py and tools/score.py read them (see harness/README.md for why the
mock bank needs a stand-in: harness/mock_bank.py).
"""
import argparse, copy, datetime as dt, json, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "test-briefs"
D = dt.date.fromisoformat
iso = lambda d: d.isoformat()


class Cal:
    def __init__(self, weekdays, holidays):
        self.wd, self.hol = set(weekdays), {D(h) for h in holidays}

    def is_bd(self, d): return d.weekday() in self.wd and d not in self.hol

    def nbd(self, today, n):
        """The n-th business day after today."""
        d = today
        while n:
            d += dt.timedelta(days=1)
            n -= self.is_bd(d)
        return d

    def next_bd(self, d):
        """The first business day strictly after d."""
        return self.nbd(d, 1)

    def last_bd_of_week(self, today):
        """Last business day of the Monday-to-Sunday week of today; if that is today, of the next week."""
        for monday in (today - dt.timedelta(days=today.weekday()), today - dt.timedelta(days=today.weekday()) + dt.timedelta(days=7)):
            days = [monday + dt.timedelta(days=k) for k in range(7)]
            last = max(d for d in days if self.is_bd(d))
            if last != today and last > today: return last
        raise ValueError


def case(cid, brief, family, level, title, who, identity, products, script, expected, checks, now, faults=None):
    c = {"id": cid, "brief": brief, "family": family, "level": level, "title": title,
         "variables": {**who, "now": now}, "identity": identity, "products": products, "script": script,
         "expected": {"outcome": None, "reason": None, "promises": [], "notes": [], "callbacks": [], "transfers": [], **expected},
         "checks": checks}
    if faults: c["faults"] = faults
    return c


P = lambda pid, amount, date: {"product_id": pid, "amount": float(amount), "date": iso(date) if not isinstance(date, str) else date}
N = lambda pid, reason: {"product_id": pid, "reason": reason}


# ---------------------------------------------------------------- tool API files
def make_api(server, verify_fields, verify_desc, hints, product_fields, types, note_reasons, queues, outcomes, close_desc):
    api = json.load(open(ROOT / "tools" / "openapi.json"))
    api = copy.deepcopy(api)
    if server: api["servers"] = [{"url": server.rstrip("/") + "/v1"}]
    paths = api["paths"]
    props = paths["/verify_identity"]["post"]["requestBody"]["content"]["application/json"]["schema"]["properties"]
    props["field"]["enum"] = verify_fields
    props["answer"]["description"] = verify_desc
    resp = paths["/verify_identity"]["post"]["responses"]["200"]["content"]["application/json"]["schema"]["properties"]
    resp["hint"]["enum"] = hints
    item = paths["/get_account"]["post"]["responses"]["200"]["content"]["application/json"]["schema"]["properties"]["products"]["items"]["properties"]
    old = dict(item)
    item.clear()
    for k, v in old.items():
        k2 = product_fields.get(k, k)
        if k2 is None: continue                      # field does not exist in this variant
        item[k2] = v
    item["type"]["enum"] = types
    if "minimum_due" in item: item["minimum_due"]["description"] = "the floor, every product type"
    paths["/add_note"]["post"]["requestBody"]["content"]["application/json"]["schema"]["properties"]["reason"]["enum"] = note_reasons
    paths["/transfer_to_agent"]["post"]["requestBody"]["content"]["application/json"]["schema"]["properties"]["queue"]["enum"] = queues
    cc = paths["/close_call"]["post"]["requestBody"]["content"]["application/json"]["schema"]["properties"]
    cc["outcome"]["enum"] = outcomes
    cc["reason"]["description"] = close_desc
    return api


# ---------------------------------------------------------------- Brief C (Nordhaven, one product)
def cases_c():
    cal = Cal(range(6), ["2026-10-31", "2026-11-02", "2026-12-24", "2026-12-25", "2026-12-26", "2027-01-01"])
    now, today = "2026-10-28T14:30", D("2026-10-28")            # a Wednesday
    dl = {"early": cal.nbd(today, 8), "middle": cal.nbd(today, 5), "late": cal.nbd(today, 3)}
    fri = cal.last_bd_of_week(today)                              # Saturday 31 Oct is a holiday, so Friday 30 Oct
    who = lambda f, l, t: {"first_name": f, "last_name": l, "title": t}
    card = lambda l4, due, days, floor: {"type": "card", "card_last4": l4, "amount_overdue": due, "days_overdue": days, "minimum_due": floor}
    cs = []
    cs.append(case("TC-01", "C", "Happy path", "easy", "Pays the full amount today", who("Karin", "Lund", "Ms"),
        {"date_of_birth": "1984-09-12", "postcode": "8200"}, [card("3318", 560.0, 4, 140.0)],
        "Confirms she is Karin Lund. Date of birth 12 September 1984, postcode 8200. Says she can pay the full amount today. Confirms at the read-back.",
        {"outcome": "promise", "promises": [P("p1", 560, today)]},
        ["both security questions passed before get_account", "the words 'overdue', 'card' and 'arrears' are not said before identity is verified", "create_promise called exactly once", "the email sentence is said after the promise (not the text-message sentence of Brief A)"], now))
    sat = D("2026-10-31")
    cs.append(case("TC-02", "C", "Dates", "hard", "Names a holiday Saturday, takes the floor", who("Jonas", "Berg", "Mr"),
        {"date_of_birth": "1979-02-27", "postcode": "5000"}, [{"type": "instalment_loan", "amount_overdue": 1240.0, "days_overdue": 18, "minimum_due": 310.0}],
        "Verified. Cannot pay today. When offered the full amount, says it is too much. Accepts the floor, but wants to pay it this Saturday. Accepts the next day offered.",
        {"outcome": "promise", "promises": [P("p1", 310, cal.next_bd(sat))]},
        ["the agent never asks how much he can pay", "the floor is offered once with the note that the rest stays overdue", "Saturday 31 October is refused as a holiday and Tuesday 3 November is offered", "promise for 310.00 on 3 November"], now))
    cs.append(case("TC-03", "C", "Identity", "medium", "Two wrong answers end the check", who("Mats", "Holm", "Mr"),
        {"date_of_birth": "1991-06-05", "postcode": "7100"}, [card("0912", 95.0, 4, 28.5)],
        "Confirms the name. First gives date of birth 5 July 1991, which is wrong. When asked again gives the right one, 5 June 1991. Then gives postcode 7001, which is wrong. Asks how much he owes.",
        {"outcome": "not_verified", "reason": "failed"},
        ["the check ends after the second wrong answer (not after three)", "no amount or product disclosed", "customer told to visit a branch"], now))
    cs.append(case("TC-04", "C", "Identity", "hard", "Numeric date of birth is month first", who("Elin", "Sand", "Ms"),
        {"date_of_birth": "1990-03-04", "postcode": "2300"}, [card("7745", 560.0, 4, 140.0)],
        "Confirms the name. When asked for the date of birth says it in digits only: 03/04/1990. Postcode 2300. Says she can pay the full amount tomorrow and confirms at the read-back.",
        {"outcome": "promise", "promises": [P("p1", 560, cal.next_bd(today))]},
        ["the first verify_identity call for the date of birth sends 1990-03-04 (month first, as the brief says)", "promise for 560.00 on 29 October"], now))
    cs.append(case("TC-05", "C", "Persuasion", "hard", "Late band uses all three attempts", who("Hugo", "Strand", "Mr"),
        {"date_of_birth": "1975-11-30", "postcode": "9000"}, [card("5521", 2000.0, 40, 500.0)],
        "Verified. Cannot pay today. Says no to the first offer (the full amount on Friday). Says no to the second offer (the minimum tomorrow). Accepts the third offer, the minimum on the last possible day.",
        {"outcome": "promise", "promises": [P("p1", 500, dl["late"])]},
        [f"attempt 1 offers the full 2000.00 on Friday {fri.day} October", "attempt 2 offers the floor 500.00 on 29 October", f"attempt 3 offers the floor on the deadline, {dl['late'].day} November", "no offer is repeated", "promise for 500.00 on 3 November"], now))
    cs.append(case("TC-06", "C", "Third party", "hard", "First callback time is outside the window, second is fine", who("Maria", "Vik", "Ms"),
        {"date_of_birth": "1982-08-19", "postcode": "3400"}, [card("1180", 310.5, 11, 93.0)],
        "The person who answers is her husband. Asks what the call is about. Says Maria can be reached tomorrow evening at 18:00. When asked for another time says Friday at ten in the morning.",
        {"outcome": "no_contact", "reason": "callback_set", "callbacks": [{"date": iso(cal.nbd(today, 2)), "time": "10:00"}]},
        ["the agent does not say why it is calling", "verify_identity and get_account never called", "the out-of-window time is answered with a request for another time, not with a booking", "callback booked for Friday 30 October at 10:00"], now))
    cs.append(case("TC-07", "C", "Hardship", "medium", "Job loss, accepts the care team", who("Axel", "Dahl", "Mr"),
        {"date_of_birth": "1986-01-23", "postcode": "6100"}, [{"type": "vehicle_finance", "amount_overdue": 780.0, "days_overdue": 22, "minimum_due": 260.0}],
        "Verified. Says he lost his job last month. Accepts when offered the care team. Names no date and no amount.",
        {"outcome": "handover", "reason": "care", "transfers": [{"queue": "care"}]},
        ["one short sentence of sympathy and no persuasion attempt", "transfer queue is care", "no promise requested"], now))
    cs.append(case("TC-08", "C", "Already paid", "medium", "Says the payment was made yesterday", who("Sara", "Nygaard", "Ms"),
        {"date_of_birth": "1993-04-02", "postcode": "4500"}, [card("2290", 305.0, 9, 91.5)],
        "Verified. Says she paid the overdue amount yesterday by bank transfer. Does not want to make another promise.",
        {"outcome": "settled"},
        ["agent says payments can take one business day to appear", "no promise is taken", "close outcome is settled with no reason"], now))
    return cs


def api_c(server):
    return make_api(server, ["date_of_birth", "postcode"],
        "For date_of_birth: the date as YYYY-MM-DD. An unreadable value is rejected with ok=false and is not counted as a wrong answer. For postcode: four digits.",
        ["day_month_swapped", "year_two_digits"],
        {"past_due": "amount_overdue", "days_late": "days_overdue", "minimum_payment": "minimum_due", "instalment_amount": None},
        ["card", "instalment_loan", "vehicle_finance"],
        ["refused", "hardship", "disputed", "paid", "service_error"], ["plan", "agents", "care"],
        ["promise", "settled", "handover", "no_promise", "not_verified", "no_contact"],
        "Required for every outcome except promise and settled. See the table in the brief.")


# ---------------------------------------------------------------- Brief D (Alpenbank, raw material, three products)
def cases_d():
    cal = Cal(range(5), ["2026-11-23", "2026-12-08", "2026-12-24", "2026-12-25", "2027-01-01"])   # the memo removed 31 Dec and added 23 Nov
    now, today = "2026-11-18T09:40", D("2026-11-18")            # a Wednesday
    early, late = cal.nbd(today, 10), cal.nbd(today, 5)
    who = lambda f, l, t: {"first_name": f, "last_name": l, "title": t}
    card = lambda l4, due, days, floor: {"type": "credit_card", "card_last4": l4, "arrears": due, "days_past_due": days, "minimum_payment": floor}
    loan = lambda due, days, inst: {"type": "consumer_loan", "arrears": due, "days_past_due": days, "monthly_instalment": inst}
    od = lambda due, days: {"type": "overdraft", "arrears": due, "days_past_due": days}
    ident = lambda y, d: {"account_open_year": y, "date_of_birth": d}
    cs = []
    d25 = D("2026-11-25")
    cs.append(case("TD-01", "D", "Multi-product", "medium", "Three products, one date inside every deadline", who("Sofia", "Meier", "Ms"),
        ident("2011", "1987-06-03"), [card("2288", 300.0, 5, 90.0), loan(800.0, 12, 270.0), od(400.0, 30)],
        "Verified. Cannot pay everything today. Agrees to pay all three in full on Wednesday 25 November. Confirms once.",
        {"outcome": "PTP", "promises": [P("p1", 300, d25), P("p2", 800, d25), P("p3", 400, d25)]},
        ["all three products stated before any ask", "the word 'debt' and the word 'collections' are never said", "one read-back and one confirmation for all three", "one create_promise per product", "the post and email sentence is said after the promises"], now))
    cs.append(case("TD-02", "D", "Multi-product", "hard", "One date for all, two deadlines are earlier", who("Lukas", "Frei", "Mr"),
        ident("2008", "1982-03-21"), [card("4410", 300.0, 5, 90.0), loan(800.0, 12, 270.0), od(400.0, 30)],
        "Verified. Cannot pay today. Wants to pay everything in full on 1 December. Accepts when told two products have an earlier latest date.",
        {"outcome": "PTP", "promises": [P("p1", 300, D("2026-12-01")), P("p2", 800, late), P("p3", 400, late)]},
        [f"the card (early band, deadline {early.day} December) is recorded on 1 December", f"the loan and the overdraft (10 to 60 days, deadline {late.day} November) are recorded on 26 November", "the read-back names the changed dates"], now))
    tue = D("2026-11-24")
    cs.append(case("TD-03", "D", "Amounts", "hard", "Overdraft floor is 25 percent", who("Nina", "Roth", "Ms"),
        ident("2015", "1986-05-17"), [card("1903", 300.0, 3, 90.0), od(480.0, 20)],
        "Verified. Says she can pay the card in full today but not the overdraft. For the overdraft says the full amount is too much and accepts the minimum, on Tuesday next week.",
        {"outcome": "PTP", "promises": [P("p1", 300, today), P("p2", 120, tue)]},
        ["the agent works out the overdraft floor as 120.00 (25 percent of 480.00)", "the agent never asks how much she can pay", "promises: card 300.00 today, overdraft 120.00 on 24 November"], now))
    cs.append(case("TD-04", "D", "Multi-product", "hard", "Disputes one loan, pays the card", who("Pascal", "Gerber", "Mr"),
        ident("2004", "1975-10-08"), [loan(900.0, 14, 300.0), card("7740", 250.0, 6, 75.0)],
        "Verified. Says he never took out the loan. Does not argue. Agrees to pay the card in full this Friday.",
        {"outcome": "PTP", "promises": [P("p2", 250, D("2026-11-20"))], "notes": [N("p1", "DISPUTE")]},
        ["the dispute on the loan does not end the call", "note DISPUTE for p1 only", "promise for the card on Friday 20 November", "no promise offered for the loan"], now))
    cs.append(case("TD-05", "D", "Persuasion", "hard", "Refuses both products", who("Rita", "Baumann", "Ms"),
        ident("2012", "1990-12-01"), [card("9063", 500.0, 8, 150.0), od(800.0, 25)],
        "Verified. Says no to everything for both products. Says she cannot and will not pay anything this month. Names no date and no amount. Does not mention hardship or a dispute.",
        {"outcome": "NOPTP", "reason": "REFUSED", "notes": [N("p1", "REFUSED"), N("p2", "REFUSED")]},
        ["early product gets one attempt (full amount on the last working day of the week, Friday 20 November)", "late product gets two attempts, the second one the floor 200.00 on the deadline", "no offer is repeated", "note REFUSED for each product", "close NOPTP / REFUSED"], now))
    cs.append(case("TD-06", "D", "Third party", "easy", "Wrong number", who("Beat", "Keller", "Mr"),
        ident("2010", "1978-09-09"), [card("3321", 220.0, 4, 66.0)],
        "The person who answers says Beat Keller does not live here and this is not his number.",
        {"outcome": "NOREACH", "reason": "WRONGNO"},
        ["the agent says nothing about the reason for the call", "verify_identity and get_account never called"], now))
    cs.append(case("TD-07", "D", "Third party", "hard", "Callback at 09:30, the memo's window", who("Erika", "Vogel", "Ms"),
        ident("2014", "1984-07-14"), [card("5512", 410.0, 7, 123.0)],
        "The person who answers is her husband. Says she can be called back today at half past six in the evening. When asked for another time says tomorrow at half past nine in the morning.",
        {"outcome": "NOREACH", "reason": "CALLBK", "callbacks": [{"date": "2026-11-19", "time": "09:30"}]},
        ["18:30 is refused as outside the window and another time is asked once", "09:30 is accepted (window starts at 09:30 after the memo)", "callback booked for 19 November at 09:30"], now))
    cs.append(case("TD-08", "D", "Dates", "hard", "'Next Friday' is after the deadline", who("Thomas", "Egger", "Mr"),
        ident("2009", "1975-11-07"), [card("6618", 640.0, 22, 160.0)],
        "Confirms the name. Gives the account opening year, then the date of birth in digits only: 07/11/1975. Cannot pay today. Wants to pay the full amount next Friday. Accepts the latest possible date when told.",
        {"outcome": "PTP", "promises": [P("p1", 640, late)]},
        ["the date of birth is sent as 1975-11-07 (day first)", f"'next Friday' is 27 November, one day after the deadline of {late.day} November", "the agent offers 26 November and says it is the latest date", "promise 640.00 on 26 November"], now))
    cs.append(case("TD-09", "D", "Tool failure", "hard", "Recording the first promise fails twice", who("Anja", "Huber", "Ms"),
        ident("2013", "1989-02-23"), [card("7741", 200.0, 4, 60.0), loan(600.0, 16, 200.0)],
        "Verified. Cannot pay today. Agrees to pay both in full tomorrow and confirms.",
        {"outcome": "PTP", "promises": [P("p2", 600, cal.next_bd(today))], "notes": [N("p1", "SVCERR")]},
        ["the agent tries the failed promise once more", "the agent does not say it is recorded for the card", "note SVCERR for p1", "the agent tells the customer the card promise could not be recorded and the loan promise was"], now,
        faults=[{"tool": "create_promise", "fail_first_n": 2}]))
    cs.append(case("TD-10", "D", "Restructuring", "medium", "Asks for a payment holiday", who("Marco", "Studer", "Mr"),
        ident("2007", "1981-04-30"), [card("8830", 350.0, 10, 105.0)],
        "Verified. Asks whether he can have a payment holiday for three months because money is tight. Does not name a date or an amount.",
        {"outcome": "XFER", "reason": "RESTR", "transfers": [{"queue": "Q_RESTR"}]},
        ["no plan or holiday is described or promised", "transfer to Q_RESTR", "no notes at all", "close XFER / RESTR"], now))
    cs.append(case("TD-11", "D", "Opening", "medium", "'Speaking' alone is not an acknowledgement", who("Laura", "Zimmermann", "Ms"),
        ident("2016", "1992-08-25"), [card("2147", 180.0, 3, 54.0)],
        "Answers the phone with 'Speaking.' to the first question. When asked again says 'Yes, that's me.' Then verified. Pays the full amount today and confirms.",
        {"outcome": "PTP", "promises": [P("p1", 180, today)]},
        ["the agent asks the identity-confirmation question a second time after 'Speaking.'", "no security question is asked before the second answer", "promise 180.00 today"], now))
    return cs


def api_d(server):
    return make_api(server, ["account_open_year", "date_of_birth"],
        "For date_of_birth: the date as YYYY-MM-DD. An unreadable value is rejected with ok=false and is not counted as a wrong answer. For account_open_year: four digits.",
        ["day_month_swapped"],
        {"past_due": "arrears", "days_late": "days_past_due", "instalment_amount": "monthly_instalment"},
        ["credit_card", "consumer_loan", "overdraft"],
        ["REFUSED", "HARDSHIP", "DISPUTE", "PAID", "SVCERR"], ["Q_RESTR", "Q_GENERAL", "Q_SUPPORT"],
        ["PTP", "PAID", "XFER", "NOPTP", "NOVER", "NOREACH"],
        "Required for every outcome except PTP and PAID. See the code list in the brief.")


# ---------------------------------------------------------------- Brief E (change list on top of A and B)
def cases_e():
    cal = Cal(range(5), ["2026-11-20", "2026-12-24", "2026-12-25", "2027-01-01", "2027-01-04"])
    now, today = "2026-11-17T10:15", D("2026-11-17")            # a Tuesday
    early, late, severe = cal.nbd(today, 10), cal.nbd(today, 5), cal.nbd(today, 3)
    who = lambda f, l, t: {"first_name": f, "last_name": l, "title": t}
    card = lambda l4, due, days, floor: {"type": "credit_card", "card_last4": l4, "past_due": due, "days_late": days, "minimum_payment": floor}
    loan = lambda due, days, inst: {"type": "personal_loan", "past_due": due, "days_late": days, "instalment_amount": inst}
    ident = lambda d, p: {"date_of_birth": d, "postcode": p}
    cs = []
    mon = cal.next_bd(D("2026-11-20"))
    cs.append(case("TE-01", "E", "Multi-product", "medium", "Names a holiday Friday for both", who("Elena", "Costa", "Ms"),
        ident("1991-01-08", "6604"), [card("6604", 300.0, 3, 90.0), loan(900.0, 12, 300.0)],
        "Verified. Cannot pay today. Wants to pay both on Friday. Accepts the day offered instead.",
        {"outcome": "promise", "promises": [P("p1", 300, mon), P("p2", 900, mon)]},
        ["Friday 20 November is refused as a holiday and Monday 23 November is offered for both", "one read-back, one confirmation", "the text-message-and-email sentence of Brief E is said after the promises"], now))
    cs.append(case("TE-02", "E", "Multi-product", "hard", "One date for both, the loan deadline is earlier", who("Daniel", "Ruiz", "Mr"),
        ident("1988-03-14", "1120"), [card("4471", 300.0, 3, 90.0), loan(900.0, 12, 300.0)],
        "Verified. Cannot pay today. Wants to pay both on 1 December. Accepts when told the loan has an earlier latest date.",
        {"outcome": "promise", "promises": [P("p1", 300, D("2026-12-01")), P("p2", 900, late)]},
        [f"card recorded on 1 December (early band, deadline {early.day} December)", f"loan recorded on its own deadline, {late.day} November", "the read-back names both dates"], now))
    cs.append(case("TE-03", "E", "Dates", "hard", "Severe band, asks for a date past the deadline", who("Priya", "Shah", "Ms"),
        ident("1986-05-17", "3000"), [loan(1500.0, 40, 500.0)],
        "Verified. Cannot pay today. Wants to pay the full amount on 27 November. Accepts the latest possible date when told.",
        {"outcome": "promise", "promises": [P("p1", 1500, severe)]},
        [f"deadline is the 3rd business day, {severe.day} November (the 20th is a holiday)", "agent offers 23 November as the latest date", "promise 1500.00 on 23 November"], now))
    cs.append(case("TE-04", "E", "Multi-product", "hard", "Disputes the card, pays the loan today", who("Owen", "Lee", "Mr"),
        ident("1992-07-21", "8800"), [card("0377", 200.0, 4, 60.0), loan(500.0, 7, 170.0)],
        "Verified. Says the card is not his and he never had it. Does not argue. Agrees to pay the loan in full today.",
        {"outcome": "promise", "promises": [P("p2", 500, today)], "notes": [N("p1", "dispute")]},
        ["the dispute does not end the call", "note dispute for p1", "promise for the loan today"], now))
    cs.append(case("TE-05", "E", "Identity", "hard", "Three wrong answers do not end the check, four do", who("Tim", "Weber", "Mr"),
        ident("1980-05-15", "4100"), [card("5519", 95.0, 4, 28.5)],
        "Confirms the name. Gives date of birth 12 May 1980, then when asked again 13 May 1980, then 14 May 1980, all wrong. Then says 15 May 1980, which is right. Then gives postcode 4200, which is wrong.",
        {"outcome": "not_verified", "reason": "failed"},
        ["the agent asks again after the third wrong answer", "the check ends after the fourth wrong answer", "no amount or product disclosed"], now))
    cs.append(case("TE-06", "E", "Restructuring", "medium", "Asks for lower instalments", who("Hana", "Novak", "Ms"),
        ident("1983-09-30", "5500"), [loan(700.0, 9, 233.0)],
        "Verified. Asks whether the instalments can be made lower. Names no date and no amount.",
        {"outcome": "transferred", "reason": "restructuring", "transfers": [{"queue": "restructuring"}]},
        ["no plan described", "no notes at all", "close transferred / restructuring"], now))
    cs.append(case("TE-07", "E", "Tool failure", "hard", "The first product's promise fails twice", who("Ivan", "Petrov", "Mr"),
        ident("1985-02-02", "7700"), [card("1234", 200.0, 4, 60.0), loan(600.0, 16, 200.0)],
        "Verified. Cannot pay today. Agrees to pay both in full on Thursday and confirms once.",
        {"outcome": "promise", "promises": [P("p2", 600, D("2026-11-19"))], "notes": [N("p1", "service_error")]},
        ["the agent tries the failed promise once more", "never says the card promise is recorded", "note service_error for p1"], now,
        faults=[{"tool": "create_promise", "fail_first_n": 2}]))
    cs.append(case("TE-08", "E", "Third party", "medium", "Callback at 09:00 tomorrow, the new window", who("Maria", "Santos", "Ms"),
        ident("1979-11-02", "2200"), [loan(310.5, 11, 103.5)],
        "The person who answers is her sister. Says Maria can be called tomorrow at nine in the morning.",
        {"outcome": "not_reached", "reason": "callback", "callbacks": [{"date": "2026-11-18", "time": "09:00"}]},
        ["the agent does not say why it is calling", "09:00 is accepted (window starts at 09:00 in Brief E)", "callback booked for 18 November at 09:00"], now))
    cs.append(case("TE-09", "E", "Third party", "easy", "The customer has died", who("Karl", "Beck", "Mr"),
        ident("1950-01-01", "1000"), [card("3300", 150.0, 5, 45.0)],
        "The person who answers says Mr Beck passed away in the summer.",
        {"outcome": "not_reached", "reason": "deceased"},
        ["the agent says 'I am so sorry for your loss.' and asks nothing else", "no identity tools called"], now))
    return cs


def api_e(server):
    return make_api(server, ["date_of_birth", "postcode"],
        "For date_of_birth: the date as YYYY-MM-DD. Callers say dates in words, the agent converts. An unreadable value is rejected with ok=false and is not counted as a wrong answer. For postcode: four digits.",
        ["day_month_swapped"], {}, ["credit_card", "personal_loan", "car_loan"],
        ["refused", "hardship", "dispute", "paid", "service_error"], ["restructuring", "general", "support"],
        ["promise", "paid", "transferred", "no_promise", "not_verified", "not_reached"],
        "Required for every outcome except promise and paid. See the table in the brief.")


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--server", help="base URL of a bank that answers the seven tool calls (default: the organisers' mock)")
    a = ap.parse_args()
    OUT.mkdir(exist_ok=True)
    for tag, cf, af in (("c", cases_c, api_c), ("d", cases_d, api_d), ("e", cases_e, api_e)):
        cs = cf()
        for c in cs: c["bank"] = {"max_wrong": {"c": 2, "d": 3, "e": 4}[tag]}      # wrong answers that end the check, read by harness/mock_bank.py
        json.dump(cs, open(OUT / f"cases-{tag}.json", "w"), indent=1)
        json.dump(af(a.server), open(OUT / f"tools-{tag}.openapi.json", "w"), indent=1)
        print(tag, len(cs), "cases")


if __name__ == "__main__": main()
