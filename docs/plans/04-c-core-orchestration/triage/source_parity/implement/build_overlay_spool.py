#!/usr/bin/env python3
"""Plan 50 — private L0 overlay spool: pinned extract + cell-clipped supply bgs.

- Existing target cells: append supply BackgroundShapes (byte-preserve others).
- Absent target cells: insert new L0 records containing only the supply bgs.
- Non-target cells: byte-copied. Levels 2–12: symlinks. Pinned spool never written.
"""
from __future__ import annotations

import json
import mmap
import os
import struct
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[6]
sys.path[:0] = [str(ROOT / "parser"), str(ROOT / "parser/tools")]

from kiwiw.spool import (  # noqa: E402
    IDX_MAGIC, SpoolReader, columns_to_content, content_to_columns,
    decode_columns, encode_columns, _empty_content,
)
from supply_path_assembler import SupplyAssembler  # noqa: E402

IMPL = Path(__file__).resolve().parent
SCRATCH = ROOT / "output/scratch-50"
PINNED = ROOT / "output/extract_timing/spool"
PIN = json.loads((IMPL / "snapshot_ways_pin.json").read_text())


def build(dst: Path) -> dict:
    dst.mkdir(parents=True, exist_ok=True)
    for name in sorted(os.listdir(PINNED)):
        if name.startswith("level_0."):
            continue
        src = (PINNED / name).resolve()
        link = dst / name
        if link.exists() or link.is_symlink():
            link.unlink()
        os.symlink(src, link)

    asm = SupplyAssembler(
        members_path=IMPL / "relation_members_10.json",
        pbf_ways_path=SCRATCH / "way_geometry_pbf.json",
        snapshot_ways_path=ROOT / PIN["snapshot"]["path"],
        snapshot_sha=PIN["snapshot"]["sha256"],
        targets_path=IMPL / "targets_341.json",
    )
    extras: dict[tuple[int, int], list] = {}
    presence = []
    for em in asm.iter_emissions():
        presence.append({k: em[k] for k in (
            "dump_row", "level", "ix", "iy", "code", "relation_id", "present", "n_coords")})
        if not em["present"]:
            continue
        extras.setdefault((em["ix"], em["iy"]), []).append(em["background"])

    reader = SpoolReader(str(PINNED))
    idx = reader._load_idx(0)
    assert idx is not None
    pinned_stats = reader.stats(0)
    pinned_keys = {(int(idx.ix[i]), int(idx.iy[i])): i for i in range(idx.n)}

    n_merge = sum(1 for k in extras if k in pinned_keys)
    n_insert = sum(1 for k in extras if k not in pinned_keys)
    n_added_bgs = sum(len(v) for v in extras.values())

    # Final cell list: all pinned cells + inserted keys, sorted (iy, ix).
    final_keys = sorted(set(pinned_keys) | set(extras), key=lambda k: (k[1], k[0]))

    data_path = PINNED / "level_0.data"
    new_ix = np.zeros(len(final_keys), dtype="<i4")
    new_iy = np.zeros(len(final_keys), dtype="<i4")
    new_offs = np.zeros(len(final_keys), dtype="<u8")
    new_lens = np.zeros(len(final_keys), dtype="<u8")
    out_path = dst / "level_0.data"
    pos = 0
    n_merged = n_inserted = 0

    with data_path.open("rb") as inf, out_path.open("wb") as out:
        mm = mmap.mmap(inf.fileno(), 0, access=mmap.ACCESS_READ)
        try:
            for j, key in enumerate(final_keys):
                ix, iy = key
                new_ix[j] = ix
                new_iy[j] = iy
                if key in pinned_keys:
                    i = pinned_keys[key]
                    off = int(idx.offset[i]); ln = int(idx.length[i])
                    if key in extras:
                        blob = bytes(mm[off:off + ln])
                        cols = decode_columns(blob, 0)
                        content = columns_to_content(
                            {k: np.array(v, copy=True) for k, v in cols.items()})
                        content["backgrounds"].extend(extras[key])
                        blob = encode_columns(content_to_columns(content))
                        n_merged += 1
                    else:
                        blob = mm[off:off + ln]
                        ln_out = ln
                        out.write(blob)
                        new_offs[j] = pos
                        new_lens[j] = ln_out
                        pos += ln_out
                        if (j + 1) % 50000 == 0:
                            print(f"… {j+1}/{len(final_keys)} merge={n_merged} insert={n_inserted}", flush=True)
                        continue
                else:
                    content = _empty_content()
                    content["backgrounds"].extend(extras[key])
                    blob = encode_columns(content_to_columns(content))
                    n_inserted += 1
                out.write(blob)
                new_offs[j] = pos
                new_lens[j] = len(blob)
                pos += len(blob)
                if (j + 1) % 50000 == 0:
                    print(f"… {j+1}/{len(final_keys)} merge={n_merged} insert={n_inserted}", flush=True)
        finally:
            mm.close()

    n_cells = len(final_keys)
    n_parcels = pinned_stats["parcels"] + n_insert  # one parcel slot per new cell
    n_roads = pinned_stats["roads"]
    n_bgs = pinned_stats["backgrounds"] + n_added_bgs
    n_names = pinned_stats["names"]
    with (dst / "level_0.idx").open("wb") as fh:
        fh.write(IDX_MAGIC)
        fh.write(struct.pack("<5Q", n_cells, n_parcels, n_roads, n_bgs, n_names))
        fh.write(new_ix.tobytes())
        fh.write(new_iy.tobytes())
        fh.write(new_offs.tobytes())
        fh.write(new_lens.tobytes())

    summary = {
        "schema": "plan50-overlay-spool-v1",
        "dst": str(dst),
        "pinned": str(PINNED.resolve()),
        "n_cells_l0_pinned": int(idx.n),
        "n_cells_l0_overlay": n_cells,
        "n_merged_cells": n_merged,
        "n_inserted_cells": n_inserted,
        "n_added_bgs": n_added_bgs,
        "n_emissions_present": sum(1 for p in presence if p["present"]),
        "n_emissions_total": len(presence),
        "totals": {"parcels": n_parcels, "roads": n_roads, "backgrounds": n_bgs, "names": n_names},
        "presence_rows": presence,
    }
    (SCRATCH / "phase2").mkdir(parents=True, exist_ok=True)
    (SCRATCH / "phase2" / "overlay_build.json").write_text(
        json.dumps({k: v for k, v in summary.items() if k != "presence_rows"},
                   indent=2, sort_keys=True) + "\n")
    (SCRATCH / "phase2" / "presence_341.json").write_text(
        json.dumps(presence, indent=2, sort_keys=True) + "\n")
    return summary


def main() -> int:
    dst = SCRATCH / "spool_overlay"
    summary = build(dst)
    print(json.dumps({k: summary[k] for k in (
        "n_cells_l0_pinned", "n_cells_l0_overlay", "n_merged_cells", "n_inserted_cells",
        "n_added_bgs", "n_emissions_present", "n_emissions_total", "totals")}, sort_keys=True))
    missing = [p for p in summary["presence_rows"] if not p["present"]]
    if missing:
        print("MISSING", len(missing)); return 1
    if summary["n_merged_cells"] + summary["n_inserted_cells"] != summary["n_emissions_present"]:
        # one emission per present row; cells unique so merge+insert == unique keys with extras
        pass
    expect_keys = summary["n_merged_cells"] + summary["n_inserted_cells"]
    # emissions_present should equal n_added_bgs when 1 bg/cell
    if summary["n_added_bgs"] != summary["n_emissions_present"]:
        print("bg count mismatch", summary["n_added_bgs"], summary["n_emissions_present"])
        return 1
    if expect_keys != len({(p["ix"], p["iy"]) for p in summary["presence_rows"] if p["present"]}):
        print("key count mismatch", expect_keys)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
