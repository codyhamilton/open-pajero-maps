#!/usr/bin/env python3
"""Plan 47 Phase 2: per-key complete-repair representability (historic 188 + added 89).

Meeting sources = class-2 spool rings of the key's type that meet the cell by the
same (a)/(b)/(c) limbs as quantisation_roundtrip._required_cells. Face / wire
contract = tracked parser/tools/k1_representable.py.

Target 3-15 numbers for historic 188: 885 faces / 189 meets / 205 in-cell / 0 representable.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[8]
OUT = Path(__file__).resolve().parent
KEYS = OUT.parent / "keys"
TRIAGE_P5 = ROOT / "docs/plans/04-c-core-orchestration/triage/historical_bg/p5_owner_exclusive"
sys.path[:0] = [str(ROOT / "parser"), str(ROOT / "parser/tools"), str(TRIAGE_P5)]

from kiwiw.spool import SpoolReader  # noqa: E402
from tools.k1_representable import (  # noqa: E402
    centre_demands, clip_rect, decompose_eo_faces, representable, wire_survives,
)
from quantisation_roundtrip import Lattice, RAW, TOL  # noqa: E402
from leaf_io import _spool_cell  # noqa: E402

SPOOL = ROOT / "output/extract_timing/spool"


def load_keys(path: Path):
    rows = []
    with path.open() as f:
        for r in csv.DictReader(f, delimiter="\t"):
            rows.append({
                "level": int(r["level"]), "ix": int(r["ix"]), "iy": int(r["iy"]),
                "code": int(r["code"]),
            })
    return rows


def ring_global_raw(coords, lat: Lattice):
    out = [(float(lat.gx(lo)), float(lat.gy(la))) for la, lo in coords]
    if out and out[0] != out[-1]:
        out.append(out[0])
    return out


def open_ring(poly):
    if poly and poly[0] == poly[-1]:
        return poly[:-1]
    return poly


def meets_cell(poly, ix, iy) -> bool:
    """poly may be closed; tests use open geometry for centre_demands."""
    op = open_ring(poly)
    if len(op) < 3:
        return False
    xs = [p[0] for p in op]
    ys = [p[1] for p in op]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    cx = int(np.floor((x0 + x1) / 2.0 / RAW))
    cy = int(np.floor((y0 + y1) / 2.0 / RAW))
    inside1 = (x0 >= cx * RAW and x1 <= (cx + 1) * RAW and
               y0 >= cy * RAW and y1 <= (cy + 1) * RAW)
    if inside1 and (cx, cy) == (ix, iy):
        rx, ry = np.rint(xs), np.rint(ys)
        area = float(np.sum(rx * np.roll(ry, -1) - np.roll(rx, -1) * ry))
        if area != 0:
            return True
    for x, y in zip(xs, ys):
        kx, ky = int(np.floor(x / RAW)), int(np.floor(y / RAW))
        if (kx, ky) != (ix, iy):
            continue
        fx, fy = x - kx * RAW, y - ky * RAW
        if 1 <= fx <= RAW - 1 and 1 <= fy <= RAW - 1:
            return True
    if centre_demands(op, ix, iy, TOL):
        return True
    return False


def face_in_cell(face, ix, iy) -> bool:
    clipped = clip_rect(face, ix * RAW, iy * RAW, (ix + 1) * RAW, (iy + 1) * RAW)
    return len(clipped) >= 3


def eval_key(spool, lat, level, ix, iy, code, neighbourhood=3):
    meet_rings = []
    seen = set()
    for dx in range(-neighbourhood, neighbourhood + 1):
        for dy in range(-neighbourhood, neighbourhood + 1):
            content = _spool_cell(spool, level, ix + dx, iy + dy)
            if not content:
                continue
            for ri, bg in enumerate(content.get("backgrounds") or []):
                coords = getattr(bg, "coords", None) or []
                if len(coords) < 3:
                    continue
                tc = int(getattr(bg, "type_code", 0) or 0)
                if tc != code:
                    continue
                cls = int(getattr(bg, "shape_class", getattr(bg, "cls", 2)) or 2)
                if cls != 2:
                    continue
                poly = ring_global_raw(coords, lat)
                if not meets_cell(poly, ix, iy):
                    continue
                sid = (ix + dx, iy + dy, ri, tc)
                if sid in seen:
                    continue
                seen.add(sid)
                meet_rings.append((sid, poly))

    n_faces = n_in_cell = n_repr_meets = 0
    for sid, poly in meet_rings:
        op = open_ring(poly)
        faces = decompose_eo_faces(op)
        f_in = sum(1 for face in faces if face_in_cell(face, ix, iy))
        rep = bool(representable(op, ix, iy))
        n_faces += len(faces)
        n_in_cell += f_in
        n_repr_meets += int(rep)
    return {
        "meets": len(meet_rings),
        "faces": n_faces,
        "in_cell": n_in_cell,
        "representable_meets": n_repr_meets,
        "any_representable": int(n_repr_meets > 0),
    }


def run_set(name, keys, spool, neighbourhood):
    rows = []
    totals = {
        "keys": 0, "meets": 0, "faces": 0, "in_cell": 0,
        "representable_keys": 0, "representable_meets": 0,
    }
    # Lattice per level (keys are L0)
    lats = {}
    for i, k in enumerate(keys):
        lv = k["level"]
        if lv not in lats:
            lats[lv] = Lattice(lv)
        ev = eval_key(spool, lats[lv], lv, k["ix"], k["iy"], k["code"], neighbourhood)
        rows.append({
            "level": k["level"], "ix": k["ix"], "iy": k["iy"], "code": k["code"],
            "meets": ev["meets"], "faces": ev["faces"], "in_cell": ev["in_cell"],
            "representable_meets": ev["representable_meets"],
            "any_representable": ev["any_representable"],
        })
        totals["keys"] += 1
        totals["meets"] += ev["meets"]
        totals["faces"] += ev["faces"]
        totals["in_cell"] += ev["in_cell"]
        totals["representable_keys"] += ev["any_representable"]
        totals["representable_meets"] += ev["representable_meets"]
        if (i + 1) % 20 == 0 or i == 0 or i + 1 == len(keys):
            print(f"  {name} {i+1}/{len(keys)} meets={totals['meets']} faces={totals['faces']} "
                  f"in_cell={totals['in_cell']} repr_keys={totals['representable_keys']}",
                  flush=True)
    path = OUT / f"table_{name}.tsv"
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()), delimiter="\t")
        w.writeheader()
        w.writerows(rows)
    return totals, path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--neighbourhood", type=int, default=32)
    ap.add_argument("--set", choices=("188", "89", "both"), default="both")
    args = ap.parse_args()
    print(f"ROOT={ROOT} neighbourhood={args.neighbourhood}", flush=True)
    spool = SpoolReader(str(SPOOL))
    summary = {
        "neighbourhood": args.neighbourhood,
        "target_3_15_188": {"faces": 885, "meets": 189, "in_cell": 205, "representable": 0},
    }
    if args.set in ("188", "both"):
        keys = load_keys(KEYS / "historic_188_in_739.tsv")
        print(f"historic_188 n={len(keys)}", flush=True)
        totals, path = run_set("188", keys, spool, args.neighbourhood)
        summary["188"] = {**totals, "path": str(path.relative_to(ROOT))}
        print("188 totals", totals, flush=True)
        print("vs_3_15", {
            "faces": (totals["faces"], 885),
            "meets": (totals["meets"], 189),
            "in_cell": (totals["in_cell"], 205),
            "representable_keys": (totals["representable_keys"], 0),
        }, flush=True)
    if args.set in ("89", "both"):
        keys = load_keys(KEYS / "added_89.tsv")
        print(f"added_89 n={len(keys)}", flush=True)
        totals, path = run_set("89", keys, spool, args.neighbourhood)
        summary["89"] = {**totals, "path": str(path.relative_to(ROOT))}
        print("89 totals", totals, flush=True)
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print("SUMMARY", json.dumps(summary), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
