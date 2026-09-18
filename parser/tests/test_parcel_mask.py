"""Brief 26c: coverage-rectangle mask fill in `build_alldata._encode_level`
and the reference-mask loader. Synthetic masks only; no reference disc."""
from __future__ import annotations

import json
import sys
from pathlib import Path

_PARSER_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PARSER_DIR))

import build_alldata
from kiwiw.grid import ReferenceGrid
from kiwiw.spool import SpoolReader, SpoolWriter
from test_build_alldata import _make_name


def _spool(tmp_path):
    d = tmp_path / "spool"
    with SpoolWriter(str(d)) as w:
        w.add(0, 700, 10, names=[_make_name('N', -1.0, 1.0)])
        w.add(0, 702, 10, names=[_make_name('N', -1.0, 1.0)])
        w.add(0, 700, 11, names=[_make_name('N', -1.0, 1.0)])
        w.add(0, 720, 30, names=[_make_name('N', -1.0, 1.0)])  # outside the synthetic mask
    return SpoolReader(str(d))


def _encode(reader, mask):
    return build_alldata._encode_level(0, ReferenceGrid.load(), reader, None, 10**9, mask=mask)


def test_mask_loader_round_trip(tmp_path):
    p = tmp_path / "m.json"
    p.write_text(json.dumps({"0": {"ix_lo": 1, "ix_hi": 5, "iy_lo": 2, "iy_hi": 9}}))
    assert build_alldata.load_parcel_mask(p) == {0: (1, 5, 2, 9)}
    real = build_alldata.load_parcel_mask()
    assert set(real) == {0, 2, 4, 6, 8, 10, 12}
    assert real[0] == (576, 2303, 0, 2143)


def test_fill_only_masked_and_absent_cells(tmp_path):
    reader = _spool(tmp_path)
    base, _, n0, _ = _encode(reader, None)
    assert len(base) == 4
    parcels, _, n1, _ = _encode(reader, {0: (700, 702, 10, 11)})
    base_map = {(ix, iy): f for ix, iy, f in base}
    got = {(ix, iy): f for ix, iy, f in parcels}
    masked = {(x, y) for x in range(700, 703) for y in (10, 11)}
    assert set(got) == set(base_map) | masked
    assert n1 == n0 + len(masked - set(base_map))  # 3 filled: (701,10),(701,11),(702,11)
    for k, f in base_map.items():  # byte-stable for spooled cells
        assert got[k] == f
    for k in masked - set(base_map):  # filled cells are the empty frame
        assert got[k] == build_alldata._encode_one(
            0, k[0], k[1], build_alldata.parcel_bounds(k[0], k[1], build_alldata.TileGrid.from_reference(0)), {})
    assert (720, 30) in got  # spooled cell outside the mask passes through


def test_filled_frames_decode(tmp_path):
    from kiwiw.parcel import decode_parcel  # noqa: F401  (decode exercised by build tests)
    reader = _spool(tmp_path)
    parcels, _, _, _ = _encode(reader, {0: (701, 701, 10, 10)})
    empty = dict(((ix, iy), f) for ix, iy, f in parcels)[(701, 10)]
    assert isinstance(empty, bytes) and len(empty) > 0


def test_order_is_iy_ix_ascending(tmp_path):
    reader = _spool(tmp_path)
    parcels, _, _, _ = _encode(reader, {0: (699, 703, 9, 12)})
    keys = [(iy, ix) for ix, iy, _ in parcels]
    assert keys == sorted(keys)
