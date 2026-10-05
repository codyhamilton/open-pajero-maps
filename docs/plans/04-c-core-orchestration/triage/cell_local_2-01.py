#!/usr/bin/env python3
"""Plan 14 Phase 2 unit 2-01 -- group `g-omits-cell-local-dvd-type`.

Read-only reproducer / membership builder. It reads four committed-or-provided
inputs and writes only under the plan-14 triage directory and
`output/scratch-14/` (git-ignored scratch):

  1. `triage/completeness_evidence.tsv` (Phase 1): 776 completeness rows.
  2. The R disc `/run/media/codyh/464210-8480/ALLDATA.KWI` (cell-local decode).
  3. The G disc `output/scratch-14/G_new/ALLDATA.KWI` (absence decode).
  4. The spool `output/extract_timing/spool` (meeting-source forensics).

For every Phase 1 seed (`R_polygon_count > 0`; 343 of them) it:

  * decodes the covering R leaf slot and applies the *same* presence contract
    the checker uses (`_k1_cmp.c` / `quantisation_roundtrip._required_cells`):
    a qualifying R polygon (shape_class==2, >=3 coords, demanded `code`) is
    cell-local iff it meets the target cell by
      (a) sitting inside the cell rectangle with a non-zero rounded area,
      (b) having a vertex at least one raw unit inside the cell, or
      (c) holding the cell centre (even-odd point-in-polygon).
    This rejects a Phase 1 frame-presence hit that only aliases an L0 sparse
    tile's 16 cells.
  * decodes the G target cell and records the demanded type's presence.
  * takes the Phase 1 spool requirement witness, clips that meeting source
    polygon to the target cell rectangle, and replays the build's round/clean
    drop test exactly as `_cenc.c:emit_piece` does (rint, dedup, spike
    collapse, `q < 3` drop at :586, `area2 == 0` drop at :592).

It writes:
  * `2-01_g-omits-cell-local-dvd-type_members.tsv` -- one row per seed, with a
    `membership` column (`2-01-member` or `2-03-open-tile-alias`).
  * `2-01_g-omits-cell-local-dvd-type_rejects.tsv` -- the rejected seeds for
    unit 2-03.
  * per-member R proof JSONs under
    `output/scratch-14/cell_local/proofs/<dump_row>.json` (scratch; the
    membership TSV records the path).
  * `output/scratch-14/cell_local/summary.json`.

No rule registration; no `_k1_cmp.c`/`_cenc.c`/rules JSON edit. It is safe to
re-run; it only writes the paths above.

Plan 25 memory bounds: require ``--max-seeds N`` (or explicit ``--all-seeds``),
drop full polygon coords from RAM after each proof write, process in batches
with ``gc.collect``, and refuse whole-file reads of ALLDATA / spool data
(``whole_file_guard``). Membership / proof semantics unchanged when the same
seed set is processed.
"""
from __future__ import annotations

import argparse
import csv
import gc
import json
import sys
import hashlib
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[4]
TRIAGE = Path(__file__).resolve().parent
sys.path[:0] = [str(ROOT / "parser"), str(ROOT / "parser/tools")]

from harness import walk  # noqa: E402
from kiwiw.model import MeshLocation  # noqa: E402
from kiwiw.parcel import decode_parcel  # noqa: E402
from kiwiw.spool import SpoolReader, decode_columns  # noqa: E402
from overlay_test import RReader  # noqa: E402
from r_neighbours import LeafIndex  # noqa: E402
from quantisation_roundtrip import Lattice, RAW  # noqa: E402
from whole_file_guard import refuse_whole_file_read  # noqa: E402

EVIDENCE = TRIAGE / "completeness_evidence.tsv"
R_DISC = Path("/run/media/codyh/464210-8480")
G_DISC = ROOT / "output/scratch-14/G_new"
SPOOL = ROOT / "output/extract_timing/spool"
SCRATCH = ROOT / "output/scratch-14/cell_local"
PROOFS = SCRATCH / "proofs"
G_SHA = "4ed9cd801bdd70992a9b7bd090803ffae349515f87546f044b21157e68e99d72"

