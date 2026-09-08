"""Per-level feature selection, matched to the reference disc's per-level
census (`parser/refdata/profile/map.json`), so a from-scratch build's
content counts land inside the harness's envelope
(`parser/refdata/harness.json`, `envelopes.count_ratio`, default
[0.5, 2.0]) at levels 2..12, and level 0's background/name counts (road
link count is exempt at level 0 -- see
`parser/harness/checks/envelope.py`'s `_COUNT_FIELDS` and the "exempt"
flag it only sets for `link_count`) land inside the same envelope too.

docs/design/target-disc.md, "Per-level road selection tolerance" (Open
Question) and "Capacity accounting": OSM's road/feature density exceeds
the reference 2007 dataset's, so every level except level 0 needs
active thinning to avoid over-selecting; level 0 additionally needs its
per-parcel byte size kept under budget (unit 13's job) and, at level 12
specifically, needs zero road content because level 12 is one single
global parcel with no per-cell tiling to divide across (see this
project's brief 14 amendment: an unthinned level 12 Map Frame measured
39,555,559 bytes on the Perth fixture, ~300x the u16 format ceiling that
`synth.py:851` enforces, far more than unit 13's maximum 4x4 division can
recover -- this module's selection is the only thing that can bring level
12 under budget).

Selection table format (`parser/refdata/selection.json`)
----------------------------------------------------------
::

    {
      "levels": [[0, 0], [2, 2], ...],   # even-level ranges, must cover 0..12
      "rules": [
        {"levels": 0, "highway": [...], "background": [...], "place": [...]},
        ...
      ],
      "min_length_m": {"0": 0, "2": 0, ...}
    }

- ``levels``: disjoint ``[lo, hi]`` ranges (inclusive) whose union is
  exactly the even levels 0, 2, 4, 6, 8, 10, 12 -- same coverage rule as
  `kiwiw.vocab`'s tables, checked independently here (this module does not
  import `kiwiw.vocab`'s private validation helpers; it is a separate,
  self-contained loader per this unit's owned-paths list).
- ``rules``: one entry per declared range (keyed by the range's lower
  bound, in ``rules[i]["levels"]``). Each entry may carry:
    - ``highway``: list of OSM ``highway=`` values admitted at this level
      (empty list = no roads admitted -- this is R's own state at levels
      10/12, where the reference census has zero road links).
    - ``background``: list of ``{"key": <osm tag key>, "value": <osm tag
      value>}`` predicates; a way is admitted as a background candidate at
      this level if it matches *any* predicate (OR across the list, same
      as OSM's usual any-of-these-tags meaning; empty/omitted list = no
      background features admitted unless ``background_all`` is set).
    - ``background_all`` (bool, default false): admit *any* tags that
      reach the background branch (i.e. no ``highway``/``place`` match),
      ignoring ``background``'s predicate list entirely. Needed for level
      0: ``parser/refdata/vocab/bg_type.json`` declares a catch-all
      ``{"levels": 0, "match": {}, "value": 288}`` rule, so the real
      extractor already treats every non-road way with a ring as *some*
      background type there regardless of its tags -- an explicit
      key/value predicate list cannot express that.
    - ``place``: list of OSM ``place=`` values admitted at this level for
      place-node name records (empty/omitted = none admitted).
  A range with no rule entry admits nothing at any level in that range.
- ``min_length_m``: per-level minimum way length in metres, for
  generalisation at levels >= 4. **Not wired into the extractor by this
  module** -- see "Length threshold: recorded but not enforced" below,
  a contradiction this unit's report flags rather than resolving
  silently.

Length threshold: recorded but not enforced
--------------------------------------------
The brief's contract states `selection.level_filter(level, tags) -> bool`
-- the same two-argument signature
`parser/osm_to_parcel_geometry.py`'s `LevelFilter` type already declares,
and the *only* thing this unit's owned-paths list permits touching in
that file is the `level_filter` default (wiring it to this module's
`level_filter`). Every call site that invokes `level_filter` does so
before any geometry/length computation exists for the feature in
question (`_handle_way`'s per-level loop calls `self.level_filter(level,
tags)` before it knows whether a way is a road or a background ring, and
well before `split_polyline_by_parcel` produces per-parcel chains whose
length could be measured), and passes only `(level, tags)` -- no length
argument. So `min_length_m` cannot actually be enforced through this
seam without either widening `LevelFilter`'s signature or moving the
length check to a different call site inside `_handle_way` -- both out of
this unit's owned paths (`osm_to_parcel_geometry.py`'s owned surface is
"the `level_filter` default" only). `min_length_m` is therefore recorded
in `selection.json` and exercised by a pure function
(`meets_length_threshold`) that this module's own tests exercise, but it
is dead data as far as a real extraction run is concerned. Reported in
this unit's "Report back", not resolved by exceeding owned paths.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

_PACKAGE_DIR = Path(__file__).resolve().parent
_SELECTION_PATH = _PACKAGE_DIR.parent / "refdata" / "selection.json"

EVEN_LEVELS = (0, 2, 4, 6, 8, 10, 12)


class SelectionError(ValueError):
    """Raised when `selection.json` fails validation on load."""


@dataclass(frozen=True)
class _Range:
    lo: int
    hi: int

    def contains(self, level: int) -> bool:
        return self.lo <= level <= self.hi


@dataclass(frozen=True)
class _LevelRule:
    highway: frozenset
    background: tuple  # tuple of (key, value) pairs
    place: frozenset
    background_all: bool = False  # see level_filter() and selection.json's
    # level-0 rule: parser/refdata/vocab/bg_type.json declares a catch-all
    # `{"levels": 0, "match": {}, "value": 288}` rule (and the same for
    # level 2) -- any non-road way with a ring is classified as *some*
    # background type at those levels regardless of its tags, so an
    # explicit key/value predicate list cannot express "admit everything
    # bg_type.json would classify"; this flag does.


@dataclass
class SelectionTable:
    """One loaded `selection.json`. Construct via `SelectionTable.load()`."""

    _ranges: list = field(default_factory=list)
    _rules: dict = field(default_factory=dict)  # range_lo -> _LevelRule
    _min_length_m: dict = field(default_factory=dict)  # level(int) -> float

    # -- lookup ---------------------------------------------------------

    def _range_lo_for_level(self, level: int) -> Optional[int]:
        for r in self._ranges:
            if r.contains(level):
                return r.lo
        return None

    def _rule_for_level(self, level: int) -> Optional[_LevelRule]:
        lo = self._range_lo_for_level(level)
        if lo is None:
            return None
        return self._rules.get(lo)

    def level_filter(self, level: int, tags: dict) -> bool:
        """`LevelFilter`-shaped hook: True if `tags` (a way's or node's OSM
        tag dict) should be admitted at `level`. Mirrors the extractor's
        own way/node classification order: a `highway=` tag is checked as
        a road candidate; a `place=` tag as a place-node candidate;
        anything else is checked against the background predicate list.
        A tags dict matching none of the level's rules (or a level outside
        every declared range) is not admitted."""
        rule = self._rule_for_level(level)
        if rule is None:
            return False

        highway = tags.get("highway")
        if highway is not None:
            return highway in rule.highway

        place = tags.get("place")
        if place is not None:
            return place in rule.place

        if rule.background_all:
            return True
        for key, value in rule.background:
            if tags.get(key) == value:
                return True
        return False

    def min_length_m(self, level: int) -> float:
        """Minimum way length in metres for generalisation at `level`
        (0.0 if the level has no threshold configured). See this module's
        docstring, "Length threshold: recorded but not enforced" -- this
        value is not applied by `level_filter` or by the extractor."""
        return self._min_length_m.get(level, 0.0)

    def meets_length_threshold(self, level: int, length_m: float) -> bool:
        """Pure predicate: would a way of `length_m` metres survive
        generalisation at `level`. Exercised by tests; not wired into any
        extraction call site (see module docstring)."""
        return length_m >= self.min_length_m(level)

    # -- loading ----------------------------------------------------------

    @classmethod
    def load(cls, path: Optional[Path] = None) -> "SelectionTable":
        p = path or _SELECTION_PATH
        with open(p) as f:
            data = json.load(f)
        return _validate_and_build(data)


def _validate_and_build(data: dict) -> SelectionTable:
    if "levels" not in data or "rules" not in data:
        raise SelectionError("selection table: must have 'levels' and 'rules' keys")

    raw_ranges = data["levels"]
    if not isinstance(raw_ranges, list) or not raw_ranges:
        raise SelectionError("selection table: 'levels' must be a non-empty list")

    ranges: list = []
    covered: set = set()
    for raw in raw_ranges:
        if (not isinstance(raw, list) or len(raw) != 2
                or not all(isinstance(v, int) for v in raw)):
            raise SelectionError(
                f"selection table: each 'levels' entry must be a [lo, hi] "
                f"pair of ints, got {raw!r}")
        lo, hi = raw
        if lo > hi:
            raise SelectionError(f"selection table: range [{lo}, {hi}] has lo > hi")
        range_levels = {lv for lv in EVEN_LEVELS if lo <= lv <= hi}
        if not range_levels:
            raise SelectionError(
                f"selection table: range [{lo}, {hi}] covers no even level 0..12")
        overlap = covered & range_levels
        if overlap:
            raise SelectionError(
                f"selection table: range [{lo}, {hi}] overlaps an earlier "
                f"range at level(s) {sorted(overlap)}")
        covered |= range_levels
        ranges.append(_Range(lo=lo, hi=hi))

    missing = set(EVEN_LEVELS) - covered
    if missing:
        raise SelectionError(
            f"selection table: 'levels' ranges do not cover even level(s) "
            f"{sorted(missing)} (0..12 even must all be covered)")

    range_los = {r.lo for r in ranges}
    rules: dict = {}
    for i, raw_rule in enumerate(data["rules"]):
        if not isinstance(raw_rule, dict):
            raise SelectionError(f"selection table: rule {i} must be an object")
        if "levels" not in raw_rule:
            raise SelectionError(f"selection table: rule {i} missing 'levels'")
        range_lo = raw_rule["levels"]
        if range_lo not in range_los:
            raise SelectionError(
                f"selection table: rule {i} 'levels'={range_lo!r} does not "
                f"match any declared range's lower bound ({sorted(range_los)})")
        if range_lo in rules:
            raise SelectionError(
                f"selection table: more than one rule for range starting "
                f"at level {range_lo}")

        highway = raw_rule.get("highway", [])
        if not isinstance(highway, list) or not all(isinstance(v, str) for v in highway):
            raise SelectionError(
                f"selection table: rule {i} 'highway' must be a list of strings")

        background_raw = raw_rule.get("background", [])
        if not isinstance(background_raw, list):
            raise SelectionError(f"selection table: rule {i} 'background' must be a list")
        background = []
        for j, pred in enumerate(background_raw):
            if (not isinstance(pred, dict) or "key" not in pred or "value" not in pred
                    or not isinstance(pred["key"], str) or not isinstance(pred["value"], str)):
                raise SelectionError(
                    f"selection table: rule {i} background predicate {j} must be "
                    f"an object with string 'key' and 'value'")
            background.append((pred["key"], pred["value"]))

        place = raw_rule.get("place", [])
        if not isinstance(place, list) or not all(isinstance(v, str) for v in place):
            raise SelectionError(
                f"selection table: rule {i} 'place' must be a list of strings")

        background_all = raw_rule.get("background_all", False)
        if not isinstance(background_all, bool):
            raise SelectionError(
                f"selection table: rule {i} 'background_all' must be a bool")

        rules[range_lo] = _LevelRule(
            highway=frozenset(highway),
            background=tuple(background),
            place=frozenset(place),
            background_all=background_all,
        )

    min_length_raw = data.get("min_length_m", {})
    if not isinstance(min_length_raw, dict):
        raise SelectionError("selection table: 'min_length_m' must be an object")
    min_length_m: dict = {}
    for level_str, value in min_length_raw.items():
        try:
            level = int(level_str)
        except (TypeError, ValueError):
            raise SelectionError(
                f"selection table: 'min_length_m' key {level_str!r} is not an int")
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise SelectionError(
                f"selection table: 'min_length_m'[{level_str!r}] must be a number")
        min_length_m[level] = float(value)

    return SelectionTable(_ranges=ranges, _rules=rules, _min_length_m=min_length_m)


# ---------------------------------------------------------------------------
# Module-level default table + `level_filter` (the brief's contract:
# `selection.level_filter(level, tags) -> bool`)
# ---------------------------------------------------------------------------

_default_table: Optional[SelectionTable] = None


def _table() -> SelectionTable:
    global _default_table
    if _default_table is None:
        _default_table = SelectionTable.load()
    return _default_table


def level_filter(level: int, tags: dict) -> bool:
    """Module-level `LevelFilter`-shaped hook, wired as
    `osm_to_parcel_geometry.py`'s `level_filter` default. Lazily loads and
    caches `parser/refdata/selection.json` on first call."""
    return _table().level_filter(level, tags)


def meets_length_threshold(level: int, length_m: float) -> bool:
    """Module-level convenience wrapper over the default table's
    `meets_length_threshold` -- see that method and the module docstring's
    "Length threshold: recorded but not enforced" section."""
    return _table().meets_length_threshold(level, length_m)


# ---------------------------------------------------------------------------
# Dry-run counting mode (brief 14: "add it to selection.py, not the
# extractor"; "Do not run a full-Australia extract+build to iterate ...
# use the cheap counting path for every tuning pass").
#
# A full geometry extraction (osm_to_parcel_geometry.extract_parcel_geometry)
# takes 1:27:24 over the full Australia PBF (unit 07's report) because it
# resolves node locations, splits polylines at parcel boundaries and spools
# ~21 GB to disk. This counting mode instead makes one lightweight pyosmium
# pass with no location index and no parcel tiling -- it only reads each
# way's/node's tags and tallies, per level, how many would be admitted by
# a candidate `SelectionTable`. On this repo's australia-260824.osm.pbf
# (11,464,956 ways, 134,709,031 nodes) a ways-only tag pass takes ~20-50s;
# a full ways+nodes pass (needed to also count place-node names) takes a
# few minutes -- both dramatically cheaper than a real extraction.
#
# Caveat (recorded, not hidden): this mode counts *ways*/*nodes*, not the
# post-parcel-split *links* the harness's envelope check actually compares
# against R's `road.link_count`. Background/name counts are not affected
# by this caveat (background shapes are not clipped per parcel --
# `osm_to_parcel_geometry._make_background_shape` emits one shape per way,
# centroid-assigned to a single cell -- so a national way count is directly
# comparable to R's `shape_count`). Road link counts, by contrast, are
# split per parcel by `split_polyline_by_parcel`, so this mode's road
# counts under-approximate the real, post-split count by an amount that
# grows with how finely a level's grid cuts through long ways; unit 07's
# own unfiltered spool showed roughly a 30% inflation at level 0 (a
# 2,320,289-way ROADS-matching total became 3,015,057 spooled links) and
# essentially none at level 12 (one global parcel, no splitting at all).
# This unit's report records the caveat per level; it is not silently
# treated as an exact count.
# ---------------------------------------------------------------------------

DEFAULT_PBF = str(
    Path(__file__).resolve().parent.parent.parent / "australia-260824.osm.pbf"
)

ROADS = {
    "motorway", "trunk", "primary", "secondary", "tertiary",
    "motorway_link", "trunk_link", "primary_link", "secondary_link", "tertiary_link",
    "unclassified", "residential", "living_street", "service", "track", "road", "busway",
}


@dataclass
class DryRunCounts:
    """Per-level tallies from `count_dry_run`."""
    highway: dict  # level -> count of ROADS-matching ways admitted
    background: dict  # level -> count of background-candidate ways admitted
    place: dict  # level -> count of place nodes admitted


def count_dry_run(table: SelectionTable, pbf_path: str = DEFAULT_PBF,
                   levels=EVEN_LEVELS, include_nodes: bool = True,
                   verbose: bool = True) -> DryRunCounts:
    """Cheap, tags-only count of what `table.level_filter` would admit at
    each of `levels`, over `pbf_path`. No location index, no geometry, no
    spooling -- see the module-level docstring above for why this is safe
    to run for every tuning pass, and for the road-link-count caveat.

    `include_nodes=False` skips the node pass (place-node counting), which
    is far slower than the way pass (134M nodes vs 11.5M ways on the
    Australia PBF) -- useful for a fast highway/background-only iteration
    loop.
    """
    import osmium

    highway_counts = {lv: 0 for lv in levels}
    background_counts = {lv: 0 for lv in levels}
    place_counts = {lv: 0 for lv in levels}

    outer_levels = list(levels)

    class _Handler(osmium.SimpleHandler):
        def way(self, w):
            # Same TagList.get()-before-dict() pattern as node() below --
            # cheap on ways too (11.5M of them), even though the win
            # matters far less here than for the 134M-node pass.
            highway = w.tags.get("highway")
            tags = dict(w.tags)
            is_road = highway in ROADS
            for lv in outer_levels:
                if not table.level_filter(lv, tags):
                    continue
                if is_road:
                    highway_counts[lv] += 1
                else:
                    background_counts[lv] += 1

        def node(self, n):
            if not include_nodes:
                return
            # `n.tags` is an osmium TagList backed by C++ storage; `.get()`
            # does a native linear scan without materialising a Python
            # dict. Checking this first avoids `dict(n.tags)` (expensive
            # for a TagList) on all ~134M Australia nodes just to discard
            # the ~134.7M-35k that carry no `place` tag -- the earlier,
            # unoptimised version of this loop took >18 minutes and was
            # still climbing before this fix (see this unit's report).
            if n.tags.get("place") is None:
                return
            tags = dict(n.tags)
            for lv in outer_levels:
                if table.level_filter(lv, tags):
                    place_counts[lv] += 1

    if verbose:
        print(f"selection dry-run: scanning {pbf_path} "
              f"(include_nodes={include_nodes}) ...", flush=True)
    h = _Handler()
    h.apply_file(pbf_path)
    if verbose:
        print("selection dry-run: done.", flush=True)

    return DryRunCounts(highway=highway_counts, background=background_counts,
                         place=place_counts)


def report_envelope(counts: DryRunCounts, profile: dict,
                     count_ratio=(0.5, 2.0), level0_link_exempt: bool = True) -> dict:
    """Compare `counts` (from `count_dry_run`) against `profile`
    (`parser/refdata/profile/map.json`, already loaded) per level, and
    report which levels fall inside `count_ratio` of R for each of
    link/background/place counts. Level 0's link count is exempt when
    `level0_link_exempt` (matches `harness.json`'s `level0_count_exempt`
    for `link_count` only -- background/place are NOT exempt at level 0,
    see `parser/harness/checks/envelope.py`)."""
    lo_ratio, hi_ratio = count_ratio
    levels_data = profile["levels"]
    report: dict = {}
    for lv_str, lv_data in levels_data.items():
        lv = int(lv_str)
        if lv not in counts.highway:
            continue
        ref_links = lv_data["road"]["link_count"]
        ref_bg = lv_data["background"]["shape_count"]
        ref_names = lv_data["name"]["record_count"]

        g_links = counts.highway[lv]
        g_bg = counts.background[lv]
        g_places = counts.place[lv]

        def _status(g, ref, exempt):
            if exempt:
                return "exempt"
            if ref == 0:
                return "in_range" if g == 0 else "out_of_range"
            in_range = lo_ratio * ref <= g <= hi_ratio * ref
            return "in_range" if in_range else "out_of_range"

        report[lv] = {
            "link": {"generated_ways": g_links, "reference": ref_links,
                     "status": _status(g_links, ref_links, level0_link_exempt and lv == 0)},
            "background": {"generated_ways": g_bg, "reference": ref_bg,
                            "status": _status(g_bg, ref_bg, False)},
            "place": {"generated_nodes": g_places, "reference": ref_names,
                      "status": _status(g_places, ref_names, False)},
        }
    return report


def main() -> None:
    import argparse

    ap = argparse.ArgumentParser(
        description="Cheap dry-run counting mode for selection.json calibration "
                    "(no geometry, no spool -- see module docstring).")
    ap.add_argument("--pbf", default=DEFAULT_PBF)
    ap.add_argument("--selection", default=None,
                     help="path to selection.json (default: checked-in table)")
    ap.add_argument("--profile", default=str(
        Path(__file__).resolve().parent.parent / "refdata" / "profile" / "map.json"))
    ap.add_argument("--no-nodes", action="store_true",
                     help="skip the (slower) node pass; place counts report as 0")
    args = ap.parse_args()

    table = SelectionTable.load(Path(args.selection)) if args.selection else _table()
    counts = count_dry_run(table, pbf_path=args.pbf, include_nodes=not args.no_nodes)

    with open(args.profile) as f:
        profile = json.load(f)

    report = report_envelope(counts, profile)
    for lv in sorted(report.keys()):
        entry = report[lv]
        print(f"level {lv}:")
        for kind in ("link", "background", "place"):
            d = entry[kind]
            gkey = "generated_ways" if kind != "place" else "generated_nodes"
            print(f"  {kind}: generated={d[gkey]} reference={d['reference']} "
                  f"status={d['status']}")


if __name__ == "__main__":
    main()
