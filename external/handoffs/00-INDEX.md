# External handoffs

One folder per task. For each: open the folder as the agent's project folder, then give it the file `PROMPT.md` (paste it or point to it). Everything the agent needs is inside the folder; nothing to attach. The agent writes its results to `output/` (or you paste its answer into a file there), then copy the result into `external/<agent-name>/`.

| Folder | Task |
|---|---|
| `task-1-practice-briefs/` | 3 new practice briefs with cases and tool API |
| `task-2-customer-scripts/` | harder customer scripts per practice case |
| `task-3-spec-review/` | review of the parsed spec vs Briefs A and B |
| `task-4-readme-judges/` | draft README section for judges |

Folders contain copies of repo files only (no env.sh, keys, traces).
