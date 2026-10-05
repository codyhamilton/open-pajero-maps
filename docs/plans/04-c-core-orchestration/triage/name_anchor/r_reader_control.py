#!/usr/bin/env python3
"""Bounded R Perth reader control and target-block census; run under the heavy guard."""
from __future__ import annotations

import argparse
from collections import Counter
import importlib.util
from pathlib import Path

PLAN = Path(__file__).resolve().parent
ROOT = PLAN.parents[4]
spec = importlib.util.spec_from_file_location("witness_p1_control", PLAN / "witness_p1.py")
w = importlib.util.module_from_spec(spec)
spec.loader.exec_module(w)


def control(disc):
    perth = next(w.disc_cells(disc, [(827, 866)]))
    name_control = next((n for f in perth["frames"] for n in f["names"]), None)
    # The first decoded record keeps its absolute offset, raw bytes and hash;
    # all frames retain directory/subframe bytes for offline index/name replay.
    for frame in perth["frames"]:
        del frame["names"]
    statuses = Counter()
    nonempty, failures, target = [], [], None
    names = frames = 0
    for row in w.disc_cells(disc, [(x, y) for y in range(512, 576) for x in range(32)]):
        statuses[row["status"]] += 1
        frames += len(row["frames"])
        names += sum(f["name_count"] for f in row["frames"])
        if row["frames"]:
            nonempty.append(row["cell"])
        if row["status"] == "lookup_failed":
            failures.append({"cell": row["cell"], "reason": row["reason"],
                             "index_evidence": row["index_evidence"]})
        if row["cell"] == w.CELL:
            target = row
    error = w.validate_cell_evidence(perth)
    concerns = []
    if error or perth["status"] != "resolved" or name_control is None:
        concerns.append(f"Perth positive name control unresolved: {error or perth['status']}")
    if failures:
        concerns.append(f"target block has {len(failures)} failed lookups")
    return {"disc": str(disc), "historical_disc_sha256": w.R_PIN,
            "full_pin_remeasured": False,
            "perth_827_866": [[perth["status"], len(perth["frames"]),
                                sum(f["name_count"] for f in perth["frames"])]],
            "perth_index_frames": perth, "perth_name_record_control": name_control,
            "block0_cells_requested": 32 * 64, "block0_status_counts": dict(statuses),
            "block0_cells_with_frames": len(nonempty), "block0_frame_count": frames,
            "block0_names": names, "block0_nonempty": nonempty,
            "block0_lookup_failures": failures, "target_cell_index_frames": target,
            "concerns": concerns}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--disc", type=Path, default=w.R_DISC)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    # Repository-relative CLI paths work from any invocation directory.
    if not args.disc.is_absolute():
        args.disc = ROOT / args.disc
    if not args.out.is_absolute():
        args.out = ROOT / args.out
    record = control(args.disc)
    w.write_json(args.out, {"schema": 2, "R": record})
    return 2 if record["concerns"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
