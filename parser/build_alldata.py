#!/usr/bin/env python3
"""Build ALLDATA.KWI from a spool written by `osm_to_parcel_geometry.py`.

End-to-end pipeline:
  1. Reads a spool directory (`kiwiw.spool.SpoolReader`) written by
     `osm_to_parcel_geometry.py`'s extraction pass -- never reads a PBF or
     touches OSM data itself.
  2. For each requested level, encodes every spooled parcel's road/
     background/name content into a Map Frame (`kiwiw.synth`), passing
     `level=` explicitly to `build_name_frame_bytes()` (unit 11's amendment:
     omitting it silently reverts to the legacy type-1-only string path).
  3. Calls `kiwiw.alldata_writer.build_alldata_kwi()` to assemble the whole
     container: the reference's per-level LMR/BSMR/BMT shape
     (`kiwiw.grid.ReferenceGrid`), the record-29 copy-through frame, and
     the wrap-safe coverage box -- all from checked-in `grid.json`, never
     a mounted disc (docs/design/target-disc.md, "Grid contract").
  4. Writes the output file and a `manifest.json` beside it.

Usage::

    python3 parser/build_alldata.py                      # spool at output/spool, all 7 levels
    python3 parser/build_alldata.py --fixture perth \\
        --spool output/spool-perth --out output/perth/ALLDATA.KWI
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from kiwiw import alldata_writer as aw
from kiwiw import divide
from kiwiw import synth
from kiwiw.grid import ReferenceGrid
from kiwiw.spool import SpoolReader

# Read-only imports from the extractor: TileGrid/parcel_bounds are pure
# geometry helpers with no OSM/PBF dependency of their own (build_alldata.py
# never calls extract_parcel_geometry() -- that is unit 07/osm_to_parcel_
# geometry.py's own job, run as a separate, prior step). Not touching that
# module's own contents; this is the same "TileGrid.from_reference()" every
# extraction run already uses to agree on cell boundaries.
from osm_to_parcel_geometry import FIXTURE_BBOXES, TileGrid, assign_to_parcel, parcel_bounds

DEFAULT_SPOOL = str(Path(__file__).resolve().parent.parent / "output" / "spool")
DEFAULT_OUT = str(Path(__file__).resolve().parent.parent / "output" / "ALLDATA.KWI")
DEFAULT_LEVELS = [12, 10, 8, 6, 4, 2, 0]

# `synth.build_map_frame_bytes()`'s hard format ceiling (Map Frame header's
# size field is a 16-bit word count: `total_size // 2` must fit in u16) --
# see synth.py:851 and unit 12's done evidence (IMPLEMENTATION.md, "Unit
# 12"). Unit 13's Amendment: the threshold `plan_divisions()` divides
# against is `min(profile's per-level mapframe_size.max, this ceiling)`,
# not the profile max alone -- some of R's own level-0 parcels the profile
# measured are themselves already divided sub-frames, not whole-cell
# frames, so the profile max can itself exceed what this format can
# represent undivided.
U16_MAPFRAME_BYTE_CEILING = 131070

_PROFILE_MAP_PATH = (
    Path(__file__).resolve().parent / "refdata" / "profile" / "map.json"
)


def _load_level_thresholds() -> dict[int, int]:
    """Per-level `plan_divisions()` threshold: `min(profile mapframe_size.
    max, U16_MAPFRAME_BYTE_CEILING)`. Falls back to the u16 ceiling alone
    for any level missing from the checked-in profile (defensive; every
    level `DEFAULT_LEVELS` names is present in the checked-in profile as
    of this unit)."""
    with open(_PROFILE_MAP_PATH) as fh:
        profile = json.load(fh)
    levels = profile.get("levels", {})
    out: dict[int, int] = {}
    for level_str, level_data in levels.items():
        ref_max = level_data.get("mapframe_size", {}).get("max")
        out[int(level_str)] = (
            min(ref_max, U16_MAPFRAME_BYTE_CEILING) if ref_max else U16_MAPFRAME_BYTE_CEILING
        )
    return out

# This unit populates only the main map layer; route-planning/index-data
# flags in the copy-through Volume Header (see alldata_writer.py) describe
# R's own disc contents, not this build's -- record what's actually built
# here so the harness's `layers_present` config can be checked against it.
LAYERS_PRESENT = ["map"]


def _level_dims(grid: ReferenceGrid, level: int) -> dict:
    lvl = grid._level_dict(level)
    return dict(
        npc_lat=1 + lvl["n_parcels_lat"][0],
        npc_lng=1 + lvl["n_parcels_lng"][0],
    )


def _fixture_cell_range(level: int, fixture: str, tile_grid: TileGrid) -> tuple[int, int, int, int]:
    """(ix_lo, ix_hi, iy_lo, iy_hi) inclusive global-cell range covering a
    named fixture bbox at `level`, via the same `assign_to_parcel()` the
    extractor itself uses -- so `--fixture perth` restricts to exactly the
    same global cells `osm_to_parcel_geometry.py --fixture perth` would
    have populated, regardless of what else the input spool contains."""
    lon_l, lat_b, lon_r, lat_t = FIXTURE_BBOXES[fixture]
    corners = [
        assign_to_parcel(lat_b, lon_l, tile_grid),
        assign_to_parcel(lat_b, lon_r, tile_grid),
        assign_to_parcel(lat_t, lon_l, tile_grid),
        assign_to_parcel(lat_t, lon_r, tile_grid),
    ]
    ixs = [c[0] for c in corners if c is not None]
    iys = [c[1] for c in corners if c is not None]
    return min(ixs), max(ixs), min(iys), max(iys)


def _encode_one(level: int, ix: int, iy: int, bounds, content: dict) -> bytes:
    """`divide.plan_divisions()`'s `encode` callback: build one Map Frame
    (whole-cell or divided sub-cell -- this function doesn't know or care
    which) from a content dict shaped like `SpoolReader.iter_level()`
    yields. `ix`/`iy` only feed `llcode`, a Map Frame header field with no
    established on-disc semantics anywhere in this codebase (confirmed by
    grep across kiwiw/ -- nothing decodes or checks its value; see
    parser/kiwiw/parcel.py's decode docstring) -- used here as a generic
    position marker, valid for both a parent cell's own (ix, iy) and a
    divided sub-cell's (sub_ix, sub_iy)."""
    roads = content.get("roads") or []
    bgs = content.get("backgrounds") or []
    names = content.get("names") or []

    road_bytes = synth.build_road_frame_bytes(roads, bounds) if roads else None
    bg_bytes = synth.build_background_frame_bytes(bgs, bounds) if bgs else None
    # Amendment (post-11, orchestrator): `level=` must be passed
    # explicitly -- omitting it silently reverts to the legacy
    # type-1-only string path instead of unit 11's type-5/6 encoding.
    name_bytes = synth.build_name_frame_bytes(names, bounds, level=level) if names else None

    llpid = (bounds.lat_lo, bounds.lon_lo)
    llcode = (ix % 256, iy % 256)

    return synth.build_map_frame_bytes(
        level, llpid, llcode, road_bytes, bg_bytes, name_bytes)


def _encode_level(level: int, grid: ReferenceGrid, reader: SpoolReader,
                   fixture: str | None, threshold_bytes: int
                   ) -> tuple[list[tuple[int, int, bytes]],
                              list[tuple[int, int, int, int, int, bytes]], int, int]:
    """Encode every spooled parcel at `level`, splitting any parcel whose
    whole-cell Map Frame would exceed `threshold_bytes` via
    `divide.plan_divisions()` (unit 13). Returns (parcels, divided_parcels,
    n_parcels, total_frame_bytes) -- `parcels` is type-0 (undivided)
    ``(ix, iy, frame_bytes)`` for ``LevelBuild``, `divided_parcels` is
    ``(ix, iy, parcel_type, sub_ix, sub_iy, frame_bytes)`` for
    ``build_alldata_kwi(..., divided=...)``; `n_parcels`/total bytes count
    every frame actually placed (divided sub-frames included, the parent
    cell itself does not)."""
    tile_grid = TileGrid.from_reference(level)
    cell_range = _fixture_cell_range(level, fixture, tile_grid) if fixture else None

    def _cells():
        for ix, iy, content in reader.iter_level(level):
            if cell_range is not None:
                ix_lo, ix_hi, iy_lo, iy_hi = cell_range
                if not (ix_lo <= ix <= ix_hi and iy_lo <= iy <= iy_hi):
                    continue
            yield ix, iy, content

    out: list[tuple[int, int, bytes]] = []
    divided_out: list[tuple[int, int, int, int, int, bytes]] = []
    n_bytes = 0
    n_parcels = 0
    for ix, iy, parcel_type, sub_ix, sub_iy, frame_bytes in divide.plan_divisions(
            level, _cells(), threshold_bytes, _encode_one):
        if parcel_type == 0:
            out.append((ix, iy, frame_bytes))
        else:
            divided_out.append((ix, iy, parcel_type, sub_ix, sub_iy, frame_bytes))
        n_parcels += 1
        n_bytes += len(frame_bytes)

    return out, divided_out, n_parcels, n_bytes


def run(spool_dir: str, out_path: str, levels: list[int],
        fixture: str | None, disk_title: str) -> int:
    if not os.path.isdir(spool_dir):
        print(f"ERROR: spool directory not found: {spool_dir}", file=sys.stderr)
        return 1

    reader = SpoolReader(spool_dir)
    available = set(reader.levels())
    grid = ReferenceGrid.load()
    thresholds = _load_level_thresholds()

    spool_stats = {lvl: reader.stats(lvl) for lvl in levels}

    level_builds: dict[int, aw.LevelBuild] = {}
    divided_builds: dict[int, list[tuple[int, int, int, int, int, bytes]]] = {}
    manifest_levels: dict[str, dict] = {}
    for level in levels:
        print(f"level {level}: encoding ...", flush=True)
        if level not in available:
            print(f"level {level}: no spooled content, skipping", flush=True)
            level_builds[level] = aw.LevelBuild(level=level, parcels=[])
            manifest_levels[str(level)] = {"parcels": 0, "bytes": 0, "divided_parents": 0}
            continue
        threshold_bytes = thresholds.get(level, U16_MAPFRAME_BYTE_CEILING)
        parcels, divided_parcels, n_parcels, n_bytes = _encode_level(
            level, grid, reader, fixture, threshold_bytes)
        level_builds[level] = aw.LevelBuild(level=level, parcels=parcels)
        if divided_parcels:
            divided_builds[level] = divided_parcels
        n_divided_parents = len({(ix, iy) for ix, iy, *_ in divided_parcels})
        max_frame = max(
            [len(fb) for _ix, _iy, fb in parcels]
            + [len(fb) for *_rest, fb in divided_parcels],
            default=0)
        manifest_levels[str(level)] = {
            "parcels": n_parcels, "bytes": n_bytes,
            "divided_parents": n_divided_parents,
            "threshold_bytes": threshold_bytes,
            "max_frame_bytes": max_frame,
        }
        print(f"level {level}: {n_parcels} parcels ({n_divided_parents} parents divided), "
              f"{n_bytes:,} frame bytes, max frame {max_frame:,} bytes "
              f"(threshold {threshold_bytes:,})", flush=True)

    print("assembling ALLDATA.KWI ...", flush=True)
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    data = aw.build_alldata_kwi(level_builds, grid, disk_title=disk_title,
                                 out_path=out_path, divided=divided_builds)
    print(f"wrote {out_path} ({len(data):,} bytes)", flush=True)

    sha256 = hashlib.sha256(data).hexdigest()
    manifest = {
        "spool_dir": spool_dir,
        "spool_stats": {str(k): v for k, v in spool_stats.items()},
        "levels": manifest_levels,
        "total_size": len(data),
        "sha256": sha256,
        "layers_present": LAYERS_PRESENT,
        "fixture": fixture,
    }
    manifest_path = os.path.join(os.path.dirname(out_path) or ".", "manifest.json")
    with open(manifest_path, "w") as fh:
        json.dump(manifest, fh, indent=2)
    print(f"wrote {manifest_path}", flush=True)

    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--spool", default=DEFAULT_SPOOL,
                     help="Spool directory written by osm_to_parcel_geometry.py "
                          "(default: %(default)s)")
    ap.add_argument("--out", default=DEFAULT_OUT,
                     help="Output ALLDATA.KWI path (default: %(default)s)")
    ap.add_argument("--levels", type=int, nargs="+", default=DEFAULT_LEVELS,
                     help="Map levels to build (default: %(default)s)")
    ap.add_argument("--fixture", choices=sorted(FIXTURE_BBOXES), default=None,
                     help="Restrict the build to a named dev fixture's cells "
                          "(e.g. 'perth'); container shape stays the full 7-level "
                          "structure regardless")
    ap.add_argument("--disk-title", default="AU ",
                     help="Volume Header disk title (default: %(default)r)")
    args = ap.parse_args()

    return run(spool_dir=args.spool, out_path=args.out, levels=args.levels,
               fixture=args.fixture, disk_title=args.disk_title)


if __name__ == "__main__":
    raise SystemExit(main())
