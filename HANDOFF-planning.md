# Handoff: planning / integration thread

Paused 2026-10-10 ~12:10 UTC (user near usage limit).

## Done
- Read the whole kit, briefs, docs, mails, kickoff notes and https://www.freyavoice.ai/hackathon.
- `env.sh` (gitignored) exports FREYA_API_KEY, FREYA_API_URL, FREYA_BANK_TEAM_KEY. Key verified against the workspace API. Load with `source env.sh` in Git Bash.
- Git repo in this folder, remote `origin` = https://github.com/KutayGorur/Phone-Agent-Builder (private), branch `main`.
- `builder/SPEC_CONTRACT.md`: the spec.json shape between parser and generator (owned by this thread).
- Work split into 5 threads: date/amount logic (`builder/logic/`, `tests/logic/`), brief parser (`builder/parse/`, `builder/specs/`), workflow generator (`builder/generate/`, `out/`), build.py + trace (`builder/build.py`, `builder/trace.py`), practice briefs + harness (`test-briefs/`, `harness/`, `results/`).

## Next (integration lead)
1. Check each thread's handoff note and what landed on `main`.
2. Reconcile any changes threads proposed to SPEC_CONTRACT.md.
3. Wire parse -> generate -> save -> self-test in `builder/build.py`; run end to end on Brief A, then A+B, then on the variant briefs in `test-briefs/`.
4. Measure 3/3 pass rates with `--reps 3` and the `--style` options; check build time stays well under 30 min.

## Gotchas
- Submission command: `python3 builder/build.py <brief> <tool_api>`; trace is mandatory; top-10 entries get re-run from the commit.
- One simulation per workspace at a time; threads queue on it.
- Shared checkout: no branch switching, `git add` only owned paths, `git pull --rebase origin main` before push.
- Root folder `public-test-set.json` is an older copy; use the kit's.
