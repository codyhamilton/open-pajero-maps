"""Plan 39 P1 item 2, interior_cover +29: K1 counts an interior_cover item per class-2 shape whose every vertex lies on
the leaf rectangle boundary and whose shoelace area equals the leaf rectangle (|area-rect| < 0.5), in lattice units.
Count such shapes among the 167,936 formerly-unread records (frame raw coordinates; leaf extent from the frame range)."""
import json, sys
sys.path.insert(0, "parser")
src = open(__import__("os").path.dirname(__import__("os").path.abspath(__file__)) + "/../p1/wrap37.py").read().split("O, N = frames")[0]
exec(src)
from kiwiw.coordconv import decode_region_coord
from kiwiw import mesh
O = frames("output/scratch-36/G_pre311/ALLDATA.KWI")
def recverts(r):
    nco = sec.u16(r, 2) & 0x7FF; mult = 1 << (sec.u16(r, 6) & 7)
    x, y = decode_region_coord(sec.u16(r, 8)), decode_region_coord(sec.u16(r, 10)); v = [(x, y)]
    for m in range(nco):
        xo, yo = r[12 + 2 * m], r[13 + 2 * m]
        x += (xo - 256 if xo > 127 else xo) * mult; y += (yo - 256 if yo > 127 else yo) * mult; v.append((x, y))
    return v
tot = 0; per = {}; ranges = set()
for k in sorted(O):
    so = sec.split(O[k]); eo = bg_elems(so["background"])
    for a in eo:
        if a is None or sum(c for c, _ in a[1]) == len(a[2]): continue
        decl = sum(c for c, _ in a[1]); cls = a[1][0][1]
        # leaf raw extent: the max |coordinate| any record of this element reaches on the leaf edge
        allv = [p for r in a[2] for p in recverts(r)]
        X1 = max(x for x, _ in allv); Y1 = max(y for _, y in allv); X0 = min(x for x, _ in allv); Y0 = min(y for _, y in allv)
        ranges.add((X0, Y0, X1, Y1))
        n = 0
        for r in a[2][decl:]:
            v = recverts(r)
            if cls != 2: continue
            if not all(x in (X0, X1) or y in (Y0, Y1) for x, y in v): continue
            s = sum(v[i][0] * v[(i + 1) % len(v)][1] - v[(i + 1) % len(v)][0] * v[i][1] for i in range(len(v)))
            if abs(abs(s) / 2 - (X1 - X0) * (Y1 - Y0)) < 0.5: n += 1
        per[str(k)] = n; tot += n
json.dump({"unread_whole_leaf_cover_shapes": tot, "per_leaf": per, "element_extents": sorted(ranges)[:10]}, open("output/scratch-39/wrap37_cover.json", "w"), indent=1)
print(tot, sorted(ranges)[:6])
