#!/usr/bin/env python3
"""Compare regenerated AU.differing_cells.tsv to plan 31's list (DESIGN plan 49)."""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from pathlib import Path


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_tsv_bytes(path: Path) -> bytes:
    if path.suffix == ".gz":
        return gzip.open(path, "rb").read()
    return path.read_bytes()


def cell_keys(text: str):
    lines = text.splitlines()
    if not lines:
        return set(), {}
    header = lines[0].split("\t")
    # level ix iy ... old_cell_sha256 new_cell_sha256
    try:
        i_old = header.index("old_cell_sha256")
        i_new = header.index("new_cell_sha256")
    except ValueError:
        i_old, i_new = 6, 7
    keys = set()
    shas = {}
    for line in lines[1:]:
        if not line.strip():
            continue
        parts = line.split("\t")
        key = (parts[0], parts[1], parts[2])
        keys.add(key)
        shas[key] = (parts[i_old] if len(parts) > i_old else "",
                     parts[i_new] if len(parts) > i_new else "")
    return keys, shas


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--regen", type=Path, required=True)
    ap.add_argument("--plan31", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--expected-plan31-sha",
                    default="77ff1d86ee9ca9d41e2d5137d304e0f52dee093cf2ccc2c0911d085eb448544f")
    args = ap.parse_args()

    regen_b = read_tsv_bytes(args.regen)
    plan_b = read_tsv_bytes(args.plan31)
    regen_sha = sha256_bytes(regen_b)
    plan_sha = sha256_bytes(plan_b)
    literal_equal = regen_sha == plan_sha

    rk, rs = cell_keys(regen_b.decode())
    pk, ps = cell_keys(plan_b.decode())
    only_regen = sorted(rk - pk)[:50]
    only_plan = sorted(pk - rk)[:50]
    sha_diffs = []
    for k in sorted(rk & pk):
        if rs[k] != ps[k]:
            sha_diffs.append({"key": list(k), "regen": list(rs[k]), "plan31": list(ps[k])})
            if len(sha_diffs) >= 50:
                break

    perth = [("0", "828", "862"), ("0", "827", "869"), ("0", "832", "856")]
    perth_present = { "/".join(k): (k in rk) for k in perth }

    out = {
        "schema": 1,
        "regen_sha256": regen_sha,
        "plan31_sha256": plan_sha,
        "plan31_sha_matches_expected": plan_sha == args.expected_plan31_sha,
        "literal_equal": literal_equal,
        "n_regen": len(rk),
        "n_plan31": len(pk),
        "n_only_regen": len(rk - pk),
        "n_only_plan31": len(pk - rk),
        "n_sha_diffs": sum(1 for k in (rk & pk) if rs[k] != ps[k]),
        "only_regen_sample": [list(x) for x in only_regen],
        "only_plan31_sample": [list(x) for x in only_plan],
        "sha_diff_sample": sha_diffs,
        "perth_shared_cells_present_in_regen": perth_present,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps({k: out[k] for k in (
        "literal_equal", "n_regen", "n_plan31", "n_only_regen",
        "n_only_plan31", "n_sha_diffs", "plan31_sha_matches_expected")}, indent=2))


if __name__ == "__main__":
    raise SystemExit(main())
