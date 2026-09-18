"""WP1 unit 13: divided parcels (Ch.6 divided/integrated-parcel types 1..3)
for oversize Map Frames.

`synth.build_map_frame_bytes()` cannot represent a frame whose total size
exceeds the format's 131,070-byte u16 word-count ceiling (`total_size // 2`
must fit in 16 bits) -- see `synth.py:851`, and unit 12's done evidence
(`docs/plans/01-eval-harness-and-map-layer/IMPLEMENTATION.md`, "Unit 12")
hit this directly. This module splits any parcel whose whole-cell Map Frame
would exceed the per-level threshold into the divided sub-grid the LMR
already declares for that level (`n_parcels_lat[1]`/`n_parcels_lng[1]` for
type 1 = 2x2, `n_parcels_lat[2]`/`n_parcels_lng[2]` for type 2 = 4x4 --
confirmed constant across every level in `parser/refdata/grid.json`, so
these dimensions are not re-derived per call). Type 3 (1x1, "integration")
is the opposite direction -- merging small parcels together -- and out of
scope here (DESIGN.md section 6; this brief only ever splits).

Division order: type 1 (2x2) is tried first (finest split, keeps sibling
frames closest to a normal single-cell size); type 2 (4x4) is only used if
a type-1 quadrant would still be oversize. If a type-2 sub-frame is *still*
oversize (the fixture's level-12 case: a single global parcel ~300x over
the u16 ceiling -- see the brief's Amendment), it is emitted anyway rather
than raising: type 2 is the largest division this unit implements, and the
remaining overshoot is unit 14's (per-level feature selection) to close,
not a bug in this module.

Content re-tiling mirrors `osm_to_parcel_geometry.py`'s own top-level
per-parcel assignment rules (read-only reuse -- this module does not
modify the extractor):

- Roads are actually clipped at sub-cell boundaries via
  `split_polyline_by_parcel()`, using a `TileGrid` scoped to the parent
  cell's own bounds as the sub-grid. A parent `RoadLink`'s
  `(osm_way_id, ordinal)` identity is preserved *unchanged* on every
  resulting sub-chain (this is deliberate, not an oversight: WP2's
  `LinkIdRegistry` join key is `(osm_way_id, ordinal)`, and this module
  does not renumber it just because a chain crosses another internal
  boundary -- if a single parent chain is cut into more than one sub-chain
  by this second split, every piece keeps the same identity, so more than
  one on-disc link can carry that identity after division; WP2 must be
  aware its registry key is not guaranteed unique after a divided-parcel
  split).
- Backgrounds and names are *not* clipped -- each whole shape/point is
  assigned wholesale to whichever sub-cell contains its centroid
  (backgrounds) or point (names), exactly as the original extractor
  assigns whole shapes to a top-level parcel.

Per-node road attributes (`oneway`/`tunnel`/`bridge`/`planned`) are not
reproduced on re-split sub-chains: `split_polyline_by_parcel()` operates on
bare `(lat, lon)` coordinate lists (`RoadLink.points`), which carry no
per-node attribute data to correlate back to the new nodes built here. New
sub-chain `RoadNode`s are built with those flags defaulted to false/0 and
`x=y=0` so `synth.encode_road_link_bytes()` recomputes pixel coordinates
from `lat`/`lon` against the new sub-cell bounds rather than reusing pixel
coordinates computed against the parent cell (see that function's x==0/
y==0 fallback).

Deviation found during the Perth fixture's done-evidence build (report
this, do not treat it as silently resolved): `synth.build_map_frame_bytes()`
does not merely produce a *large* frame past the u16 word-count ceiling --
it raises `ValueError` (synth.py:851, `_u16(total_size // 2)`) the moment
`total_size` itself exceeds 131,070 bytes, for *any* call, whole-cell or
sub-frame. The brief's Amendment ("level 12 may still overshoot even after
maximal division -- report it, don't fix it") reads as if `encode()` still
*returns* an overshooting frame that is merely bigger than the threshold;
in the real fixture, level 12's reference-grid cell is a single (nx=ny=1)
macro-cell holding ~975k background shapes and ~223k names, so even a 4x4
(16-way) division leaves each sub-frame ~60x over the *hard* 131,070-byte
ceiling, not just over the softer profile threshold -- `encode()` raises
on every one of those 16 sub-frames, not just returns something oversize.
Recursing this module's own division past type 2 is explicitly out of
this brief's scope (Amendment says report, not resolve), and truncating
band-aids the actual fix (finer per-level feature selection -- unit 14's
job, running concurrently as of this unit). So `plan_divisions()` below:
treats any `encode()` `ValueError` during a size probe as "definitely
oversize" (forces further escalation, same as a merely-large frame would);
and, only at the final accepted tier (type 2, forced acceptance) when
`encode()` still raises even there, falls back to *shrinking* that one
sub-cell's content (bisecting road/background/name counts) until it fits under
the format's hard ceiling, discarding the rest and printing a `stderr`
warning with the per-cell dropped-item counts -- rather than crashing the
whole build or silently writing nothing for that sub-cell. The yielded row
shape is unchanged (still `(ix, iy, parcel_type, sub_ix, sub_iy,
map_frame_bytes)`); this is a content-lossy stopgap for an out-of-scope
situation, not a fix -- report the printed per-cell drop counts, don't
treat them as resolved.
"""
from __future__ import annotations

