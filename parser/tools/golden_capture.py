#!/usr/bin/env python3
"""Capture Contract T (c) goldens: closed fixture spools + expected frames (3C-03).

A golden is a cell window at one level, the **closed fixture spool** for it
(every source cell of that level holding a shape whose lat/lon bounding box
meets the window, sliced out of the full spool through `SpoolReader` and
rewritten through `SpoolWriter`), and the frames the windowed build emits
from that fixture (`build_alldata.py --window ... --frame-dump ...`).

This is a verification tool (Contract B): its bounding-box index only picks
which spool records to copy; it never feeds the build, and it holds no build
logic. The expected frames always come from running the build itself.

Subcommands:
  size     closure cells and bytes of a window (for choosing windows)
  capture  write <out>/<name>/{spool/, frames.bin, frames.tsv, golden.json}
  prove    three-way closure proof: full-AU --frame-digest rows, a windowed
           build on the full spool, and the golden's fixture frames must agree
  check    rebuild a golden from its fixture spool and compare byte for byte
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "parser"))

from kiwiw.spool import _SEG_HDR, SpoolReader, SpoolWriter, decode_columns  # noqa: E402

BUILD = REPO / "parser" / "build_alldata.py"
PYTHON = sys.executable
MARGIN = 1e-3  # cell units; wider than the build's own 1e-6, so the closure is a superset
INDEX_DIR = REPO / "output" / "goldens-3C" / "index"

# (points-per-shape column, lat column, lon column); None = one point per item.
_SHAPES = (("r_nstored", "n_lat", "n_lon"), ("r_npts", "p_lat", "p_lon"),
           ("b_nstored", "c_lat", "c_lon"), (None, "s_lat", "s_lon"))


def _grid(level: int):
    from osm_to_parcel_geometry import TileGrid
    return TileGrid.from_reference(level)


# ------------------------------------------------------------------ index

def _cell_reach(cols, ix, iy, g):
    """Cell-unit bboxes `(x0, x1, y0, y1)` (inclusive, integer) of every shape
    in one cell record that reaches outside the cell itself."""
    out = []
    for ncol, latc, lonc in _SHAPES:
        lat, lon = cols[latc], cols[lonc]
        if not len(lat):
            continue
        gx = (lon - g.disc_lon_lo) / g.cell_lon
        gy = (lat - g.disc_lat_lo) / g.cell_lat
        if ncol is None:
            x0 = x1 = gx
            y0 = y1 = gy
        else:
            n = cols[ncol].astype(np.int64)
            n = n[n > 0]
            if not len(n):
                continue
            s = np.cumsum(n) - n
            x0, x1 = np.minimum.reduceat(gx, s), np.maximum.reduceat(gx, s)
            y0, y1 = np.minimum.reduceat(gy, s), np.maximum.reduceat(gy, s)
        b = np.stack([np.floor(x0 - MARGIN), np.floor(x1 + MARGIN),
                      np.floor(y0 - MARGIN), np.floor(y1 + MARGIN)], 1).astype(np.int64)
        b = b[(b[:, 0] < ix) | (b[:, 1] > ix) | (b[:, 2] < iy) | (b[:, 3] > iy)]
        if len(b):
            out.append(b)
    return np.concatenate(out) if out else np.zeros((0, 4), np.int64)


def load_index(spool: str, level: int) -> dict:
    """`{"cell": source cell ordinal, "box": (n, 4) reach boxes}` for every
    shape leaving its own cell; cached per spool index file."""
    idx_file = Path(spool) / f"level_{level}.idx"
    st = idx_file.stat()
    tag = hashlib.sha256(f"{idx_file.resolve()}|{st.st_size}|{st.st_mtime_ns}|{MARGIN}"
                         .encode()).hexdigest()[:16]
    cache = INDEX_DIR / f"L{level}_{tag}.npz"
    if cache.exists():
        z = np.load(cache)
        return {"cell": z["cell"], "box": z["box"]}
    g = _grid(level)
    rd = SpoolReader(spool)
    cells, boxes = [], []
    for i, (ix, iy, raw) in enumerate(rd.iter_cell_raw(level)):
        b = _cell_reach(decode_columns(raw), ix, iy, g)
        if len(b):
            cells.append(np.full(len(b), i, np.int64))
            boxes.append(b)
    rd.close()
    res = {"cell": np.concatenate(cells) if cells else np.zeros(0, np.int64),
           "box": np.concatenate(boxes) if boxes else np.zeros((0, 4), np.int64)}
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    np.savez(cache, **res)
    return res


def closure(spool: str, level: int, window) -> np.ndarray:
    """Ordinals (ascending, i.e. spool `(iy, ix)` order) of the source cells
    of the closed fixture for half-open `window = (ix0, iy0, ix1, iy1)`."""
    ix0, iy0, ix1, iy1 = window
    rd = SpoolReader(spool)
    li = rd._load_idx(level)
    rd.close()
    inside = np.nonzero((li.ix >= ix0) & (li.ix < ix1) & (li.iy >= iy0) & (li.iy < iy1))[0]
    ind = load_index(spool, level)
    b = ind["box"]
    hit = (b[:, 1] >= ix0) & (b[:, 0] <= ix1 - 1) & (b[:, 3] >= iy0) & (b[:, 2] <= iy1 - 1)
    return np.union1d(inside, np.unique(ind["cell"][hit]))


def write_fixture(spool: str, level: int, ordinals: np.ndarray, dest: Path) -> int:
    """Copy the chosen records through `SpoolWriter` (raw records, one
    segment each) and check every rewritten record is byte-identical."""
    if dest.exists():
        shutil.rmtree(dest)
    rd = SpoolReader(spool)
    li = rd._load_idx(level)
    raws = {}
    w = SpoolWriter(dest)
    f = w._file_for(level)
    for i in ordinals.tolist():
        ix, iy = int(li.ix[i]), int(li.iy[i])
        rec = rd._read_cell(level, int(li.offset[i]), int(li.length[i]))
        raws[(ix, iy)] = rec
        f.write(_SEG_HDR.pack(ix, iy, len(rec)))
        w._segs[level][(ix, iy)].append((w._pos[level] + _SEG_HDR.size, len(rec)))
        f.write(rec)
        w._pos[level] += _SEG_HDR.size + len(rec)
    w._levels_seen.add(level)
    w.close()
    rd.close()
    back = SpoolReader(dest)
    got = {(ix, iy): raw for ix, iy, raw in back.iter_cell_raw(level)}
    back.close()
    if got != raws:
        raise SystemExit(f"fixture spool {dest}: rewritten records differ from the source")
    return sum(p.stat().st_size for p in dest.iterdir())


# ------------------------------------------------------------------ build

def run_build(spool, level, window, work: Path, jobs: int = 1, log=None):
    """Windowed build with `--frame-dump`; returns `(tsv_rows, bin_bytes, secs)`."""
    work.mkdir(parents=True, exist_ok=True)
    for p in ("frames.bin", "frames.tsv"):
        (work / p).unlink(missing_ok=True)
    cmd = [PYTHON, str(BUILD), "--spool", str(spool), "--out", str(work / "ALLDATA.KWI"),
           "--window", str(level), *map(str, window), "--frame-dump", str(work / "frames"),
           "-j", str(jobs)]
    t0 = time.monotonic()
    r = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True)
    secs = time.monotonic() - t0
    if log is not None:
        Path(log).write_text(r.stdout + r.stderr)
    if r.returncode:
        raise RuntimeError(f"build failed rc={r.returncode}: {' '.join(cmd)}\n{r.stderr[-3000:]}")
    rows = (work / "frames.tsv").read_text().splitlines()
    return rows, (work / "frames.bin").read_bytes(), secs


def _key(row: str) -> tuple:
    """(level ix iy parcel_type sub_ix sub_iy len sha256) of a dump or digest row."""
    f = row.split()
    if len(f) == 9:  # dump: ... offset len sha
        f = f[:6] + f[7:]
    return tuple(f)


def compare(golden: Path, rows, data: bytes) -> list[str]:
    """Differences between a build's dump and the stored golden (empty = identical)."""
    want = (golden / "frames.tsv").read_text().splitlines()
    wbin = (golden / "frames.bin").read_bytes()
    errs = []
    if len(rows) != len(want):
        errs.append(f"frame count {len(rows)} != golden {len(want)}")
    for a, b in zip(rows, want):
        if a != b:
            errs.append(f"frame differs: got {a} want {b}")
            if len(errs) > 10:
                break
    if data != wbin:
        errs.append(f"frame bytes differ (sha {hashlib.sha256(data).hexdigest()[:16]} vs "
                    f"{hashlib.sha256(wbin).hexdigest()[:16]})")
    return errs


