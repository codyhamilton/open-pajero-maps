"""Plan 39 P1 item 1: HEAD K1 totals on a disc vs the 3C-04 table (plan 04 IMPLEMENTATION 2-08) and the 3-90 rerun #3 (013586b5)."""
import json, sys
C3C04 = {"range": (309192246, 0), "step": (252444802, 0), "road_node": (42995770, 0), "name_anchor": (2317983, 1),
         "background": (174332105, 1438558), "background_boundary": (89546388, 16549569),
         "completeness": (1800514, 752), "interior_cover": (1592016, 824)}
R3 = {"range": (310053353, 0), "step": (253137973, 0), "road_node": (42995770, 0), "name_anchor": (2317983, 1),
      "background": (175171302, 1438571), "background_boundary": (89568298, 16550043), "completeness": (1800514, 739),
      "interior_cover": (1592045, 824)}
ref = {"3c04": C3C04, "rerun3_013586b5": R3}[sys.argv[2]]
t = json.load(open(sys.argv[1]))["totals"]
out = {}
for k, (c, f) in ref.items():
    g = t.get(k, {})
    out[k] = {"checked": g.get("checked"), "ref_checked": c, "d_checked": g.get("checked", 0) - c,
              "failing": g.get("failing"), "ref_failing": f, "d_failing": g.get("failing", 0) - f}
    print(f"{k:20s} checked {g.get('checked'):>12,} ref {c:>12,} d {out[k]['d_checked']:>+10,}   failing {g.get('failing'):>10,} ref {f:>10,} d {out[k]['d_failing']:>+8,}")
json.dump(out, open(sys.argv[3], "w"), indent=1)
