"""Plan 29: stale names are counted; valid content and disc placement survive."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import build_alldata
from kiwiw import cenc, mesh
from kiwiw.model import NameRecord
from kiwiw.spool import SpoolWriter, decode_columns


def name(text, lat, lon):
    return NameRecord(string_type=6, type_code=288, type_label='', priority=0,
                      vertical=False, display_scale_flag=0, text=text, lat=lat, lon=lon)


def write(path, names):
    with SpoolWriter(str(path)) as w:
        w.add(0, 0, 541, names=names)
        w.add(0, 1, 541, names=[name('neighbour', -38.727285888, 90.04)])


def test_private_guard_counts_and_keeps_columns(tmp_path):
    path = tmp_path / 'spool'
    write(path, [name('outside', -38.727285888, 77.519035766),
                 name('valid', -38.727285888, 90.01)])
    before = {p.name: p.read_bytes() for p in path.iterdir()}
    raw = cenc.E1Spool(path, 0)
    guarded = cenc.E1Spool(path, 0, guard_names=True)
    assert guarded.name_drops(None, None) == 1
    assert guarded.name_drops(542, None) == 0
    assert guarded.name_drops(541, 542) == 1
    a = decode_columns(raw.data, int(raw.offsets[0]))
    b = decode_columns(guarded.data, int(guarded.offsets[0]))
    for key in a:
        if key.startswith('s_'):
            assert b[key].tobytes() == a[key][1:].tobytes()
        elif key == 'blob_name_text':
            assert b[key].tobytes() == b'valid'
        else:
            assert b[key].tobytes() == a[key].tobytes()
    raw.close()
    guarded.close()
    assert before == {p.name: p.read_bytes() for p in path.iterdir()}


def test_build_drops_without_relocating_neighbour(tmp_path, monkeypatch, capsys):
    path = tmp_path / 'spool'
    write(path, [name('outside', -38.727285888, 77.519035766),
                 name('valid', -38.727285888, 90.01)])
    before = {p.name: p.read_bytes() for p in path.iterdir()}
    original = cenc.E1Spool
    with monkeypatch.context() as m:
        m.setattr(cenc, 'E1Spool', lambda p, lv, **kw: original(p, lv))
        build_alldata._WORKER.clear()
        old = tmp_path / 'old' / 'ALLDATA.KWI'
        assert build_alldata.run(str(path), str(old), [0], None, 'TEST') == 0
    build_alldata._WORKER.clear()
    new = tmp_path / 'new' / 'ALLDATA.KWI'
    assert build_alldata.run(str(path), str(new), [0], None, 'TEST') == 0
    manifest = json.loads((new.parent / 'manifest.json').read_text())
    assert manifest['out_of_span_names_dropped'] == {'0': 1}
    assert 'out-of-span names dropped: 1' in capsys.readouterr().out
    a, b = old.read_bytes(), new.read_bytes()
    assert len(a) == len(b)
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'docs/plans/04-c-core-orchestration/triage/name_anchor'))
    from witness_p1 import disc_cells
    oldcells = list(disc_cells(old, [(0, 541), (1, 541)]))
    newcells = list(disc_cells(new, [(0, 541), (1, 541)]))
    oldframe, newframe = oldcells[0]['frames'][0], newcells[0]['frames'][0]
    assert [n['text'] for n in newframe['names']] == ['valid']
    assert newframe['names'][0]['record_hex'] == oldframe['names'][1]['record_hex']
    assert oldframe['offset'] == newframe['offset']
    assert oldframe['length'] == newframe['length']
    assert oldcells[1] == newcells[1]
    start, end = oldframe['offset'], oldframe['offset'] + oldframe['length']
    assert a[:start] == b[:start] and a[end:] == b[end:]
    import diff_disc
    diff = diff_disc.compare(old, new)
    assert diff['confined_to_cell_0_541']
    assert diff['changed_leaf_list'] == [
        {'kind': 'frame', 'level': 0, 'cell': [0, 541], 'leaf': [928]}]
    import quantisation_roundtrip as qr
    historical = qr.roundtrip(str(old), str(path), workers=1, engine='c')
    successor = qr.roundtrip(str(new), str(path), workers=1, engine='c')
    assert historical['totals']['name_anchor']['failing'] == 1
    assert successor['totals']['name_anchor']['failing'] == 0
    assert successor['totals']['name_anchor']['checked'] == historical['totals']['name_anchor']['checked'] - 1
    assert successor['pass']
    other = bytearray(b)
    other[0] ^= 1
    new.write_bytes(other)
    assert not diff_disc.compare(old, new)['confined_to_cell_0_541']
    assert before == {p.name: p.read_bytes() for p in path.iterdir()}


@pytest.mark.parametrize('lat,lon', [(-50.001, 90), (-50, 77.5), (90, 90)])
def test_coverage_boundaries(tmp_path, lat, lon):
    path = tmp_path / 'spool'
    grid = mesh.CellGrid.from_reference(0)
    assert mesh.assign_to_parcel(lat, lon, grid) is None
    write(path, [name('outside', lat, lon)])
    sp = cenc.E1Spool(path, 0, guard_names=True)
    assert sp.name_drops(None, None) == 1
    sp.close()


def test_worker_partition_counts_once(tmp_path):
    path = tmp_path / 'spool'
    with SpoolWriter(str(path)) as w:
        for iy in (540, 541, 542):
            names = [name('valid', -50 + (iy + 0.5) * mesh.CellGrid.from_reference(0).cell_lat, 90.01)]
            if iy == 541:
                names.insert(0, name('outside', -38.727285888, 77.519035766))
            w.add(0, 0, iy, names=names)
    results = []
    for jobs in (1, 2):
        out = tmp_path / f'j{jobs}' / 'ALLDATA.KWI'
        assert build_alldata.run(str(path), str(out), [0], None, 'TEST', workers=jobs) == 0
        manifest = json.loads((out.parent / 'manifest.json').read_text())
        assert manifest['out_of_span_names_dropped'] == {'0': 1}
        results.append(out.read_bytes())
    assert results[0] == results[1]


@pytest.mark.parametrize('window', [(0, 1, 541, 2, 542), (0, 0, 542, 1, 543)])
def test_window_away_from_drop_counts_zero_without_probe(tmp_path, monkeypatch, capsys, window):
    path = tmp_path / 'spool'
    with SpoolWriter(str(path)) as w:
        w.add(0, 0, 541, names=[name('outside', -38.727285888, 77.519035766)])
        w.add(0, 1, 541, names=[name('neighbour', -38.727285888, 90.04)])
        w.add(0, 0, 542, names=[name('next row', -38.7, 90.01)])
    original_spool = cenc.E1Spool
    with monkeypatch.context() as m:
        m.setattr(cenc, 'E1Spool', lambda p, lv, **kw: original_spool(p, lv))
        build_alldata._WORKER.clear()
        old = tmp_path / 'old' / 'ALLDATA.KWI'
        assert build_alldata.run(str(path), str(old), [0], None, 'TEST', window=window) == 0
    build_alldata._WORKER.clear()
    calls = []
    original_e2 = cenc.e2

    def counted_e2(*args, **kwargs):
        calls.append(1)
        return original_e2(*args, **kwargs)

    monkeypatch.setattr(cenc, 'e2', counted_e2)
    new = tmp_path / 'new' / 'ALLDATA.KWI'
    assert build_alldata.run(str(path), str(new), [0], None, 'TEST', window=window) == 0
    manifest = json.loads((new.parent / 'manifest.json').read_text())
    assert manifest['out_of_span_names_dropped'] == {'0': 0}
    assert 'out-of-span names dropped: 1' not in capsys.readouterr().out
    assert len(calls) == 1
    assert new.read_bytes() == old.read_bytes()


def test_wiring_fixture_names_are_outside_lattice_span(tmp_path):
    from test_build_alldata import _make_multirow_spool
    path = tmp_path / 'spool'
    _make_multirow_spool(path)
    grid = mesh.CellGrid.from_reference(6)
    raw = cenc.E1Spool(path, 6)
    guarded = cenc.E1Spool(path, 6, guard_names=True)
    assert len(raw.offsets) == 9
    for offset in raw.offsets:
        cols = decode_columns(raw.data, int(offset))
        assert list(cols['s_lat']) == [-1.0] and list(cols['s_lon']) == [1.0]
        assert mesh.assign_to_parcel(-1.0, 1.0, grid) is None
    assert guarded.name_drops(None, None) == 9
    raw.close()
    guarded.close()


def test_vectorised_screen_matches_per_cell_scan(tmp_path):
    """Plan 41: the once-per-level screen gives the per-cell verdicts and bytes."""
    path = tmp_path / 'spool'
    with SpoolWriter(str(path)) as w:
        w.add(0, 0, 541, names=[name('outside', -38.727285888, 77.519035766),
                                name('valid', -38.727285888, 90.01)])
        w.add(0, 1, 541, names=[name('neighbour', -38.727285888, 90.04)])
        w.add(0, 2, 541, names=[])
        w.add(0, 3, 542, names=[name('wrap', -38.6, 90.02 + 360.0),
                                name('south', -91.0, 90.02),
                                name('ok2', -38.6, 90.03)])
    fast = cenc.E1Spool(path, 0, guard_names=True)
    slow = cenc.E1Spool(path, 0)
    slow.data = slow.data.copy()
    slow.lengths = slow.lengths.copy()
    grid = mesh.CellGrid.from_reference(0)
    for i in range(len(slow.offsets)):
        slow._guard_cell(i, grid)
    assert fast.drops.tolist() == slow.drops.tolist()
    assert cenc.E1Spool(path, 0)._name_rejects(grid).tolist() == slow.drops.tolist()
    assert sum(slow.drops) == 2
    assert bytes(fast.data) == bytes(slow.data)
    assert fast.lengths.tolist() == slow.lengths.tolist()


def test_unaligned_layout_fallback_matches_vectorised_screen(tmp_path, monkeypatch):
    """Plan 41 review F5: the per-cell fallback (layout not 8-byte aligned) gives
    the vectorised screen's drops, lengths and bytes."""
    path = tmp_path / 'spool'
    with SpoolWriter(str(path)) as w:
        w.add(0, 0, 541, names=[name('outside', -38.727285888, 77.519035766),
                                name('valid', -38.727285888, 90.01)])
        w.add(0, 1, 541, names=[])
        w.add(0, 3, 542, names=[name('wrap', -38.6, 90.02 + 360.0),
                                name('south', -91.0, 90.02)])
    fast = cenc.E1Spool(path, 0, guard_names=True)
    monkeypatch.setattr(cenc.E1Spool, '_name_rejects', lambda self, grid: None)
    slow = cenc.E1Spool(path, 0, guard_names=True)
    assert slow.drops.tolist() == fast.drops.tolist()
    assert sum(slow.drops) == 2
    assert bytes(slow.data) == bytes(fast.data)
    assert slow.lengths.tolist() == fast.lengths.tolist()
