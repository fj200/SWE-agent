from pathlib import Path
from json import loads

path = Path("baseline_traj/baseline_pred.json")
base_pred = {}
with path.open(mode="r", encoding="utf-8") as base_pred_file:
    content = base_pred_file.read()
    base_pred = loads(content)


path = Path("/workspaces/SWE-agent/trajectories/vscode/default__claude-sonnet-4-20250514__t-0.00__p-1.00__c-1.00___swe_bench_lite_test/preds.json")
claude_pred = {}
with path.open(mode="r", encoding="utf-8") as claude_pred_file:
    content = claude_pred_file.read()
    claude_pred = loads(content)






