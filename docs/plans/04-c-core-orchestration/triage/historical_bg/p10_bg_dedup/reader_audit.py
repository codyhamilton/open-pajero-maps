#!/usr/bin/env python3
"""Plan 68 reader re-audit (Design ruling 2026-10-09 17:23): which committed claims read R through
plan 63's truncating cut `frame[:U16(frame, 0) * 2]`, and do they change when R is read whole?

  g    --disc D : every distinct frame of a G disc: background records parsed from the truncated frame
                  == parsed from the whole leaf entry? (G-side claims of plans 63 / 64 / 68 rely on the cut
                  being lossless on G.) Counts frames, mismatches, and frames where the length word
                  exceeds the entry.
  p64           : plan 64's 23 groups (classify.json): per leaf cell on R, background records decoded by
                  plan 48's r_parent (whole entry) vs wires parsed whole vs wires parsed truncated (what
                  trace.disc_cell used); type-288 counts (all classes, class 2) in each.
Output: <out>.json."""
from __future__ import annotations

import argparse, json, sys, time
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
HB = HERE.parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HB / "p8_source_removed"))
from r_census import iter_full  # noqa: E402
from provenance import leaf_all_records  # noqa: E402
from census import L  # noqa: E402

R_DISC = "/run/media/codyh/464210-8480/ALLDATA.KWI"


def cmd_g(a):
    c = Counter(); ex = []
    for level, ix, iy, path, full, tr in iter_full(a.disc):
        c["frames"] += 1
        if L.U16(full, 0) * 2 > len(full):
            c["lenword_exceeds_entry"] += 1
        rf = leaf_all_records(full); rt = leaf_all_records(tr)
        c["records"] += len(rf)
        if rf != rt:
            c["mismatch_frames"] += 1
            if len(ex) < 20:
                ex.append([level, ix, iy, list(path), len(rf), len(rt)])
    return {"disc": str(a.disc), "counts": dict(sorted(c.items())), "examples": ex}


def cmd_p64(a):
    import trace as TR  # noqa: F401  (sets sys.path like plan 64)
    import trim_witness as TW
    from overlay_test import RReader
    from r_neighbours import LeafIndex
    from quantisation_roundtrip import Lattice
    cl = json.loads((HB / "p8_source_removed/classify.json").read_text())
    rr = RReader(str(Path(R_DISC).parent)); li = LeafIndex(rr, 0); lat = Lattice(0)
    cells = sorted({(g["leaf"][1], g["leaf"][2]) for g in cl["groups"]})
    out = []; tot = Counter()
    for ix, iy in cells:
        st, div, leaves = TW.r_parent(rr, li, 0, ix, iy, lat)
        row = {"cell": [ix, iy], "status": st, "leaves": len(leaves), "decoded": 0, "wires_whole": 0,
               "wires_trunc": 0, "t288_decoded": 0, "t288_c2_decoded": 0, "t288_wires_whole": 0,
               "decoded_eq_whole_types": True}
        for lf in leaves:
            rr.fh.seek(lf["file_offset"]); buf = rr.fh.read(lf["length"])
            wf = leaf_all_records(buf); wt = leaf_all_records(buf[:L.U16(buf, 0) * 2])
            bg = lf["_bgs"]
            row["decoded"] += len(bg); row["wires_whole"] += len(wf); row["wires_trunc"] += len(wt)
            row["t288_decoded"] += sum(1 for tc, sc, _P in bg if int(tc) == 288)
            row["t288_c2_decoded"] += sum(1 for tc, sc, _P in bg if int(tc) == 288 and int(sc) == 2)
            row["t288_wires_whole"] += sum(1 for r in wf if r[2] == 288)
            if [(int(tc), int(sc)) for tc, sc, _P in bg] != [(r[2], r[1]) for r in wf]:
                row["decoded_eq_whole_types"] = False
        for k in ("leaves", "decoded", "wires_whole", "wires_trunc", "t288_decoded", "t288_c2_decoded", "t288_wires_whole"):
            tot[k] += row[k]
        tot["cells_decoded_eq_whole"] += row["decoded_eq_whole_types"]
        out.append(row)
    tot["cells"] = len(cells)
    return {"cells": out, "total": dict(sorted(tot.items()))}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["g", "p64"])
    ap.add_argument("--disc", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    t0 = time.time()
    r = cmd_g(a) if a.mode == "g" else cmd_p64(a)
    r["wall_s"] = round(time.time() - t0, 1)
    Path(str(a.out) + ".json").write_text(json.dumps(r, indent=1, sort_keys=True) + "\n")
    print(json.dumps(r.get("counts") or r.get("total")))


if __name__ == "__main__":
    main()
