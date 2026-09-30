"""Fixture frames for the harness and writer tests, produced through E2.

Plan 03 3C-10 (Contract T, "Current exposure"): tests that need Map Frame
bytes get them from the C build kernel (E1 then E2), fed a fixture spool
written with `boundary.write_fixture_spool`. Nothing here encodes a frame or
computes an expected value: it only drives the boundary (spool -> descriptor
-> E1 -> E2) for a handful of cells and returns the frame bytes E2 wrote.
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

import numpy as np

_PARSER = Path(__file__).resolve().parents[3]
for _p in (_PARSER, _PARSER / "tests"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import boundary  # noqa: E402
import build_alldata  # noqa: E402
from kiwiw import cenc, descriptor, mesh  # noqa: E402
from kiwiw.model import NameRecord  # noqa: E402


def cell_bounds(level: int, ix: int, iy: int):
    """The real level grid's bounds of cell (ix, iy), carrying the undivided
    frame's coordinate range (what `decode_frame` needs)."""
    return mesh.frame_bounds(ix, iy, mesh.CellGrid.from_reference(level))


def _anchor_record(level: int, ix: int, iy: int) -> NameRecord:
    b = mesh.parcel_bounds(ix, iy, mesh.CellGrid.from_reference(level))
    return NameRecord(string_type=5, type_code=0x210, type_label="", priority=0,
                      vertical=False, display_scale_flag=0, text="ANCHOR",
                      lat=(b.lat_lo + b.lat_hi) / 2, lon=(b.lon_lo + b.lon_hi) / 2,
                      angle_deg=0, angle_flags=0)


def e2_frames(work_dir, level: int, cells: dict | None = None,
              empty=()) -> dict[tuple[int, int], bytes]:
    """Whole-cell Map Frames E2 emits at `level`, keyed `(ix, iy)`.

    `cells` maps `(ix, iy)` to a spool content dict (`"roads"`,
    `"backgrounds"`, `"names"`; see `boundary.write_fixture_spool`); `empty`
    lists further cells that hold no content (E2's mask-filled empty frames).
    The spool needs at least one item at the level, so an anchor name is
    written at a cell outside the request (the level's last cell, else its
    first); it is not in the returned frames. On a level with one cell the
    anchor is that cell's content.
    """
    cells = dict(cells or {})
    want = set(cells) | {tuple(c) for c in empty}
    g = mesh.CellGrid.from_reference(level)
    anchor = next((c for c in ((g.nx - 1, g.ny - 1), (0, 0)) if c not in want), (0, 0))
    spool = Path(work_dir) / f"spool{level}"
    spool_cells = {(level, ix, iy): dict(content) for (ix, iy), content in cells.items()}
    slot = spool_cells.setdefault((level, *anchor), {})
    slot["names"] = list(slot.get("names") or []) + [_anchor_record(level, *anchor)]
    boundary.write_fixture_spool(spool, spool_cells)

    xs = [c[0] for c in want]
    ys = [c[1] for c in want]
    window = (min(xs), max(xs), min(ys), max(ys))
    budgets = build_alldata._load_level_kind_budgets().get(level) or {}
    ex = np.array([c[0] for c in want | {anchor}], np.int32)
    ey = np.array([c[1] for c in want | {anchor}], np.int32)
    desc = descriptor.build(
        level, ex, ey, window=window,
        threshold=build_alldata._load_level_thresholds()[level], name_halo=False,
        kind_limits={"road": budgets.get("road"), "bg": budgets.get("background"),
                     "name": budgets.get("name")})
    sp = cenc.E1Spool(spool, level)
    try:
        rows, _ = cenc.e1(desc, sp, None, None)
        rows = rows[np.lexsort((rows["tix"], rows["tiy"]))]
        out = Path(work_dir) / f"frames{level}.bin"
        fd = os.open(out, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)
        try:
            index, declined, _cnt = cenc.e2(desc, sp, rows, None, None, fd, 0)
        finally:
            os.close(fd)
    finally:
        sp.close()
    assert len(declined) == 0, "E2 declined a fixture cell"
    blob = out.read_bytes()
    frames = {}
    for r in index:
        assert int(r["pt"]) == 0, "fixture cell was divided; use a smaller fixture"
        frames[(int(r["ix"]), int(r["iy"]))] = blob[int(r["off"]):int(r["off"]) + int(r["len"])]
    return {c: frames[c] for c in want}


def alldata_bytes(work_dir, level: int, cells: dict | None = None, empty=(),
                  disk_title: str = "TEST") -> bytes:
    """A single-level `ALLDATA.KWI` on the real reference grid holding the
    frames E2 emits for `cells`/`empty` (see `e2_frames`), assembled by
    `alldata_writer.build_alldata_kwi` (the only assembler)."""
    from kiwiw import alldata_writer as aw
    from kiwiw.grid import ReferenceGrid
    frames = e2_frames(work_dir, level, cells, empty)
    parcels = [(ix, iy, frames[(ix, iy)]) for (ix, iy) in sorted(frames, key=lambda c: (c[1], c[0]))]
    return aw.build_alldata_kwi({level: aw.LevelBuild(level=level, parcels=parcels)},
                                ReferenceGrid.load(), disk_title=disk_title)
