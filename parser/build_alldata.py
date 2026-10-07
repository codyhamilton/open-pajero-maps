#!/usr/bin/env python3
"""Build ALLDATA.KWI from a spool written by `osm_to_parcel_geometry.py`.

End-to-end pipeline:
  1. Reads a spool directory (`kiwiw.spool.SpoolReader`) written by
     `osm_to_parcel_geometry.py`'s extraction pass -- never reads a PBF or
     touches OSM data itself.
  2. For each requested level, encodes every spooled parcel's road/
     background/name content into Map Frames in C (`kiwiw.cenc`: E1, the level
     pre-pass, then E2, the range encode, which also divides, retiles, trims
     and adds the name halo; Contract B in docs/plans/03-map-layer-parity-remediation).
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
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from kiwiw import alldata_writer as aw
from kiwiw import cenc
from kiwiw import descriptor
from kiwiw import frame_table as ft
from kiwiw import mesh
from kiwiw.grid import ReferenceGrid
from kiwiw.spool import SpoolReader

DEFAULT_SPOOL = str(Path(__file__).resolve().parent.parent / "output" / "spool")
DEFAULT_OUT = str(Path(__file__).resolve().parent.parent / "output" / "ALLDATA.KWI")
DEFAULT_LEVELS = [12, 10, 8, 6, 4, 2, 0]

# The Map Frame's hard format ceiling (Map Frame header's
# size field is a 16-bit word count: `total_size // 2` must fit in u16;
# enforced in C by `_cenc.c`) and unit 12's done evidence (IMPLEMENTATION.md, "Unit
# 12"). Unit 13's Amendment: the threshold E2 divides
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
    """Per-level division threshold. Brief 34: the u16 ceiling for
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


_PARCEL_MASK_PATH = Path(__file__).resolve().parent / "refdata" / "parcel_mask.json"


def load_parcel_mask(path: str | os.PathLike | None = None) -> dict[int, tuple[int, int, int, int]]:
    """Per-level coverage rectangle `(ix_lo, ix_hi, iy_lo, iy_hi)` (inclusive)
    inside which `R` materialises a Map Frame for every cell (brief 26c:
    R's populated cell set is a full rectangle at every level)."""
    import json
    with open(path or _PARCEL_MASK_PATH) as fh:
        raw = json.load(fh)
    return {int(k): (v["ix_lo"], v["ix_hi"], v["iy_lo"], v["iy_hi"]) for k, v in raw.items()}


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


_KIND_KEYS = (("road", "road"), ("background", "bg"), ("name", "name"))


def _e2_trim_stats(cnt: dict) -> dict:
    """E2's counters as the additive stats dict `_merge_stats` sums:
    `total` (every cell's encoded items per kind), `dropped` / `cells`
    (kinds that lost items to trimming, in road, background, name order)
    and `halo_names`."""
    st: dict = {"total": {k: cnt[f"total_{c}"] for k, c in _KIND_KEYS}}
    for k, c in _KIND_KEYS:
        if cnt[f"dropped_{c}"]:
            st.setdefault("dropped", {})[k] = cnt[f"dropped_{c}"]
            st.setdefault("cells", {})[k] = cnt[f"trimmed_cells_{c}"]
    if cnt["halo_names"]:
        st["halo_names"] = cnt["halo_names"]
    return st


def _trim_manifest_blocks(level: int, st: dict) -> tuple[dict, dict]:
    """`(trimmed_items, halo_names)` manifest blocks for one level's merged
    stats (each `{}` when the level trimmed nothing / added no halo)."""
    trimmed: dict = {}
    dropped = st.get("dropped", {})
    if dropped:
        total = st.get("total", {})
        trimmed[str(level)] = {
            k: {"dropped": n, "total": total.get(k, 0), "cells": st.get("cells", {}).get(k, 0)}
            for k, n in dropped.items()}
    halo = {str(level): st["halo_names"]} if st.get("halo_names") else {}
    return trimmed, halo


def _combined_cell_range(level, fixture, window_rect):
    """`--window`'s cell rectangle takes precedence over `--fixture`'s (the
    two are not used together); either narrows which cells receive, are
    mask-filled and emitted -- it rides in the level descriptor's window
    (planning only, per Contract B)."""
    if window_rect is not None:
        return window_rect
    return mesh.fixture_cell_range(level, fixture) if fixture else None


