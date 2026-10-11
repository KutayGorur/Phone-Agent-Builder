# Offline review: scam answers and exact terminal speech

Reviewed 2026-10-11 against main dc6a46e and proposed PR #9 commit 0411ebe. No Freya calls, speech-model calls, workflow writes, or application-code changes were made in this review.

## Verdict

Claude correctly identified a real problem: the fixed-TTS path on main speaks instruction-style scam answers literally. The golden H spec and fresh I/J specs contain these instructions. PR #9 avoids reading them literally by returning those replies to the speaking model. Its state handling looks sound in the isolated checks below, but it does not establish the same deterministic speech guarantee as the main hardship fix. I recommend revising the proposal before bringing it onto main.

This is a correctness/accuracy review, not a cybersecurity finding.

## Evidence and scope

Ran 30 isolated engine scenarios: main and PR #9, five answer wordings, three conversation states. The answer wordings came from A, H, I and J, plus a valid customer-facing sentence variant. To isolate wording, all used the A policy and the same account; this is not a full H/I/J workflow test.

The states were:

1. Initial hardship plus a scam question: support remains pending.
2. Declined support plus a scam question: close remains no_promise/hardship; the next ordinary response closes.
3. Customer volunteers 300 tomorrow after hardship, declines support, then asks whether the call is genuine during confirmation: the amount/date remain 300 and 2026-10-15, and subsequent agreement selects create on those terms.

All 30 state/record assertions passed. The test supplies extraction variables and executes the actual engine text; it does not run extraction or speech models. Local reproduction: out/codex-check/review-scam-pr.py. Captured routes and instructions: out/codex-check/scam-pr-review.json. Both are gitignored review artifacts.

## Confirmed issues

### 1. Main speaks developer-style instructions to customers

Actual fixed lines include:

- H: "invite them to call the bank's customer-service number."
- I: "invite the customer to ring the number on the back of their card; do not state a number."
- J: "suggest calling the number printed on the card."

The contract currently allows descriptive `say` values: its scam example is "verify by phoning Freya Bank's customer service number". This is therefore a parser/compiler contract mismatch, not simply an extraction mistake by Claude. The same distinction can affect other fields used as exact speech; changing scam handling alone does not establish a general utterance contract.

### 2. PR #9 mistakes valid sentences for instructions

The only scam answers that retain fixed speech are those beginning "you can " or "you may ". A valid answer such as "Please call the number printed on your card to verify this call." is sent to route=ask in all three tested states. Equivalent openings such as "Call ..." or "To verify ..." would also fall outside the prefix rule by inspection.

Consequence: safe, complete speech unnecessarily becomes stochastic, and the behavior depends on harmless parser wording variation. A prefix whitelist is not a reliable representation of whether a value is an instruction or an utterance.

### 3. Readbacks lose fixed speech under the proposed fallback

The H/I/J instruction path during confirmation produces this task:

> Add no amount, no date and no offer of your own. Then say exactly this, word for word: So that is personal loan, 300.00 on Thursday 15 October. Do you confirm?

The amount/date are correctly customer-volunteered and should be read back. However, the speaking model is now responsible for their exact wording. The proposal's description of a fallback with "no account facts" is only true of the scam-answer portion; the complete task contains financial terms when a readback follows. Existing tests check the prompt/state, not the actual spoken amount/date.

This is a confirmed route/control change, not evidence that a real call has already misstated these terms. Keep that distinction in any handoff or PR description.

## Remaining uncertainty

PR #9 has a narrower task than the prior failing terminal reply, so it may reduce unintended offers. It has not demonstrated prevention of them. Conversation history already contains account details, and removing those details from the immediate task does not establish that the model cannot use them. The actual PUB-05 failure already showed a model ignoring explicit no-offer instructions; do not claim this fallback is deterministic or safe on the basis of prompt assertions alone.

AI/scam question-kind classification is also untested here. Missed or mixed questions may receive the unknown answer. Neither the main tests nor this review proves speech/extraction accuracy or 3/3 live robustness.

## Proposed implementation

Make the distinction at build time, before the customer call:

1. Preserve exact quoted customer-facing wording when the brief supplies it.
2. Represent descriptive directions separately from speakable text. For example, an optional `spoken_answer` can hold a complete utterance while existing `say` retains source-compatible behavior; a structured verification method can distinguish calling the bank's customer service from calling the number printed on the customer's card.
3. Ask the parser to produce customer-facing wording using only the brief's facts and restrictions. For known verification methods, the compiler can render a fixed template. Do not invent a phone number, a URL, a verification method, or a bank identity.
4. Validate the result before generation. An unresolved instruction-only answer should be reported as not ready/degraded, or use an explicitly documented fallback. Do not silently assume every descriptive `say` field is a TTS sentence.
5. Use fixed TTS for the final answer and any payment readback. Preserve pending support, the deferred close, and interruption by a transfer request.

This keeps wording conversion in the existing build pipeline and avoids reintroducing unconstrained speech at a sensitive customer turn. Parser/contract changes require compatibility checks against existing specs; this is a proposal, not an implemented schema change.

Acceptance cases should include H/I/J instructions, direct "You can ..." sentences, "Please call ..." and "To verify ..." sentences, exact quoted wording, no-number restrictions, an unsupported verification method, and the three conversation states exercised above. Assert final `say_text` and fixed-TTS routing, exact customer-volunteered payment terms, no unsolicited proposal after declined support, correct close reason, and preserved transfer interruption. Separately test question-kind extraction. After local gates pass and Freya recovers, run targeted speech cases and inspect transcripts before claiming live accuracy.

## Platform status

The fixed A workflow is already published as version 7. Its latest targeted PUB-05 attempt failed to start with HTTP 500; listing simulations then returned HTTP 504. There is no new live verdict. Backups and the request ID are recorded in log-codex-flight.md. PR #8 is superseded; this review concerns the incremental PR #9 only.
