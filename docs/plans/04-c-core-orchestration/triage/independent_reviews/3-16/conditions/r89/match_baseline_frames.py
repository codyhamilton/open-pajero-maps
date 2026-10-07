#!/usr/bin/env python3
"""Plan 47 Phase 3: re-extract 89 target-cell frames from disc 4ed9cd80 and
match TSV baseline_padded_frame_sha256 (R-G8-3-b baseline half).

Sector-padded frame = leaf payload read at entry.dsa for entry.size logical
sectors (size * logical_sector_size bytes), hashed sha256.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[8]
sys.path[:0] = [
    str(ROOT / "parser"),
    str(ROOT / "docs/plans/04-c-core-orchestration/triage/historical_bg/p5_owner_exclusive"),
]

from leaf_io import frames  # noqa: E402

TSV = ROOT / "docs/plans/04-c-core-orchestration/triage/completeness_3-16_outcomes.tsv"
DISC = ROOT / "output/scratch-14/G_new/ALLDATA.KWI"
OUT = Path(__file__).resolve().parent


def load_keys():
    rows = []
    with TSV.open() as f:
        hdr = f.readline().rstrip("\n").split("\t")
        for line in f:
            d = dict(zip(hdr, line.rstrip("\n").split("\t")))
            path = tuple(int(d[f"p{i}"]) for i in range(7) if d[f"p{i}"] not in ("",))
            # historic keys use p0.. and trailing; undivided leaf path is ()
            # leaf_io uses tree path tuple from parcel tree — match mass_decide:
            # depth from non-zero? For shape=-1 undivided, path often (0,) or ()
            # Use p0 as first path element when present; strip trailing zeros after first?
            # TSV shows p0=0 for all sample rows. Prefer empty path for undivided.
            depth_path = []
            for i in range(7):
                v = int(d[f"p{i}"])
                depth_path.append(v)
            # Trim trailing zeros for a compact path; keep at least nothing
            while depth_path and depth_path[-1] == 0:
                depth_path.pop()
            rows.append({
                "ordinal": int(d["ordinal"]),
                "level": int(d["level"]),
                "ix": int(d["ix"]),
                "iy": int(d["iy"]),
                "code": int(d["code"]),
                "path": tuple(depth_path),
                "path_raw": tuple(int(d[f"p{i}"]) for i in range(7)),
                "expect": d["baseline_padded_frame_sha256"],
                "expect_raw": d["baseline_raw_frame_dump_sha256"],
            })
    return rows


def main() -> int:
    rows = load_keys()
    cells = {(r["level"], r["ix"], r["iy"]) for r in rows}
    print(f"keys={len(rows)} cells={len(cells)} disc={DISC}", flush=True)
    fr = frames(str(DISC), cells)
    print(f"frame_index_leaves={len(fr)}", flush=True)

    results = []
    n_match = n_miss = n_path = 0
    with open(DISC, "rb") as fh:
        for r in rows:
            # Try exact path, then empty, then (0,), then any leaf at cell
            candidates = [r["path"], (), (0,)]
            ent = None
            used = None
            for p in candidates:
                key = (r["level"], r["ix"], r["iy"], p)
                if key in fr:
                    ent = fr[key]
                    used = p
                    break
            if ent is None:
                # any leaf at this cell
                hits = [k for k in fr if k[0] == r["level"] and k[1] == r["ix"] and k[2] == r["iy"]]
                if len(hits) == 1:
                    ent = fr[hits[0]]
                    used = hits[0][3]
                elif len(hits) > 1:
                    n_path += 1
                    results.append({**{k: r[k] for k in ("ordinal", "level", "ix", "iy", "expect")},
                                    "status": "ambiguous_leaf", "hits": [list(h[3]) for h in hits]})
                    continue
                else:
                    n_miss += 1
                    results.append({**{k: r[k] for k in ("ordinal", "level", "ix", "iy", "expect")},
                                    "status": "leaf_missing"})
                    continue
            dsa, size, ss, ls = ent
            from kiwiw import volume
            off = volume.getsector(dsa, ss, ls)
            padded = os.pread(fh.fileno(), size * ls, off)
            # raw = first U16*2 bytes (word count)
            nwords = int.from_bytes(padded[0:2], "big")
            raw = padded[: nwords * 2]
            hp = hashlib.sha256(padded).hexdigest()
            hr = hashlib.sha256(raw).hexdigest()
            ok = hp == r["expect"]
            if ok:
                n_match += 1
            status = "match" if ok else "mismatch"
            if not ok and hr == r["expect"]:
                status = "match_as_raw"  # diagnostic
            if not ok and hp == r["expect_raw"]:
                status = "matched_expect_raw_col"
            results.append({
                "ordinal": r["ordinal"], "level": r["level"], "ix": r["ix"], "iy": r["iy"],
                "path_used": list(used) if used is not None else None,
                "status": status,
                "got_padded": hp, "got_raw": hr,
                "expect_padded": r["expect"], "expect_raw": r["expect_raw"],
                "padded_len": len(padded), "raw_len": len(raw),
            })
            if status != "match":
                print(f"  {status} ord={r['ordinal']} ({r['level']},{r['ix']},{r['iy']}) "
                      f"path={used} got={hp[:12]}… expect={r['expect'][:12]}…", flush=True)

    summary = {
        "n_keys": len(rows),
        "n_match_padded": n_match,
        "n_leaf_missing": n_miss,
        "n_ambiguous": n_path,
        "n_mismatch": sum(1 for x in results if x["status"] not in ("match", "leaf_missing", "ambiguous_leaf")),
        "all_match": n_match == len(rows),
        "disc": str(DISC),
        "residual": "R-G8-3-b",
        "half": "baseline",
    }
    (OUT / "baseline_match.json").write_text(json.dumps({"summary": summary, "rows": results}, indent=2) + "\n")
    print(json.dumps(summary, indent=2), flush=True)
    return 0 if summary["all_match"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
