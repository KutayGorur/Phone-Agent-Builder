# External handoffs: which file goes with which attachments

Paste the whole handoff file as the first message. Attach the files listed in its "Attach" section. Save the answer into `external/<agent-name>/` as the handoff says (agent-name = `gemini` or `chatgpt`).

All paths are relative to the repo folder `build-the-builder-v3/build-the-builder/`.

| File | Task | Attach | Result goes to |
|---|---|---|---|
| `01-practice-briefs.md` | 2-3 new practice briefs + cases + tool API | `briefs/brief-a.md`, `briefs/brief-b.md`, `test-briefs/brief-d.md`, `test-briefs/brief-e.md`, `test-briefs/cases-e.json`, `test-briefs/tools-e.openapi.json` | `external/<agent>/briefs/` |
| `02-customer-scripts.md` | Difficult customer scripts per practice case | `public-test-set.json`, `briefs/brief-a.md`, `briefs/brief-b.md` (optional second pass: `test-briefs/cases-c.json`, `cases-d.json`, `cases-e.json`) | `external/<agent>/scripts/` |
| `03-spec-review.md` | Review of the parsed spec vs Briefs A and B | `briefs/brief-a.md`, `briefs/brief-b.md`, `builder/specs/brief-ab.spec.json`, `builder/SPEC_CONTRACT.md` | `external/<agent>/review.md` |
| `04-readme-judges.md` | Draft README section for judges | `README.md`, `TEST_PLAN.md`, `builder/SPEC_CONTRACT.md`, `HANDOFF-planning.md`, `builder/HANDOFF-build.md`, `builder/generate/HANDOFF.md` | `external/<agent>/README-judges.md` |

Never attach `env.sh`, `apikey.txt`, `.freya-agents.json`, `results/` or `traces/`.