import dataclasses
import sys
from typing import Callable, Iterable, Iterator

from .model import BoundingBox, RoadNode

# Read-only imports from the extractor (geometry helpers only; this module
# never calls extract_parcel_geometry() and does not modify that file --
# see docs/design/target-disc.md and this unit's own module docstring).
from osm_to_parcel_geometry import TileGrid, assign_to_parcel, parcel_bounds, split_polyline_by_parcel

# (nx, ny) sub-grid dimensions per division type, confirmed constant across
# every level in parser/refdata/grid.json: n_parcels_lat/lng index 1 is
# always [1, 1] (2x2, sws-decoded as 1+1) and index 2 is always [3, 3]
# (4x4, sws-decoded as 1+3). Index 3 (type 3, integration/1x1) is out of
# scope for this module.
_SUBGRID_DIMS: dict[int, tuple[int, int]] = {1: (2, 2), 2: (4, 4)}

EncodeFn = Callable[[int, int, int, BoundingBox, dict], bytes]
# `measure(level, ix, iy, bounds, content) -> (frame_bytes, {kind: size})`
# where kind in KINDS and size is the (even-padded) sub-frame byte length
# (0 when that sub-frame is absent). Brief 29.
MeasureFn = Callable[[int, int, int, BoundingBox, dict], "tuple[bytes, dict[str, int]]"]

KINDS = ("road", "background", "name")
_CONTENT_KEY = {"road": "roads", "background": "backgrounds", "name": "names"}

# road_type (4-bit code, refdata/vocab/road_type.json semantic via
# display_class.json ordering) -> importance rank, 0 = most important.
# Motorway=12, trunk=0, primary=4, secondary=3, tertiary=9, minor=7/2, 10 =
# track at L0 but "secondary and below" at L>=2.
def _road_rank(level: int, road_type: int) -> int:
    if road_type == 12:
        return 0
    if road_type == 0:
        return 1
    if road_type == 4:
        return 2
    if road_type == 3:
        return 3
    if road_type == 9:
        return 4
    if road_type == 10:
        return 7 if level == 0 else 5
    if road_type == 7:
        return 6
    return 8


def _road_keep_order(level: int, roads: list) -> tuple[list, int]:
    """Roads sorted best-first (highest class, then longest, then lowest
    `(osm_way_id, ordinal)`), so dropping the tail drops lowest class first,
    shortest first, ties -> highest `(osm_way_id, ordinal)`. Returns
    `(ordered, n_pinned)`: at level >= 2 motorway/trunk links are pinned
    (never trimmed) and sort first."""
    def key(r):
        return (_road_rank(level, r.road_type), -len(r.points),
                r.osm_way_id if r.osm_way_id is not None else 0, r.ordinal)
    ordered = sorted(roads, key=key)
    n_pinned = 0
    if level >= 2:
        n_pinned = sum(1 for r in ordered if r.road_type in (12, 0))
    return ordered, n_pinned


