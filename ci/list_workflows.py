"""Read-only: list the Freya workflows in the workspace (newest first). Never deletes or changes anything.

python3 ci/list_workflows.py            # table: id, agent id, name, updated, whether .freya-agents.json knows it
python3 ci/list_workflows.py --json
The hackathon page says max 10 workflows per workspace. Delete extras by hand in the Freya UI, not from here.
"""
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import freya


def main():
    items = freya.api("GET", "/api/v2/workflow", workspaceId=freya.workspace_id()).get("workflows", [])
    items.sort(key=lambda w: w.get("updatedAt") or "", reverse=True)
    state_file = ROOT / ".freya-agents.json"
    slots = {}
    if state_file.exists():
        for slot, v in json.loads(state_file.read_text()).items():
            slots[v.get("workflow_id")] = slot
    if "--json" in sys.argv:
        print(json.dumps(items, indent=1)); return
    for w in items:
        print(f"{w['id']}  agent={w.get('agentId')}  v{w.get('latestVersionNumber')}  {(w.get('updatedAt') or '')[:19]}  {w.get('name')}"
              f"  [slot: {slots.get(w['id'], '-')}]")
    over = len(items) - 10
    print(f"\n{len(items)} workflows in workspace (limit per the page: 10)" + (f"; {over} over, tidy up in the Freya UI" if over > 0 else ""))


if __name__ == "__main__":
    main()
