"""Plan 43 P2: rebuild a 3-17-shaped dump_ext (152-byte rows: native 144 + s02_producer_verified@144 + other_mechanism@145
+ residual_crossing_verified@146) on 4ed9cd80, for the full-CLI (R-G8-4-b) and kind-view (R-G8-4-a, S2e) runs.
- completeness: the 776 rows of dump_forced (dump_join other_mechanism output, mechanism forced to 0 on 3-14 changed cells);
  its 144 native bytes are checked equal to K1@1cf40f8's fresh completeness.bin (itself sha-equal to dump_raw 1a91b1c2).
- name_anchor: K1@1cf40f8's one row. other_mechanism = 6 (O03 spool), the value fixed by the committed pre-3-14
  classification at cause_table.md:36 (O03 / one source name at L0 home(0,541)); inherited as the 3-14 extension
  did on byte-unchanged cells (rebaseline_3-17_9064.md:112). Row identity checked against plan 29 (L0 (0,541),
  leaf [928], raw (0,370), lat -38.7272..) and 3-08 review item 7 (Ile Saint-Paul); cell (0,0,541) is NOT in
  plan 31's 3-14 changed-cell list. S2e verifies CLI behaviour on this inferred byte, not recovered 3-17 bytes.
- background, background_boundary, interior_cover: zero rows (as in 3-17's dump_ext)."""
import json, sys
from pathlib import Path
import numpy as np
S = Path("/home/codyh/workspace/open-pajero-maps/output/scratch-43/p2")
T = {"f64": "<f8", "i32": "<i4", "u16": "<u2", "u8": "u1"}
def dt(fields): return np.dtype([(f["name"], T[f["type"]]) for f in fields], align=True)
mk = json.load(open(S / "dump_k1old_all/dump_manifest.json")); dk = dt(mk["fields"]); assert dk.itemsize == 144
mf = json.load(open(S / "dump_forced/dump_manifest.json")); df = dt(mf["fields"])
fields = list(mk["fields"]) + [{"name": "s02_producer_verified", "type": "u8"}, {"name": "other_mechanism", "type": "u8"},
                               {"name": "residual_crossing_verified", "type": "u8"}]
de = dt(fields); assert de.itemsize == 152 and de.fields["s02_producer_verified"][1] == 144 and de.fields["other_mechanism"][1] == 145 and de.fields["residual_crossing_verified"][1] == 146
out = S / "dump_ext43"; out.mkdir(exist_ok=True)
comp_f = np.fromfile(S / "dump_forced/completeness.bin", dtype=df)
comp_k = np.fromfile(S / "dump_k1old_all/completeness.bin", dtype=dk)
assert len(comp_f) == len(comp_k) == 776
e = np.zeros(776, de)
for n in dk.names:
    assert np.array_equal(comp_f[n], comp_k[n], equal_nan=True) if comp_f[n].dtype.kind == "f" else np.array_equal(comp_f[n], comp_k[n]), n
    e[n] = comp_k[n]
e["other_mechanism"] = comp_f["other_mechanism"]; e["s02_producer_verified"] = comp_f["s02_producer_verified"]
e.tofile(out / "completeness.bin")
na = np.fromfile(S / "dump_k1old_all/name_anchor.bin", dtype=dk); assert len(na) == 1
r = na[0]
assert (int(r["level"]), int(r["ix"]), int(r["iy"]), int(r["p0"]), int(r["vx"]), int(r["vy"])) == (0, 0, 541, 928, 0, 370)
assert abs(float(r["lat"]) + 38.7272857) < 1e-5 and float(r["lon"]) == 90.0
cells = ROOT_CELLS = Path(__file__).resolve().parents[7] / "output/scratch-31/diff-3-14-au.cells.tsv"
assert not any(l.startswith("0\t0\t541\t") for l in open(cells))
en = np.zeros(1, de)
for n in dk.names: en[n] = na[n]
en["other_mechanism"] = 6; en.tofile(out / "name_anchor.bin")
for k in ("background", "background_boundary", "interior_cover"): open(out / f"{k}.bin", "wb").close()
man = dict(mk); man["fields"] = fields; man["row_size"] = 152
man["kinds"] = {k: dict(v, rows={"completeness": 776, "name_anchor": 1}.get(k, 0), row_size=152) for k, v in mk["kinds"].items()}
man["plan43_extension"] = {"completeness": "dump_forced other_mechanism (plan 31 forced-zero)", "name_anchor": "other_mechanism 6 inherited (cell unchanged in 3-14)", "zero_rows": ["background", "background_boundary", "interior_cover"]}
json.dump(man, open(out / "dump_manifest.json", "w"), indent=1)
print({k: v["rows"] for k, v in man["kinds"].items()}, "mech counts", np.unique(e["other_mechanism"], return_counts=True))