def _bg_keep_order(shapes: list) -> list:
    """Largest bounding-box area first, then most coords, then input order."""
    def key(item):
        i, sh = item
        cs = sh.coords
        if not cs:
            return (0.0, 0, i)
        area = (max(c[0] for c in cs) - min(c[0] for c in cs)) * \
               (max(c[1] for c in cs) - min(c[1] for c in cs))
        return (-area, -len(cs), i)
    return [sh for _i, sh in sorted(enumerate(shapes), key=key)]


def _name_keep_order(names: list) -> list:
    """Keep order: road names (string_type 5), place names, POI/background
    names (string_type 6), then duplicate `(text, string_type)` (first kept)."""
    seen: set = set()

    def rank(rec) -> int:
        k = (rec.text, rec.string_type)
        if k in seen:
            return 3
        seen.add(k)
        if rec.string_type == 5:
            return 0
        if rec.string_type == 6:
            return 2
        return 1
    ranked = [(rank(r), i, r) for i, r in enumerate(names)]
    ranked.sort(key=lambda t: (t[0], t[1]))
    return [r for _k, _i, r in ranked]


def _kind_breach(sizes: dict, kind_limits: dict | None) -> list[str]:
    if not kind_limits:
        return []
    return [k for k in KINDS if k in kind_limits and sizes.get(k, 0) > kind_limits[k]]


def _sub_tile_grid(level: int, bounds: BoundingBox, nx: int, ny: int) -> TileGrid:
    """A local sub-grid scoped to one parent cell's bounds -- `target` is
    only consulted by `TileGrid`'s `target_cells()`-family methods, which
    this module never calls (`assign_to_parcel`/`split_polyline_by_parcel`
    ignore it), so `bounds` doubling as `target` here is inert, not a
    semantic claim about coverage."""
    return TileGrid(
        level=level,
        disc_lat_lo=bounds.lat_lo,
        disc_lon_lo=bounds.lon_lo,
        disc_lat_span=bounds.lat_hi - bounds.lat_lo,
        disc_lon_span=bounds.lon_hi - bounds.lon_lo,
        nx=nx,
        ny=ny,
        target=bounds,
    )


def _retile_content(content: dict, sub_grid: TileGrid) -> dict[tuple[int, int], dict]:
    """Re-tile one parcel's content dict (`{"roads": [...], "backgrounds":
    [...], "names": [...]}`, the shape `SpoolReader.iter_level()` yields)
    into `sub_grid`'s cells. Returns `{(sub_ix, sub_iy): content}`; cells
    with no content are simply absent (no empty placeholder entries)."""
    out: dict[tuple[int, int], dict] = {}

    def _bucket(cell: tuple[int, int]) -> dict:
        return out.setdefault(cell, {"roads": [], "backgrounds": [], "names": []})

    for link in content.get("roads") or []:
        by_cell = split_polyline_by_parcel(link.points, sub_grid)
        for cell, chains in by_cell.items():
            for chain in chains:
                nodes = [
                    RoadNode(x=0, y=0, lat=lat, lon=lon,
                             oneway=0, planned=0, tunnel=False, bridge=False)
                    for lat, lon in chain
                ]
                new_link = dataclasses.replace(
                    link, nodes=nodes, n_nodes=len(nodes), points=list(chain),
                    raw_offset=0, raw_bytes=b"",
                    # osm_way_id/ordinal deliberately NOT touched -- see
                    # module docstring's "Link ordinals are preserved" note.
                )
                _bucket(cell)["roads"].append(new_link)

    for shape in content.get("backgrounds") or []:
        coords = shape.coords
        if not coords:
            continue
        lat = sum(c[0] for c in coords) / len(coords)
        lon = sum(c[1] for c in coords) / len(coords)
        cell = assign_to_parcel(lat, lon, sub_grid)
        if cell is None:
            continue
        _bucket(cell)["backgrounds"].append(shape)

    for rec in content.get("names") or []:
        if rec.lat is None or rec.lon is None:
            continue
        cell = assign_to_parcel(rec.lat, rec.lon, sub_grid)
        if cell is None:
            continue
        _bucket(cell)["names"].append(rec)

    return out


