"""E1, the C level pre-pass (plan 03, 3C-06; DESIGN.md Contract B, "E1").

Layer (a): hand-described fixture spools in, E1's 32-byte routing rows and
additive counters out, asserted against the geometry each case is drawn
from (cell units on the level-6 grid). No Python copy of the scan exists or
is imported here (`overlap.py` is never imported: Contract B).

The real-spool check at the bottom compares E1's counter totals at the
small levels with the `overlap` block of the 3-11 G manifest (skipped when
either is absent -- both are gitignored build products)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from kiwiw import cenc, descriptor, mesh
from kiwiw.model import BackgroundShape

import boundary

REPO = Path(__file__).resolve().parents[2]
SPOOL = REPO / "output/extract_timing/spool"
MANIFEST = REPO / "output/scratch-3-11/G/manifest.json"
MASK_JSON = REPO / "parser/refdata/parcel_mask.json"

LEVEL = 6
G = mesh.CellGrid.from_reference(LEVEL)
EVERYWHERE = (0, G.nx - 1, 0, G.ny - 1)


def _ll(gx, gy):
    return (G.disc_lat_lo + gy * G.cell_lat, G.disc_lon_lo + gx * G.cell_lon)


def _shape(cls, pts):
    coords = [_ll(x, y) for x, y in pts]
    return BackgroundShape(shape_class=cls, type_code=1, type_label="", n_coords=len(coords),
                           mult_const=1, underground=False, pen_up=False, coords=coords)


def _run(tmp_path, cells, mask_rect=EVERYWHERE, window=None, ranges=((None, None),)):
    boundary.write_fixture_spool(tmp_path, {(LEVEL, ix, iy): {"backgrounds": s}
                                            for (ix, iy), s in cells.items()})
    desc = descriptor.build_for_spool(tmp_path, LEVEL, mask_rect=mask_rect, window=window)
    sp = cenc.E1Spool(tmp_path, LEVEL)
    rows, tot = [], {k: 0 for k in cenc.E1_COUNTERS}
    for lo, hi in ranges:
        r, c = cenc.e1(desc, sp, lo, hi)
        assert r.dtype == descriptor.E1_ROW_DTYPE
        rows.append(r)
        for k in tot:
            tot[k] += c[k]
    return np.concatenate(rows), tot


def _targets(rows, kind=None):
    sel = rows if kind is None else rows[rows["kind"] == kind]
    return [(int(a), int(b)) for a, b in zip(sel["tix"], sel["tiy"])]


def _counts(shared, edge, interior, skipped):
    return dict(zip(cenc.E1_COUNTERS, (shared, edge, interior, skipped)))


def test_line_into_neighbour(tmp_path):
    rows, c = _run(tmp_path, {(10, 10): [_shape(1, [(10.5, 10.5), (11.5, 10.5)])]})
    assert _targets(rows, 0) == [(11, 10)]
    assert len(rows) == 1
    r = rows[0]
    assert (r["six"], r["siy"], r["shape"], r["kind"], r["cell_off"]) == (10, 10, 0, 0, 0)
    assert c == _counts(1, 1, 0, 0)


def test_diagonal_through_corner(tmp_path):
    rows, c = _run(tmp_path, {(10, 10): [_shape(1, [(10.5, 10.5), (11.5, 11.5)])]})
    assert _targets(rows) == [(11, 10), (10, 11), (11, 11)]   # (iy, ix) order
    assert c == _counts(1, 3, 0, 0)


def test_polygon_edge_and_interior_cover(tmp_path):
    sq = [(9.25, 9.25), (12.75, 9.25), (12.75, 12.75), (9.25, 12.75)]
    rows, c = _run(tmp_path, {(10, 10): [_shape(2, sq)]})
    border = {(x, y) for x in range(9, 13) for y in range(9, 13)} - \
             {(x, y) for x in (10, 11) for y in (10, 11)}
    assert set(_targets(rows, 0)) == border
    assert _targets(rows, 1) == [(11, 10), (10, 11), (11, 11)]
    keys = [(int(y), int(x)) for x, y in zip(rows["tix"], rows["tiy"])]
    assert keys == sorted(keys)
    assert c == _counts(1, 12, 3, 0)


def test_open_line_has_no_interior(tmp_path):
    sq = [(9.25, 9.25), (12.75, 9.25), (12.75, 12.75), (9.25, 12.75), (9.25, 9.25)]
    rows, c = _run(tmp_path, {(10, 10): [_shape(1, sq)]})
    assert c == _counts(1, 12, 0, 0)


def test_shape_inside_own_cell_is_not_shared(tmp_path):
    rows, c = _run(tmp_path, {(10, 10): [_shape(2, [(10.2, 10.2), (10.8, 10.2), (10.5, 10.8)]),
                                         _shape(0, [(10.5, 10.5)])]})
    assert len(rows) == 0 and c == _counts(0, 0, 0, 0)


def test_missing_target_counts_as_skipped(tmp_path):
    rows, c = _run(tmp_path, {(10, 10): [_shape(1, [(10.5, 10.5), (11.5, 10.5)])]},
                   mask_rect=None)
    assert len(rows) == 0 and c == _counts(0, 0, 0, 1)


def test_existing_idx_cell_needs_no_mask(tmp_path):
    rows, c = _run(tmp_path, {(10, 10): [_shape(1, [(10.5, 10.5), (11.5, 10.5)])],
                              (11, 10): [_shape(0, [(11.5, 10.5)])]}, mask_rect=None)
    assert _targets(rows) == [(11, 10)] and c == _counts(1, 1, 0, 0)
    # the second cell's record follows the first in .data
    assert rows[0]["six"] == 10 and rows[0]["cell_off"] == 0


def test_window_drops_receivers_without_skipping(tmp_path):
    rows, c = _run(tmp_path, {(10, 10): [_shape(1, [(10.5, 10.5), (12.5, 10.5)])]},
                   mask_rect=None, window=(0, 10, 0, G.ny - 1))
    assert len(rows) == 0 and c == _counts(0, 0, 0, 0)
    rows, c = _run(tmp_path / "b", {(10, 10): [_shape(1, [(10.5, 10.5), (12.5, 10.5)])]},
                   window=(0, 11, 0, G.ny - 1))
    assert _targets(rows) == [(11, 10)] and c == _counts(1, 1, 0, 0)


def test_rows_ordered_by_source_cell_then_shape(tmp_path):
    cells = {(10, 20): [_shape(1, [(10.5, 20.5), (11.5, 20.5)])],
             (10, 10): [_shape(1, [(10.5, 10.5), (10.5, 11.5)]),
                        _shape(1, [(10.5, 10.5), (9.5, 10.5)])]}
    rows, c = _run(tmp_path, cells)
    got = [(int(r["siy"]), int(r["six"]), int(r["shape"]), int(r["tix"]), int(r["tiy"]))
           for r in rows]
    assert got == [(10, 10, 0, 10, 11), (10, 10, 1, 9, 10), (20, 10, 0, 11, 20)]
    assert rows[2]["cell_off"] > 0
    assert c == _counts(3, 3, 0, 0)


def test_range_split_is_additive(tmp_path):
    cells = {(10, 20): [_shape(1, [(10.5, 20.5), (11.5, 20.5)])],
             (10, 10): [_shape(2, [(9.25, 9.25), (12.75, 9.25), (12.75, 12.75)])],
             (30, 40): [_shape(1, [(30.5, 40.5), (30.5, 41.5)])]}
    whole, cw = _run(tmp_path / "a", cells)
    split, cs = _run(tmp_path / "b", cells, ranges=((None, 15), (15, 21), (21, 40), (40, None)))
    assert cw == cs
    assert whole.tobytes() == split.tobytes()
    empty, ce = _run(tmp_path / "c", cells, ranges=((11, 20),))
    assert len(empty) == 0 and ce == _counts(0, 0, 0, 0)


def test_output_growth_retries_and_one_call_per_range(tmp_path):
    sq = [(1.25, 1.25), (30.75, 1.25), (30.75, 30.75), (1.25, 30.75)]
    boundary.write_fixture_spool(tmp_path, {(LEVEL, 10, 10): {"backgrounds": [_shape(2, sq)]}})
    desc = descriptor.build_for_spool(tmp_path, LEVEL, mask_rect=EVERYWHERE)
    sp = cenc.E1Spool(tmp_path, LEVEL)
    before = cenc.e1_stats()
    rows, c = cenc.e1(desc, sp, None, None, cap_hint=1)
    after = cenc.e1_stats()
    assert len(rows) == 30 * 30 - 1
    assert c["edge_cells"] + c["interior_cells"] == 30 * 30 - 1
    assert after["ranges"] - before["ranges"] == 1
    assert after["calls"] - before["calls"] == 2        # one retry after growing
    again, c2 = cenc.e1(desc, sp, None, None)
    assert again.tobytes() == rows.tobytes() and c2 == c


def test_bad_descriptor_is_rejected(tmp_path):
    boundary.write_fixture_spool(tmp_path, {(LEVEL, 1, 1): {"backgrounds": [_shape(0, [(1.5, 1.5)])]}})
    sp = cenc.E1Spool(tmp_path, LEVEL)
    desc = bytearray(descriptor.build_for_spool(tmp_path, LEVEL))
    desc[0:1] = b"X"
    with pytest.raises(cenc.E1Error):
        cenc.e1(bytes(desc), sp, None, None)
    with pytest.raises(cenc.E1Error):
        cenc.e1(descriptor.build_for_spool(tmp_path, 8), sp, None, None)


@pytest.mark.skipif(not (SPOOL / "level_8.idx").exists() or not MANIFEST.exists(),
                    reason="extract_timing spool or 3-11 G manifest absent")
@pytest.mark.parametrize("level", (12, 10, 8, 6))
def test_real_spool_counters_equal_manifest(level):
    raw = json.loads(MASK_JSON.read_text())[str(level)]
    rect = (raw["ix_lo"], raw["ix_hi"], raw["iy_lo"], raw["iy_hi"])
    want = json.loads(MANIFEST.read_text())["overlap"][str(level)]
    desc = descriptor.build_for_spool(SPOOL, level, mask_rect=rect)
    rows, c = cenc.e1(desc, cenc.E1Spool(SPOOL, level), None, None)
    assert c == want
    assert int((rows["kind"] == 0).sum()) == want["edge_cells"]
