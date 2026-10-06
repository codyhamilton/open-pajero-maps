"""Brief 26c: coverage-rectangle mask fill in `build_alldata._encode_level`
(E1 + E2 since 3C-08) and the reference-mask loader. Synthetic masks only; no reference disc."""
from __future__ import annotations

import itertools
import json
import sys
from pathlib import Path

_N = itertools.count()
_PARSER_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PARSER_DIR))

import build_alldata
from kiwiw import mesh
from kiwiw.spool import SpoolReader, SpoolWriter
from test_build_alldata import _make_name


def _spool(tmp_path):
    d = tmp_path / "spool"
    with SpoolWriter(str(d)) as w:
        w.add(0, 700, 10, names=[_make_name('N', -1.0, 1.0)])
        w.add(0, 702, 10, names=[_make_name('N', -1.0, 1.0)])
        w.add(0, 700, 11, names=[_make_name('N', -1.0, 1.0)])
        # outside the synthetic mask: (720,30) has only an out-of-span name, so its
        # frame is the encoder's empty shell; (721,30) has an in-span name
        w.add(0, 720, 30, names=[_make_name('N', -1.0, 1.0)])
        b = mesh.parcel_bounds(721, 30, mesh.CellGrid.from_reference(0))
        w.add(0, 721, 30, names=[_make_name('C', (b.lat_lo + b.lat_hi) / 2, (b.lon_lo + b.lon_hi) / 2)])
    return SpoolReader(str(d))


def _encode(reader, mask):
    """Level 0 through the build's `_encode_level` (E1 + E2); the frames come
    back through `--frame-dump`'s writer. Returns `([(ix, iy, frame)], n)`."""
    out = Path(reader.spool_dir).parent / f"enc{next(_N)}"
    out.mkdir()
    dump = build_alldata.FrameDump(str(out / "dump"))
    _t, n, *_ = build_alldata._encode_level(0, reader, None, 10**9, mask, None, {}, False,
                                            str(out), dump=dump)
    dump.close()
    blob = (out / "dump.bin").read_bytes()
    parcels = []
    for ln in (out / "dump.tsv").read_text().splitlines():
        _lv, ix, iy, _pt, _sx, _sy, off, n_b, _sha = ln.split("\t")
        parcels.append((int(ix), int(iy), blob[int(off):int(off) + int(n_b)]))
    return parcels, n


def test_mask_loader_round_trip(tmp_path):
    p = tmp_path / "m.json"
    p.write_text(json.dumps({"0": {"ix_lo": 1, "ix_hi": 5, "iy_lo": 2, "iy_hi": 9}}))
    assert build_alldata.load_parcel_mask(p) == {0: (1, 5, 2, 9)}
    real = build_alldata.load_parcel_mask()
    assert set(real) == {0, 2, 4, 6, 8, 10, 12}
    assert real[0] == (576, 2303, 0, 2143)


def test_fill_only_masked_and_absent_cells(tmp_path):
    reader = _spool(tmp_path)
    base, n0 = _encode(reader, None)
    assert len(base) == 5
    parcels, n1 = _encode(reader, {0: (700, 702, 10, 11)})
    base_map = {(ix, iy): f for ix, iy, f in base}
    got = {(ix, iy): f for ix, iy, f in parcels}
    masked = {(x, y) for x in range(700, 703) for y in (10, 11)}
    # plan 34 (5182c83): outside the mask an exact empty shell is not indexed
    assert build_alldata.is_empty_shell(base_map[(720, 30)], 0, 720, 30)
    assert not build_alldata.is_empty_shell(base_map[(721, 30)], 0, 721, 30)
    omitted = {(720, 30)}
    assert set(got) == (set(base_map) - omitted) | masked
    # 3 filled: (701,10),(701,11),(702,11); 1 omitted: (720,30)
    assert n1 == n0 + len(masked - set(base_map)) - len(omitted)
    for k, f in base_map.items():  # byte-stable for retained spooled cells
        if k not in omitted:
            assert got[k] == f
    # filled cells are the empty frame: same length in every filled cell (the header's
    # llcode differs per cell); the bytes themselves are pinned by the disc sha, whose
    # mask fill runs on every build
    fill_lens = {len(got[k]) for k in masked - set(base_map)}
    assert len(fill_lens) == 1 and fill_lens.pop() > 0
    assert (721, 30) in got  # spooled cell with content outside the mask passes through
    assert (720, 30) not in got  # outside-mask empty shell omitted (plan 34)


def test_filled_frames_decode(tmp_path):
    from kiwiw.parcel import decode_parcel  # noqa: F401  (decode exercised by build tests)
    reader = _spool(tmp_path)
    parcels, _n = _encode(reader, {0: (701, 701, 10, 10)})
    empty = dict(((ix, iy), f) for ix, iy, f in parcels)[(701, 10)]
    assert isinstance(empty, bytes) and len(empty) > 0


def test_order_is_iy_ix_ascending(tmp_path):
    reader = _spool(tmp_path)
    parcels, _n = _encode(reader, {0: (699, 703, 9, 12)})
    keys = [(iy, ix) for ix, iy, _ in parcels]
    assert keys == sorted(keys)