def _try_encode(encode: EncodeFn, level: int, ix: int, iy: int,
                 bounds: BoundingBox, content: dict) -> bytes | None:
    """`encode()`, but a `ValueError` (the format's hard u16 word-count
    ceiling, synth.py:851) is treated as "cannot be represented at all"
    rather than propagated -- callers treat `None` as definitely-oversize.
    """
    try:
        return encode(level, ix, iy, bounds, content)
    except ValueError:
        return None


def _shrink_to_fit(encode: EncodeFn, level: int, ix: int, iy: int,
                    bounds: BoundingBox, content: dict) -> tuple[bytes, int]:
    """Last-resort fallback for a sub-cell whose content still can't be
    encoded even at the largest division this module implements (type 2) --
    see module docstring's "Deviation found during the Perth fixture's
    done-evidence build". Bisects the combined road-chain+background+name
    item count until `encode()` stops raising, discarding roads first (a
    fixture cell this far over the ceiling is typically road-chain-dominated
    -- see the level-8 case in this unit's report), then backgrounds, and
    only then names -- names are kept preferentially because they are the
    smallest, highest-value-per-byte class (a dropped `NameRecord` fails
    `spotcheck`'s fixture contract outright, whereas the corresponding road
    geometry going missing from an already-lossy, five-cells-out-of-hundreds
    of thousands fallback is a softer degradation). See brief 22
    (`docs/plans/01-eval-harness-and-map-layer/briefs/22-spotcheck-missing-names.md`)
    -- this ordering was previously roads-preserved-first/names-dropped-first,
    which is what caused Sydney/Melbourne level-0 `spotcheck` FAILs; the
    ordering below is the fix.
    Returns `(frame_bytes, n_items_dropped)`; raises the original
    `ValueError` if even a single item still doesn't fit (nothing left to
    shrink)."""
    roads = list(content.get("roads") or [])
    bgs = list(content.get("backgrounds") or [])
    names = list(content.get("names") or [])
    total = len(roads) + len(bgs) + len(names)

    def _attempt(keep: int) -> bytes | None:
        # Drop priority (lowest priority first): roads, then backgrounds,
        # then names. `keep` items are kept starting from the *end* of this
        # priority order (names first, then backgrounds, then whatever
        # budget remains for roads) so names and backgrounds survive a tight
        # budget preferentially over road geometry.
        keep_names = names[:keep] if keep <= len(names) else names
        remaining = max(0, keep - len(names))
        keep_bgs = bgs[:remaining] if remaining <= len(bgs) else bgs
        remaining = max(0, remaining - len(bgs))
        keep_roads = roads[:remaining]
        trial = dict(content, roads=keep_roads, backgrounds=keep_bgs, names=keep_names)
        return _try_encode(encode, level, ix, iy, bounds, trial)

    lo, hi = 0, total
    best_bytes: bytes | None = None
    best_keep = 0
    # Bisect for the largest `keep` that still encodes.
    while lo <= hi:
        mid = (lo + hi) // 2
        fb = _attempt(mid)
        if fb is not None:
            best_bytes, best_keep = fb, mid
            lo = mid + 1
        else:
            hi = mid - 1

    if best_bytes is None:
        # Not even an empty content dict fits -- re-raise the real error
        # rather than silently emitting nothing.
        raise ValueError(
            f"cannot encode ({ix},{iy}) at ({level=}) even with all "
            f"background/name content dropped")

    dropped = total - best_keep
    if dropped:
        print(
            f"WARNING [kiwiw.divide]: level {level} cell ({ix},{iy}): "
            f"content still exceeds the format's hard 131,070-byte ceiling "
            f"after type-2 (4x4) division -- dropped {dropped}/{total} "
            f"road/background/name items to keep this sub-frame encodable "
            f"(see divide.py module docstring)", file=sys.stderr)
    return best_bytes, dropped