def _level_rect(mask, level, cell_range):
    rect = mask.get(level) if mask else None
    if rect is not None and cell_range is not None:  # fixture: clip the mask to the window
        rect = (max(rect[0], cell_range[0]), min(rect[1], cell_range[1]),
                max(rect[2], cell_range[2]), min(rect[3], cell_range[3]))
    return rect


# Relative cost of an empty mask-filled cell vs one spool byte (only balances chunks).
_EMPTY_CELL_WEIGHT = 512


def _plan_chunks(reader: SpoolReader, level: int, mask,
                 n_chunks: int) -> list[tuple[int | None, int | None]]:
    """Split the whole level's row space into <= `n_chunks` weight-balanced
    `[lo, hi)` row ranges (first lo / last hi unbounded) -- also under
    `--fixture`/`--window`, whose rectangle rides in the descriptor. Any
    partition yields identical output; this only balances work."""
    iy, length = reader.cell_weights(level)
    rect = _level_rect(mask, level, None)
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
        ln = length.astype(np.float64)
        # big records are the ones that divide/retile (superlinear cost)
        w += np.bincount(rows, weights=ln + ln * ln / 65536.0, minlength=nrows)
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
_SPILL: dict = {}


def _e1spool(spool_dir: str, level: int) -> cenc.E1Spool:
    """This process's memory-mapped spool for `level` (one per level).

    Plan 58: closing the previous level's E1Spool before opening the next
    drops private COW memmaps so they do not accumulate across the Pool's
    long-lived workers.
    """
    key = (os.getpid(), spool_dir, level)
    sp = _WORKER.get("e1spool")
    if sp is not None and sp[0] == key:
        return sp[1]
    if sp is not None:
        try:
            sp[1].close()
        except Exception:
            pass
        _WORKER.pop("e1spool", None)
    spool = cenc.E1Spool(spool_dir, level, guard_names=True)
    _WORKER["e1spool"] = (key, spool)
    return spool


def _release_worker_encode_caches(_ignored=None) -> dict:
    """Pool/post-level: close cached E1Spool in this worker (plan 58).

    Spill files stay open until assemble (FrameTable offsets). Returns a small
    status dict for the parent (pid + whether a spool was closed).
    """
    import gc
    closed = False
    sp = _WORKER.pop("e1spool", None)
    if sp is not None:
        try:
            sp[1].close()
            closed = True
        except Exception:
            pass
    gc.collect()
    return {"pid": os.getpid(), "e1spool_closed": closed}


def _e1_job(job):
    """Pool entry, stage 1: E1 over source rows `[lo, hi)`. Returns the
    routing rows, E1's counters and this call's time split."""
    spool_dir, level, desc, (lo, hi), *rest = job
    cell_range = rest[0] if rest else None
    t0 = time.perf_counter()
    s0 = cenc.e1_stats()
    spool = _e1spool(spool_dir, level)
    rows, counters = cenc.e1(desc, spool, lo, hi)
    counters["out_of_span_names_dropped"] = spool.name_drops(lo, hi, cell_range)
    s1 = cenc.e1_stats()
    d = {k: s1[k] - s0[k] for k in ("ranges", "calls", "c_s", "handoff_s")}
    d["py_s"] = max(0.0, time.perf_counter() - t0 - d["c_s"] - d["handoff_s"])
    return rows, counters, d


