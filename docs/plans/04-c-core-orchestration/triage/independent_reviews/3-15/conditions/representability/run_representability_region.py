#!/usr/bin/env python3
"""Plan 47 Phase 2: representability via Region + _required_cells (tracked yardstick).

Meeting sources = class-2 shapes that demand the key cell under the same (a)/(b)/(c)
limbs as quantisation_roundtrip._required_cells, using Region(local Moore-1 ∪ tall).
Face / wire contract = tracked parser/tools/k1_representable.py.

Target 3-15 historic 188: 885 faces / 189 meets / 205 in-cell / 0 representable.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[8]
OUT = Path(__file__).resolve().parent
KEYS = OUT.parent / "keys"
sys.path[:0] = [str(ROOT / "parser"), str(ROOT / "parser/tools")]

from kiwiw.spool import SpoolReader  # noqa: E402
from tools.k1_representable import (  # noqa: E402
    centre_demands, clip_rect, decompose_eo_faces, representable,
)
from tools import quantisation_roundtrip as qr  # noqa: E402

SPOOL = ROOT / "output/extract_timing/spool"
RAW, TOL = qr.RAW, qr.TOL


def load_keys(path: Path):
    rows = []
    with path.open() as f:
        for r in csv.DictReader(f, delimiter="\t"):
            rows.append({
                "level": int(r["level"]), "ix": int(r["ix"]), "iy": int(r["iy"]),
                "code": int(r["code"]),
            })
    return rows


def load_tall(reader: SpoolReader, level: int, workers: int = 1):
    """Pass-1 tall shapes for one level (serial; lock already held)."""
    tasks = qr._pass1_tasks(reader, [level], workers)
    parts = []
    t0 = time.time()
    for i, task in enumerate(tasks):
        lv, a, arrs = qr._pass1(task)
        parts.append((a, qr.Shapes(*arrs)))
        if (i + 1) % 20 == 0 or i + 1 == len(tasks):
            print(f"  tall pass1 {i+1}/{len(tasks)} ({time.time()-t0:.1f}s)", flush=True)
    sh = qr.Shapes.concat([s for _a, s in sorted(parts, key=lambda p: p[0])])
    print(f"tall level {level}: {sh.n} shapes, {len(sh.x)} coords ({time.time()-t0:.1f}s)",
          flush=True)
    return sh, sh.bbox()


def open_ring(poly):
    if poly and poly[0] == poly[-1]:
        return poly[:-1]
    return poly


def face_in_cell(face, ix, iy) -> bool:
    clipped = clip_rect(face, ix * RAW, iy * RAW, (ix + 1) * RAW, (iy + 1) * RAW)
    return len(clipped) >= 3


def eval_key(reader, lat, tall, tall_bb, level, ix, iy, code):
    """Demanders via Region+_required_cells; count meets/faces/in_cell/representable."""
    region = qr.Region(reader, level, lat, tall, tall_bb, ix, ix, iy, iy)
    cells = {(ix, iy)}
    req = qr._required_cells(region, cells, ix, ix, iy, iy, with_demanders=True)
    key = (ix, iy, code)
    demanders = req.get(key, set())
    sh = region.shapes

    # Resolve shape indices (including -1 centre-batch → all class-2 of type)
    if -1 in demanders:
        candidates = set(np.nonzero(
            (sh.cls == 2) & (sh.type == code) & (sh.lengths() >= 3))[0].tolist())
        # Keep explicit demanders too
        candidates |= {s for s in demanders if s >= 0}
    else:
        candidates = {s for s in demanders if s >= 0}

    meet_polys = []
    seen = set()
    for s in sorted(candidates):
        if s < 0 or s >= sh.n:
            continue
        if int(sh.cls[s]) != 2 or int(sh.type[s]) != code or int(sh.lengths()[s]) < 3:
            continue
        poly = list(zip(
            sh.x[sh.off[s]:sh.off[s + 1]].tolist(),
            sh.y[sh.off[s]:sh.off[s + 1]].tolist(),
        ))
        # Must actually demand under (a)/(b)/(c) — centre-batch extras filtered
        if s not in demanders:
            if not centre_demands(open_ring(poly), ix, iy, TOL):
                continue
        sid = (int(sh.off[s]), int(sh.off[s + 1]), int(sh.type[s]))
        if sid in seen:
            continue
        seen.add(sid)
        meet_polys.append((s, poly, int(sh.mult[s])))

    n_faces = n_in_cell = n_repr = 0
    for s, poly, mult in meet_polys:
        op = open_ring(poly)
        faces = decompose_eo_faces(op)
        f_in = sum(1 for face in faces if face_in_cell(face, ix, iy))
        rep = bool(representable(op, ix, iy, mult))
        n_faces += len(faces)
        n_in_cell += f_in
        n_repr += int(rep)
    return {
        "meets": len(meet_polys),
        "faces": n_faces,
        "in_cell": n_in_cell,
        "representable_meets": n_repr,
        "any_representable": int(n_repr > 0),
        "n_demanders_raw": len(demanders),
    }


def run_set(name, keys, reader, lat, tall, tall_bb):
    rows = []
    totals = {
        "keys": 0, "meets": 0, "faces": 0, "in_cell": 0,
        "representable_keys": 0, "representable_meets": 0,
    }
    for i, k in enumerate(keys):
        ev = eval_key(reader, lat, tall, tall_bb, k["level"], k["ix"], k["iy"], k["code"])
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
    ap.add_argument("--set", choices=("188", "89", "both"), default="both")
    ap.add_argument("--workers", type=int, default=1)
    args = ap.parse_args()
    print(f"ROOT={ROOT} engine=Region+_required_cells", flush=True)
    reader = SpoolReader(str(SPOOL))
    # Keys are L0
    lat = qr.Lattice(0)
    tall, tall_bb = load_tall(reader, 0, workers=args.workers)
    summary = {
        "engine": "Region+_required_cells",
        "target_3_15_188": {"faces": 885, "meets": 189, "in_cell": 205, "representable": 0},
    }
    if args.set in ("188", "both"):
        keys = load_keys(KEYS / "historic_188_in_739.tsv")
        print(f"historic_188 n={len(keys)}", flush=True)
        totals, path = run_set("188", keys, reader, lat, tall, tall_bb)
        summary["188"] = {**totals, "path": str(path.relative_to(ROOT))}
        print("188 totals", totals, flush=True)
        print("vs_3_15", {
            "faces": (totals["faces"], 885),
            "meets": (totals["meets"], 189),
            "in_cell": (totals["in_cell"], 205),
            "representable_keys": (totals["representable_keys"], 0),
        }, flush=True)
        summary["match_3_15_188"] = (
            totals["faces"] == 885 and totals["meets"] == 189
            and totals["in_cell"] == 205 and totals["representable_keys"] == 0
        )
    if args.set in ("89", "both"):
        keys = load_keys(KEYS / "added_89.tsv")
        print(f"added_89 n={len(keys)}", flush=True)
        totals, path = run_set("89", keys, reader, lat, tall, tall_bb)
        summary["89"] = {**totals, "path": str(path.relative_to(ROOT))}
        print("89 totals", totals, flush=True)
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print("SUMMARY", json.dumps(summary), flush=True)
    return 0 if summary.get("match_3_15_188", True) else 0  # always 0; compare in summary


if __name__ == "__main__":
    raise SystemExit(main())
