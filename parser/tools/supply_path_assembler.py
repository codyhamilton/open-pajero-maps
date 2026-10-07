#!/usr/bin/env python3
"""Plan 50 — assemble the 10 plan-30 supply-path relations and emit cell-clipped
background records (presence parity, not geometry clone).

Pinned Geofabrik PBF ways for 338 rows; date-matched snapshot ways for the 16
member ways of r2647638 (rows 396/397/775). Overlay preferred: callers merge
emitted BackgroundShapes into a private spool; the live extract is untouched.
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
from collections import defaultdict
from pathlib import Path
from typing import Iterable, Iterator, Optional

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "parser"), str(ROOT / "parser/tools")]

from kiwiw.model import BackgroundShape  # noqa: E402
from kiwiw.mesh import CellGrid  # noqa: E402

# Ring / clip helpers — same algorithms as plan-30 disposition (presence parity).
AREA_ROLES = ("", "outer", "inner")
MAX_RELATION_VERTICES = 250_000
MAX_RELATION_MEMBERS = 12_000
SUPPLY_RELATION_IDS = (
    8426743, 8601872, 8426822, 8602593, 8426745,
    2647638, 8602093, 8602037, 80500, 8390145,
)
SNAPSHOT_WAY_RELATION = 2647638
CODE_288 = 288
TYPE_LABEL_288 = "unknown type 0x120"  # vocab catch-all; matches extract


def require(cond: bool, msg: str) -> None:
    if not cond:
        raise ValueError(msg)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def area_members(members):
    area, ignored, nested = [], [], []
    for member in members:
        if member["type"] == "w" and member["role"] in AREA_ROLES:
            area.append(member)
        elif member["type"] == "r" and member["role"] in AREA_ROLES:
            nested.append(member)
        else:
            ignored.append(member)
    return area, ignored, nested


def join_rings(members, ways, vertex_limit=MAX_RELATION_VERTICES):
    """Join by OSM node IDs. Reject branches, missing members, open rings."""
    members, _, nested = area_members(members)
    require(not nested, "nested area relation member")
    rings = []
    for role in ("outer", "inner"):
        remaining = []
        for member in members:
            require(member["type"] == "w" and member["role"] in ("", "outer", "inner"),
                    "unsupported relation member/role")
            if (member["role"] or "outer") != role:
                continue
            require(member["ref"] in ways, "missing relation member way")
            ids, coords = ways[member["ref"]]
            require(len(ids) == len(coords) >= 2, "invalid relation member geometry")
            remaining.append((list(ids), [list(p) for p in coords]))
        while remaining:
            ids, coords = remaining.pop(0)
            while ids[-1] != ids[0]:
                matches = [(i, part) for i, part in enumerate(remaining)
                           if ids[-1] in (part[0][0], part[0][-1])]
                require(len(matches) == 1, "open/branched relation ring")
                i, (more_ids, more_coords) = matches[0]
                remaining.pop(i)
                if more_ids[-1] == ids[-1]:
                    more_ids, more_coords = more_ids[::-1], more_coords[::-1]
                require(coords[-1] == more_coords[0], "inconsistent shared-node coordinates")
                ids.extend(more_ids[1:])
                coords.extend(more_coords[1:])
                require(len(ids) <= vertex_limit, "relation vertex limit")
            require(len(set(ids)) >= 3, "degenerate relation ring")
            rings.append((role, coords))
    require(any(role == "outer" for role, _ in rings), "relation has no outer ring")
    return rings


def stitch_rings(rings, vertex_limit=MAX_RELATION_VERTICES):
    """Even-odd compound ring with doubled bridges (plan-30 / production EO)."""
    outer = next(coords for role, coords in rings if role == "outer")
    anchor, result = outer[0], list(outer)
    skipped = False
    for role, ring in rings:
        if not skipped and role == "outer" and ring is outer:
            skipped = True
            continue
        result.extend([ring[0], *ring[1:], anchor])
    require(len(result) <= vertex_limit, "compound relation vertex limit")
    return result


def clip_rect(poly, x0, y0, x1, y1):
    """Sutherland-Hodgman clip (same as cell_local_2-01). poly is (x,y) pairs."""
    def run(pts, inside, inter):
        out = []
        n = len(pts)
        for i in range(n):
            a, b = pts[i], pts[(i + 1) % n]
            ia, ib = inside(a), inside(b)
            if ia:
                out.append(a)
                if not ib:
                    out.append(inter(a, b))
            elif ib:
                out.append(inter(a, b))
        return out

    def ix_(a, b):
        t = (x0 - a[0]) / (b[0] - a[0]) if b[0] != a[0] else 0.0
        return (x0, a[1] + t * (b[1] - a[1]))

    def iX(a, b):
        t = (x1 - a[0]) / (b[0] - a[0]) if b[0] != a[0] else 0.0
        return (x1, a[1] + t * (b[1] - a[1]))

    def iy_(a, b):
        t = (y0 - a[1]) / (b[1] - a[1]) if b[1] != a[1] else 0.0
        return (a[0] + t * (b[0] - a[0]), y0)

    def iY(a, b):
        t = (y1 - a[1]) / (b[1] - a[1]) if b[1] != a[1] else 0.0
        return (a[0] + t * (b[0] - a[0]), y1)

    p = list(poly)
    p = run(p, lambda a: a[0] >= x0, ix_)
    if not p:
        return []
    p = run(p, lambda a: a[0] <= x1, iX)
    if not p:
        return []
    p = run(p, lambda a: a[1] >= y0, iy_)
    if not p:
        return []
    return run(p, lambda a: a[1] <= y1, iY)


def cell_bbox_lat_lon(grid: CellGrid, ix: int, iy: int):
    a = grid.disc_lat_lo + iy * grid.cell_lat
    c = grid.disc_lon_lo + ix * grid.cell_lon
    return a, a + grid.cell_lat, c, c + grid.cell_lon


def clip_to_cell(coords_latlon, grid: CellGrid, ix: int, iy: int):
    """Clip a closed (lat,lon) ring to the cell; return (lat,lon) list or []."""
    lat_lo, lat_hi, lon_lo, lon_hi = cell_bbox_lat_lon(grid, ix, iy)
    # Antimeridian: AU cells sit in 112–155 E; shift negative lons into [0,360).
    shifted = []
    used_shift = False
    for lat, lon in coords_latlon:
        if lon < 0:
            lon = lon + 360.0
            used_shift = True
        shifted.append((lat, lon))
    if used_shift and any(abs(p[1] - q[1]) > 180 for p, q in zip(shifted, shifted[1:] + shifted[:1])):
        raise ValueError("ambiguous antimeridian after 0-360 shift")
    # clip_rect wants (x,y)=(lon,lat)
    local = clip_rect([(lon, lat) for lat, lon in shifted], lon_lo, lat_lo, lon_hi, lat_hi)
    if len(local) < 3:
        return []
    return [(lat, lon) for lon, lat in local]


def make_bg(coords_latlon) -> BackgroundShape:
    return BackgroundShape(
        shape_class=2,
        type_code=CODE_288,
        type_label=TYPE_LABEL_288,
        n_coords=len(coords_latlon),
        mult_const=1,
        underground=False,
        pen_up=False,
        coords=[(float(lat), float(lon)) for lat, lon in coords_latlon],
    )


def load_relation_members(path: Path) -> dict[int, dict]:
    raw = json.loads(path.read_text())
    return {int(k): v for k, v in raw.items()}


def load_ways_pbf_json(path: Path) -> dict[int, tuple]:
    raw = json.loads(path.read_text())
    return {int(k): (v["nodes"], v["coords"]) for k, v in raw["ways"].items()}


def load_snapshot_ways(path: Path, expected_sha: Optional[str] = None) -> dict[int, tuple]:
    text = path.read_bytes()
    digest = hashlib.sha256(text).hexdigest()
    if expected_sha is not None:
        require(digest == expected_sha, f"snapshot ways sha mismatch: {digest}")
    doc = json.loads(text)
    require(doc.get("schema") == "plan50-r2647638-missing-ways-v1", "snapshot ways schema")
    require(int(doc.get("relation_id")) == SNAPSHOT_WAY_RELATION, "snapshot relation id")
    return {int(k): (v["nodes"], v["coords"]) for k, v in doc["ways"].items()}


def assemble_coords(rid: int, members: list, ways: dict) -> list:
    area, _ignored, nested = area_members(members)
    require(not nested, "nested area relation member")
    require(len(area) <= MAX_RELATION_MEMBERS, "relation-member-limit")
    total = sum(len(ways[m["ref"]][1]) for m in area)
    require(total <= MAX_RELATION_VERTICES, "relation vertex limit")
    rings = join_rings(area, ways, MAX_RELATION_VERTICES)
    return stitch_rings(rings, MAX_RELATION_VERTICES)


def load_targets(path: Path) -> list[dict]:
    rows = json.loads(path.read_text())
    require(len(rows) == 341, f"expected 341 targets, got {len(rows)}")
    return rows


class SupplyAssembler:
    """Assembles the 10 supply relations once; clips per target cell on demand."""

    def __init__(self, members_path: Path, pbf_ways_path: Path,
                 snapshot_ways_path: Path, snapshot_sha: str,
                 targets_path: Path):
        self.members = load_relation_members(members_path)
        ways = load_ways_pbf_json(pbf_ways_path)
        snap = load_snapshot_ways(snapshot_ways_path, snapshot_sha)
        # Snapshot ways only fill holes for r2647638; never overwrite PBF.
        for wid, geom in snap.items():
            if wid not in ways:
                ways[wid] = geom
        self.ways = ways
        self.targets = load_targets(targets_path)
        self.grid = CellGrid.from_reference(0)
        self._coords: dict[int, list] = {}
        self.snapshot_sha = snapshot_sha
        self.provenance = {
            "members_path": str(members_path),
            "pbf_ways_path": str(pbf_ways_path),
            "snapshot_ways_path": str(snapshot_ways_path),
            "snapshot_ways_sha256": snapshot_sha,
            "targets_path": str(targets_path),
            "n_targets": len(self.targets),
            "n_ways": len(self.ways),
        }

    def coords_for(self, rid: int) -> list:
        if rid not in self._coords:
            doc = self.members[rid]
            self._coords[rid] = assemble_coords(rid, doc["members"], self.ways)
        return self._coords[rid]

    def emit_for_cell(self, rid: int, ix: int, iy: int) -> Optional[BackgroundShape]:
        coords = self.coords_for(rid)
        clipped = clip_to_cell(coords, self.grid, ix, iy)
        if len(clipped) < 3:
            return None
        return make_bg(clipped)

    def iter_emissions(self, rows: Optional[Iterable[dict]] = None) -> Iterator[dict]:
        for row in (rows if rows is not None else self.targets):
            rid = int(row["relation_id"])
            ix, iy = int(row["ix"]), int(row["iy"])
            bg = self.emit_for_cell(rid, ix, iy)
            yield {
                "dump_row": int(row["dump_row"]),
                "level": int(row["level"]),
                "ix": ix,
                "iy": iy,
                "code": int(row["code"]),
                "relation_id": rid,
                "present": bg is not None,
                "n_coords": 0 if bg is None else bg.n_coords,
                "background": bg,
            }

    def stratified_sample(self) -> list[dict]:
        """≥1 cell per relation, forcing rows 396/397/775 for r2647638."""
        by_rid: dict[int, list] = defaultdict(list)
        for row in self.targets:
            by_rid[int(row["relation_id"])].append(row)
        sample = []
        # Snapshot rows first
        for dr in (396, 397, 775):
            row = next(r for r in self.targets if int(r["dump_row"]) == dr)
            sample.append(row)
        for rid in SUPPLY_RELATION_IDS:
            if rid == SNAPSHOT_WAY_RELATION:
                continue
            sample.append(by_rid[rid][0])
        return sample


def production_c_probe(coords_latlon, ix: int, iy: int, scratch: Path) -> dict:
    """Replay plan-30 evaluate() via complete_repair CProbe (presence only)."""
    import importlib.util
    triage = ROOT / "docs/plans/04-c-core-orchestration/triage"
    spec = importlib.util.spec_from_file_location(
        "plan30_complete_repair", triage / "complete_repair_2-02.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    grid = CellGrid.from_reference(0)
    lat_lo, lat_hi, lon_lo, lon_hi = cell_bbox_lat_lon(grid, ix, iy)
    box = [lat_lo, lat_hi, lon_lo, lon_hi]
    # densify path not required for presence; use CProbe.run like disposition
    probe = mod.CProbe(scratch)
    lats = [p[0] for p in coords_latlon]
    lons = [p[1] for p in coords_latlon]
    # close ring if needed
    if (lats[0], lons[0]) != (lats[-1], lons[-1]):
        lats = lats + [lats[0]]
        lons = lons + [lons[0]]
    size, records = probe.run(lats, lons, 1, CODE_288, 0, box)
    return {"bytes": int(size), "records": int(records), "emits": records > 0 and size > 0}