def _trim_kinds(measure: MeasureFn, level: int, ix: int, iy: int,
                bounds: BoundingBox, content: dict, kind_limits: dict,
                stats: dict | None) -> tuple[bytes, int]:
    """Final-tier deterministic priority trim (brief 29): for each kind
    over its limit, bisect the largest kept prefix of that kind's
    priority-sorted items whose sub-frame size is <= the limit. Only the
    offending kind is touched. Returns `(frame_bytes, n_dropped)`."""
    dropped_total = 0
    cur = dict(content)
    fb, sizes = measure(level, ix, iy, bounds, cur)
    for kind in KINDS:
        limit = kind_limits.get(kind)
        if limit is None or sizes.get(kind, 0) <= limit:
            continue
        key = _CONTENT_KEY[kind]
        items = list(cur.get(key) or [])
        n_pinned = 0
        if kind == "road":
            ordered, n_pinned = _road_keep_order(level, items)
        elif kind == "background":
            ordered = _bg_keep_order(items)
        else:
            ordered = _name_keep_order(items)

        def _try(k: int):
            trial = dict(cur, **{key: ordered[:k]})
            try:
                return measure(level, ix, iy, bounds, trial)
            except ValueError:
                return None

        lo, hi = n_pinned, len(ordered)
        best = n_pinned
        best_res = None
        while lo <= hi:
            mid = (lo + hi) // 2
            res = _try(mid)
            if res is not None and res[1].get(kind, 0) <= limit:
                best, best_res = mid, res
                lo = mid + 1
            else:
                hi = mid - 1
        if best_res is None:
            best_res = _try(best)
            if best_res is None:
                continue
        dropped = len(ordered) - best
        cur[key] = ordered[:best]
        fb, sizes = best_res
        dropped_total += dropped
        if dropped:
            print(f"WARNING [kiwiw.divide]: level {level} sub-cell ({ix},{iy}): "
                  f"trimmed {kind} {dropped}/{len(ordered)} items to meet kind budget "
                  f"{limit:,} B (brief 29)", file=sys.stderr)
            if stats is not None:
                d = stats.setdefault("dropped", {})
                d[kind] = d.get(kind, 0) + dropped
                c = stats.setdefault("cells", {})
                c[kind] = c.get(kind, 0) + 1
    return fb, dropped_total