NATIVE = ("level", "ix", "iy", "code", "p0", "p1", "p2", "p3", "p4", "p5", "p6",
          "shape", "vert")
MEMBERSHIP_HEADER = [
    "level", "ix", "iy", "code", "p0", "p1", "p2", "p3", "p4", "p5", "p6",
    "shape", "vert", "dump_row", "in_historic_188", "in_added_89",
    "R_polygon_count", "G_polygon_count", "r_slot_status", "r_meet_branches",
    "r_meeting_polygons", "r_proof_path", "g_cell_type_count",
    "spool_source_branch", "spool_source_cell", "spool_source_ncoord",
    "spool_source_bbox_raw", "clipped_ring_q", "clipped_ring_area2",
    "encoder_emits", "mechanism", "membership",
]


def digest(path: Path) -> str:
    with Path(path).open("rb") as fh:
        return hashlib.file_digest(fh, "sha256").hexdigest()


def decode_slot_shapes(reader: RReader, index: LeafIndex, level: int, ix: int, iy: int,
                       code: int):
    """Decode the covering leaf slot; return (status, matching polygons).

    A matching polygon is a decoded class-2 shape with >=3 coordinates and the
    demanded `code`, returned as {"coords": [(lat, lon)...], "latlon": ...}.
    """
    slot = index.get(ix, iy)
    out = {"status": slot.status, "polys": []}
    if slot.status != "resolved":
        return out
    for (lmr, blk, leaf_row) in slot.handles:
        lpath, le, lb, ptype, _, (fb, fc) = leaf_row
        frng = walk.leaf_frame_range(level, ptype, lpath, fc)
        fbr = walk.with_range(fb, frng)
        off = reader.volume.getsector(le.dsa, reader.ss, reader.ls)
        length = le.size * reader.ls
        reader.fh.seek(off)
        buf = reader.fh.read(length)
        loc = MeshLocation(level=level, parcel_type=ptype, blockset_index=blk[1],
                           block_index=blk[2], parcel_index=lpath[-1], bounds=fbr,
                           sector_addr=le.dsa, size_logical_sectors=le.size)
        parcel = decode_parcel(loc, buf, n_basic_map=lmr.n_basic_map,
                               n_ext_map=lmr.n_ext_map)
        shapes = parcel.background.shapes if parcel.background else []
        for s in shapes:
            if s.shape_class == 2 and len(s.coords) >= 3 and s.type_code == code:
                out["polys"].append({"leaf_path": list(lpath), "n_coords": len(s.coords),
                                     "coords": [list(c) for c in s.coords]})
    return out


def point_in_poly(px: float, py: float, xs, ys) -> bool:
    inside = False
    n = len(xs)
    for i in range(n):
        j = (i + 1) % n
        if (ys[i] > py) != (ys[j] > py):
            xi = (xs[j] - xs[i]) * (py - ys[i]) / (ys[j] - ys[i]) + xs[i]
            if px < xi:
                inside = not inside
    return inside


