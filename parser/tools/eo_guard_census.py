#!/usr/bin/env python3
"""Plan 48 Phase 2: EO face-walk decline census via kw__eo_stats (output-neutral).

Loads an EO_DIAG-optional probe.so that exports kw__eo_stats_get/reset (always
compiled into _cenc.c). Runs seeded rings or a build sidecar aggregation.
"""
from __future__ import annotations

import argparse
import ctypes
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "parser")]


def build_probe(so: Path, *, eo_diag: bool = False) -> Path:
    from kiwiw import cbuild
    so.parent.mkdir(parents=True, exist_ok=True)
    flags = list(cbuild.CFLAGS)
    if eo_diag:
        flags.append("-DEO_DIAG")
    cmd = [cbuild._find_cc(), *flags, "-shared",
           str(ROOT / "parser/tests/fixtures/bg_eo/probe.c"), "-lm", "-o", str(so)]
    subprocess.run(cmd, check=True)
    return so


def load_stats_api(so: Path):
    lib = ctypes.CDLL(str(so))
    lib.kw__eo_stats_reset.argtypes = []
    lib.kw__eo_stats_reset.restype = None
    lib.kw__eo_stats_get.argtypes = [ctypes.POINTER(ctypes.c_int64)] * 10 + [
        ctypes.POINTER(ctypes.c_double)]
    lib.kw__eo_stats_get.restype = None
    # probe_bg
    fn = lib.probe_bg
    fn.restype = ctypes.c_int64
    fn.argtypes = [ctypes.c_void_p] * 2 + [ctypes.c_int64] + [ctypes.c_void_p] * 2 + [
        ctypes.c_int64, ctypes.c_void_p]
    return lib, fn


def read_stats(lib) -> dict:
    vals = [ctypes.c_int64() for _ in range(10)]
    margin = ctypes.c_double()
    lib.kw__eo_stats_get(
        *[ctypes.byref(v) for v in vals], ctypes.byref(margin))
    keys = ("eo_clip_entries", "eo_clip_complex",
            "decline_intersect", "decline_cut", "decline_connect",
            "decline_walk_used", "decline_walk_bound", "decline_walk_nobest",
            "decline_grow", "walk_starts")
    out = {k: int(v.value) for k, v in zip(keys, vals)}
    out["walk_min_margin"] = float(margin.value)
    out["declines_total"] = sum(out[k] for k in keys if k.startswith("decline_"))
    return out


def run_ring(fn, ring):
    lat = np.array([y for x, y in ring], "f8")
    lon = np.array([x for x, y in ring], "f8")
    rect = np.array([0, 0, 4096, 4096], "f8")
    out = np.zeros(1 << 20, "u1")
    nr = ctypes.c_int64()
    size = fn(lat.ctypes.data, lon.ctypes.data, len(ring), rect.ctypes.data,
              out.ctypes.data, 1 << 20, ctypes.byref(nr))
    return int(size), int(nr.value)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rings", type=Path,
                    default=ROOT / "docs/plans/04-c-core-orchestration/triage/"
                    "independent_reviews/3-14/conditions/eo_decline/decline_rings.json")
    ap.add_argument("--so", type=Path, default=ROOT / "output/scratch-48/probe_census.so")
    ap.add_argument("--out", type=Path, default=ROOT / "output/scratch-48/census_rings.json")
    ap.add_argument("--case", action="append", default=None,
                    help="Restrict to named cases (default: all in --rings)")
    args = ap.parse_args()
    rings = json.loads(args.rings.read_text())
    if args.case:
        rings = {k: rings[k] for k in args.case}
    build_probe(args.so)
    lib, fn = load_stats_api(args.so)
    results = {}
    for name, ring in rings.items():
        lib.kw__eo_stats_reset()
        size, nr = run_ring(fn, ring)
        st = read_stats(lib)
        results[name] = {"size": size, "nrec": nr, **st}
        print(name, "size", size, "walk_used", st["decline_walk_used"],
              "declines", st["declines_total"], flush=True)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(results, indent=2) + "\n")
    # Sanity: r359 should hit walk_used >= 1
    if "r359" in results:
        ok = results["r359"]["decline_walk_used"] >= 1 and results["r359"]["size"] < 0
        print("r359_census_ok", ok, flush=True)
        return 0 if ok else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
