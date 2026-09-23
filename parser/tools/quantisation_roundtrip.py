#!/usr/bin/env python3
"""Per-vertex quantisation round-trip over a build spool.

Plan 03, DESIGN.md "Phase 3 -- Outcome, as amended": "lat/lon to pixel to
lat/lon agrees within half a pixel for every vertex written".

For every vertex in the spool -- road nodes (`n_lat`/`n_lon`), road
intermediate points (`p_`), background shape vertices (`c_`) and name
anchors (`s_`, where the record carries both lat and lon) -- this projects
the vertex into its native frame at `coordconv.range_for`, quantises
(round, then clamp to `[0, range]` inclusive, as an encoder must), maps back
and measures the error in raw units.

**Half a pixel** is half of one raw unit: the frame's lon (lat) extent
divided by `2 * range`. The per-class values in degrees are in the output.

**What this really measures is clamping.** `round()` alone cannot err by
more than half a raw unit, so a vertex fails the half-pixel criterion only
when it falls outside its frame and is clamped. The output therefore
reports the clamped vertices -- per (level, class): count and the worst
overshoot in raw units -- not just a boolean.

**The frame does not depend on division.** A divided sub-parcel is encoded
in its parent's 4096 frame, so a vertex's frame is a function of
`(level, ix, iy)` and `coord_scale.json`'s `class_rule` alone: the spool
cell's slot (range 4096), or at level 0 in a non-urban tile the 4x4
integrated-parcel tile (class `sparse`). No division policy is modelled.

The spool's `n_x`/`n_y` columns (pixel values precomputed at extraction)
are not used: the round-trip starts from lat/lon, as the encoders will.

Output is deterministic JSON (sorted keys, no timestamps, no paths).
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from kiwiw.coordconv import _COORD_SCALE_PATH, range_for  # noqa: E402
from kiwiw.grid import ReferenceGrid  # noqa: E402

KINDS = ("n", "p", "c", "s")
_EPS = 1e-9  # float slack on the 0.5 bound; round() alone never exceeds 0.5


class Frames:
    """(level, ix, iy) -> (class, range, lat_lo, lon_lo, lat_span, lon_span)."""

    def __init__(self, level: int, grid: ReferenceGrid | None = None, class_rule=None):
        grid = grid or ReferenceGrid.load()
        if class_rule is None:
            class_rule = json.loads(Path(_COORD_SCALE_PATH).read_text())["class_rule"]
        lmr = grid._level_dict(level)
        c = grid.coverage
        lg = grid.level(level)
        self.level = level
        self.lat0, self.lon0 = c["lat_lo"], c["lon_lo"]
        self.cell_lat, self.cell_lon = lg.cell_lat, lg.cell_lon
        self.nbs_lng = 1 + lmr["n_blocksets_lng"]
        self.nbl_lng, self.nbl_lat = 1 + lmr["n_blocks_lng"], 1 + lmr["n_blocks_lat"]
        self.npc_lng, self.npc_lat = 1 + lmr["n_parcels_lng"][0], 1 + lmr["n_parcels_lat"][0]
        self.tile = int(class_rule["l0_tile"])
        self.urban = {tuple(t) for t in class_rule["urban_tiles"]}

    def locate(self, ix: int, iy: int):
        bsx, rx = divmod(ix, self.nbl_lng * self.npc_lng)
        blx, lx = divmod(rx, self.npc_lng)
        bsy, ry = divmod(iy, self.nbl_lat * self.npc_lat)
        bly, ly = divmod(ry, self.npc_lat)
        return bsy * self.nbs_lng + bsx, bly * self.nbl_lng + blx, lx, ly

    def frame(self, ix: int, iy: int):
        if self.level != 0:
            cls, n, x0, y0 = "full", 1, ix, iy
        else:
            bs, blk, lx, ly = self.locate(ix, iy)
            t = self.tile
            if (bs, blk, ly // t, lx // t) in self.urban:
                cls, n, x0, y0 = "urban", 1, ix, iy
            else:
                cls, n, x0, y0 = "sparse", t, ix - lx % t, iy - ly % t
        rng = range_for(self.level, cls, "normal")
        return (cls, rng, self.lat0 + y0 * self.cell_lat, self.lon0 + x0 * self.cell_lon,
                n * self.cell_lat, n * self.cell_lon)


def cell_vertices(cols: dict) -> dict:
    """{kind: (lat, lon)} arrays of one cell's vertices, plus the count of
    name records without a full position (not a vertex)."""
    out = {"n": (cols["n_lat"], cols["n_lon"]), "p": (cols["p_lat"], cols["p_lon"]),
           "c": (cols["c_lat"], cols["c_lon"])}
    pr = cols["s_present"]
    has = (pr & 3) == 3
    out["s"] = (cols["s_lat"][has], cols["s_lon"][has])
    return out, int(len(pr) - int(has.sum()))


def measure(lat, lon, fr) -> tuple:
    """(n, failing, clamped, worst overshoot raw, worst error raw) for one
    batch of vertices in frame `fr`."""
    _, rng, lat_lo, lon_lo, lat_sp, lon_sp = fr
    dlon = np.mod(np.asarray(lon, dtype=np.float64) - lon_lo + 180.0, 360.0) - 180.0
    fx = dlon / lon_sp * rng
    fy = (np.asarray(lat, dtype=np.float64) - lat_lo) / lat_sp * rng
    rx, ry = np.round(fx), np.round(fy)
    # Clamped: the rounded pixel falls outside [0, range] (float noise at an
    # edge rounds back onto it and is not a clamp).
    clamped = (rx < 0) | (rx > rng) | (ry < 0) | (ry > rng)
    over = np.maximum(np.maximum(fx - rng, -fx), np.maximum(fy - rng, -fy))
    over = np.where(clamped, np.maximum(over, 0.0), 0.0)
    qx, qy = np.clip(rx, 0, rng), np.clip(ry, 0, rng)
    err = np.maximum(np.abs(qx - fx), np.abs(qy - fy))
    n = int(len(fx))
    if n == 0:
        return 0, 0, 0, 0.0, 0.0
    return (n, int((err > 0.5 + _EPS).sum()), int(clamped.sum()),
            float(over.max()), float(err.max()))


def _blank_class(fr) -> dict:
    _, rng, _, _, lat_sp, lon_sp = fr
    return {"range": rng, "half_pixel_deg": {"lat": lat_sp / (2 * rng), "lon": lon_sp / (2 * rng)},
            "cells": 0, "vertices": 0, "failing": 0, "clamped": 0,
            "worst_overshoot_raw": 0.0, "worst_error_raw": 0.0,
            "per_kind": {k: {"vertices": 0, "failing": 0} for k in KINDS}}


def _merge(a: dict, b: dict) -> None:
    for key in ("cells", "vertices", "failing", "clamped"):
        a[key] += b[key]
    for key in ("worst_overshoot_raw", "worst_error_raw"):
        a[key] = max(a[key], b[key])
    for k in KINDS:
        for f in ("vertices", "failing"):
            a["per_kind"][k][f] += b["per_kind"][k][f]


def run_cells(level: int, cells, frames: Frames) -> tuple[dict, int]:
    """Aggregate `(ix, iy, cols)` cells into {class: stats}; also returns
    the count of name records without a full position."""
    per: dict = {}
    no_pos = 0
    for ix, iy, cols in cells:
        fr = frames.frame(ix, iy)
        st = per.setdefault(fr[0], _blank_class(fr))
        st["cells"] += 1
        verts, np_ = cell_vertices(cols)
        no_pos += np_
        for k in KINDS:
            n, fail, clamp, ov, er = measure(*verts[k], fr)
            if not n:
                continue
            st["vertices"] += n
            st["failing"] += fail
            st["clamped"] += clamp
            st["worst_overshoot_raw"] = max(st["worst_overshoot_raw"], ov)
            st["worst_error_raw"] = max(st["worst_error_raw"], er)
            st["per_kind"][k]["vertices"] += n
            st["per_kind"][k]["failing"] += fail
    return per, no_pos


def _legacy(spool_dir: str) -> bool:
    """True for a legacy pickle spool (`kiwiw.spool_legacy`), which
    `output/spool` still is; read through the legacy reader's own format."""
    from kiwiw.spool import IDX_MAGIC
    idx = sorted(Path(spool_dir).glob("level_*.idx"))
    return bool(idx) and idx[0].read_bytes()[:len(IDX_MAGIC)] != IDX_MAGIC