def r_meet_branches(xs, ys, code, ix, iy):
    """Checker-contract meet branches of one R polygon for cell (ix, iy)."""
    x0, x1 = float(min(xs)), float(max(xs))
    y0, y1 = float(min(ys)), float(max(ys))
    cx = int(np.floor((x0 + x1) / 2.0 / RAW))
    cy = int(np.floor((y0 + y1) / 2.0 / RAW))
    one = x0 >= cx * RAW and x1 <= (cx + 1) * RAW and y0 >= cy * RAW and y1 <= (cy + 1) * RAW
    hits = []
    if one and (cx, cy) == (ix, iy):
        rx, ry = np.rint(np.array(xs)), np.rint(np.array(ys))
        area = float(np.sum(rx * np.roll(ry, -1) - np.roll(rx, -1) * ry))
        if area != 0:
            hits.append({"branch": "a", "rounded_area2": area})
    if point_in_poly((ix + 0.5) * RAW, (iy + 0.5) * RAW, list(xs), list(ys)):
        hits.append({"branch": "c"})
    if not hits or hits[0]["branch"] != "a":
        for j in range(len(xs)):
            kx = int(np.floor(xs[j] / RAW))
            ky = int(np.floor(ys[j] / RAW))
            if (kx, ky) != (ix, iy):
                continue
            fx, fy = xs[j] - kx * RAW, ys[j] - ky * RAW
            if 1 <= fx <= RAW - 1 and 1 <= fy <= RAW - 1:
                hits.append({"branch": "b", "vertex": j, "cell_raw": [fx, fy]})
                break
    # stable order a, b, c
    order = {"a": 0, "b": 1, "c": 2}
    hits.sort(key=lambda h: order[h["branch"]])
    return hits


def clip_rect(poly, x0, y0, x1, y1):
    """Sutherland-Hodgman clip of a closed ring to an axis-aligned rectangle."""
    def run(pts, inside, inter):
        out = []
        n = len(pts)
        for i in range(n):
            a, b = pts[i], pts[(i + 1) % n]
            ia, ib = inside(a), inside(b)
            if ia:
                out.append(a)
                if not ib:
                    out.append(inter(a, b))
            elif ib:
                out.append(inter(a, b))
        return out

    def ix_(a, b):
        t = (x0 - a[0]) / (b[0] - a[0])
        return (x0, a[1] + t * (b[1] - a[1]))

    def iX(a, b):
        t = (x1 - a[0]) / (b[0] - a[0])
        return (x1, a[1] + t * (b[1] - a[1]))

    def iy_(a, b):
        t = (y0 - a[1]) / (b[1] - a[1])
        return (a[0] + t * (b[0] - a[0]), y0)

    def iY(a, b):
        t = (y1 - a[1]) / (b[1] - a[1])
        return (a[0] + t * (b[0] - a[0]), y1)

    p = list(poly)
    p = run(p, lambda a: a[0] >= x0, ix_)
    if not p:
        return []
    p = run(p, lambda a: a[0] <= x1, iX)
    if not p:
        return []
    p = run(p, lambda a: a[1] >= y0, iy_)
    if not p:
        return []
    return run(p, lambda a: a[1] <= y1, iY)


def encoder_piece(poly):
    """Replay `_cenc.c:emit_piece` round/clean/drop for a closed ring.

    Returns (q, area2, emitted). Mirrors rint rounding, consecutive dedup,
    closing dedup, spike collapse, `q < 3` drop (line 586) and `area2 == 0`
    drop (line 592). The build's rect path is only taken for whole-cell fills,
    which these slivers are not.
    """
    if not poly:
        return 0, 0, False
    qx, qy = [], []
    for x, y in poly:
        rx, ry = int(np.rint(x)), int(np.rint(y))
        if qx and qx[-1] == rx and qy[-1] == ry:
            continue
        qx.append(rx)
        qy.append(ry)
    q = len(qx)
    while q > 1 and qx[q - 1] == qx[0] and qy[q - 1] == qy[0]:
        q -= 1
        qx.pop()
        qy.pop()
    while q >= 3:
        found = -1
        for i in range(q):
            a = i - 1 if i else q - 1
            c = (i + 1) % q
            if qx[a] == qx[c] and qy[a] == qy[c]:
                found = i
                break
        if found < 0:
            break
        del qx[found], qy[found]
        q -= 1
        r = found if found < q else 0
        if q > 0:
            del qx[r], qy[r]
            q -= 1
    if q < 3:
        return q, 0, False
    area2 = sum(qx[i] * qy[(i + 1) % q] - qx[(i + 1) % q] * qy[i] for i in range(q))
    return q, area2, area2 != 0


