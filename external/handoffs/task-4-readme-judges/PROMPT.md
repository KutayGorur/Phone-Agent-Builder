# Task: draft the judges' README section

A hackathon team ("Build the Builder") wrote a program that reads a bank's brief and builds a phone agent on the Freya platform. Judges read our repo README. You draft a section explaining our approach honestly. No repo access; use only the attachments. **No Freya API key, no secrets; claim nothing the files do not support.**

**Files already in this project folder (read them from disk, paths as written):** `README.md` (kit README; our builder is described in its last section "Our builder"), `TEST_PLAN.md`, `builder/SPEC_CONTRACT.md`, `HANDOFF-planning.md`, `builder/HANDOFF-build.md`, `builder/generate/HANDOFF.md`.

## Event constraints (the text must not contradict them)
- The builder takes everything from the brief; nothing from the final briefs is written into code or prompts.
- Scoring is all-or-nothing per customer, and three runs must pass.
- One builder run is limited to 30 minutes; a trace is mandatory.

## Write (technical, plain English, "we", 600 to 800 words)
1. **Approach in one paragraph**: parse -> spec -> generate -> save -> optional self-test -> export; deterministic code for dates and amounts, a model for language.
2. **Why a spec contract**: what the stage boundary buys (testability, no brief-specific code).
3. **How we avoid overfitting**: practice briefs C/D/E, local engine sim, what the builder takes from the brief.
4. **Testing with limited credits**: gates 0-6 of TEST_PLAN.md, the ledger.
5. **Reliability**: three-run requirement, degraded fallback, tracing.
6. **Known limits**: be candid, take them from the HANDOFF files, mark anything unsure with `[CHECK]`.
7. **How to run**: the exact commands from README "Our builder".

## Output format (exact)
One Markdown file, to be saved as `README-judges.md`, starting with `## Our approach` and no other top-level heading. End with a list "Claims to verify" for every statement you could not confirm from the attachments.

## Where to write
Write every output file under `output/` in this folder (never overwrite the input files). In task 1 the output paths above are relative to `output/`, e.g. `output/briefs/brief-f.md`. If you cannot write files, give each file in a code block labelled with its path.