# ------------------------------------------------------------------ commands

def cmd_size(a):
    ords = closure(a.spool, a.level, a.window)
    rd = SpoolReader(a.spool)
    li = rd._load_idx(a.level)
    n = int(li.length[ords].sum())
    print(json.dumps({"level": a.level, "window": a.window, "cells": len(ords), "bytes": n}))


def cmd_capture(a):
    dest = Path(a.out) / a.name
    dest.mkdir(parents=True, exist_ok=True)
    ords = closure(a.spool, a.level, a.window)
    rd = SpoolReader(a.spool)
    li = rd._load_idx(a.level)
    src = [[int(li.ix[i]), int(li.iy[i])] for i in ords.tolist()]
    rd.close()
    spool_bytes = write_fixture(a.spool, a.level, ords, dest / "spool")
    with tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR")) as td:
        rows, data, secs = run_build(dest / "spool", a.level, a.window, Path(td), a.jobs,
                                     log=dest / "capture_build.log" if a.keep_log else None)
        man = json.loads((Path(td) / "manifest.json").read_text())
    (dest / "frames.tsv").write_text("".join(r + "\n" for r in rows))
    (dest / "frames.bin").write_bytes(data)
    meta = {
        "level": a.level, "window": list(a.window), "covers": a.covers,
        "frames": len(rows), "frame_sha256": [r.split()[8] for r in rows],
        "total_sha256": hashlib.sha256(data).hexdigest(), "frame_bytes": len(data),
        "fixture_spool_bytes": spool_bytes, "source_cells": src,
        "manifest": {k: man.get(k) for k in ("trimmed_items", "halo_names", "overlap")},
        "capture_build_s": round(secs, 1),
    }
    (dest / "golden.json").write_text(json.dumps(meta, indent=1) + "\n")
    print(json.dumps({k: meta[k] for k in ("level", "window", "frames", "frame_bytes",
                                           "fixture_spool_bytes")} | {"name": a.name,
                                                                      "cells": len(src)}))


