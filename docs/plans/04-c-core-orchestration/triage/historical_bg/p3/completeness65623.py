"""Plan 39 P3: completeness (65 rows) and name_anchor (1 row) on 87a01b14 against source 65623.
Name rows: the source cell has no name records -> cannot produce a name_anchor row. Completeness rows: only type-288 rows
can involve a type-288 source; for each, (i) does the CF change the cell's frames (65623 produced a piece there)?
(ii) does the source ring geometrically meet the cell rectangle (vertex inside, edge crossing, or rectangle inside ring)?"""
import sys, json, csv, numpy as np
sys.path.insert(0, "parser")
from kiwiw.spool import SpoolReader
from kiwiw import mesh
T = {"f64": "<f8", "i32": "<i4", "u16": "<u2", "u8": "u1"}
D = "output/scratch-39/dump_pre311_small"; m = json.load(open(f"{D}/dump_manifest.json"))["kinds"]
dt = np.dtype([(f["name"], T[f["type"]]) for f in m["completeness"]["fields"]], align=True)
R = np.fromfile(f"{D}/completeness.bin", dtype=dt)
r = SpoolReader("output/extract_timing/spool"); idx = r._load_idx(0)
i = int(np.flatnonzero((idx.ix == 1689) & (idx.iy == 508))[0])
cols = next(iter(r.iter_cell_columns(0, i, i + 1)))[2]
n = int(cols["b_ncoords"][0]); lat = np.array(cols["c_lat"][:]); lon = np.array(cols["c_lon"][:])
ring = list(zip(lon, lat)); closed = ring + [ring[0]] if ring[0] != ring[-1] else ring
grid = mesh.CellGrid.from_reference(0)
def seg_x(a, b, c, d):
    def o(p, q, r): return (q[0]-p[0])*(r[1]-p[1]) - (q[1]-p[1])*(r[0]-p[0])
    return (o(a,b,c) * o(a,b,d) <= 0) and (o(c,d,a) * o(c,d,b) <= 0)
def pip(x, y):
    ins = False
    for (x1, y1), (x2, y2) in zip(closed[:-1], closed[1:]):
        if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * (x2 - x1) / (y2 - y1): ins = not ins
    return ins
def meets(ix, iy):
    b = mesh.parcel_bounds(ix, iy, grid)
    x0, x1, y0, y1 = b.lon_lo, b.lon_hi, b.lat_lo, b.lat_hi
    if any(x0 <= x <= x1 and y0 <= y <= y1 for x, y in ring): return "vertex"
    E = [((x0,y0),(x1,y0)), ((x1,y0),(x1,y1)), ((x1,y1),(x0,y1)), ((x0,y1),(x0,y0))]
    for a, c in zip(closed[:-1], closed[1:]):
        if max(a[0], c[0]) < x0 or min(a[0], c[0]) > x1 or max(a[1], c[1]) < y0 or min(a[1], c[1]) > y1: continue
        if any(seg_x(a, c, p, q) for p, q in E): return "edge"
    return "inside" if pip((x0 + x1) / 2, (y0 + y1) / 2) else "no"
ctl = {}; cf = {}
for name, d in (("ctl", ctl), ("cf", cf)):
    for row in csv.reader(open(f"output/scratch-39/p3/{name}/frames.tsv"), delimiter="\t"):
        d.setdefault((int(row[1]), int(row[2])), []).append(row[8])
out = {"name_anchor": {"rows": int(m["name_anchor"]["rows"]), "source_cell_names": int(len(cols["s_type"])), "produced_by_65623": 0},
       "completeness": {"rows": int(len(R)), "type288": int((R["code"] == 288).sum()), "rows_detail": []}}
for row in R[R["code"] == 288]:
    c = (int(row["ix"]), int(row["iy"]))
    inwin = 1414 <= c[0] < 1890 and 274 <= c[1] < 750
    chg = (sorted(ctl.get(c, [])) != sorted(cf.get(c, []))) if inwin else None
    out["completeness"]["rows_detail"].append({"cell": c, "in_window": inwin, "cf_changes_cell": chg, "ring_meets_cell": meets(*c)})
det = out["completeness"]["rows_detail"]
out["completeness"]["ring_meets"] = sum(d["ring_meets_cell"] != "no" for d in det)
out["completeness"]["cf_changes"] = sum(bool(d["cf_changes_cell"]) for d in det)
json.dump(out, open("output/scratch-39/p3/completeness65623.json", "w"), indent=1)
print(json.dumps({k: {kk: vv for kk, vv in v.items() if kk != "rows_detail"} for k, v in out.items()}))
print([d for d in det if d["ring_meets_cell"] != "no" or d["cf_changes_cell"]])
