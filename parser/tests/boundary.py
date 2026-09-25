"""Layer (a) boundary-test helpers (Contract T, plan 03 3C-02).

These helpers write and read fixture spool bytes, decode a whole-cell Map
Frame's bytes with the existing Python decoders, and check invariants on the
decoded result. None of them compute an expected encoding: the oracle stays
the Python decoder, committed goldens and invariants measured on R
(`DESIGN.md`, "Contract T -- tests").
"""
from __future__ import annotations

from pathlib import Path
from typing import Iterable, Optional

from kiwiw.model import BoundingBox, MeshLocation, RoadNode
from kiwiw.parcel import decode_parcel
from kiwiw.spool import SpoolReader, SpoolWriter

# `kw_encode_cell`/E1/E2's own hard ceiling (`_cenc.c`'s `MAX_FRAME`); used
# only as an invariant bound, never to compute a frame's bytes.
MAX_FRAME_BYTES = 131070


# ---------------------------------------------------------------------------
# fixture spool: write / read
# ---------------------------------------------------------------------------

def write_fixture_spool(spool_dir, cells: dict[tuple[int, int, int], dict]) -> None:
    """Write a fixture spool at `spool_dir` via `SpoolWriter`.

    `cells` maps `(level, ix, iy)` to a content dict with any of
    `"roads"`/`"backgrounds"`/`"names"` (lists of `kiwiw.model.RoadLink` /
    `BackgroundShape` / `NameRecord`, hand-described by the caller -- this
    helper does not fabricate shapes)."""
    with SpoolWriter(spool_dir) as w:
        for (level, ix, iy), content in cells.items():
            w.add(level, ix, iy, roads=content.get("roads"),
                  backgrounds=content.get("backgrounds"), names=content.get("names"))


def open_spool(spool_dir) -> SpoolReader:
    """Open `spool_dir` (written by `write_fixture_spool` or a real
    extraction run) for reading. Caller closes it."""
    return SpoolReader(spool_dir)


# ---------------------------------------------------------------------------
# Map Frame decode
# ---------------------------------------------------------------------------

def decode_frame(mapframe_bytes: bytes, bounds: BoundingBox):
    """Decode one whole-cell Map Frame's bytes -- as `kw_encode_cell`/E1/E2
    produce, or as sliced out of a real disc -- into a `kiwiw.model.Parcel`
    via the existing Python decoders (`kiwiw.parcel.decode_parcel`), giving
    `.road`/`.background`/`.name` plain structures to assert on.

    `bounds` must carry `coord_range` (`BoundingBox.require_range`); the
    other `MeshLocation` fields are decode-irrelevant metadata, so this
    passes placeholders."""
    loc = MeshLocation(level=0, parcel_type=0, blockset_index=0, block_index=0,
                        parcel_index=0, bounds=bounds, sector_addr=0,
                        size_logical_sectors=0)
    return decode_parcel(loc, mapframe_bytes)


# ---------------------------------------------------------------------------
# invariants
# ---------------------------------------------------------------------------

def assert_road_nodes_in_range(nodes: Iterable[RoadNode], coord_range: int) -> None:
    """Every road node's stored `(x, y)` lies in `[0, coord_range]`
    (`_cenc.c`'s `to_xy`/`cmax` clamp)."""
    for n in nodes:
        assert 0 <= n.x <= coord_range, f"x={n.x} outside [0, {coord_range}]"
        assert 0 <= n.y <= coord_range, f"y={n.y} outside [0, {coord_range}]"


def assert_latlon_in_bounds(points: Iterable[tuple[float, float]], bounds: BoundingBox,
                             tol: float = 1e-9) -> None:
    """Every `(lat, lon)` lies within `bounds`' lat/lon rectangle (the
    decoded-space form of "clip-rectangle containment": stored coordinates
    in `[0, range]` map affinely onto `[lat_lo, lat_hi]` x `[lon_lo,
    lon_hi]`, so containment there is containment here)."""
    for lat, lon in points:
        assert bounds.lat_lo - tol <= lat <= bounds.lat_hi + tol, \
            f"lat={lat} outside [{bounds.lat_lo}, {bounds.lat_hi}]"
        assert bounds.lon_lo - tol <= lon <= bounds.lon_hi + tol, \
            f"lon={lon} outside [{bounds.lon_lo}, {bounds.lon_hi}]"


def assert_delta_representable(coords: list[int], mult_const: int) -> None:
    """Every consecutive raw-coordinate delta, divided by `mult_const`,
    fits the record's signed-byte delta field (`[-128, 127]`; mirrors
    `_cenc.c`'s `write_record` clamp -- this asserts the clamp was never
    needed, not what value it would produce)."""
    for a, b in zip(coords, coords[1:]):
        d = (b - a) // mult_const if (b - a) % mult_const == 0 else None
        assert d is not None, f"delta {b - a} not a multiple of mult_const={mult_const}"
        assert -128 <= d <= 127, f"delta units {d} outside [-128, 127]"


def assert_frame_size_ceiling(frame_bytes: bytes,
                               limit: int = MAX_FRAME_BYTES) -> None:
    assert len(frame_bytes) <= limit, f"frame is {len(frame_bytes)} bytes > {limit}"
