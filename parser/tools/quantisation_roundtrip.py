"""Per-vertex quantisation round-trip over a build spool: the vertices G writes.

Plan 03, DESIGN.md "Phase 3 -- Outcome, as amended": "lat/lon to pixel to
lat/lon agrees within half a pixel for every vertex written".

Every vertex is measured in the frame G writes it in: the spool cell's own
Map Frame (`osm_to_parcel_geometry.frame_bounds`, range `g_frame_range` --
4096 at every level; G never aliases an L0 sparse tile, `g_frame_class`).

- **Background shapes (`c_`)** are clipped to the frame, never clamped
  (3-07, `kiwiw.clip` -- the encoders' own algorithm). The written vertices
  are the clipped pieces' vertices: original in-frame vertices plus inserted
  crossing, corner and densified points. Each is compared with its exact
  pre-rounding position on the clipped geometry (error <= 0.5 raw), and
  additionally asserted (a) inside the parcel's clip rectangle, (b) on 0 or
  `range` of its crossed axis exactly when it is a crossing vertex, and
  (c) one signed-8-bit delta (`127 * mult`) from its predecessor. Any
  breach counts as failing.
- **Road nodes (`n_`), road intermediate points (`p_`) and name anchors
  (`s_`, where both lat and lon are present)** are written clamped to
  `[0, range]` by their encoders (untouched by 3-07): round, clamp, compare.

**Half a pixel** is half of one raw unit: the frame's lon (lat) extent
divided by `2 * range`. The per-class values in degrees are in the output.

A divided sub-parcel is clipped to its quadrant/cell of the parent frame
(`divide._sub_frame`); division is a build-time decision this tool does not
replay, so every spool cell is measured against its whole frame.

The spool's `n_x`/`n_y` columns (pixel values precomputed at extraction)
are not used: the round-trip starts from lat/lon, as the encoders do.

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

from kiwiw import clip  # noqa: E402
from osm_to_parcel_geometry import TileGrid, frame_bounds, g_frame_class  # noqa: E402

KINDS = ("n", "p", "c", "s")
_EPS = 1e-9  # float slack on the 0.5 bound; round() alone never exceeds 0.5
_PROV = ("original", "crossing", "corner", "densified")


class Frames:
    """(level, ix, iy) -> (class, range, lat_lo, lon_lo, lat_span, lon_span,
    bounds): the frame G writes cell (ix, iy) in."""

    def __init__(self, level: int, grid: TileGrid | None = None):
        self.level = level
        self.grid = grid or TileGrid.from_reference(level)
        self.cls = g_frame_class(level)

    def frame(self, ix: int, iy: int):
        b = frame_bounds(ix, iy, self.grid)
        return (self.cls, b.coord_range, b.lat_lo, b.lon_lo,
                b.lat_hi - b.lat_lo, b.lon_hi - b.lon_lo, b)


def cell_vertices(cols: dict) -> dict:
    """{kind: (lat, lon)} arrays of one cell's point vertices (n, p, s), plus
    the count of name records without a full position (not a vertex)."""
    out = {"n": (cols["n_lat"], cols["n_lon"]), "p": (cols["p_lat"], cols["p_lon"])}
    pr = cols["s_present"]
    has = (pr & 3) == 3
    out["s"] = (cols["s_lat"][has], cols["s_lon"][has])
    return out, int(len(pr) - int(has.sum()))


def measure(lat, lon, fr) -> tuple:
    """(n, failing, worst error raw) for one batch of road/name vertices in
    frame `fr`, quantised as their encoders write them: round, clamp to
    `[0, range]`. A clamped vertex errs by its overshoot and fails."""
    _, rng, lat_lo, lon_lo, lat_sp, lon_sp = fr[:6]
    fx = (np.asarray(lon, dtype=np.float64) - lon_lo) / lon_sp * rng
    fy = (np.asarray(lat, dtype=np.float64) - lat_lo) / lat_sp * rng
    qx, qy = np.clip(np.round(fx), 0, rng), np.clip(np.round(fy), 0, rng)
    err = np.maximum(np.abs(qx - fx), np.abs(qy - fy))
    n = int(len(fx))
    if n == 0:
        return 0, 0, 0.0
    return n, int((err > 0.5 + _EPS).sum()), float(err.max())


def _blank_bg() -> dict:
    return {"input_vertices": 0, "shapes": 0, "shapes_dropped": 0, "records": 0,
            "max_deltas_per_record": 0, "outside_rect": 0, "crossing_off_edge": 0,
            "step_overflow": 0, "written_by_provenance": {k: 0 for k in _PROV}}


def measure_backgrounds(cols: dict, fr) -> dict:
    """Clip every background line/polygon of one cell to frame `fr` exactly
    as the encoders do and check each written vertex."""
    b = fr[6]
    rng = fr[1]
    rect = clip.clip_rect(b, rng)
    x0, y0, x1, y1 = rect
    st = {"vertices": 0, "failing": 0, "worst_error_raw": 0.0, **_blank_bg()}
    cls, nst, mult = cols["b_class"], cols["b_nstored"], cols["b_mult"]
    fxa = (np.asarray(cols["c_lon"], dtype=np.float64) - b.lon_lo) / (b.lon_hi - b.lon_lo) * rng
    fya = (np.asarray(cols["c_lat"], dtype=np.float64) - b.lat_lo) / (b.lat_hi - b.lat_lo) * rng
    starts = np.concatenate(([0], np.cumsum(nst, dtype=np.int64)))
    for i in range(len(cls)):
        c = int(cls[i])
        a, e = int(starts[i]), int(starts[i + 1])
        if c == 0 or e == a:
            continue
        mc = max(int(mult[i]), 1)
        st["shapes"] += 1
        st["input_vertices"] += e - a
        pieces = clip.shape_pieces(fxa[a:e].tolist(), fya[a:e].tolist(), c == 2, rect, mc)
        if not pieces:
            st["shapes_dropped"] += 1
        lim = 127 * mc
        for piece in pieces:
            st["records"] += 1
            st["max_deltas_per_record"] = max(st["max_deltas_per_record"], len(piece) - 1)
            px = py = None
            for x, y, fx, fy, kind in piece:
                bad = False
                err = max(abs(x - fx), abs(y - fy))
                if err > st["worst_error_raw"]:
                    st["worst_error_raw"] = err
                if err > 0.5 + _EPS:
                    bad = True
                if not (x0 <= x <= x1 and y0 <= y <= y1):
                    st["outside_rect"] += 1
                    bad = True
                if (kind == clip.CROSS_X and fx not in (x0, x1)) or \
                        (kind == clip.CROSS_Y and fy not in (y0, y1)):
                    st["crossing_off_edge"] += 1
                    bad = True
                if px is not None and (abs(x - px) > lim or abs(y - py) > lim):
                    st["step_overflow"] += 1
                    bad = True
                px, py = x, y
                st["vertices"] += 1
                st["failing"] += bad
                st["written_by_provenance"][clip.KIND_NAMES[kind]] += 1
    return st


def _blank_class(fr) -> dict:
    _, rng, _, _, lat_sp, lon_sp = fr[:6]
    return {"range": rng, "half_pixel_deg": {"lat": lat_sp / (2 * rng), "lon": lon_sp / (2 * rng)},
            "cells": 0, "vertices": 0, "failing": 0, "worst_error_raw": 0.0,
            "per_kind": {k: {"vertices": 0, "failing": 0, "worst_error_raw": 0.0} for k in KINDS},
            "background": _blank_bg()}


def _merge_bg(a: dict, b: dict) -> None:
    for key in ("input_vertices", "shapes", "shapes_dropped", "records", "outside_rect",
                "crossing_off_edge", "step_overflow"):
        a[key] += b[key]
    a["max_deltas_per_record"] = max(a["max_deltas_per_record"], b["max_deltas_per_record"])
    for k in _PROV:
        a["written_by_provenance"][k] += b["written_by_provenance"][k]


def _merge(a: dict, b: dict) -> None:
    for key in ("cells", "vertices", "failing"):
        a[key] += b[key]
    a["worst_error_raw"] = max(a["worst_error_raw"], b["worst_error_raw"])
    for k in KINDS:
        for f in ("vertices", "failing"):
            a["per_kind"][k][f] += b["per_kind"][k][f]
        a["per_kind"][k]["worst_error_raw"] = max(a["per_kind"][k]["worst_error_raw"],
                                                  b["per_kind"][k]["worst_error_raw"])
    _merge_bg(a["background"], b["background"])


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
        for k in ("n", "p", "s"):
            n, fail, er = measure(*verts[k], fr)
            st["vertices"] += n
            st["failing"] += fail
            st["worst_error_raw"] = max(st["worst_error_raw"], er)
            st["per_kind"][k]["vertices"] += n
            st["per_kind"][k]["failing"] += fail
            st["per_kind"][k]["worst_error_raw"] = max(st["per_kind"][k]["worst_error_raw"], er)
        bg = measure_backgrounds(cols, fr)
        st["vertices"] += bg["vertices"]
        st["failing"] += bg["failing"]
        st["worst_error_raw"] = max(st["worst_error_raw"], bg["worst_error_raw"])
        st["per_kind"]["c"]["vertices"] += bg["vertices"]
        st["per_kind"]["c"]["failing"] += bg["failing"]
        st["per_kind"]["c"]["worst_error_raw"] = max(st["per_kind"]["c"]["worst_error_raw"],
                                                     bg["worst_error_raw"])
        _merge_bg(st["background"], bg)
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
    totals = {"vertices": 0, "failing": 0, "worst_error_raw": 0.0,
              "per_kind": {k: {"vertices": 0, "failing": 0, "worst_error_raw": 0.0} for k in KINDS},
              "background": _blank_bg()}
    for lv in levels.values():
        for st in lv.values():
            for key in ("vertices", "failing"):
                totals[key] += st[key]
            totals["worst_error_raw"] = max(totals["worst_error_raw"], st["worst_error_raw"])
            for k in KINDS:
                for f in ("vertices", "failing"):
                    totals["per_kind"][k][f] += st["per_kind"][k][f]
                totals["per_kind"][k]["worst_error_raw"] = max(
                    totals["per_kind"][k]["worst_error_raw"], st["per_kind"][k]["worst_error_raw"])
            _merge_bg(totals["background"], st["background"])
    return {
        "criterion": ("every written vertex agrees with its exact pre-rounding position within "
                      "half a pixel (= frame extent / (2 * range) = 0.5 raw units). Background "
                      "vertices are the clipped geometry's (kiwiw.clip) and must also lie in the "
                      "parcel's clip rectangle, on the crossed edge exactly when a crossing, and "
                      "one signed-8-bit delta from their predecessor; road nodes/points and name "
                      "anchors are rounded then clamped to [0, range] as their encoders write them"),
        "coverage": {
            "kinds": {"n": "road nodes (n_lat/n_lon)", "p": "road intermediate points "
                      "(p_lat/p_lon)", "c": "background vertices written after clipping "
                      "(from c_lat/c_lon)",
                      "s": "name anchors with both lat and lon present (s_lat/s_lon)"},
            "names_without_position": no_pos,
            "not_used": "n_x/n_y (extraction-time pixels); the round-trip starts from lat/lon",
            "not_modelled": "division: sub-parcels clip to their quadrant/cell (build-time)",
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
    print(f"vertices={t['vertices']} failing={t['failing']} "
          f"worst_error_raw={t['worst_error_raw']:.6f} "
          f"per_kind={json.dumps(t['per_kind'], sort_keys=True)} "
          f"background={json.dumps(t['background'], sort_keys=True)} "
          f"wall={time.monotonic() - t0:.1f}s", file=sys.stderr)
    return 0 if res["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
