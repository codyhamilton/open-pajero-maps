"""Plan 43 P2: rules files for the classify runs. 'at317' = the rule files as at 3-17's commit ac1a64d (git show), 'cur' = master.
all = rules_bg + rules_other (3-17's rules_all.before.json shape); completeness / name_anchor = that kind's rules, original order."""
import json, subprocess, sys
from pathlib import Path
S = Path(sys.argv[1]); S.mkdir(parents=True, exist_ok=True)
T = "docs/plans/04-c-core-orchestration/triage"
def load(rev, name):
    if rev == "cur": return json.load(open(f"{T}/{name}"))
    return json.loads(subprocess.check_output(["git", "show", f"{rev}:{T}/{name}"]))
for tag, rev in (("at317", "ac1a64d"), ("cur", "cur")):
    bg, other = load(rev, "rules_bg.json"), load(rev, "rules_other.json")
    allr = {"version": other.get("version", 1), "rules": bg["rules"] + other["rules"]}
    json.dump(allr, open(S / f"rules_all_{tag}.json", "w"), indent=1)
    for kind in ("completeness", "name_anchor"):
        json.dump({"version": allr["version"], "rules": [r for r in allr["rules"] if r["kind"] == kind]}, open(S / f"rules_{kind}_{tag}.json", "w"), indent=1)
    print(tag, len(allr["rules"]), [(r["id"], r["kind"]) for r in allr["rules"] if r["kind"] in ("completeness", "name_anchor")])
a, c = (json.load(open(S / f"rules_completeness_{t}.json")) for t in ("at317", "cur"))
print("completeness rules equal at317 vs cur:", a == c)
a, c = (json.load(open(S / f"rules_name_anchor_{t}.json")) for t in ("at317", "cur"))
print("name_anchor rules equal at317 vs cur:", a == c)
