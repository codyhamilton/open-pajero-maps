"""Extract reference-disc parameters that the map-layer build needs, so the
build never has to read the mounted disc.

Run once against a mounted reference `ALLDATA.KWI`; commit its output
(`parser/refdata/grid.json`, `parser/refdata/mht29_frame.bin`). This script
is the *only* code in this unit (see docs/design/target-disc.md, "Grid
contract" and "Copy-through management data") that touches the mounted
disc -- everything downstream reads the checked-in files via
`kiwiw.grid.ReferenceGrid`.

Usage:
    .venv-rp/bin/python parser/extract_reference_data.py \
        [--alldata /path/to/ALLDATA.KWI] [--out-dir parser/refdata]
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from kiwiw import volume  # noqa: E402

DEFAULT_ALLDATA = "/run/media/codyh/464210-8480/ALLDATA.KWI"
DEFAULT_OUT_DIR = Path(__file__).resolve().parent / "refdata"

MHT29_INDEX = 29
NO_DATA_DSA32 = 0xFFFFFFFF


def _level_to_dict(lmr) -> dict:
    d = dataclasses.asdict(lmr)
    # grid_nx/grid_ny are derived (by kiwiw.grid.ReferenceGrid) from the
    # other LMR fields; they are not independent reference data.
    del d["grid_nx"]
    del d["grid_ny"]
    return d


def extract(alldata_path: str) -> tuple[dict, bytes]:
    with open(alldata_path, "rb") as fh:
        raw_hdr = fh.read(volume.DATAVOL_SIZE)
        hdr = volume.parse_volume_header(raw_hdr)
        extras = volume.parse_volume_header_extras(raw_hdr)

        raw_mht = fh.read(volume.MHT_SIZE)
        mht = volume.parse_management_header_table(raw_mht)

        prdm = mht.entries[0]
        prdm_off = volume.getsector(prdm.dsa, hdr.sector_size, hdr.logical_sector_size)
        fh.seek(prdm_off)
        raw_pdmdh = fh.read(prdm.size * hdr.logical_sector_size)
        pdmdh = volume.parse_pdmdh_full(raw_pdmdh)

        mht29 = mht.entries[MHT29_INDEX]
        if mht29.dsa == NO_DATA_DSA32:
            raise ValueError(
                f"MHT entry {MHT29_INDEX} is the 0xFFFFFFFF sentinel "
                "(no record-29 frame on this disc); refusing to write "
                "mht29_frame.bin"
            )
        mht29_off = volume.getsector(mht29.dsa, hdr.sector_size, hdr.logical_sector_size)
        fh.seek(mht29_off)
        mht29_bytes = fh.read(mht29.size * hdr.logical_sector_size)

    grid = {
        "source": {
            "disk_title": hdr.disk_title,
            "data_version": hdr.data_version,
            "format_version": hdr.format_version,
        },
        "sector_size": hdr.sector_size,
        "logical_sector_size": hdr.logical_sector_size,
        "coverage": {
            "lat_lo": pdmdh.coverage.lat_lo,
            "lat_hi": pdmdh.coverage.lat_hi,
            "lon_lo": pdmdh.coverage.lon_lo,
            "lon_hi": pdmdh.coverage.lon_hi,
        },
        "coverage_exponents": list(extras.coverage_exponents),
        "pdmdh": {
            "lmr_size": pdmdh.lmr_size,
            "bsmr_size": pdmdh.bsmr_size,
            "bmr_size": pdmdh.bmr_size,
            "n_lmr": pdmdh.n_lmr,
            "n_bsmr": pdmdh.n_bsmr,
            "header_gap_hex": pdmdh.header_gap_hex,
            "record_size": pdmdh.record_size,
            "total_size": pdmdh.total_size,
        },
        "levels": [_level_to_dict(lmr) for lmr in pdmdh.levels],
        "blocksets": [
            {
                "level": bs.level,
                "blockset_index": bs.blockset_index,
                "has_bmt": not (bs.bmt_size == 0 or bs.bmt_offset >= len(raw_pdmdh)),
            }
            for bs in pdmdh.blocksets
        ],
    }
    return grid, mht29_bytes


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--alldata", default=DEFAULT_ALLDATA,
                     help="path to the reference disc's ALLDATA.KWI")
    ap.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR),
                     help="directory to write grid.json / mht29_frame.bin into")
    args = ap.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    grid, mht29_bytes = extract(args.alldata)

    grid_path = out_dir / "grid.json"
    with open(grid_path, "w") as f:
        json.dump(grid, f, sort_keys=True, indent=2)
        f.write("\n")

    frame_path = out_dir / "mht29_frame.bin"
    with open(frame_path, "wb") as f:
        f.write(mht29_bytes)

    print(f"wrote {grid_path} ({grid_path.stat().st_size} bytes)")
    print(f"wrote {frame_path} ({frame_path.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
