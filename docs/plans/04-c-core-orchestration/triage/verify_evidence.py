#!/usr/bin/env python3
"""Audit the committed table against the live dump and referenced byte ranges.

Run from the repository root under flock output/.heavy.lock. No inputs change;
the verification result is written under output/scratch-14 only.
"""
import csv
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[4]
SCRATCH = ROOT / "output/scratch-14"
TRIAGE = Path(__file__).resolve().parent
OLD = ROOT / "docs/plans/04-c-core-orchestration/triage"
KEY = ("level", "ix", "iy", "code", "p0", "p1", "p2", "p3", "p4", "p5", "p6", "shape", "vert")


def key(row):
    return tuple(int(row[n]) for n in KEY)


def main():
    manifest = json.loads((SCRATCH / "dump_raw/dump_manifest.json").read_text())
    ts = {"f64": "<f8", "i32": "<i4", "u16": "<u2", "u8": "u1"}
    dtype = np.dtype([(f["name"], ts[f["type"]]) for f in manifest["fields"]], align=True)
    raw = np.fromfile(SCRATCH / "dump_raw/completeness.bin", dtype=dtype)
    with (TRIAGE / "completeness_evidence.tsv").open() as fh:
        table = list(csv.DictReader(fh, delimiter="\t"))
    native = [key(row) for row in raw]
    assert len(table) == len(native) == len(set(native)) == 776
    assert [key(row) for row in table] == native
    text = (OLD / "rebaseline_3-17_9064.md").read_text().split("## Preserved live completeness identities", 1)[1]
    historic = {(0, int(ix), int(iy), int(code), *([0] * 7), -1, -1)
                for ix, iy, code in re.findall(r"^\| (\d+) \| (\d+) \| (\d+) \| \d+ \| \d+ \|$", text, re.M)}
    with (OLD / "completeness_3-16_outcomes.tsv").open() as fh:
        added = {key({**row, "vert": -1}) for row in csv.DictReader(fh, delimiter="\t")}
    assert len(historic) == 188 and len(added) == 89 and not historic & added
    handles, checked = {}, set()

    def check_bytes(path, off, length, sha):
        absolute = Path(path) if Path(path).is_absolute() else ROOT / path
        address = (str(absolute), off, length, sha)
        if address in checked:
            return
        fh = handles.setdefault(str(absolute), None)
        if fh is None:
            fh = handles[str(absolute)] = absolute.open("rb")
        fh.seek(off)
        buf = fh.read(length)
        assert len(buf) == length
        assert hashlib.sha256(buf).hexdigest() == sha, address
        checked.add(address)

    sources, gaps = 0, Counter()
    for i, row in enumerate(table):
        assert int(row["dump_row"]) == i
        assert int(row["in_historic_188"]) == (key(row) in historic)
        assert int(row["in_added_89"]) == (key(row) in added)
        assert row["classify_assignment"] == "evidence-gap:other_mechanism"
        assert "unknown column 'other_mechanism'" in (ROOT / row["classify_witness"]).read_text()
        for label in ("R", "G"):
            w = json.loads((ROOT / row[f"{label}_witness"]).read_text())
            assert w["cell"] == list(key(row)[:3]) and w["code"] == int(row["code"])
            if "evidence-gap" in w:
                assert row[f"{label}_polygon_count"] == "evidence-gap"
                gaps[label] += 1
            else:
                assert int(row[f"{label}_polygon_count"]) == w["polygon_count"]
                assert w["polygon_count"] == sum(f["matching_polygon_count"] for f in w["frames"])
            for f in w["frames"]:
                check_bytes(w["disc"], f["offset"], f["length"], f["sha256"])
            if "parcel_management" in w:
                f = w["parcel_management"]
                check_bytes(w["disc"], f["offset"], f["length"], f["sha256"])
        w = json.loads((ROOT / row["spool_K1_requirement_witness"]).read_text())
        assert key(w["native_key"]) == key(row)
        assert w["dump_row"] == i and w["byte_offset"] == i * dtype.itemsize
        assert w["reason"] == int(raw[i]["reason"])
        if w["source"]:
            s = w["source"]
            check_bytes(s["spool_data"], s["offset"], s["length"], s["source_cell_sha256"])
            if s["branch"] == "b":
                assert all(1 <= f <= 4095 for f in s["trigger"]["cell_raw"])
            elif s["branch"] == "a":
                assert s["trigger"]["rounded_area2"] != 0
            else:
                raise AssertionError(s["branch"])
            sources += 1
        else:
            assert "evidence-gap" in w
            gaps["source"] += 1
    for fh in handles.values():
        fh.close()
    assert (SCRATCH / "dump_raw/completeness.bin").read_bytes() == (SCRATCH / "dump_ext/completeness.bin").read_bytes()
    summary = json.loads((SCRATCH / "evidence_summary.json").read_text())
    assert summary["source_requirement_witnesses"] == sources
    assert summary["R_decode_gaps"] == gaps["R"] and summary["G_decode_gaps"] == gaps["G"]
    result = {"status": "PASS", "rows": len(table), "unique_native_keys": len(set(native)),
              "historic": len(historic), "added": len(added), "byte_ranges_verified": len(checked),
              "source_requirement_witnesses": sources, "witness_gaps": dict(gaps),
              "assignment_evidence_gaps": len(table)}
    (SCRATCH / "evidence_verification.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