def _levels_and_counts(spool_dir: str) -> list:
    if _legacy(spool_dir):
        from kiwiw import spool_legacy
        rd = spool_legacy.SpoolReader(spool_dir)
        return [(lv, len(rd._load_idx(lv)["cells"])) for lv in sorted(rd.levels())]
    from kiwiw.spool import SpoolReader
    rd = SpoolReader(spool_dir)
    try:
        return [(lv, rd.n_cells(lv)) for lv in sorted(rd.levels())]
    finally:
        rd.close()


def _iter_legacy(spool_dir: str, level: int, start: int, stop: int):
    import pickle
    from kiwiw import spool_legacy
    from kiwiw.spool import content_to_columns
    cells = spool_legacy.SpoolReader(spool_dir)._load_idx(level)["cells"][start:stop]
    with open(Path(spool_dir) / f"level_{level}.data", "rb") as fh:
        for ix, iy, offsets in cells:
            merged = {"roads": [], "backgrounds": [], "names": []}
            for off in offsets:
                fh.seek(off)
                _, _, content = pickle.load(fh)
                for key in merged:
                    merged[key].extend(content.get(key, []))
            yield ix, iy, content_to_columns(merged)


def _work(args) -> tuple:
    spool_dir, level, start, stop = args
    if _legacy(spool_dir):
        return level, run_cells(level, _iter_legacy(spool_dir, level, start, stop), Frames(level))
    from kiwiw.spool import SpoolReader
    reader = SpoolReader(spool_dir)
    try:
        return level, run_cells(level, reader.iter_cell_columns(level, start, stop), Frames(level))
    finally:
        reader.close()