def cmd_prove(a):
    g = Path(a.golden)
    meta = json.loads((g / "golden.json").read_text())
    lvl, (ix0, iy0, ix1, iy1) = meta["level"], meta["window"]
    want = [_key(r) for r in (g / "frames.tsv").read_text().splitlines()]
    dig = []
    with open(a.digest) as fh:
        for line in fh:
            f = line.split()
            if (int(f[0]) == lvl and ix0 <= int(f[1]) < ix1 and iy0 <= int(f[2]) < iy1):
                dig.append(tuple(f))
    errs = []
    if dig != want:
        errs.append(f"digest rows ({len(dig)}) != golden rows ({len(want)})")
    work = Path(a.work) / g.name
    rows, data, secs = run_build(a.spool, lvl, meta["window"], work, a.jobs,
                                 log=work.with_suffix(".log"))
    errs += [f"full-spool windowed: {e}" for e in compare(g, rows, data)]
    fix = compare(g, *run_build(g / "spool", lvl, meta["window"], work / "fixture", 1)[:2])
    errs += [f"fixture rebuild: {e}" for e in fix]
    man = json.loads((work / "manifest.json").read_text())
    for k in ("trimmed_items", "halo_names"):
        if man.get(k) != meta["manifest"].get(k):
            errs.append(f"manifest {k}: full-spool {man.get(k)} != fixture {meta['manifest'].get(k)}")
    print(f"{g.name}: digest {len(dig)} rows, full-spool windowed {len(rows)} frames "
          f"[{secs:.1f}s], fixture {len(want)} frames -> "
          + ("IDENTICAL" if not errs else "MISMATCH"))
    for e in errs:
        print("  " + e)
    return 1 if errs else 0


def cmd_check(a):
    g = Path(a.golden)
    meta = json.loads((g / "golden.json").read_text())
    with tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR")) as td:
        rows, data, secs = run_build(g / "spool", meta["level"], meta["window"], Path(td), a.jobs)
    errs = compare(g, rows, data)
    print(f"{g.name}: {len(rows)} frames [{secs:.1f}s] -> " + ("IDENTICAL" if not errs else "MISMATCH"))
    for e in errs:
        print("  " + e)
    return 1 if errs else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    def win(p):
        p.add_argument("--spool", default=str(REPO / "output" / "extract_timing" / "spool"))
        p.add_argument("--level", type=int, required=True)
        p.add_argument("--window", type=int, nargs=4, required=True,
                       metavar=("IX0", "IY0", "IX1", "IY1"), help="half-open, as build --window")

    p = sub.add_parser("size")
    win(p)
    p = sub.add_parser("capture")
    win(p)
    p.add_argument("--name", required=True)
    p.add_argument("--covers", required=True, help="Contract T range(s) this golden covers")
    p.add_argument("--out", required=True, help="parent dir (committed fixtures or output/goldens-3C)")
    p.add_argument("-j", "--jobs", type=int, default=1)
    p.add_argument("--keep-log", action="store_true")
    p = sub.add_parser("prove")
    p.add_argument("--golden", required=True)
    p.add_argument("--spool", default=str(REPO / "output" / "extract_timing" / "spool"))
    p.add_argument("--digest", required=True, help="full-AU --frame-digest listing")
    p.add_argument("--work", required=True)
    p.add_argument("-j", "--jobs", type=int, default=1)
    p = sub.add_parser("check")
    p.add_argument("--golden", required=True)
    p.add_argument("-j", "--jobs", type=int, default=1)
    a = ap.parse_args()
    return {"size": cmd_size, "capture": cmd_capture, "prove": cmd_prove,
            "check": cmd_check}[a.cmd](a) or 0


if __name__ == "__main__":
    raise SystemExit(main())
