#!/usr/bin/env python3
"""Plan 14 Phase 2 unit 2-03 -- residual discriminators + exhaustive membership.

Read-only. Loads Phase 1 evidence (776), 2-01 members/rejects, 2-02
members/rejects; asserts disjointness; writes `phase2_membership.tsv`.

Discriminators tried on the residual rows (written to
`output/scratch-14/residuals/` and summarised in `phase2_open_questions.md`):

  Q-source-335   windowed centre-branch (c) search: every spool L0 class-2
                 ring of the demanded code homed within +-W cells whose
                 per-ring even-odd interior holds the target cell centre, plus
                 (a)/(b) hits in that window; each hit's in-cell footprint is
                 run through densified emit_piece mirror and production C
                 bg_shape.
  Q-tile-alias   2-01 reject (765): complete repair + C on its Phase 1 source.
  Q-2-01-densify C bg_shape on each 2-01 member's meeting source (original
                 ring, target cell) to test the no-densify mirror caveat.

Plan 25: windowed spool reads only (pread per cell), --window bounded,
whole_file_guard via 2-02 module, run under run_heavy_python.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
import importlib.util as ilu
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[4]
TRIAGE = Path(__file__).resolve().parent
sys.path[:0] = [str(ROOT / "parser"), str(ROOT / "parser/tools")]


def _load(name, fname):
    spec = ilu.spec_from_file_location(name, TRIAGE / fname)
    mod = ilu.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


cr = _load("complete_repair_2_02", "complete_repair_2-02.py")
from kiwiw.spool import SpoolReader, decode_columns  # noqa: E402

RAW = cr.RAW
OUT = ROOT / "output/scratch-14/residuals"
NATIVE = cr.NATIVE


def read_tsv(p):
    with open(p) as fh:
        return list(csv.DictReader(fh, delimiter="\t"))


def key(r):
    return tuple(int(r[k]) for k in NATIVE)


def cell_records(spool, lat, ix, iy):
    idx = spool._load_idx(0)
    pos = np.nonzero((idx.ix == ix) & (idx.iy == iy))[0]
    if not len(pos):
        return []
    cols = decode_columns(spool._read_cell(0, int(idx.offset[pos[0]]), int(idx.length[pos[0]])))
    n = cols["b_nstored"].astype(np.int64)
    off = np.r_[0, np.cumsum(n)]
    out = []
    for k in range(len(n)):
        a, b = int(off[k]), int(off[k + 1])
        out.append({
            "ordinal": k, "class": int(cols["b_class"][k]), "type": int(cols["b_type"][k]),
            "mult": int(cols["b_mult"][k]), "flags": int(cols["b_flags"][k]),
            "lat": np.array(cols["c_lat"][a:b], np.float64),
            "lon": np.array(cols["c_lon"][a:b], np.float64),
        })
    return out


def pip_eo(px, py, xs, ys):
    inside = False
    n = len(xs)
    for i in range(n):
        j = (i + 1) % n
        if (ys[i] > py) != (ys[j] > py):
            if px < (xs[j] - xs[i]) * (py - ys[i]) / (ys[j] - ys[i]) + xs[i]:
                inside = not inside
    return inside


def represent(cprobe, lat, rec, ix, iy):
    """Densified mirror + C on original and EO faces for cell (ix, iy)."""
    xs, ys = lat.gx(rec["lon"]), lat.gy(rec["lat"])
    poly = list(zip(xs.tolist(), ys.tolist()))
    faces = cr.decompose_eo_faces(poly)
    py_emit, max_a2 = 0, 0
    for f in faces:
        cl = cr.clip_rect(f, ix * RAW, iy * RAW, (ix + 1) * RAW, (iy + 1) * RAW)
        q, a2, em = cr.encoder_piece_densified(cl, max(1, rec["mult"]))
        py_emit += bool(em)
        max_a2 = max(max_a2, abs(a2))
    b4 = cr.cell_b4(lat, ix, iy)
    r0, n0 = cprobe.run(rec["lat"], rec["lon"], rec["mult"], rec["type"], rec["flags"], b4)
    nf = 0
    for f in faces:
        fx = np.array([v[0] for v in f]); fy = np.array([v[1] for v in f])
        _, k = cprobe.run(lat.lat0 + fy / RAW * lat.cell_lat, lat.lon0 + fx / RAW * lat.cell_lon,
                          rec["mult"], rec["type"], rec["flags"], b4)
        nf += k
    return {"n_faces": len(faces), "n_crossings": cr.count_crossings(poly),
            "py_faces_emit": py_emit, "py_max_abs_area2": max_a2,
            "c_bytes_original": r0, "c_records_original": n0, "c_records_faces": nf}


def q_source_335(spool, lat, cprobe, row, window):
    ix, iy, code = int(row["ix"]), int(row["iy"]), int(row["code"])
    cxr, cyr = (ix + 0.5) * RAW, (iy + 0.5) * RAW
    scanned, typed, hits = 0, 0, []
    for sx in range(ix - window, ix + window + 1):
        for sy in range(iy - window, iy + window + 1):
            recs = cell_records(spool, lat, sx, sy)
            scanned += 1
            for rec in recs:
                if rec["class"] != 2 or rec["type"] != code or len(rec["lat"]) < 3:
                    continue
                typed += 1
                xs, ys = lat.gx(rec["lon"]), lat.gy(rec["lat"])
                if xs.max() < ix * RAW or xs.min() > (ix + 1) * RAW or \
                   ys.max() < iy * RAW or ys.min() > (iy + 1) * RAW:
                    continue
                br = []
                if pip_eo(cxr, cyr, xs.tolist(), ys.tolist()):
                    br.append("c")
                fx, fy = xs - ix * RAW, ys - iy * RAW
                if np.any((fx >= 1) & (fx <= RAW - 1) & (fy >= 1) & (fy <= RAW - 1)):
                    br.append("b_vertex_in_cell")
                h = {"source_cell": [0, sx, sy], "ordinal": rec["ordinal"],
                     "n_coords": len(rec["lat"]), "branches": br,
                     "bbox_cell_raw": [float(fx.min()), float(fx.max()),
                                       float(fy.min()), float(fy.max())]}
                h.update(represent(cprobe, lat, rec, ix, iy))
                hits.append(h)
    return {"dump_row": int(row["dump_row"]), "cell": [0, ix, iy], "code": code,
            "window_cells": window, "spool_cells_scanned": scanned,
            "same_code_class2_rings_in_window": typed,
            "rings_whose_bbox_meets_cell": len(hits), "hits": hits,
            "centre_branch_hits": sum("c" in h["branches"] for h in hits),
            "any_representable": any(h["c_records_original"] or h["c_records_faces"]
                                     or h["py_faces_emit"] for h in hits)}


def q_from_witness(spool, lat, cprobe, row):
    req = json.loads((ROOT / row["spool_K1_requirement_witness"]).read_text())
    src = req["source"]
    got = cr.source_cell_sha(spool, 0, src["source_cell"])
    assert got == src["source_cell_sha256"], "spool pin mismatch"
    recs = cell_records(spool, lat, int(src["source_cell"][1]), int(src["source_cell"][2]))
    rec = recs[src["background_ordinal"]]
    out = {"dump_row": int(row["dump_row"]), "source": {k: src[k] for k in
           ("branch", "source_cell", "background_ordinal", "n_coords")}}
    out.update(represent(cprobe, lat, rec, int(row["ix"]), int(row["iy"])))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--window", type=int, default=8,
                    help="Q-source-335 search half-width in L0 cells (plan 25 bound; max 32)")
    args = ap.parse_args(argv)
    if not (0 <= args.window <= 32):
        ap.error("--window must be in [0, 32]")

    assert cr.digest(cr.G_DISC / "ALLDATA.KWI") == cr.G_SHA
    cr.assert_no_whole_file(cr.SPOOL, cr.G_DISC / "ALLDATA.KWI")
    OUT.mkdir(parents=True, exist_ok=True)

    ev = read_tsv(TRIAGE / "completeness_evidence.tsv")
    m1 = read_tsv(TRIAGE / "2-01_g-omits-cell-local-dvd-type_members.tsv")
    j1 = read_tsv(TRIAGE / "2-01_g-omits-cell-local-dvd-type_rejects.tsv")
    m2 = read_tsv(TRIAGE / "2-02_r-absent-complete-repair-zero_members.tsv")
    j2 = read_tsv(TRIAGE / "2-02_r-absent-complete-repair-zero_rejects.tsv")
    assert len(ev) == 776 and len({key(r) for r in ev}) == 776
    s1, s2 = {key(r) for r in m1}, {key(r) for r in m2}
    assert not (s1 & s2), "2-01 / 2-02 overlap"
    by_key = {key(r): r for r in ev}
    assert s1 <= by_key.keys() and s2 <= by_key.keys()
    residual = [r for r in ev if key(r) not in s1 and key(r) not in s2]

    lat = cr.Lattice(0)
    spool = SpoolReader(cr.SPOOL)
    cprobe = cr.CProbe(OUT / "cprobe")

    results = {}
    oq = {}
    for r in residual:
        dr = int(r["dump_row"])
        if dr == 335:
            res = q_source_335(spool, lat, cprobe, r, args.window)
            oq[key(r)] = "open-question:Q-source-335"
        elif key(r) in {key(x) for x in j1}:
            res = q_from_witness(spool, lat, cprobe, r)
            oq[key(r)] = "open-question:Q-tile-alias"
        elif key(r) in {key(x) for x in j2}:
            res = q_from_witness(spool, lat, cprobe, r)
            oq[key(r)] = "open-question:Q-repair-emits"
        else:
            res = {"dump_row": dr, "note": "unexpected residual"}
            oq[key(r)] = "open-question:Q-unexpected"
        results[dr] = res
        (OUT / f"{dr}.json").write_text(json.dumps(res, sort_keys=True, indent=1) + "\n")

    # Q-2-01-densify: production C on each 2-01 member's meeting source
    c201 = {"members": len(m1), "c_records_nonzero": 0, "rows_nonzero": []}
    for r in m1:
        er = by_key[key(r)]
        res = q_from_witness(spool, lat, cprobe, er)
        if res["c_records_original"] or res["c_records_faces"]:
            c201["c_records_nonzero"] += 1
            c201["rows_nonzero"].append(res["dump_row"])
    (OUT / "q_2-01_densify_c.json").write_text(json.dumps(c201, sort_keys=True, indent=1) + "\n")

    rows_out = []
    for r in ev:
        k = key(r)
        g = ("g-omits-cell-local-dvd-type" if k in s1 else
             "r-absent-complete-repair-zero" if k in s2 else oq[k])
        rows_out.append(list(k) + [int(r["dump_row"]), g])
    hdr = list(NATIVE) + ["dump_row", "phase2_group"]
    with (TRIAGE / "phase2_membership.tsv").open("w", newline="") as fh:
        w = csv.writer(fh, delimiter="\t", lineterminator="\n")
        w.writerow(hdr)
        w.writerows(sorted(rows_out, key=lambda x: x[13]))
    counts = {}
    for x in rows_out:
        counts[x[-1]] = counts.get(x[-1], 0) + 1
    assert sum(counts.values()) == 776
    assert len(s1) + len(s2) + len(residual) == 776
    summary = {"counts": counts, "n_2_01": len(s1), "n_2_02": len(s2),
               "n_open": len(residual), "disjoint": True, "exhaustive": True,
               "window": args.window, "q_2_01_densify_c": c201,
               "residuals": results, "c_positive_ok": True}
    (OUT / "summary.json").write_text(json.dumps(summary, sort_keys=True, indent=1) + "\n")
    print(json.dumps({k: v for k, v in summary.items() if k != "residuals"}, sort_keys=True, indent=1))
    for dr, res in results.items():
        print(dr, json.dumps({k: v for k, v in res.items() if k != "hits"}, sort_keys=True))
        for h in res.get("hits", [])[:20]:
            print("   hit", json.dumps(h, sort_keys=True))
    spool.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
