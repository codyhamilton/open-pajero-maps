"""Plan 39 P1 items 2/4 (partial): failing-row identity across the 3-11 hop (87a01b14 replay vs 013586b5), outside vs inside the 37 changed L0 cells.
Fixed K1 (HEAD) + spool. Rows compared byte-for-byte (all dump fields) in dump order on named-field bytes (struct padding excluded)."""
import json, numpy as np
S = "output/scratch-39"
cells37 = set()
for line in open("output/scratch-36/diff-3-11-au.cells.tsv").read().splitlines()[1:]:
    a = line.split("\t"); cells37.add((int(a[0]), int(a[1]), int(a[2])))
T = {"f64": "<f8", "i32": "<i4", "u16": "<u2", "u8": "u1", "i16": "<i2", "u32": "<u4", "i8": "i1", "f32": "<f4", "i64": "<i8", "u64": "<u8"}
def load(d, kind):
    """Dump rows with the C struct layout (natural alignment), as parser/tools/k1_triage.py reads them."""
    m = json.load(open(f"{d}/dump_manifest.json"))["kinds"][kind]
    dt = np.dtype([(f["name"], T[f["type"]]) for f in m["fields"]], align=True)
    assert dt.itemsize == m["row_size"], (dt.itemsize, m["row_size"])
    return np.memmap(f"{d}/{kind}.bin", dtype=dt, mode="r"), m["rows"]
out = {"cells37": len(cells37)}
for kind in ("background", "background_boundary", "interior_cover"):
    A, na = load(f"{S}/dump_pre311", kind); B, nb = load(f"{S}/dump_311", kind)
    def in37(R):
        key = (R["level"].astype(np.int64) << 40) | (R["ix"].astype(np.int64) << 20) | R["iy"].astype(np.int64)
        k37 = np.array(sorted((l << 40) | (x << 20) | y for l, x, y in cells37), dtype=np.int64)
        return np.isin(key, k37)
    ma, mb = in37(A), in37(B)
    res = {"rows_pre311": int(na), "rows_311": int(nb), "in37_pre311": int(ma.sum()), "in37_311": int(mb.sum()),
           "out37_pre311": int((~ma).sum()), "out37_311": int((~mb).sum())}
    ao, bo = np.asarray(A[~ma]), np.asarray(B[~mb])
    # compare named-field bytes only: fancy-index copies leave struct padding uninitialised
    nonpad = np.array([i for n in ao.dtype.names for i in range(ao.dtype.fields[n][1], ao.dtype.fields[n][1] + ao.dtype.fields[n][0].itemsize)])
    if len(ao) == len(bo):
        xa = ao.view(np.uint8).reshape(len(ao), -1)[:, nonpad]; xb = bo.view(np.uint8).reshape(len(bo), -1)[:, nonpad]
        res["out37_identical_in_order"] = bool((xa == xb).all())
    else:
        res["out37_identical_in_order"] = False
    res["whole_file_byte_identical"] = (na == nb) and bool((np.fromfile(f"{S}/dump_pre311/{kind}.bin", np.uint8) == np.fromfile(f"{S}/dump_311/{kind}.bin", np.uint8)).all()) if na == nb else False
    # per-cell failing deltas inside the 37
    from collections import Counter
    ca = Counter(zip(*(A[ma][f].astype(int).tolist() for f in ("level", "ix", "iy"))))
    cb = Counter(zip(*(B[mb][f].astype(int).tolist() for f in ("level", "ix", "iy"))))
    res["per_cell_failing_delta_in37"] = {f"{c[0]}/{c[1]}/{c[2]}": cb.get(c, 0) - ca.get(c, 0) for c in sorted(cells37) if cb.get(c, 0) != ca.get(c, 0)}
    out[kind] = res
    print(kind, json.dumps({k: v for k, v in res.items() if k != "per_cell_failing_delta_in37"}), flush=True)
json.dump(out, open(f"{S}/basis_311.json", "w"), indent=1)
print("BASISDONE")
