#!/usr/bin/env python3
"""Plan 67 Phase 1 reproduction gate: compare a census.py run's P53 block (and PE) with plan 53's
committed census.json (aeae426c) / census_after.json (0c22b266). Writes p53_reproduction.json."""
from __future__ import annotations

import ast, json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
L0 = HERE.parent


def by_edge(d):
    return {"".join(ast.literal_eval(k)): n for k, n in d.items()}


def main(aeae_json, live_json, out):
    a, l = json.loads(Path(aeae_json).read_text()), json.loads(Path(live_json).read_text())
    c53, c53a = json.loads((L0 / "census.json").read_text()), json.loads((L0 / "census_after.json").read_text())
    def mine(j):
        p = j["P53"]
        return {"outside": p.get("on_edge_outside_leaf_rect", 0), "inside": p.get("on_edge_inside_leaf_rect", 0),
                "coincident_not_on_parent_edge": p.get("coincident_not_on_parent_edge", 0),
                "by_edge": {"".join(ast.literal_eval(k[8:])): n for k, n in p.items() if k.startswith("by_edge/")},
                "n_parents_outside": len(p["parents_outside"]), "n_links": j["n_road_links_in_divided_leaves"],
                "n_divided_parents": j["n_divided_parents"]}
    ma, ml = mine(a), mine(l)
    ra = {"outside": c53["all_vertices_on_parent_edge_outside_leaf_rect"],
          "inside": c53["all_vertices_on_parent_edge_inside_leaf_rect"],
          "coincident_not_on_parent_edge": c53["coincident_not_on_parent_edge"],
          "by_edge": by_edge(c53["outside_by_edge"]), "n_parents_outside": len(c53["parents_outside"]),
          "n_links": c53["n_road_links_in_divided_leaves"], "n_divided_parents": c53["n_divided_parents"]}
    rl = {"outside": c53a["edge_out"], "by_edge": by_edge(c53a["by_edge"]), "n_links": c53a["n_links_divided"]}
    checks = {f"aeae426c/{k}": [ma[k], v, ma[k] == v] for k, v in ra.items()}
    checks["aeae426c/parents_outside_identical"] = [None, None, a["P53"]["parents_outside"] == c53["parents_outside"]]
    checks.update({f"0c22b266/{k}": [ml[k], v, ml[k] == v] for k, v in rl.items()})
    res = {"schema": "plan67-p53-reproduction-v1", "P53_variant": a["P53"]["variant"],
           "checks [mine, recorded, equal]": checks, "all_equal": all(c[2] for c in checks.values()),
           "live_unrecorded_by_plan53": {k: ml[k] for k in ("inside", "coincident_not_on_parent_edge",
                                                            "n_parents_outside", "n_divided_parents")},
           "PE": {"aeae426c": a["PE"], "0c22b266": l["PE"]}}
    Path(out).write_text(json.dumps(res, indent=1, sort_keys=True) + "\n")
    print(json.dumps({"all_equal": res["all_equal"]}))
    return 0 if res["all_equal"] else 1


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:4]))