def spool_source_shape(spool, lat, level, source_cell, ordinal):
    ix, iy = int(source_cell[1]), int(source_cell[2])
    idx = spool._load_idx(level)
    pos = np.nonzero((idx.ix == ix) & (idx.iy == iy))[0]
    if not len(pos):
        return None
    cols = decode_columns(spool._read_cell(level, int(idx.offset[pos[0]]),
                                           int(idx.length[pos[0]])))
    n = cols["b_nstored"].astype(np.int64)
    off = np.r_[0, np.cumsum(n)]
    a, b = int(off[ordinal]), int(off[ordinal + 1])
    return (lat.gx(cols["c_lon"][a:b]), lat.gy(cols["c_lat"][a:b]))



def polys_without_coords(polys):
    """Proof metadata without full coordinate rings (plan 25 RAM bound)."""
    out = []
    for p in polys:
        out.append({"leaf_path": p["leaf_path"], "n_coords": p["n_coords"]})
    return out


def assert_no_whole_file_discs(r_path: Path, g_path: Path, spool_dir: Path) -> None:
    """Fail closed if caller would need whole-file anon for discs/spool data.

    Leaf decode and SpoolReader.pread are the allowed paths; this only asserts
    the on-disk sizes exceed the refuse threshold so a mistaken read_bytes would
    be caught by whole_file_guard elsewhere.
    """
    for label, p in (("R", r_path), ("G", g_path),
                     ("spool_L0", spool_dir / "level_0.data")):
        if not p.exists():
            continue
        # Expect these to be large; calling refuse confirms the guard trips.
        try:
            refuse_whole_file_read(p)
            raise SystemExit(
                f"plan25: {label} {p} is unexpectedly under refuse threshold; "
                f"update WHOLE_FILE_REFUSE_BYTES or path"
            )
        except Exception as e:
            # WholeFileReadError expected for real discs/spool data
            if e.__class__.__name__ != "WholeFileReadError":
                raise


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--max-seeds", type=int, default=None,
                    help="Process at most N R>0 seeds (plan 25 bound; required unless --all-seeds)")
    ap.add_argument("--seed-offset", type=int, default=0,
                    help="Skip this many R>0 seeds before taking --max-seeds")
    ap.add_argument("--all-seeds", action="store_true",
                    help="Process every R>0 seed (343). Explicit opt-in; prefer windowed runs.")
    ap.add_argument("--batch-size", type=int, default=32,
                    help="gc.collect + drop buffers every N seeds (default 32)")
    ap.add_argument("--keep-proof-coords", action="store_true",
                    help="Retain full rings in proof JSON (default: strip coords after write meta)")
    ap.add_argument("--proofs-dir", type=Path, default=None,
                    help="Override proofs output directory (harness isolation)")
    args = ap.parse_args(argv)

    gdisc = G_DISC / "ALLDATA.KWI"
    rdisc = R_DISC / "ALLDATA.KWI"
    assert digest(gdisc) == G_SHA, "G disc sha mismatch"
    assert_no_whole_file_discs(rdisc, gdisc, SPOOL)
    SCRATCH.mkdir(parents=True, exist_ok=True)
    proofs_dir = Path(args.proofs_dir) if args.proofs_dir else PROOFS
    if not proofs_dir.is_absolute():
        proofs_dir = (ROOT / proofs_dir).resolve()
    else:
        proofs_dir = proofs_dir.resolve()
    proofs_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    with EVIDENCE.open() as fh:
        for r in csv.DictReader(fh, delimiter="\t"):
            rows.append(r)
    seeds_all = [r for r in rows if int(r["R_polygon_count"]) > 0]
    assert len(rows) == 776 and len(seeds_all) == 343, (len(rows), len(seeds_all))
    if args.all_seeds:
        if args.max_seeds is not None:
            ap.error("pass only one of --all-seeds / --max-seeds")
        seeds = seeds_all[args.seed_offset:]
    else:
        if args.max_seeds is None:
            raise SystemExit(
                "plan25: refuse uncapped cell_local run — pass --max-seeds N "
                "or explicit --all-seeds (see docs/plans/25-oom-memory-rca/)"
            )
        if args.max_seeds < 1:
            ap.error("--max-seeds must be >= 1")
        seeds = seeds_all[args.seed_offset: args.seed_offset + args.max_seeds]
    if not seeds:
        raise SystemExit("plan25: empty seed window")

    r_reader = RReader(str(R_DISC))
    g_reader = RReader(str(G_DISC))
    r_index = {0: LeafIndex(r_reader, 0)}
    g_index = {0: LeafIndex(g_reader, 0)}
    lat = Lattice(0)
    spool = SpoolReader(SPOOL)

    members, rejects = [], []
    branch_hist, mech_hist = {}, {}
    for r in seeds:
        level, ix, iy, code = int(r["level"]), int(r["ix"]), int(r["iy"]), int(r["code"])
        assert level == 0
        dump_row = int(r["dump_row"])

        rsl = decode_slot_shapes(r_reader, r_index[level], level, ix, iy, code)
        meet = []
        for p in rsl["polys"]:
            xs = [lat.gx(c[1]) for c in p["coords"]]
            ys = [lat.gy(c[0]) for c in p["coords"]]
            hits = r_meet_branches(xs, ys, code, ix, iy)
            if hits:
                meet.append({"leaf_path": p["leaf_path"], "n_coords": p["n_coords"],
                             "branches": [h["branch"] for h in hits],
                             "bbox_cell": [int(np.floor(min(xs) / RAW)), int(np.floor(max(xs) / RAW)),
                                           int(np.floor(min(ys) / RAW)), int(np.floor(max(ys) / RAW))]})

        gsl = decode_slot_shapes(g_reader, g_index[level], level, ix, iy, code)
        g_count = len(gsl["polys"])

        req = json.loads((ROOT / r["spool_K1_requirement_witness"]).read_text())
        src = req.get("source")
        mech = {"spool_source_branch": None, "spool_source_cell": None,
                "spool_source_ncoord": None, "spool_source_bbox_raw": None,
                "clipped_ring_q": None, "clipped_ring_area2": None,
                "encoder_emits": None, "mechanism": "no_cell_local_r"}
        if meet and src is not None:
            arrs = spool_source_shape(spool, lat, level, src["source_cell"],
                                      src["background_ordinal"])
            if arrs is not None:
                xs, ys = arrs
                poly = list(zip(xs.tolist(), ys.tolist()))
                cl = clip_rect(poly, ix * RAW, iy * RAW, (ix + 1) * RAW, (iy + 1) * RAW)
                q, area2, emits = encoder_piece(cl)
                mech = {
                    "spool_source_branch": src["branch"],
                    "spool_source_cell": src["source_cell"],
                    "spool_source_ncoord": src["n_coords"],
                    "spool_source_bbox_raw": [round(v, 3) for v in src["bbox_global_raw"]],
                    "clipped_ring_q": q, "clipped_ring_area2": area2,
                    "encoder_emits": emits,
                    "mechanism": ("encoder_drops_clipped_source_sliver" if not emits
                                  else "source_piece_representable"),
                }
        proof = {
            "dump_row": dump_row,
            "native_key": {k: int(r[k]) for k in NATIVE},
            "r_slot_status": rsl["status"],
            "g_slot_status": gsl["status"],
            "r_matching_polygons": rsl["polys"],
            "r_cell_local_meets": meet,
            "g_cell_type_count": g_count,
            "spool_requirement_witness": r["spool_K1_requirement_witness"],
            "mechanism": mech,
        }
        # Strip full rings from the in-RAM proof before/after write (plan 25).
        if not args.keep_proof_coords:
            proof["r_matching_polygons"] = polys_without_coords(rsl["polys"])
        proof_path = proofs_dir / f"{dump_row}.json"
        proof_path.write_text(json.dumps(proof, sort_keys=True, indent=1) + "\n")
        # Drop large decode buffers each seed; batch GC.
        rsl["polys"] = polys_without_coords(rsl["polys"])
        gsl["polys"] = []
        del proof

        branches = sorted({b for m in meet for b in m["branches"]})
        member = bool(meet) and g_count == 0
        row_out = [int(r[k]) for k in NATIVE] + [
            dump_row, int(r["in_historic_188"]), int(r["in_added_89"]),
            int(r["R_polygon_count"]), int(r["G_polygon_count"]), rsl["status"],
            "|".join(branches), len(meet),
            str(proof_path.relative_to(ROOT) if proof_path.is_relative_to(ROOT)
                else proof_path),
            g_count,
            mech["spool_source_branch"], mech["spool_source_cell"],
            mech["spool_source_ncoord"],
            json.dumps(mech["spool_source_bbox_raw"]) if mech["spool_source_bbox_raw"] else "",
            mech["clipped_ring_q"], mech["clipped_ring_area2"],
            mech["encoder_emits"], mech["mechanism"],
            "2-01-member" if member else "2-03-open-tile-alias",
        ]
        (members if member else rejects).append(row_out)
        key = "|".join(branches) if branches else "none"
        branch_hist[key] = branch_hist.get(key, 0) + 1
        mech_hist[mech["mechanism"]] = mech_hist.get(mech["mechanism"], 0) + 1
        if (len(members) + len(rejects)) % max(1, args.batch_size) == 0:
            gc.collect()

    def write_tsv(path, data):
        with path.open("w", newline="") as fh:
            w = csv.writer(fh, delimiter="\t", lineterminator="\n")
            w.writerow(MEMBERSHIP_HEADER)
            w.writerows(data)

    # Plan 25: never overwrite the committed full membership TSVs from a
    # windowed probe. Full TSV write requires --all-seeds.
    if args.all_seeds:
        write_tsv(TRIAGE / "2-01_g-omits-cell-local-dvd-type_members.tsv", members)
        write_tsv(TRIAGE / "2-01_g-omits-cell-local-dvd-type_rejects.tsv", rejects)
    else:
        probe = SCRATCH / "windowed"
        probe.mkdir(parents=True, exist_ok=True)
        write_tsv(probe / f"members_offset{args.seed_offset}_n{len(seeds)}.tsv", members)
        write_tsv(probe / f"rejects_offset{args.seed_offset}_n{len(seeds)}.tsv", rejects)

    summary = {
        "seeds": len(seeds),
        "seeds_available": len(seeds_all),
        "seed_offset": args.seed_offset,
        "max_seeds": args.max_seeds,
        "all_seeds": bool(args.all_seeds),
        "proof_coords_retained": bool(args.keep_proof_coords),
        "plan25_memory_bounds": True,
        "members_2_01": len(members),
        "rejects_2_03_open_tile_alias": len(rejects),
        "g_absence_on_all_seeds": all(int(r["G_polygon_count"]) == 0 for r in seeds),
        "r_cell_local_branch_histogram": branch_hist,
        "mechanism_histogram": mech_hist,
        "expected_completeness_movement": len(members),
        "disc": {"G_sha256": G_SHA, "R_path": str(R_DISC / "ALLDATA.KWI"),
                 "spool": str(SPOOL)},
        "rejects": [{"dump_row": x[13], "key": x[:4], "in_historic_188": x[14]}
                    for x in rejects],
    }
    (SCRATCH / "summary.json").write_text(json.dumps(summary, sort_keys=True, indent=2) + "\n")
    print(json.dumps(summary, sort_keys=True, indent=2))
    r_reader.fh.close()
    g_reader.fh.close()
    spool.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(None))