def roundtrip(spool_dir: str, workers: int = 1, chunk: int = 4000) -> dict:
    jobs = [(spool_dir, level, a, min(a + chunk, n))
            for level, n in _levels_and_counts(spool_dir) for a in range(0, n, chunk)]
    levels: dict = {}
    no_pos = 0
    if workers > 1:
        with ProcessPoolExecutor(workers) as ex:
            results = list(ex.map(_work, jobs))
    else:
        results = [_work(j) for j in jobs]
    for level, (per, npos) in results:
        no_pos += npos
        lv = levels.setdefault(str(level), {})
        for cls, st in per.items():
            if cls in lv:
                _merge(lv[cls], st)
            else:
                lv[cls] = st
    totals = {"vertices": 0, "failing": 0, "clamped": 0, "worst_overshoot_raw": 0.0,
              "per_kind": {k: {"vertices": 0, "failing": 0} for k in KINDS}}
    for lv in levels.values():
        for st in lv.values():
            for key in ("vertices", "failing", "clamped"):
                totals[key] += st[key]
            totals["worst_overshoot_raw"] = max(totals["worst_overshoot_raw"],
                                                st["worst_overshoot_raw"])
            for k in KINDS:
                for f in ("vertices", "failing"):
                    totals["per_kind"][k][f] += st["per_kind"][k][f]
    return {
        "criterion": ("lat/lon -> round -> clamp to [0, range] -> lat/lon agrees within half "
                      "a pixel; half a pixel = frame extent / (2 * range) = 0.5 raw units"),
        "coverage": {
            "kinds": {"n": "road nodes (n_lat/n_lon)", "p": "road intermediate points "
                      "(p_lat/p_lon)", "c": "background shape vertices (c_lat/c_lon)",
                      "s": "name anchors with both lat and lon present (s_lat/s_lon)"},
            "names_without_position": no_pos,
            "not_used": "n_x/n_y (extraction-time pixels); the round-trip starts from lat/lon",
        },
        "levels": {lv: {c: levels[lv][c] for c in sorted(levels[lv])}
                   for lv in sorted(levels, key=int)},
        "pass": totals["failing"] == 0,
        "totals": totals,
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--spool", required=True, help="spool directory")
    ap.add_argument("--out", required=True, help="output JSON path")
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args(argv)
    t0 = time.monotonic()
    res = roundtrip(args.spool, workers=args.workers)
    Path(args.out).write_text(json.dumps(res, indent=2, sort_keys=True) + "\n")
    t = res["totals"]
    print(f"vertices={t['vertices']} failing={t['failing']} clamped={t['clamped']} "
          f"worst_overshoot_raw={t['worst_overshoot_raw']:.3f} "
          f"per_kind={json.dumps(t['per_kind'], sort_keys=True)} "
          f"wall={time.monotonic() - t0:.1f}s", file=sys.stderr)
    return 0 if res["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