def plan_divisions(
    level: int,
    parcels: Iterable[tuple[int, int, dict]],
    threshold_bytes: int,
    encode: EncodeFn,
    kind_limits: dict | None = None,
    measure: MeasureFn | None = None,
    trim_stats: dict | None = None,
) -> Iterator[tuple[int, int, int, int, int, bytes]]:
    """For every `(ix, iy, content)` in `parcels`, encode it whole via
    `encode(level, ix, iy, bounds, content)`; if the result fits in
    `threshold_bytes`, yield it as an undivided (type 0) parcel. Otherwise
    re-tile `content` into a type-1 (2x2) sub-grid and encode each
    populated sub-cell the same way; if any type-1 sub-frame is still
    oversize, escalate to type-2 (4x4) instead (not in addition -- type 2
    replaces type 1 for that parcel, it does not further subdivide a
    type-1 quadrant). A still-oversize type-2 sub-frame is emitted anyway
    (see module docstring) rather than raised as an error.

    `encode(level, ix, iy, bounds, content) -> bytes` is supplied by the
    caller (`build_alldata.py`) and wraps the existing road/background/
    name sub-frame + `synth.build_map_frame_bytes()` assembly; `ix`/`iy`
    are only used by callers that want a position-derived `llcode` (Map
    Frame header field with no established on-disc semantics -- see
    `parser/kiwiw/parcel.py`'s decode docstring) and are otherwise inert
    here.

    Yields `(ix, iy, parcel_type, sub_ix, sub_iy, map_frame_bytes)`:
    `parcel_type` is 0 for an undivided parcel (in which case `sub_ix` =
    `sub_iy` = 0 and `map_frame_bytes` is the whole-cell frame), or 1/2 for
    a divided sub-frame at `(sub_ix, sub_iy)` within that parcel's own
    2x2/4x4 sub-grid. `parcels` is consumed once per call (a plain
    iterator is fine); output order matches input order for type-0
    parcels, then each divided parcel's sub-frames in ascending
    `(sub_iy, sub_ix)` order. Deterministic given deterministic input.
    """
    if kind_limits and measure is None:
        raise ValueError("kind_limits requires a measure callback")
    use_kinds = bool(kind_limits)

    def _probe(lv, cx, cy, b, c):
        """-> (bytes | None, sizes | None); None = over the hard ceiling."""
        if not use_kinds:
            return _try_encode(encode, lv, cx, cy, b, c), None
        try:
            return measure(lv, cx, cy, b, c)
        except ValueError:
            return None, None

    # Bounds are not part of the `parcels` contract -- they're fully
    # derivable from (level, ix, iy) via the checked-in reference grid, so
    # this is computed once per call rather than requiring every caller to
    # pass them in (see this unit's report re: this design choice).
    tile_grid = TileGrid.from_reference(level)

    for ix, iy, content in parcels:
        bounds = parcel_bounds(ix, iy, tile_grid)
        whole_bytes, whole_sizes = _probe(level, ix, iy, bounds, content)
        if (whole_bytes is not None and len(whole_bytes) <= threshold_bytes
                and not _kind_breach(whole_sizes or {}, kind_limits)):
            yield (ix, iy, 0, 0, 0, whole_bytes)
            continue
        # `whole_bytes is None` means encode() couldn't even represent the
        # whole-cell frame (over the format's hard ceiling, not just the
        # threshold) -- definitely oversize, fall through to division the
        # same as an ordinary over-threshold frame would.

        chosen_type = 1
        chosen_frames: dict[tuple[int, int], bytes] = {}
        for parcel_type in (1, 2):
            nx, ny = _SUBGRID_DIMS[parcel_type]
            sub_grid = _sub_tile_grid(level, bounds, nx, ny)
            sub_content = _retile_content(content, sub_grid)

            frames: dict[tuple[int, int], bytes] = {}
            oversize = False
            last_tier = parcel_type == 2
            for cell, c in sub_content.items():
                sub_bounds = parcel_bounds(cell[0], cell[1], sub_grid)
                fb, sizes = _probe(level, cell[0], cell[1], sub_bounds, c)
                if fb is None:
                    oversize = True
                    if not last_tier:
                        continue  # will escalate to type 2; no bytes needed yet
                    # Last tier and still unrepresentable at the format's
                    # hard ceiling -- shrink content until it fits (see
                    # module docstring's "Deviation found ..." note).
                    fb, _dropped = _shrink_to_fit(
                        encode, level, cell[0], cell[1], sub_bounds, c)
                    sizes = None
                elif len(fb) > threshold_bytes:
                    oversize = True
                if fb is not None and use_kinds:
                    if sizes is None:  # shrunk frame: re-measure kinds
                        _fb2, sizes = _probe(level, cell[0], cell[1], sub_bounds, c)
                    if _kind_breach(sizes or {}, kind_limits):
                        if last_tier:
                            fb, _n = _trim_kinds(measure, level, cell[0], cell[1],
                                                 sub_bounds, c, kind_limits, trim_stats)
                        else:
                            oversize = True
                frames[cell] = fb

            chosen_type = parcel_type
            chosen_frames = frames
            if not oversize or parcel_type == 2:
                # type-1 fits, or type-2 is the largest division this
                # module implements -- accept it even if still oversize
                # (see module docstring / brief Amendment on level 12).
                break

        for (sub_ix, sub_iy) in sorted(chosen_frames, key=lambda c: (c[1], c[0])):
            yield (ix, iy, chosen_type, sub_ix, sub_iy, chosen_frames[(sub_ix, sub_iy)])
