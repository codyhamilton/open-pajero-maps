#!/usr/bin/env python3
"""Build ALLDATA.KWI from a spool written by `osm_to_parcel_geometry.py`.

End-to-end pipeline:
  1. Reads a spool directory (`kiwiw.spool.SpoolReader`) written by
     `osm_to_parcel_geometry.py`'s extraction pass -- never reads a PBF or
     touches OSM data itself.
  2. For each requested level, encodes every spooled parcel's road/
     background/name content into a Map Frame (`kiwiw.synth`), passing
     `level=` explicitly to `build_name_frame_bytes()` (unit 11's amendment:
     omitting it silently reverts to the legacy type-1-only string path).
  3. Calls `kiwiw.alldata_writer.build_alldata_kwi()` to assemble the whole
     container: the reference's per-level LMR/BSMR/BMT shape
     (`kiwiw.grid.ReferenceGrid`), the record-29 copy-through frame, and
     the wrap-safe coverage box -- all from checked-in `grid.json`, never
     a mounted disc (docs/design/target-disc.md, "Grid contract").
  4. Writes the output file and a `manifest.json` beside it.

Usage::

    python3 parser/build_alldata.py                      # spool at output/spool, all 7 levels
    python3 parser/build_alldata.py --fixture perth \\
        --spool output/spool-perth --out output/perth/ALLDATA.KWI
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import struct
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from kiwiw import alldata_writer as aw
from kiwiw import cenc
from kiwiw import divide
from kiwiw.spill import FrameSpill
from kiwiw import synth
from kiwiw.grid import ReferenceGrid
from kiwiw.spool import SpoolReader

# Read-only imports from the extractor: TileGrid/parcel_bounds are pure
# geometry helpers with no OSM/PBF dependency of their own (build_alldata.py
# never calls extract_parcel_geometry() -- that is unit 07/osm_to_parcel_
# geometry.py's own job, run as a separate, prior step). Not touching that
# module's own contents; this is the same "TileGrid.from_reference()" every
# extraction run already uses to agree on cell boundaries.
from osm_to_parcel_geometry import FIXTURE_BBOXES, TileGrid, assign_to_parcel, parcel_bounds

DEFAULT_SPOOL = str(Path(__file__).resolve().parent.parent / "output" / "spool")
DEFAULT_OUT = str(Path(__file__).resolve().parent.parent / "output" / "ALLDATA.KWI")
DEFAULT_LEVELS = [12, 10, 8, 6, 4, 2, 0]

# `synth.build_map_frame_bytes()`'s hard format ceiling (Map Frame header's
# size field is a 16-bit word count: `total_size // 2` must fit in u16) --
# see synth.py:851 and unit 12's done evidence (IMPLEMENTATION.md, "Unit
# 12"). Unit 13's Amendment: the threshold `plan_divisions()` divides
# against is `min(profile's per-level mapframe_size.max, this ceiling)`,
# not the profile max alone -- some of R's own level-0 parcels the profile
# measured are themselves already divided sub-frames, not whole-cell
# frames, so the profile max can itself exceed what this format can
# represent undivided.
U16_MAPFRAME_BYTE_CEILING = 131070

# Brief 32: levels where a divided sub-cell also receives the nearby road
# names its point-based re-tiling left with a neighbouring sub-cell. Only L0:
# R's L0 name density is ~10x G's (name_count 0.10x, declared deviation), so
# added road names move toward R; L2-L8 name counts are already at 0.75-1.2x.
NAME_HALO_LEVELS = (0,)

_PROFILE_MAP_PATH = (
    Path(__file__).resolve().parent / "refdata" / "profile" / "map.json"
)


def _load_level_kind_budgets() -> dict[int, dict[str, int]]:
    """Per-level `{road, background, name}` sub-frame byte budgets. Brief 34:
    the u16 frame ceiling is the only known hard limit, so every kind at every
    level is budgeted at `U16_MAPFRAME_BYTE_CEILING`; R's per-kind maxima are
    observations of R, not limits."""
    with open(_PROFILE_MAP_PATH) as fh:
        profile = json.load(fh)
    return {int(lv): {k: U16_MAPFRAME_BYTE_CEILING for k in ("road", "background", "name")}
            for lv in profile.get("levels", {})}


def _load_level_thresholds() -> dict[int, int]:
    """Per-level `plan_divisions()` threshold. Brief 34: the u16 ceiling for
    every level (R's `mapframe_size.max` is an observation, not a limit)."""
    with open(_PROFILE_MAP_PATH) as fh:
        profile = json.load(fh)
    return {int(lv): U16_MAPFRAME_BYTE_CEILING for lv in profile.get("levels", {})}

# This unit populates only the main map layer; route-planning/index-data
# flags in the copy-through Volume Header (see alldata_writer.py) describe
# R's own disc contents, not this build's -- record what's actually built
# here so the harness's `layers_present` config can be checked against it.
LAYERS_PRESENT = ["map"]


def _level_dims(grid: ReferenceGrid, level: int) -> dict:
    lvl = grid._level_dict(level)
    return dict(
        npc_lat=1 + lvl["n_parcels_lat"][0],
        npc_lng=1 + lvl["n_parcels_lng"][0],
    )


def _fixture_cell_range(level: int, fixture: str, tile_grid: TileGrid) -> tuple[int, int, int, int]:
    """(ix_lo, ix_hi, iy_lo, iy_hi) inclusive global-cell range covering a
    named fixture bbox at `level`, via the same `assign_to_parcel()` the
    extractor itself uses -- so `--fixture perth` restricts to exactly the
    same global cells `osm_to_parcel_geometry.py --fixture perth` would
    have populated, regardless of what else the input spool contains."""
    lon_l, lat_b, lon_r, lat_t = FIXTURE_BBOXES[fixture]
    corners = [
        assign_to_parcel(lat_b, lon_l, tile_grid),
        assign_to_parcel(lat_b, lon_r, tile_grid),
        assign_to_parcel(lat_t, lon_l, tile_grid),
        assign_to_parcel(lat_t, lon_r, tile_grid),
    ]
    ixs = [c[0] for c in corners if c is not None]
    iys = [c[1] for c in corners if c is not None]
    return min(ixs), max(ixs), min(iys), max(iys)


def _encode_one(level: int, ix: int, iy: int, bounds, content: dict) -> bytes:
    """`plan_divisions()`'s `encode` callback (bytes only)."""
    return _measure_one(level, ix, iy, bounds, content)[0]


def _measure_one(level: int, ix: int, iy: int, bounds, content: dict):
    """Like `_encode_one` but also returns per-kind (even-padded) sub-frame
    byte lengths `{road, background, name}` (0 when absent)."""
    """`divide.plan_divisions()`'s `encode` callback: build one Map Frame
    (whole-cell or divided sub-cell -- this function doesn't know or care
    which) from a content dict shaped like `SpoolReader.iter_level()`
    yields. `ix`/`iy` only feed `llcode`, a Map Frame header field with no
    established on-disc semantics anywhere in this codebase (confirmed by
    grep across kiwiw/ -- nothing decodes or checks its value; see
    parser/kiwiw/parcel.py's decode docstring) -- used here as a generic
    position marker, valid for both a parent cell's own (ix, iy) and a
    divided sub-cell's (sub_ix, sub_iy)."""
    roads = content.get("roads") or []
    bgs = content.get("backgrounds") or []
    names = content.get("names") or []

    road_bytes = synth.build_road_frame_bytes(roads, bounds) if roads else None
    # DESIGN.md section 4 / mfde index 1: `R` carries a background sub-frame
    # (in_buffer) at 100% of parcels, every level -- never absent, even for
    # a parcel with zero background shapes (`build_background_frame_bytes`
    # returns a 2-byte minimal-empty frame for `shapes=[]`, matching
    # `test_synth_map_frame.py`'s `_fixture_bg_bytes()`/
    # `test_absent_slot_sentinel_when_no_content`). Unlike road/name (which
    # really are legitimately absent on `R` when a parcel has no such
    # content -- DESIGN.md indices 0/2), background must always be called
    # unconditionally here, not gated behind `if bgs`.
    bg_bytes = synth.build_background_frame_bytes(bgs, bounds)
    # Amendment (post-11, orchestrator): `level=` must be passed
    # explicitly -- omitting it silently reverts to the legacy
    # type-1-only string path instead of unit 11's type-5/6 encoding.
    name_bytes = synth.build_name_frame_bytes(names, bounds, level=level) if names else None

    llpid = (bounds.lat_lo, bounds.lon_lo)
    llcode = (ix % 256, iy % 256)

    frame = synth.build_map_frame_bytes(
        level, llpid, llcode, road_bytes, bg_bytes, name_bytes)
    sizes = {"road": len(synth._pad_even(road_bytes) or b""),
             "background": len(synth._pad_even(bg_bytes) or b""),
             "name": len(synth._pad_even(name_bytes) or b"")}
    return frame, sizes


_PARCEL_MASK_PATH = Path(__file__).resolve().parent / "refdata" / "parcel_mask.json"


def load_parcel_mask(path: str | os.PathLike | None = None) -> dict[int, tuple[int, int, int, int]]:
    """Per-level coverage rectangle `(ix_lo, ix_hi, iy_lo, iy_hi)` (inclusive)
    inside which `R` materialises a Map Frame for every cell (brief 26c:
    R's populated cell set is a full rectangle at every level)."""
    import json
    with open(path or _PARCEL_MASK_PATH) as fh:
        raw = json.load(fh)
    return {int(k): (v["ix_lo"], v["ix_hi"], v["iy_lo"], v["iy_hi"]) for k, v in raw.items()}


def _fill_masked(cells, mask_rect, empty_factory):
    """Merge a `(iy, ix)`-ascending stream of `(ix, iy, content)` with every
    cell of `mask_rect`: cells the stream lacks are yielded with empty
    content; stream cells outside the mask are passed through unchanged."""
    ix_lo, ix_hi, iy_lo, iy_hi = mask_rect

    def _mask():
        for iy in range(iy_lo, iy_hi + 1):
            for ix in range(ix_lo, ix_hi + 1):
                yield (iy, ix)

    m = _mask()
    nxt = next(m, None)
    for ix, iy, content in cells:
        key = (iy, ix)
        while nxt is not None and nxt < key:
            yield nxt[1], nxt[0], empty_factory()
            nxt = next(m, None)
        if nxt == key:
            nxt = next(m, None)
        yield ix, iy, content
    while nxt is not None:
        yield nxt[1], nxt[0], empty_factory()
        nxt = next(m, None)


def _merge_stats(dst: dict, src: dict) -> None:
    """Add `src`'s additive counters (`total`/`dropped`/`cells` maps and
    `halo_names`) into `dst`, inserting keys in `src`'s order so the merged
    key order equals a serial run's when chunks merge in stream order."""
    for k, v in src.items():
        if isinstance(v, dict):
            d = dst.setdefault(k, {})
            for kk, vv in v.items():
                d[kk] = d.get(kk, 0) + vv
        else:
            dst[k] = dst.get(k, 0) + v


def _level_frames(level: int, reader: SpoolReader, fixture: str | None,
                  threshold_bytes: int, mask, kind_limits, trim_stats, name_halo: bool,
                  row_range: tuple[int | None, int | None] = (None, None)):
    """Yield `(ix, iy, parcel_type, sub_ix, sub_iy, frame_bytes)` for the
    cells of `level` whose row `iy` lies in `row_range` (`[lo, hi)`, `None` =
    unbounded), in canonical order. Rows partition the `(iy, ix)` stream, so
    the concatenation of consecutive row ranges equals the whole-level stream
    and `trim_stats` counters add up (`_merge_stats`)."""
    row_lo, row_hi = row_range
    tile_grid = TileGrid.from_reference(level)
    cell_range = _fixture_cell_range(level, fixture, tile_grid) if fixture else None
    a, b = reader.row_bounds(level, row_lo, row_hi)

    def _in_fixture(ix, iy):
        if cell_range is None:
            return True
        ix_lo, ix_hi, iy_lo, iy_hi = cell_range
        return ix_lo <= ix <= ix_hi and iy_lo <= iy <= iy_hi

    def _count(n_roads, n_bgs, n_names):
        if trim_stats is not None:
            t = trim_stats.setdefault("total", {})
            t["road"] = t.get("road", 0) + n_roads
            t["background"] = t.get("background", 0) + n_bgs
            t["name"] = t.get("name", 0) + n_names

    rect = _level_rect(mask, level, cell_range)
    if rect is not None:
        rect = (rect[0], rect[1],
                rect[2] if row_lo is None else max(rect[2], row_lo),
                rect[3] if row_hi is None else min(rect[3], row_hi - 1))
        if not (rect[0] <= rect[1] and rect[2] <= rect[3]):
            rect = None

    enc = cenc.make_encoder(level, tile_grid, threshold_bytes, kind_limits)
    if enc is not None:
        return _level_frames_c(level, reader, a, b, _in_fixture, _count, rect, enc,
                               threshold_bytes, kind_limits, trim_stats, name_halo)

    def _cells():
        for ix, iy, content in reader.iter_cells(level, a, b):
            if not _in_fixture(ix, iy):
                continue
            _count(len(content.get("roads") or []), len(content.get("backgrounds") or []),
                   len(content.get("names") or []))
            yield ix, iy, content

    cells_iter = _cells
    if rect is not None:
        from kiwiw.spool import _empty_content

        def cells_iter():
            return _fill_masked(_cells(), rect, _empty_content)

    return divide.plan_divisions(
        level, cells_iter(), threshold_bytes, _encode_one,
        kind_limits=kind_limits, measure=_measure_one,
        trim_stats=trim_stats, name_halo=name_halo)


_HDR_COUNTS = struct.Struct("<9Q")


def _level_frames_c(level, reader, a, b, in_fixture, count, rect, enc,
                    threshold_bytes, kind_limits, trim_stats, name_halo):
    """C fast path: the kernel yields the frame for every cell that fits and
    breaches no kind budget; every other cell goes through the Python oracle
    (`divide.plan_divisions` on that one cell), so output is identical."""
    from kiwiw.spool import _empty_content, columns_to_content, decode_columns

    def _raw_cells():
        for ix, iy, raw in reader.iter_cell_raw(level, a, b):
            if not in_fixture(ix, iy):
                continue
            h = _HDR_COUNTS.unpack_from(raw)
            count(h[0], h[3], h[5])
            yield ix, iy, raw

    stream = _raw_cells()
    if rect is not None:
        stream = _fill_masked(stream, rect, lambda: None)
    for ix, iy, raw in stream:
        frame = enc.encode(raw, ix, iy)
        if frame is not None:
            yield ix, iy, 0, 0, 0, frame
            continue
        content = _empty_content() if raw is None else columns_to_content(decode_columns(raw))
        yield from divide.plan_divisions(
            level, iter(((ix, iy, content),)), threshold_bytes, _encode_one,
            kind_limits=kind_limits, measure=_measure_one,
            trim_stats=trim_stats, name_halo=name_halo)


def _level_rect(mask, level, cell_range):
    rect = mask.get(level) if mask else None
    if rect is not None and cell_range is not None:  # fixture: clip the mask to the window
        rect = (max(rect[0], cell_range[0]), min(rect[1], cell_range[1]),
                max(rect[2], cell_range[2]), min(rect[3], cell_range[3]))
    return rect


# Relative cost of an empty mask-filled cell vs one spool byte (only balances chunks).
_EMPTY_CELL_WEIGHT = 512


def _plan_chunks(reader: SpoolReader, level: int, fixture, mask, n_chunks: int
                 ) -> list[tuple[int | None, int | None]]:
    """Split the level's row space into <= `n_chunks` weight-balanced `[lo, hi)`
    row ranges (first lo / last hi unbounded). Any partition yields identical
    output; this only balances work."""
    import numpy as np
    iy, length = reader.cell_weights(level)
    rect = _level_rect(mask, level, _fixture_cell_range(level, fixture, TileGrid.from_reference(level))
                       if fixture else None)
    r_lo = int(iy[0]) if len(iy) else 0
    r_hi = int(iy[-1]) if len(iy) else -1
    if rect is not None and rect[0] <= rect[1] and rect[2] <= rect[3]:
        r_lo, r_hi = min(r_lo, rect[2]), max(r_hi, rect[3])
    nrows = r_hi - r_lo + 1
    if n_chunks <= 1 or nrows <= 1:
        return [(None, None)]
    w = np.zeros(nrows, dtype=np.float64)
    if len(iy):
        rows = iy.astype(np.int64) - r_lo
        w += np.bincount(rows, weights=length.astype(np.float64), minlength=nrows)
        if rect is not None and rect[0] <= rect[1]:
            pop = np.bincount(rows, minlength=nrows)
            in_rect = np.zeros(nrows, dtype=bool)
            in_rect[max(rect[2], r_lo) - r_lo:min(rect[3], r_hi) - r_lo + 1] = True
            w += np.where(in_rect, np.maximum(0, (rect[1] - rect[0] + 1) - pop), 0) \
                * _EMPTY_CELL_WEIGHT
    elif rect is not None:
        w += (rect[1] - rect[0] + 1) * _EMPTY_CELL_WEIGHT
    cum = np.cumsum(w)
    n = min(n_chunks, nrows)
    cuts = np.searchsorted(cum, cum[-1] * np.arange(1, n) / n, side="left") + 1
    bounds = sorted({int(c) for c in cuts if 0 < c < nrows})
    edges = [None] + [r_lo + c for c in bounds] + [None]
    return list(zip(edges[:-1], edges[1:]))


_WORKER: dict = {}


def _chunk_worker(job):
    """Process-pool entry: encode one row range; return its frames + counters."""
    (spool_dir, level, fixture, threshold_bytes, mask, kind_limits, name_halo, rows) = job
    reader = _WORKER.get(spool_dir)
    if reader is None:
        reader = _WORKER[spool_dir] = SpoolReader(spool_dir)
    stats: dict = {}
    frames = list(_level_frames(level, reader, fixture, threshold_bytes, mask,
                                kind_limits, stats, name_halo, rows))
    return frames, stats


def _encode_level(level: int, grid: ReferenceGrid, reader: SpoolReader,
                   fixture: str | None, threshold_bytes: int,
                   mask: dict[int, tuple[int, int, int, int]] | None = None,
                   kind_limits: dict[str, int] | None = None,
                   trim_stats: dict | None = None,
                   name_halo: bool = False,
                   spill=None, digest_fh=None, pool=None, jobs: int = 1
                   ) -> tuple[list[tuple[int, int, bytes]],
                              list[tuple[int, int, int, int, int, bytes]], int, int]:
    """Encode every spooled parcel at `level`, splitting any parcel whose
    whole-cell Map Frame would exceed `threshold_bytes` via
    `divide.plan_divisions()` (unit 13). Returns (parcels, divided_parcels,
    n_parcels, total_frame_bytes) -- `parcels` is type-0 (undivided)
    ``(ix, iy, frame_bytes)`` for ``LevelBuild``, `divided_parcels` is
    ``(ix, iy, parcel_type, sub_ix, sub_iy, frame_bytes)`` for
    ``build_alldata_kwi(..., divided=...)``; `n_parcels`/total bytes count
    every frame actually placed (divided sub-frames included, the parent
    cell itself does not).

    With `spill` (a `kiwiw.spill.FrameSpill`) each frame is appended to the
    spill file and the returned tuples carry a `FrameRef` instead of bytes
    (`len()` still works), so frame bytes are never accumulated in RAM.
    `digest_fh` receives one ``level ix iy type sub_ix sub_iy len sha256``
    line per frame.

    With `pool` (a `multiprocessing.Pool`) the level's row space is cut into
    weight-balanced row ranges encoded in parallel; results are consumed in
    row order, so output and counters equal the serial run for any `jobs`."""
    if pool is not None and jobs > 1:
        chunks = _plan_chunks(reader, level, fixture, mask, jobs * 8)
    else:
        chunks = [(None, None)]

    def _serial():
        st: dict = {}
        yield (_level_frames(level, reader, fixture, threshold_bytes, mask, kind_limits,
                             st if trim_stats is not None else None, name_halo,
                             chunks[0]), st)

    def _parallel():
        from collections import deque
        pending: deque = deque()
        it = iter(chunks)
        depth = jobs * 2

        def _fill():
            while len(pending) < depth:
                rows = next(it, None)
                if rows is None:
                    return
                pending.append(pool.apply_async(_chunk_worker, ((
                    str(reader.spool_dir), level, fixture, threshold_bytes, mask,
                    kind_limits, name_halo, rows),)))
        _fill()
        while pending:
            frames, st = pending.popleft().get()
            _fill()
            yield frames, st

    out: list[tuple[int, int, bytes]] = []
    divided_out: list[tuple[int, int, int, int, int, bytes]] = []
    n_bytes = 0
    n_parcels = 0
    for frames, st in (_parallel() if len(chunks) > 1 else _serial()):
        for ix, iy, parcel_type, sub_ix, sub_iy, frame_bytes in frames:
            n_frame = len(frame_bytes)
            if digest_fh is not None:
                digest_fh.write(f"{level} {ix} {iy} {parcel_type} {sub_ix} {sub_iy} "
                                f"{n_frame} {hashlib.sha256(frame_bytes).hexdigest()}\n")
            if spill is not None:
                frame_bytes = spill.add(frame_bytes)
            if parcel_type == 0:
                out.append((ix, iy, frame_bytes))
            else:
                divided_out.append((ix, iy, parcel_type, sub_ix, sub_iy, frame_bytes))
            n_parcels += 1
            n_bytes += n_frame
        if trim_stats is not None:
            _merge_stats(trim_stats, st)

    return out, divided_out, n_parcels, n_bytes


def run(spool_dir: str, out_path: str, levels: list[int],
        fixture: str | None, disk_title: str, fill_mask: bool = False,
        frame_digest: str | None = None, workers: int = 1) -> int:
    if not os.path.isdir(spool_dir):
        print(f"ERROR: spool directory not found: {spool_dir}", file=sys.stderr)
        return 1

    reader = SpoolReader(spool_dir)
    mask = load_parcel_mask() if fill_mask else None
    available = set(reader.levels())
    grid = ReferenceGrid.load()
    thresholds = _load_level_thresholds()
    kind_budgets = _load_level_kind_budgets()
    trimmed_items: dict[str, dict] = {}
    halo_names: dict[str, int] = {}

    spool_stats = {lvl: reader.stats(lvl) for lvl in levels}
    # Optional per-frame digest listing (plan 02): localizes a byte mismatch to a
    # (level, ix, iy, parcel_type, sub_ix, sub_iy) frame. Regenerable, never committed.
    digest_fh = open(frame_digest, "w") if frame_digest else None
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    spill = FrameSpill(os.path.dirname(out_path) or ".")

    pool = None
    if workers > 1:
        import multiprocessing as mp
        # Eager fork while the parent is still small: workers' shared copy-on-write
        # pages then stay small (a lazily-forked executor would fork a big parent).
        pool = mp.get_context("fork").Pool(workers)

    level_builds: dict[int, aw.LevelBuild] = {}
    divided_builds: dict[int, list[tuple[int, int, int, int, int, bytes]]] = {}
    manifest_levels: dict[str, dict] = {}
    t_run = time.monotonic()
    for level in levels:
        t_level = time.monotonic()
        print(f"level {level}: encoding ...", flush=True)
        if level not in available:
            print(f"level {level}: no spooled content, skipping", flush=True)
            level_builds[level] = aw.LevelBuild(level=level, parcels=[])
            manifest_levels[str(level)] = {"parcels": 0, "bytes": 0, "divided_parents": 0}
            continue
        threshold_bytes = thresholds.get(level, U16_MAPFRAME_BYTE_CEILING)
        trim_stats: dict = {}
        parcels, divided_parcels, n_parcels, n_bytes = _encode_level(
            level, grid, reader, fixture, threshold_bytes, mask=mask,
            kind_limits=kind_budgets.get(level) or None, trim_stats=trim_stats,
            name_halo=(level in NAME_HALO_LEVELS), spill=spill, digest_fh=digest_fh,
            pool=pool, jobs=workers)
        if trim_stats.get("halo_names"):
            print(f"level {level}: name halo added {trim_stats['halo_names']:,} "
                  f"neighbouring road-name records to divided sub-cells (brief 32)",
                  flush=True)
            halo_names[str(level)] = trim_stats["halo_names"]
        dropped = trim_stats.get("dropped", {})
        if dropped:
            total = trim_stats.get("total", {})
            trimmed_items[str(level)] = {
                k: {"dropped": n, "total": total.get(k, 0),
                    "cells": trim_stats.get("cells", {}).get(k, 0)}
                for k, n in dropped.items()}
            for k, n in dropped.items():
                pct = 100.0 * n / max(1, total.get(k, 0))
                print(f"level {level}: TRIM {k}: dropped {n:,}/{total.get(k, 0):,} "
                      f"({pct:.3f}%) in {trim_stats.get('cells', {}).get(k, 0)} sub-cells"
                      + ("  ** >1% BLOCKER **" if pct > 1.0 else ""), flush=True)
        level_builds[level] = aw.LevelBuild(level=level, parcels=parcels)
        if divided_parcels:
            divided_builds[level] = divided_parcels
        n_divided_parents = len({(ix, iy) for ix, iy, *_ in divided_parcels})
        max_frame = max(
            [len(fb) for _ix, _iy, fb in parcels]
            + [len(fb) for *_rest, fb in divided_parcels],
            default=0)
        manifest_levels[str(level)] = {
            "parcels": n_parcels, "bytes": n_bytes,
            "divided_parents": n_divided_parents,
            "threshold_bytes": threshold_bytes,
            "max_frame_bytes": max_frame,
        }
        print(f"level {level}: {n_parcels} parcels ({n_divided_parents} parents divided), "
              f"{n_bytes:,} frame bytes, max frame {max_frame:,} bytes "
              f"(threshold {threshold_bytes:,}) [{time.monotonic() - t_level:.1f}s]",
              flush=True)

    if digest_fh is not None:
        digest_fh.close()
    print(f"assembling ALLDATA.KWI ... [encode total {time.monotonic() - t_run:.1f}s]",
          flush=True)
    t_asm = time.monotonic()
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    if pool is not None:
        pool.close()
        pool.join()
    assembled = aw.build_alldata_kwi(level_builds, grid, disk_title=disk_title,
                                      out_path=out_path, divided=divided_builds,
                                      return_bytes=False)
    spill.close()
    print(f"wrote {out_path} ({assembled.size:,} bytes) "
          f"[assemble {time.monotonic() - t_asm:.1f}s]", flush=True)

    sha256 = assembled.sha256
    manifest = {
        "spool_dir": spool_dir,
        "spool_stats": {str(k): v for k, v in spool_stats.items()},
        "levels": manifest_levels,
        "total_size": assembled.size,
        "sha256": sha256,
        "layers_present": LAYERS_PRESENT,
        "trimmed_items": trimmed_items,
        "halo_names": halo_names,
        "fixture": fixture,
    }
    manifest_path = os.path.join(os.path.dirname(out_path) or ".", "manifest.json")
    with open(manifest_path, "w") as fh:
        json.dump(manifest, fh, indent=2)
    print(f"wrote {manifest_path}", flush=True)

    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--spool", default=DEFAULT_SPOOL,
                     help="Spool directory written by osm_to_parcel_geometry.py "
                          "(default: %(default)s)")
    ap.add_argument("--out", default=DEFAULT_OUT,
                     help="Output ALLDATA.KWI path (default: %(default)s)")
    ap.add_argument("--levels", type=int, nargs="+", default=DEFAULT_LEVELS,
                     help="Map levels to build (default: %(default)s)")
    ap.add_argument("--fixture", choices=sorted(FIXTURE_BBOXES), default=None,
                     help="Restrict the build to a named dev fixture's cells "
                          "(e.g. 'perth'); container shape stays the full 7-level "
                          "structure regardless")
    ap.add_argument("--disk-title", default="AU ",
                     help="Volume Header disk title (default: %(default)r)")
    ap.add_argument("--no-fill-mask", action="store_true",
                     help="Do not emit empty frames for R's coverage-rectangle cells "
                          "the spool lacks (brief 26c; default: fill)")
    ap.add_argument("-j", "--workers", type=int, default=1,
                     help="Worker processes for cell encoding (output is byte-identical "
                          "for any value; default: %(default)s)")
    ap.add_argument("--frame-digest", default=None, metavar="PATH",
                     help="Write a per-frame sha256 listing (level ix iy parcel_type "
                          "sub_ix sub_iy len sha256) for byte-diff localization")
    args = ap.parse_args()

    return run(spool_dir=args.spool, out_path=args.out, levels=args.levels,
               fixture=args.fixture, disk_title=args.disk_title,
               fill_mask=not args.no_fill_mask,
               frame_digest=args.frame_digest, workers=args.workers)


if __name__ == "__main__":
    raise SystemExit(main())
