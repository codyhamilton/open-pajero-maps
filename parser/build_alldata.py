#!/usr/bin/env python3
"""Build ALLDATA.KWI from an OSM PBF file.

End-to-end pipeline:
  1. Accepts a PBF path, bounding box, and list of levels.
  2. Constructs a synthetic TileGrid for each level (or reads from the real
     disc LMR if it is mounted).
  3. Calls ``extract_parcel_geometry`` to extract road/background/name data
     per parcel.
  4. Encodes each parcel to a Map Frame binary using the synthetic frame
     encoders in ``kiwiw/synth.py``.
  5. Calls ``build_alldata_kwi`` to assemble a complete ALLDATA.KWI file.
  6. Writes the output (default: ``output/ALLDATA.KWI``).
  7. Verifies the output by calling ``decode_parcel`` on each map frame and
     checking that road/background/name record counts match.

Usage::

    python3 parser/build_alldata.py \\
        --pbf ~/workspace/open-pajero-maps/australia-260824.osm.pbf \\
        --out output/ALLDATA.KWI

    python3 parser/build_alldata.py --dry-run   # print stats, no file written
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from kiwiw import alldata_writer as aw
from kiwiw.alldata_writer import SynthParcel, build_alldata_kwi
from kiwiw.model import BoundingBox, MeshLocation
from kiwiw.parcel import decode_parcel
from kiwiw.synth import (
    build_background_frame_bytes,
    build_map_frame_bytes,
    build_name_frame_bytes,
    build_road_frame_bytes,
)
from osm_to_parcel_geometry import (
    DEFAULT_ALLDATA,
    DEFAULT_BBOX,
    DEFAULT_PBF,
    TileGrid,
    build_tile_grid_from_lmr,
    extract_parcel_geometry,
    parcel_bounds,
)

DEFAULT_OUT = str(
    Path(__file__).resolve().parent.parent / "output" / "ALLDATA.KWI"
)
DEFAULT_LEVELS = [0]   # default to level 0 only (Perth metro proof-of-concept)


# ---------------------------------------------------------------------------
# Synthetic tile grid (used when the real disc is not mounted)
# ---------------------------------------------------------------------------

_SYNTH_CELL_SIZES: dict[int, float] = {
    0: 0.25,   # ~25 km cells at Perth latitude
    2: 0.125,
    4: 0.0625,
    6: 0.03125,
    8: 0.015625,
}


def _make_synth_grid(level: int, bbox: tuple) -> TileGrid:
    """Build a synthetic TileGrid for *level* covering *bbox*.

    The grid is defined entirely from the bbox (no real disc needed).
    Cell size is taken from ``_SYNTH_CELL_SIZES``; the number of cells
    is chosen so the grid exactly tiles the bbox (rounded up).
    """
    import math

    cell_size = _SYNTH_CELL_SIZES.get(level, 0.25)
    lon_l, lat_b, lon_r, lat_t = bbox
    lat_span = lat_t - lat_b
    lon_span = lon_r - lon_l
    ny = math.ceil(lat_span / cell_size)
    nx = math.ceil(lon_span / cell_size)
    if ny < 1:
        ny = 1
    if nx < 1:
        nx = 1

    target = BoundingBox(lat_lo=lat_b, lat_hi=lat_t, lon_lo=lon_l, lon_hi=lon_r)
    return TileGrid(
        level=level,
        disc_lat_lo=lat_b,
        disc_lon_lo=lon_l,
        disc_lat_span=lat_span,
        disc_lon_span=lon_span,
        nx=nx,
        ny=ny,
        target=target,
    )


# ---------------------------------------------------------------------------
# Per-parcel encoding
# ---------------------------------------------------------------------------

def encode_parcel(
    parcel_key: tuple[int, int, int],
    content: dict,
    grid: TileGrid,
) -> tuple[SynthParcel, tuple[int, int, int]]:
    """Encode one parcel's geometry to a ``SynthParcel`` + verification tuple.

    Returns ``(SynthParcel, (n_links, n_shapes, n_names))``.
    """
    level, ix, iy = parcel_key
    from osm_to_parcel_geometry import parcel_bounds as _pb
    bounds = _pb(ix, iy, grid)

    roads  = content.get("roads", [])
    bgs    = content.get("backgrounds", [])
    names  = content.get("names", [])

    road_bytes = build_road_frame_bytes(roads, bounds) if roads else None
    bg_bytes   = build_background_frame_bytes(bgs, bounds) if bgs else None
    name_bytes = build_name_frame_bytes(names, bounds) if names else None

    frame_bytes = build_map_frame_bytes(road_bytes, bg_bytes, name_bytes, bounds)

    sp = SynthParcel(ix=ix, iy=iy, bounds=bounds, map_frame_bytes=frame_bytes)
    return sp, (len(roads), len(bgs), len(names))


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------

def verify_parcel(sp: SynthParcel, expected: tuple[int, int, int]) -> list[str]:
    """Decode the map frame bytes and check record counts.

    Returns a list of error strings (empty = all checks passed).
    """
    errors: list[str] = []
    loc = MeshLocation(
        level=0, parcel_type=0,
        blockset_index=0, block_index=0, parcel_index=0,
        bounds=sp.bounds,
        sector_addr=0, size_logical_sectors=1,
    )
    try:
        parcel = decode_parcel(loc, sp.map_frame_bytes, n_basic_map=3, n_ext_map=0)
    except Exception as exc:
        errors.append(f"  decode_parcel raised: {exc}")
        return errors

    n_links, n_shapes, n_names = expected

    actual_links  = len(parcel.road.links)      if parcel.road        else 0
    actual_shapes = len(parcel.background.shapes) if parcel.background else 0
    actual_names  = len(parcel.name.records)    if parcel.name        else 0

    if actual_links != n_links:
        errors.append(
            f"  road links: encoded {n_links}, decoded {actual_links}")
    if actual_shapes != n_shapes:
        errors.append(
            f"  bg shapes: encoded {n_shapes}, decoded {actual_shapes}")
    if actual_names != n_names:
        errors.append(
            f"  name records: encoded {n_names}, decoded {actual_names}")

    return errors


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def run(
    pbf_path: str,
    bbox: tuple,
    levels: list[int],
    out_path: str | None,
    dry_run: bool = False,
    verbose: bool = False,
    alldata_path: str = DEFAULT_ALLDATA,
) -> int:
    """Run the end-to-end build pipeline.

    Returns 0 on success, non-zero on failure.
    """
    print(f"build_alldata: PBF={pbf_path}, bbox={bbox}, levels={levels}")

    # ------------------------------------------------------------------ grids
    grids: dict[int, TileGrid] = {}
    for level in levels:
        if os.path.exists(alldata_path):
            try:
                grids[level] = build_tile_grid_from_lmr(alldata_path, level, bbox)
                print(f"  Level {level}: grid from real disc "
                      f"({grids[level].nx}×{grids[level].ny} cells)")
            except Exception as exc:
                print(f"  Level {level}: real disc LMR failed ({exc}); "
                      f"using synthetic grid")
                grids[level] = _make_synth_grid(level, bbox)
        else:
            grids[level] = _make_synth_grid(level, bbox)
            if verbose:
                g = grids[level]
                print(f"  Level {level}: synthetic grid {g.nx}×{g.ny} cells, "
                      f"cell {g.cell_lat:.5f}°×{g.cell_lon:.5f}°")

    # ---------------------------------------------------------------- extract
    if not os.path.exists(pbf_path):
        print(f"ERROR: PBF not found: {pbf_path}", file=sys.stderr)
        return 1

    all_synth: list[SynthParcel] = []
    all_expected: list[tuple] = []
    per_level_grids: dict[int, TileGrid] = {}

    # For build_alldata_kwi we only support single-level for now.
    # Multi-level: produce one file per level (extend as needed).
    for level in levels:
        grid = grids[level]
        per_level_grids[level] = grid
        print(f"\nLevel {level}: extracting geometry from {pbf_path} …")
        geometry = extract_parcel_geometry(pbf_path, grid, verbose=verbose)

        n_non_empty = len(geometry)
        n_links  = sum(len(v["roads"])       for v in geometry.values())
        n_bgs    = sum(len(v["backgrounds"]) for v in geometry.values())
        n_names  = sum(len(v["names"])       for v in geometry.values())
        print(f"  Non-empty parcels: {n_non_empty}")
        print(f"  Road links:        {n_links}")
        print(f"  Background shapes: {n_bgs}")
        print(f"  Name records:      {n_names}")

        if dry_run:
            # In dry-run, just show what *would* be built.
            total_frames = sum(
                (1 if v["roads"] else 0)
                + (1 if v["backgrounds"] else 0)
                + (1 if v["names"] else 0)
                for v in geometry.values()
            )
            print(f"  (dry-run) Total non-empty sub-frames: {total_frames}")
            continue

        # Encode parcels.
        print(f"  Encoding {n_non_empty} parcels …")
        for key, content in geometry.items():
            sp, counts = encode_parcel(key, content, grid)
            all_synth.append(sp)
            all_expected.append(counts)

    if dry_run:
        print("\n(--dry-run: no file written)")
        return 0

    if not all_synth:
        print("WARNING: no parcels encoded (empty geometry?)")

    # ---------------------------------------------------------------- assemble
    # Determine coverage and grid from the first level processed.
    first_level = levels[0]
    g0 = per_level_grids[first_level]
    coverage = BoundingBox(
        lat_lo=g0.disc_lat_lo,
        lat_hi=g0.disc_lat_lo + g0.disc_lat_span,
        lon_lo=g0.disc_lon_lo,
        lon_hi=g0.disc_lon_lo + g0.disc_lon_span,
    )

    print(f"\nAssembling ALLDATA.KWI …")
    kwi_bytes = build_alldata_kwi(
        parcels=all_synth,
        coverage=coverage,
        level=first_level,
        grid_nx=g0.nx,
        grid_ny=g0.ny,
    )
    print(f"  Total output size: {len(kwi_bytes):,} bytes")

    # ------------------------------------------------------------------ verify
    print("\nVerifying all parcels …")
    n_ok = n_fail = 0
    for sp, expected in zip(all_synth, all_expected):
        errs = verify_parcel(sp, expected)
        if errs:
            n_fail += 1
            print(f"  FAIL parcel ({sp.ix},{sp.iy}):")
            for e in errs:
                print(e)
        else:
            n_ok += 1

    print(f"Verification: {n_ok} OK, {n_fail} FAILED")

    # ------------------------------------------------------------------ write
    if out_path is not None:
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, "wb") as fh:
            fh.write(kwi_bytes)
        print(f"\nOutput written to {out_path}")
    else:
        print("\n(no --out specified; output not written)")

    return 0 if n_fail == 0 else 1


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--pbf", default=DEFAULT_PBF,
        help="OSM PBF input file (default: %(default)s)"
    )
    ap.add_argument(
        "--bbox", nargs=4, type=float,
        metavar=("LON_LEFT", "LAT_BOTTOM", "LON_RIGHT", "LAT_TOP"),
        default=list(DEFAULT_BBOX),
        help="Target bounding box (default: Perth metro)"
    )
    ap.add_argument(
        "--levels", type=int, nargs="+", default=DEFAULT_LEVELS,
        help="Map levels to build (default: %(default)s)"
    )
    ap.add_argument(
        "--out", default=DEFAULT_OUT,
        help="Output KWI path (default: %(default)s)"
    )
    ap.add_argument(
        "--alldata", default=DEFAULT_ALLDATA,
        help="Real disc ALLDATA.KWI for LMR parameters (optional)"
    )
    ap.add_argument(
        "--dry-run", action="store_true",
        help="Print stats only; do not write output"
    )
    ap.add_argument(
        "--verbose", action="store_true",
        help="Enable verbose progress messages"
    )
    args = ap.parse_args()

    return run(
        pbf_path=args.pbf,
        bbox=tuple(args.bbox),
        levels=args.levels,
        out_path=None if args.dry_run else args.out,
        dry_run=args.dry_run,
        verbose=args.verbose,
        alldata_path=args.alldata,
    )


if __name__ == "__main__":
    raise SystemExit(main())
