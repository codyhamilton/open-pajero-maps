#!/usr/bin/env python3
"""Plan 48 Phase 1: dump EO arrangement for known decline rings and name mechanisms.

Expects an EO_DIAG-instrumented probe.so that writes a JSON dump path via env
EO_DIAG_OUT (production builds omit EO_DIAG — zero cost). Exact checks use
Python Fraction on dumped double coordinates (DESIGN H1–H4).
"""
from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
import sys
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DECLINE = (
    ROOT / "docs/plans/04-c-core-orchestration/triage/independent_reviews"
    / "3-14/conditions/eo_decline"
)


def orient(a, b, c):
    """Exact orientation of (a→b→c) via Fraction cross product sign."""
    ax, ay = Fraction(a[0]), Fraction(a[1])
    bx, by = Fraction(b[0]), Fraction(b[1])
    cx, cy = Fraction(c[0]), Fraction(c[1])
    v = (bx - ax) * (cy - ay) - (by - ay) * (cx - ax)
    return (v > 0) - (v < 0)


def proper_cross(p, q, r, s):
    return orient(p, q, r) * orient(p, q, s) < 0 and orient(r, s, p) * orient(r, s, q) < 0


def check_h1_crossings(edges):
    """edges: list of ((x0,y0),(x1,y1), frame_flag). Non-adjacent proper crosses."""
    hits = []
    for i in range(len(edges)):
        for j in range(i + 1, len(edges)):
            a, b, _fa = edges[i][0], edges[i][1], edges[i][2]
            c, d, _fb = edges[j][0], edges[j][1], edges[j][2]
            # skip if share a vertex (adjacent in arrangement sense — caller filters)
            if a in (c, d) or b in (c, d):
                continue
            if proper_cross(a, b, c, d):
                hits.append({"i": i, "j": j, "a": a, "b": b, "c": c, "d": d})
    return hits


def check_h2_atan2_ties(out_edges_by_vertex):
    """out_edges_by_vertex: {vid: [(dx,dy,heid), ...]}. Exact ties + order vs atan2."""
    ties, order_mismatch = [], []
    for vid, outs in out_edges_by_vertex.items():
        if len(outs) < 2:
            continue
        # exact angle sort by Fraction atan2 proxy: sort by (quadrant, dy/dx rational)
        def key(o):
            dx, dy, _ = o
            return math.atan2(dy, dx)

        by_atan = sorted(range(len(outs)), key=lambda i: key(outs[i]))
        # exact ties: equal atan2 doubles
        for i in range(len(outs)):
            for j in range(i + 1, len(outs)):
                if math.atan2(outs[i][1], outs[i][0]) == math.atan2(outs[j][1], outs[j][0]):
                    ties.append({"vid": vid, "a": outs[i], "b": outs[j]})
        # exact orientation cycle vs atan2 order
        for k in range(len(by_atan)):
            i0, i1, i2 = by_atan[k], by_atan[(k + 1) % len(by_atan)], by_atan[(k + 2) % len(by_atan)]
            # skip if <3
            if len(by_atan) < 3:
                break
            o = orient((0, 0), (outs[i0][0], outs[i0][1]), (outs[i1][0], outs[i1][1]))
            # weak check: consecutive atan2 should be CCW or tied
            if o < 0 and math.atan2(outs[i0][1], outs[i0][0]) != math.atan2(outs[i1][1], outs[i1][0]):
                order_mismatch.append({"vid": vid, "i0": outs[i0], "i1": outs[i1]})
    return ties, order_mismatch


def name_mechanism(dump: dict) -> dict:
    """Given EO_DIAG dump, return named mechanism + witnesses."""
    edges = [((e["a"][0], e["a"][1]), (e["b"][0], e["b"][1]), int(e.get("frame", 0)))
             for e in dump.get("edges", [])]
    crosses = check_h1_crossings(edges)
    outs = {}
    for he in dump.get("half_edges", []):
        vid = he["origin"]
        outs.setdefault(vid, []).append((he["dx"], he["dy"], he["id"]))
    ties, mism = check_h2_atan2_ties(outs)
    succ = dump.get("successor", {})
    # non-injective successor
    rev = {}
    non_inj = []
    for src, dst in succ.items():
        rev.setdefault(dst, []).append(src)
    for dst, srcs in rev.items():
        if len(srcs) > 1:
            non_inj.append({"dst": dst, "srcs": srcs})
    zero_len = [e for e in edges if e[0] == e[1]]
    mechanisms = []
    if crosses:
        mechanisms.append({"name": "H1_rounding_non_planarity", "witnesses": crosses[:5]})
    if ties:
        mechanisms.append({"name": "H2_equal_angle_ties", "witnesses": ties[:5]})
    if mism:
        mechanisms.append({"name": "H2_atan2_order_mismatch", "witnesses": mism[:5]})
    if zero_len:
        mechanisms.append({"name": "H3_zero_length_edge", "witnesses": zero_len[:5]})
    if non_inj:
        mechanisms.append({"name": "successor_non_injective", "witnesses": non_inj[:5]})
    if not mechanisms:
        mechanisms.append({"name": "unclassified", "witnesses": []})
    return {
        "mechanisms": mechanisms,
        "primary": mechanisms[0]["name"],
        "decline_site": dump.get("decline"),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rings", type=Path, default=DECLINE / "decline_rings.json")
    ap.add_argument("--dumps-dir", type=Path, default=DECLINE / "dumps")
    ap.add_argument("--out", type=Path, default=DECLINE / "mechanisms.json")
    ap.add_argument("--probe-so", type=Path, help="EO_DIAG-instrumented probe.so")
    args = ap.parse_args()
    rings = json.loads(args.rings.read_text())
    args.dumps_dir.mkdir(parents=True, exist_ok=True)
    results = {}
    for name, ring in rings.items():
        dump_path = args.dumps_dir / f"{name}.json"
        if args.probe_so and args.probe_so.exists():
            import ctypes
            import numpy as np
            env_path = str(dump_path.resolve())
            os.environ["EO_DIAG_OUT"] = env_path
            lib = ctypes.CDLL(str(args.probe_so))
            fn = lib.probe_bg
            fn.restype = ctypes.c_int64
            fn.argtypes = [ctypes.c_void_p]*2 + [ctypes.c_int64] + [ctypes.c_void_p]*2 + [
                ctypes.c_int64, ctypes.c_void_p]
            lat = np.array([y for x, y in ring], "f8")
            lon = np.array([x for x, y in ring], "f8")
            rect = np.array([0, 0, 4096, 4096], "f8")
            out = np.zeros(1 << 20, "u1")
            nr = ctypes.c_int64()
            size = fn(lat.ctypes.data, lon.ctypes.data, len(ring), rect.ctypes.data,
                      out.ctypes.data, 1 << 20, ctypes.byref(nr))
            print(f"{name}: probe size={size} dump={dump_path.exists()}", flush=True)
        if not dump_path.exists():
            results[name] = {"status": "dump_missing", "ring_n": len(ring)}
            continue
        dump = json.loads(dump_path.read_text())
        results[name] = name_mechanism(dump)
        results[name]["status"] = "named"
        results[name]["ring_n"] = len(ring)
    args.out.write_text(json.dumps(results, indent=2) + "\n")
    print(json.dumps({k: v.get("primary", v.get("status")) for k, v in results.items()}, indent=2))
    missing = [k for k, v in results.items() if v.get("status") != "named"]
    return 1 if missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
