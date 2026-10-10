# Spec contract (parser -> generator)

The builder runs in two stages:

```
brief files + tool API file --[parser]--> spec.json --[generator]--> workflow.json --> freya.save_workflow
```

`spec.json` is the only interface between the parser (`builder/parse/`) and the generator (`builder/generate/`).
Change this file only through the integration lead thread; both sides code against it.

Rules for the spec:
- Everything in it comes from the brief or the tool API file. Nothing brief-specific is hardcoded in parser or generator code.
- Values the generator turns into code (dates, numbers, tables) must be structured, not prose.
- Every rule that cannot be structured goes into `extra_rules` as a short sentence with its source rule number, so the generator can put it in a prompt. Nothing from the brief may be silently dropped.
- Unknown or missing fields are `null`, never guessed.

## Shape (with Brief A values as the example)

```jsonc
{
  "meta": {
    "bank_name": "Freya Bank",
    "language": "en",
    "multi_product": false,            // true when a customer can have several products (Brief B)
    "max_products": 1
  },

  "call_variables": [                  // known before any tool call
    {"name": "customer_id", "meaning": "pass to every tool call"},
    {"name": "first_name"}, {"name": "last_name"}, {"name": "title"},
    {"name": "now", "format": "YYYY-MM-DDTHH:MM", "meaning": "current date and time; use instead of real clock"}
  ],

  "opening": {
    "first_sentence_must_include": ["digital assistant", "calling from Freya Bank", "call is recorded"],
    "forbidden_words_before_verification": ["collections", "debt", "payment"],   // plus product names
    "forbid_product_name_before_verification": true,
    "confirm_identity_question": "Am I speaking with {title} {last_name}?",
    "accepted_confirmations": ["yes", "that's me", "speaking", "<customer's own name>"],
    "not_confirmations": ["hello", "go ahead", "who is this"],
    "max_confirmation_asks": 2,
    "on_unclear": {"outcome": "not_reached", "reason": "unclear"},
    "ai_question_answer": "I am Freya Bank's digital assistant."
  },

  "third_party": {
    "say_nothing_beyond_opening": true,
    "callback": {
      "allowed_days": "today_or_next_business_day",
      "window_start": "10:00", "window_end": "19:00", "inclusive": true,
      "must_be_after_now": true,
      "max_out_of_window_asks": 1,
      "on_scheduled": {"outcome": "not_reached", "reason": "callback"},
      "on_failed": {"outcome": "not_reached", "reason": "no_callback"}
    },
    "wrong_number": {"outcome": "not_reached", "reason": "wrong_number"},
    "deceased": {"say": "I am sorry for your loss.", "outcome": "not_reached", "reason": "deceased"},
    "relative_may_not_verify_or_pay": true
  },

  "identity": {
    "questions": [                     // asked in this order, one at a time
      {"field": "date_of_birth", "ask": "your date of birth", "format": "YYYY-MM-DD",
       "numeric_date_order": "DMY"},
      {"field": "phone_last4", "ask": "the last four digits of the phone number on file", "format": "4 digits"}
    ],
    "max_wrong_answers_total": 3,
    "hints": [{"hint": "day_month_swapped", "action": "ask month as a word", "counts_as_wrong": false}],
    "on_failed": {"say": "use the mobile app or a branch", "outcome": "not_verified", "reason": "failed"},
    "on_declined": {"explain_once": "the questions protect your account",
                    "max_refusals": 2, "outcome": "not_verified", "reason": "declined",
                    "asking_purpose_counts_as_refusal": true}
  },

  "debt_statement": {
    "after": "get_account",
    "say": "calling from the collections team about a late payment",
    "product_names": {"credit_card": "credit card ending {card_last4}",
                      "personal_loan": "personal loan", "car_loan": "car loan"},
    "include": ["past_due", "days_late"]
  },

  "calendar": {
    "business_days": ["Mon","Tue","Wed","Thu","Fri"],
    "holidays": ["2026-10-26","2026-11-11","2026-11-26","2026-12-25","2027-01-01"]
  },

  "bands": [                           // chosen by product days_late
    {"name": "early", "days_late_min": 1, "days_late_max": 7,
     "deadline": {"business_days_after_today": 12}, "persuasion_attempts": 1},
    {"name": "late",  "days_late_min": 8, "days_late_max": 45,
     "deadline": {"business_days_after_today": 7},  "persuasion_attempts": 2}
  ],

  "dates": {
    "promise_date_rule": "today_or_later AND business_day AND <= deadline",
    "non_business_day_before_deadline": "offer_next_business_day",
    "after_deadline": "offer_deadline; refusal of deadline = flat refusal",
    "vague_period": "ask_once_then_propose_deadline",
    "next_weekday_means": "following_calendar_week",
    "this_weekday_means": "current_week"
  },

  "amounts": {
    "first_ask": "full_past_due",
    "never_ask_customer_for_amount": true,
    "floor_field_by_product": {"credit_card": "minimum_payment",
                               "personal_loan": "instalment_amount", "car_loan": "instalment_amount"},
    "floor_offers": 1,
    "floor_note": "say the rest stays overdue",
    "accept_range": "floor <= amount <= past_due",
    "below_floor": "cannot record; offer floor once; refusal = flat refusal"
  },

  "persuasion": {
    "first_question": "Can you make this payment today?",
    "attempts": [                      // in order; band limits how many are used
      {"n": 1, "amount": "full_or_floor_if_full_refused", "date": "last_business_day_this_week_else_next_week"},
      {"n": 2, "amount": "floor", "date": "deadline"}
    ],
    "on_exhausted": {"outcome": "no_promise", "reason": "refused"}
  },

  "confirmation": {
    "readback": ["product", "amount", "date"],
    "confirm_question": "Do you confirm?",
    "one_promise_per_product": true,
    "change_after_record": "say they can change it in the mobile app",
    "create_promise_max_tries": 2,
    "on_create_failed": {"outcome": "no_promise", "reason": "service_error"},
    "after_recorded_say": "You will receive a text message confirming this promise."
  },

  "intents": [                         // things the customer may say, with the action
    {"id": "already_paid", "say": "payments can take one business day to appear",
     "action": {"close": {"outcome": "paid", "reason": null}}, "source": "39"},
    {"id": "dispute", "action": {"close": {"outcome": "no_promise", "reason": "dispute"}}, "source": "40"},
    {"id": "restructuring", "action": {"transfer": "restructuring",
     "close": {"outcome": "transferred", "reason": "restructuring"}}, "source": "41"},
    {"id": "human", "ask_once_first": true, "action": {"transfer": "general",
     "close": {"outcome": "transferred", "reason": "human"}}, "source": "42"},
    {"id": "hardship", "say": "one sentence of sympathy", "no_persuasion": true,
     "offer_transfer": "support",
     "on_accept": {"transfer": "support", "close": {"outcome": "transferred", "reason": "support"}},
     "on_decline": {"close": {"outcome": "no_promise", "reason": "hardship"}}, "source": "32"},
    {"id": "scam", "say": "verify by phoning Freya Bank's customer service number", "continue": true, "source": "43"},
    {"id": "unknown_question", "say": "I do not have that information", "continue": true, "source": "44"},
    {"id": "does_not_want_to_talk", "max": 2,
     "close_verified": {"outcome": "no_promise", "reason": "refused"},
     "close_unverified": {"outcome": "not_verified", "reason": "declined"}, "source": "45"}
  ],

  "multi_product": null,               // Brief B fills this:
  // {
  //   "state_all_products_first": true,
  //   "ask_all_today_first": true,
  //   "order": "get_account",
  //   "per_product_band_and_attempts": true,
  //   "single_date_after_deadline": "record that product on its own deadline, say so in readback",
  //   "single_confirmation_for_all": true,
  //   "note_tool": "add_note",
  //   "note_reasons": ["refused","hardship","dispute","paid","service_error"],
  //   "dispute_or_paid_continues": true,
  //   "no_notes_on_transfer": true,
  //   "closing_rule": "promise if any recorded (except restructuring transfer); all paid -> paid; else no_promise with reason of first non-paid note"
  // }

  "closing": {
    "goodbye_before_close": true,
    "close_tool": "close_call",
    "outcomes": [
      {"outcome": "promise", "reasons": []},
      {"outcome": "paid", "reasons": []},
      {"outcome": "transferred", "reasons": ["restructuring","human","support"]},
      {"outcome": "no_promise", "reasons": ["refused","hardship","dispute","service_error"]},
      {"outcome": "not_verified", "reasons": ["failed","declined"]},
      {"outcome": "not_reached", "reasons": ["callback","no_callback","wrong_number","deceased","unclear"]}
    ],
    "transfer_after_promise": "close as transferred with the transfer reason",
    "forbidden_offers": ["discount", "waiver", "instalment plan", "any term not in brief"]
  },

  "tools": {                           // copied from the tool API file, never from a brief
    "verify_identity": {"fields": {"field": {"enum": ["date_of_birth","phone_last4"]}, "answer": {}}},
    "get_account": {},
    "create_promise": {}, "add_note": {}, "schedule_callback": {},
    "transfer_to_agent": {"fields": {"queue": {"enum": ["restructuring","general","support"]}}},
    "close_call": {}
  },

  "extra_rules": [
    {"source": "4", "text": "If asked whether you are a robot or AI, say you are Freya Bank's digital assistant and continue."}
  ]
}
```

Final briefs change numbers, identity questions, the outcome table and the calendar, and may add or drop sections.
The parser must cope with fields missing (null) and with extra rules (into `extra_rules`); the generator must cope with any band count, any number of identity questions, and any outcome table.
