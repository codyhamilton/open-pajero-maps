#!/usr/bin/env python3
"""Plan 63 Phase 3: the opt-in S02 resolution for gate_repro --s02-resolve.

The 6 scope-delta groups (plan 46 ties.json) were outside S only because their producer was
ambiguous. Phase 2 proves each copy's producer (sidecar). The S02 bit is then the unchanged
plan-46 predicate (level 0, type 291, closed ring, closing edge longest, >= 1 crossing; RC6 raw-unit
stats from ties_all.json) evaluated on that proven producer, with the producer class taken as
proven (sidecar) in place of unique-byte. Output s02_resolution.tsv.gz (gz mtime 0)."""
from __future__ import annotations

import csv, gzip, io, json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[5]
sys.path.insert(0, str(ROOT / "parser/tools"))
import bg_producer_scan as S  # noqa: E402

GROUP = ("level", "ix", "iy", "code", "p0", "p1", "p2", "p3", "p4", "p5", "p6", "shape")


def main():
    ties = json.loads((HERE / "ties_all.json").read_text())
    prov = {}
    with gzip.open(HERE / "provenance.tsv.gz", "rt") as f:
        for r in csv.DictReader(f, delimiter="\t"):
            if r["group_shape"] == r["copy_shape"]:
                prov[(int(r["ix"]), int(r["iy"]), int(r["group_shape"]))] = (
                    int(r["emitter_hx"]), int(r["emitter_hy"]), int(r["emitter_ri"]))
    rows = []
    for g in ties["groups"]:
        if not g["scope_delta"]:
            continue
        lv, ix, iy, path = g["leaf"]
        p = prov[(ix, iy, g["shape"])]
        st = next(h["stats"] for h in g["hits"] if tuple(h["cid"][:3]) == p)
        bit = S.s02_producer_bit("unique-byte", st, level=lv, code=g["code"])
        pp = list(path) + [0] * (7 - len(path))
        rows.append([lv, ix, iy, g["code"], *pp, g["shape"], *p, bit,
                     st["closed"], st["closing_is_longest"], st["crossings"]])
    rows.sort()
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb", mtime=0) as f:
        f.write(("\t".join([*GROUP, "producer_hx", "producer_hy", "producer_ri", "s02",
                            "closed", "closing_is_longest", "crossings"]) + "\n").encode())
        for r in rows:
            f.write(("\t".join(map(str, r)) + "\n").encode())
    (HERE / "s02_resolution.tsv.gz").write_bytes(buf.getvalue())
    print(len(rows), sum(r[-4] for r in rows))


if __name__ == "__main__":
    main()