def _empty_shell_header(level: int, ix: int, iy: int) -> tuple[int, bytes, bytes]:
    """`_cenc.c encode_common`'s record-less frame for one cell: a 36-byte
    header, 20 MFDEs (12 at level 12) all absent except background, and the
    two-byte empty background list `0001`. Returns `(length, header[10:12],
    header[12:] + directory + background)`; bytes 2..9 (the cell's
    south-west corner) are free apart from their zero pad bytes 5 and 9."""
    mfde = 12 if level == 12 else 20
    first = 36 + mfde * 6
    directory = bytearray(b"\xff\xff\xff\xff\x00\x00" * mfde)
    directory[6:12] = (first // 2).to_bytes(4, "big") + b"\x00\x01"
    metadata = bytes.fromhex("00000000000000640000000000000000ffffffff00000000")
    return first + 2, bytes((iy % 256, ix % 256)), metadata + bytes(directory) + b"\x00\x01"


def is_empty_shell(raw: bytes, level: int, ix: int, iy: int) -> bool:
    """True only for the encoder's exact record-less shell of cell (ix, iy),
    optionally followed by zero padding (plan 29's probe-and-pad extent).
    Any road/name/extended subframe, region list, non-empty background,
    metadata difference or non-zero trailing byte returns False."""
    n, cell, tail = _empty_shell_header(level, ix, iy)
    return (len(raw) >= n and raw[:2] == (n // 2).to_bytes(2, "big")
            and raw[5] == 0 and raw[9] == 0 and raw[10:12] == cell
            and raw[12:n] == tail and not any(raw[n:]))


def _omit_outside_mask_shells(level, index, spill_path, rect):
    """Plan 34 emit rule: outside the level's parcel-mask rectangle `rect`
    (`load_parcel_mask`, brief 26c), R writes a frame only where content
    exists and the absent sentinel elsewhere. An undivided cell outside
    `rect` whose final frame is exactly the encoder's empty shell is
    therefore not indexed. Inside `rect` (R materialises every cell) nothing
    changes; without a mask (`--no-fill-mask`) nothing changes.

    Runs after the plan-29 name-drop probe-and-pad comparison, so that guard
    still sees both original and filtered topology. Retained index rows and
    frame bytes are untouched."""
    if rect is None or not len(index):
        return index
    ix_lo, ix_hi, iy_lo, iy_hi = rect
    ix, iy = index["ix"], index["iy"]
    candidate = (ix < ix_lo) | (ix > ix_hi) | (iy < iy_lo) | (iy > iy_hi)
    candidate &= (index["pt"] == 0) & (index["sx"] == 0) & (index["sy"] == 0)
    if not candidate.any():
        return index
    shortest = _empty_shell_header(level, 0, 0)[0]
    keep = np.ones(len(index), bool)
    rfd = os.open(spill_path, os.O_RDONLY)
    try:
        for i in np.flatnonzero(candidate):
            row = index[i]
            n = int(row["len"])
            if n < shortest or n > descriptor.MAX_FRAME_BYTES:
                continue
            raw = os.pread(rfd, n, int(row["off"]))
            if len(raw) != n:
                raise RuntimeError("short shell spill read")
            if is_empty_shell(raw, level, int(row["ix"]), int(row["iy"])):
                keep[i] = False
    finally:
        os.close(rfd)
    return index[keep]


def _e2_job(job):
    """Pool entry, stage 2: E2 over target rows `[lo, hi)` into this
    process's spill file. E2 divides, retiles, trims and adds the name halo
    itself (C); every frame, whole or divided, is written by it.

    Returns `(spill_path, rec, stats, digest_lines, bench, dump_recs, eo_census)`: `rec`
    is a `frame_table.FRAME_DTYPE` array in canonical order (stable on the
    cell key, so a divided parent's sub-frames keep their order), so no frame
    bytes are pickled back unless `want_dump` (small windowed captures only).
    A declined row is an error: E2 declines nothing that a build needs."""
    (spool_dir, level, desc, (lo, hi), rows, spill_dir, want_digest, want_bench,
     want_dump, *rest) = job
    cell_range = rest[0] if rest else None
    mask_rect = rest[1] if len(rest) > 1 else None
    t0 = time.perf_counter()
    sp = _SPILL.get(spill_dir)
    if sp is None or sp[0] != os.getpid():
        sp = _SPILL[spill_dir] = (os.getpid(), ft.ChunkSpill(spill_dir))
    spill = sp[1]
    s0 = cenc.e2_stats()
    cenc.eo_census_reset()
    spool = _e1spool(spool_dir, level)
    index, declined, cnt = cenc.e2(desc, spool, rows, lo, hi,
                                   spill._fd, spill.end)
    spill.end += cnt["frame_bytes"]
    # Production E2 stats end here: the drop probe below is not a build range.
    s1 = cenc.e2_stats()
    eo = cenc.eo_census_stats()  # snapshot before name-drop re-encode
    if spool.name_drops(lo, hi, cell_range):
        # Preserve original chunk topology/extents for the name guard.
        # Plan 34's outside-mask empty-shell omission runs after this comparison;
        # retained frames still fill removed content with trailing zeros.
        original = cenc.E1Spool(spool_dir, level)
        try:
            old, old_declined, old_cnt = cenc.e2(
                desc, original, rows, lo, hi, spill._fd, spill.end)
        finally:
            original.close()
        spill.end += old_cnt["frame_bytes"]
        keys = ("ix", "iy", "pt", "sx", "sy")
        if len(old_declined) or len(old) != len(index) or any(
                not np.array_equal(old[k], index[k]) for k in keys):
            raise RuntimeError("name drop changed frame topology; root-cause required")
        rfd = os.open(spill.path, os.O_RDONLY)
        try:
            for new, previous in zip(index, old):
                n, extent = int(new["len"]), int(previous["len"])
                if n == extent:
                    continue
                if n > extent:
                    raise RuntimeError("name drop enlarged a frame")
                fb = os.pread(rfd, n, int(new["off"]))
                if len(fb) != n:
                    raise RuntimeError("short spill read")
                padded = fb + bytes(extent - n)
                if os.pwrite(spill._fd, padded, spill.end) != extent:
                    raise RuntimeError("short spill write")
                new["off"], new["len"] = spill.end, extent
                spill.end += extent
        finally:
            os.close(rfd)
    if len(declined):
        cells = ", ".join(f"(level {level}, ix {int(r['ix'])}, iy {int(r['iy'])})"
                          for r in declined[:8])
        more = f" (+{len(declined) - 8} more)" if len(declined) > 8 else ""
        raise RuntimeError(
            f"E2 declined {len(declined)} cell(s) it could not encode even after "
            f"division: {cells}{more}")
    index = _omit_outside_mask_shells(level, index, spill.path, mask_rect)
    stats = _e2_trim_stats(cnt)
    rec = np.zeros(len(index), ft.FRAME_DTYPE)
    for k in ("ix", "iy", "pt", "sx", "sy", "len", "off"):
        rec[k] = index[k]
    rec = rec[np.lexsort((rec["ix"], rec["iy"]))]   # stable: sub-frames keep their order
    lines: list[str] | None = [] if want_digest else None
    dump_recs: list[tuple] | None = [] if want_dump else None
    if (want_digest or want_dump) and len(rec):
        rfd = os.open(spill.path, os.O_RDONLY)
        try:
            for r in rec:
                fb = os.pread(rfd, int(r["len"]), int(r["off"]))
                ix, iy, pt, sx, sy = (int(r["ix"]), int(r["iy"]), int(r["pt"]),
                                      int(r["sx"]), int(r["sy"]))
                if lines is not None:
                    lines.append(f"{level} {ix} {iy} {pt} {sx} {sy} {len(fb)} "
                                 f"{hashlib.sha256(fb).hexdigest()}\n")
                if dump_recs is not None:
                    dump_recs.append((ix, iy, pt, sx, sy, fb))
        finally:
            os.close(rfd)
    bench = None
    if want_bench:
        e2c, e2h = s1["c_s"] - s0["c_s"], s1["handoff_s"] - s0["handoff_s"]
        bench = {"py_s": max(0.0, time.perf_counter() - t0 - e2c - e2h), "c_s": e2c,
                 "handoff_s": e2h, "e2_c_s": e2c, "calls": {"e2": s1["ranges"] - s0["ranges"]}}
    return spill.path, rec, stats, lines, bench, dump_recs, eo


def _merge_bench(dst: dict, src: dict) -> None:
    for k, v in src.items():
        if k == "calls":
            calls = dst.setdefault("calls", {})
            for kk, vv in v.items():
                calls[kk] = calls.get(kk, 0) + vv
        else:
            dst[k] = dst.get(k, 0.0) + v


def _run_ranges(pool, fn, jobs, weights=None):
    """Results of `fn` over `jobs`, in job order; with a pool, submitted
    heaviest-first (LPT) and consumed in order."""
    if pool is None or len(jobs) <= 1:
        return [fn(j) for j in jobs]
    futs = [None] * len(jobs)
    order = range(len(jobs)) if weights is None else sorted(range(len(jobs)),
                                                            key=lambda i: -weights[i])
    for i in order:
        futs[i] = pool.apply_async(fn, (jobs[i],))
    return [f.get() for f in futs]


def _encode_level(level: int, reader: SpoolReader, fixture, threshold_bytes: int,
                  mask, kind_limits, trim_stats: dict, name_halo: bool,
                  spill_dir: str, digest_fh=None, pool=None, jobs: int = 1,
                  window_rect=None, bench: bool = False, dump=None):
    """Encode one level: E1 then E2, once per row range (Contract B).

    Returns `(FrameTable, n_parcels, total_frame_bytes, n_divided_parents,
    max_frame, overlap_counters, level_bench, eo_census)`. Output and counters equal
    the serial run's for any `jobs`: ranges are consumed in row order."""
    from kiwiw import cbuild as _cbuild
    eo_acc = _cbuild.empty_eo_stats()
    spool_dir = str(reader.spool_dir)
    kl = kind_limits or {}
    desc = descriptor.build_for_spool(
        spool_dir, level, mask_rect=(mask or {}).get(level),
        window=_combined_cell_range(level, fixture, window_rect), threshold=threshold_bytes,
        kind_limits={"road": kl.get("road"), "bg": kl.get("background"),
                     "name": kl.get("name")}, name_halo=name_halo)
    chunks = _plan_chunks(reader, level, mask, jobs * 64 if pool is not None else 1)
    weights = _chunk_weights(reader, level, chunks)

    # Stage 1: E1 per range; route the rows to their target ranges with one
    # stable sort on the target key and one split at the range edges.
    t_e1 = time.monotonic()
    cell_range = _combined_cell_range(level, fixture, window_rect)
    e1_out = _run_ranges(pool, _e1_job, [(spool_dir, level, desc, c, cell_range)
                                         for c in chunks], weights)
    rows = np.zeros(sum(len(r) for r, _c, _d in e1_out), descriptor.E1_ROW_DTYPE)
    at = 0
    for r, _c, _d in e1_out:    # (np.concatenate would drop the dtype's padding)
        rows[at:at + len(r)] = r
        at += len(r)
    rows = rows[np.lexsort((rows["tix"], rows["tiy"]))]
    edges = np.searchsorted(rows["tiy"], [hi for _lo, hi in chunks[:-1]])
    parts = np.split(rows, edges)
    ov = {k: sum(c[k] for _r, c, _d in e1_out) for k in cenc.E1_COUNTERS}
    ov["out_of_span_names_dropped"] = sum(
        c["out_of_span_names_dropped"] for _r, c, _d in e1_out)
    prepass_s = time.monotonic() - t_e1
    # Keep only bench splits from e1_out; drop large row arrays before E2.
    e1_bench_parts = [d for _r, _c, d in e1_out] if bench else None
    del e1_out

    # Stage 2: E2 per range.
    e2_out = _run_ranges(pool, _e2_job, [
        (spool_dir, level, desc, c, parts[i], spill_dir, digest_fh is not None, bench,
         dump is not None, cell_range, (mask or {}).get(level))
        for i, c in enumerate(chunks)], weights)

    tables = []
    level_bench = None
    if bench:
        level_bench = {"prepass_s": prepass_s, "py_s": 0.0, "c_s": 0.0, "handoff_s": 0.0,
                       "e1_c_s": 0.0, "e2_c_s": 0.0,
                       "calls": {"e1": 0, "e1_ctypes": 0}}
        for d in (e1_bench_parts or []):
            _merge_bench(level_bench, {"py_s": d["py_s"], "c_s": d["c_s"],
                                       "handoff_s": d["handoff_s"], "e1_c_s": d["c_s"],
                                       "calls": {"e1": d["ranges"], "e1_ctypes": d["calls"]}})
    for path, rec, st, lines, chunk_bench, dump_recs, eo in e2_out:
        tables.append((path, rec))
        if digest_fh is not None:
            digest_fh.writelines(lines)
        if dump is not None and dump_recs:
            for ix, iy, pt, sx, sy, fb in dump_recs:
                dump.write(level, ix, iy, pt, sx, sy, fb)
        if level_bench is not None and chunk_bench is not None:
            _merge_bench(level_bench, chunk_bench)
        _merge_stats(trim_stats, st)
        _cbuild.merge_eo_stats(eo_acc, eo)
    if level_bench is not None:
        level_bench["ranges"] = len(chunks)
        level_bench["workers"] = jobs if pool is not None else 1
    table = ft.merge_tables(tables)
    rec = table.rec
    n_parcels = len(rec)
    n_bytes = int(rec["len"].sum(dtype=np.int64))
    div = rec[rec["pt"] != 0]
    n_div_parents = len(np.unique((div["ix"].astype(np.int64) << 32) | div["iy"].astype(np.int64))) if len(div) else 0
    max_frame = int(rec["len"].max()) if n_parcels else 0
    return table, n_parcels, n_bytes, n_div_parents, max_frame, ov, level_bench, eo_acc


def _chunk_weights(reader: SpoolReader, level: int, chunks) -> list[float]:
    """Spool-record weight of each row chunk (ordering hint only)."""
    iy, length = reader.cell_weights(level)
    out = []
    for lo, hi in chunks:
        a = 0 if lo is None else int(np.searchsorted(iy, lo, "left"))
        b = len(iy) if hi is None else int(np.searchsorted(iy, hi, "left"))
        ln = length[a:b].astype(np.float64)
        out.append(float((ln + ln * ln / 65536.0).sum()) + 1.0)
    return out


class FrameDump:
    """`--frame-dump PATH` (3C-01): appends every emitted frame's bytes to
    `PATH.bin` and an index row to `PATH.tsv` (`level ix iy parcel_type
    sub_ix sub_iy offset len sha256`), in the build's canonical frame order.
    Planning/IO only -- no build logic."""

    def __init__(self, path_prefix: str):
        self._bin = open(path_prefix + ".bin", "ab")
        self._tsv = open(path_prefix + ".tsv", "w")
        self._off = 0

    def write(self, level: int, ix: int, iy: int, parcel_type: int,
              sub_ix: int, sub_iy: int, frame_bytes: bytes) -> None:
        self._bin.write(frame_bytes)
        n = len(frame_bytes)
        self._tsv.write(
            f"{level}\t{ix}\t{iy}\t{parcel_type}\t{sub_ix}\t{sub_iy}\t"
            f"{self._off}\t{n}\t{hashlib.sha256(frame_bytes).hexdigest()}\n")
        self._off += n

    def close(self) -> None:
        self._bin.close()
        self._tsv.close()


def run(spool_dir: str, out_path: str, levels: list[int],
        fixture: str | None, disk_title: str, fill_mask: bool = False,
        frame_digest: str | None = None, workers: int = 1,
        window: tuple[int, int, int, int, int] | None = None,
        bench_path: str | None = None, frame_dump: str | None = None) -> int:
    """`window`: `(level, ix0, iy0, ix1, iy1)`, a half-open `[ix0,ix1) x
    [iy0,iy1)` cell rectangle (3C-01) -- restricts the build to that one
    level and emits frames only for cells inside it (planning, not build
    logic: it only narrows which cells are emitted; source shapes still come
    from the whole level's spool, so borrowed edge shapes from outside the
    window still arrive). `bench_path`/`frame_dump` are the `--bench` and
    `--frame-dump` outputs."""
    t_start = time.monotonic()
    if not os.path.isdir(spool_dir):
        print(f"ERROR: spool directory not found: {spool_dir}", file=sys.stderr)
        return 1

    window_rect = None
    if window is not None:
        win_level, ix0, iy0, ix1, iy1 = window
        if ix1 <= ix0 or iy1 <= iy0:
            print("ERROR: --window is empty (IX1 <= IX0 or IY1 <= IY0)", file=sys.stderr)
            return 1
        levels = [win_level]
        window_rect = (ix0, ix1 - 1, iy0, iy1 - 1)  # half-open -> inclusive

    dump = FrameDump(frame_dump) if frame_dump else None

    reader = SpoolReader(spool_dir)
    mask = load_parcel_mask() if fill_mask else None
    available = set(reader.levels())
    grid = ReferenceGrid.load()
    thresholds = _load_level_thresholds()
    kind_budgets = _load_level_kind_budgets()
    trimmed_items: dict[str, dict] = {}
    halo_names: dict[str, int] = {}
    overlap_stats: dict[str, dict] = {}
    from kiwiw import cbuild as _cbuild
    eo_acc_total = _cbuild.empty_eo_stats()
    name_drops = {str(level): 0 for level in levels}
    bench_levels: dict[str, dict] = {}

    spool_stats = {lvl: reader.stats(lvl) for lvl in levels}
    # Optional per-frame digest listing (plan 02): localizes a byte mismatch to a
    # (level, ix, iy, parcel_type, sub_ix, sub_iy) frame. Regenerable, never committed.
    digest_fh = open(frame_digest, "w") if frame_digest else None
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    # Workers spill frames to their own files; assembly is vectorised over the tables.
    spill_dir = os.path.dirname(out_path) or "."
    table_files: list[str] = []

    pool = None
    if workers > 1:
        import multiprocessing as mp
        # Eager fork while the parent is still small: workers' shared copy-on-write
        # pages then stay small (a lazily-forked executor would fork a big parent).
        pool = mp.get_context("fork").Pool(workers)

    level_builds: dict[int, aw.LevelBuild] = {}
    manifest_levels: dict[str, dict] = {}
    t_run = time.monotonic()
    for level in levels:
        t_level = time.monotonic()
        print(f"level {level}: encoding ...", flush=True)
        if level not in available:
            print(f"level {level}: no spooled content, skipping", flush=True)
            print(f"level {level}: out-of-span names dropped: 0", flush=True)
            level_builds[level] = aw.LevelBuild(level=level)
            manifest_levels[str(level)] = {"parcels": 0, "bytes": 0, "divided_parents": 0}
            continue
        threshold_bytes = thresholds.get(level, U16_MAPFRAME_BYTE_CEILING)
        trim_stats: dict = {}
        # 3-09 / 3C-08: E1 then E2 once per row range; E1's counters are the
        # manifest's `overlap` block. `--window`/`--fixture` narrow only the
        # receiving (emitted) cells -- source shapes come from the whole level.
        (table, n_parcels, n_bytes, n_divided_parents, max_frame, ov_stats,
         level_bench, level_eo) = _encode_level(
            level, reader, fixture, threshold_bytes, mask, kind_budgets.get(level) or None,
            trim_stats, (level in NAME_HALO_LEVELS), spill_dir, digest_fh=digest_fh,
            pool=pool, jobs=workers, window_rect=window_rect,
            bench=bench_path is not None, dump=dump)
        overlap_stats[str(level)] = ov_stats
        _cbuild.merge_eo_stats(eo_acc_total, level_eo)
        name_drops[str(level)] = ov_stats.pop("out_of_span_names_dropped")
        print(f"level {level}: out-of-span names dropped: {name_drops[str(level)]:,}",
              flush=True)
        print(f"level {level}: overlap: {ov_stats['shared_shapes']:,} shapes shared into "
              f"{ov_stats['edge_cells']:,} edge + {ov_stats['interior_cells']:,} interior "
              f"cells, {ov_stats['skipped_missing_cells']:,} overlapped cells skipped "
              f"(not emitted)", flush=True)
        table_files += table.files
        if level_bench is not None:
            level_bench["wall_s"] = time.monotonic() - t_level
            bench_levels[str(level)] = level_bench
        trimmed, halo = _trim_manifest_blocks(level, trim_stats)
        if halo:
            print(f"level {level}: name halo added {trim_stats['halo_names']:,} "
                  f"neighbouring road-name records to divided sub-cells",
                  flush=True)
            halo_names.update(halo)
        if trimmed:
            trimmed_items.update(trimmed)
            total = trim_stats.get("total", {})
            for k, n in trim_stats["dropped"].items():
                pct = 100.0 * n / max(1, total.get(k, 0))
                print(f"level {level}: TRIM {k}: dropped {n:,}/{total.get(k, 0):,} "
                      f"({pct:.3f}%) in {trim_stats.get('cells', {}).get(k, 0)} sub-cells"
                      + ("  ** >1% BLOCKER **" if pct > 1.0 else ""), flush=True)
        level_builds[level] = aw.LevelBuild(level=level, table=table)
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
        # Plan 58: drop finished-level residency. Primary close is in `_e1spool`
        # on the next level key change; to *guarantee* every worker frees its
        # E1Spool (Pool.map does not pin one task per worker), recycle the
        # fork pool after each level. Spill *files* on disk stay (FrameTable
        # paths); only worker FDs/process state die with the pool.
        import gc
        import multiprocessing as mp
        if pool is not None:
            pool.close()
            pool.join()
            pool = mp.get_context("fork").Pool(workers)
        else:
            _release_worker_encode_caches()
        gc.collect()

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
                                      out_path=out_path)
    for f in set(table_files):
        try:
            os.unlink(f)
        except OSError:
            pass
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
        "overlap": overlap_stats,
        "out_of_span_names_dropped": name_drops,
        "fixture": fixture,
    }
    manifest_path = os.path.join(os.path.dirname(out_path) or ".", "manifest.json")
    with open(manifest_path, "w") as fh:
        json.dump(manifest, fh, indent=2)
    print(f"wrote {manifest_path}", flush=True)

    # Plan 48 Phase 2: EO census sidecar (output-neutral; disc bytes unchanged).
    eo_sidecar = os.path.join(os.path.dirname(out_path) or ".", "eo_census.json")
    _cbuild.write_eo_census_sidecar(
        eo_sidecar, eo_acc_total,
        meta={"out": out_path, "sha256": sha256, "workers": workers,
              "fixture": fixture, "levels": list(levels)})
    print(f"wrote {eo_sidecar} guard_hits={eo_acc_total.get('guard_hits', 0)} "
          f"declines={eo_acc_total.get('declines_total', 0)} "
          f"entries={eo_acc_total.get('eo_clip_entries', 0)}", flush=True)

    if dump is not None:
        dump.close()

    if bench_path is not None:
        wall_s = time.monotonic() - t_start
        bench_record = {
            "wall_s": wall_s,
            "outside_encode_s": wall_s - sum(
                lv.get("wall_s", 0.0) for lv in bench_levels.values()),
            "levels": bench_levels,
        }
        with open(bench_path, "w") as fh:
            json.dump(bench_record, fh, indent=2)
        print(f"wrote {bench_path}", flush=True)

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
    ap.add_argument("--fixture", choices=sorted(mesh.FIXTURE_BBOXES), default=None,
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
    ap.add_argument("--bench", default=None, metavar="PATH",
                     help="Write a Contract H bench record (JSON: per-level "
                          "wall/prepass/py/c/handoff/ranges/workers/calls, plus "
                          "top-level wall and outside_encode_s) (3C-01)")
    ap.add_argument("--window", type=int, nargs=5, default=None,
                     metavar=("LEVEL", "IX0", "IY0", "IX1", "IY1"),
                     help="Restrict the build to one level and emit frames only for "
                          "cells inside this half-open [IX0,IX1) x [IY0,IY1) cell "
                          "rectangle; source shapes still come from the whole level's "
                          "spool (3C-01)")
    ap.add_argument("--frame-dump", default=None, metavar="PATH",
                     help="Write every emitted frame's bytes to PATH.bin and an index "
                          "PATH.tsv (level ix iy parcel_type sub_ix sub_iy offset len "
                          "sha256), in canonical frame order (3C-01)")
    args = ap.parse_args()

    window = tuple(args.window) if args.window is not None else None
    return run(spool_dir=args.spool, out_path=args.out, levels=args.levels,
               fixture=args.fixture, disk_title=args.disk_title,
               fill_mask=not args.no_fill_mask,
               frame_digest=args.frame_digest, workers=args.workers,
               window=window, bench_path=args.bench, frame_dump=args.frame_dump)


if __name__ == "__main__":
    raise SystemExit(main())
