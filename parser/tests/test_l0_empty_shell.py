"""Plan 34: offline shell policy and index layout; no encode, K1 or disc I/O."""
import importlib.util
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import build_alldata as build
from kiwiw import alldata_writer as aw, descriptor, frame_table as ft, volume

PLAN = Path(__file__).resolve().parents[2] / 'docs/plans/04-c-core-orchestration/triage/l0_empty_slot'
PHASE1_CELLS = ((0, 541), (0, 562), (0, 563))
MASK = build.load_parcel_mask()
L0 = MASK[0]


def omit(level, idx, path, rect=None):
    return build._omit_outside_mask_shells(level, idx, path, MASK[level] if rect is None else rect)


def shell_for(level, ix, iy):
    """An encoder shell for any cell, derived from the retained (0,562) bytes."""
    n, cell, tail = build._empty_shell_header(level, ix, iy)
    raw = bytearray(retained_frames()[1][:n])
    raw[0:2] = (n // 2).to_bytes(2, 'big')
    raw[10:12] = cell
    raw[12:n] = tail
    return bytes(raw)


def witness_module():
    spec = importlib.util.spec_from_file_location('plan34_frame_test', PLAN / 'frame_witness.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def retained_frames(label='g_successor'):
    doc = json.loads((PLAN / 'witnesses' / f'{label}.json').read_text())
    offsets = (197597600, 197597920, 197598080)
    lengths = (320, 160, 160)
    return [bytes.fromhex(next(v['hex'] for v in doc['byte_pool'].values()
                              if v['offset'] == off and v['length'] == n))
            for off, n in zip(offsets, lengths)]


def index_and_spill(tmp_path, frames, cells=None):
    path = tmp_path / 'synthetic-spill.bin'
    cells = cells or PHASE1_CELLS
    idx = np.zeros(len(frames), descriptor.E2_INDEX_DTYPE)
    at = 0
    for row, raw, (ix, iy) in zip(idx, frames, cells):
        row['ix'], row['iy'], row['off'], row['len'] = ix, iy, at, len(raw)
        at += len(raw)
    path.write_bytes(b''.join(frames))
    return idx, path


def test_retained_shells_removed_and_sources_untouched(tmp_path):
    idx, path = index_and_spill(tmp_path, retained_frames())
    before = path.read_bytes(), idx.tobytes()
    assert len(omit(0, idx, path)) == 0
    assert (path.read_bytes(), idx.tobytes()) == before


def test_one_name_record_and_neighbour_unchanged(tmp_path):
    raw = retained_frames('g_historical')[0]
    idx, path = index_and_spill(tmp_path, [raw, retained_frames()[1]], [(0, 541), (1, 562)])
    result = omit(0, idx, path)
    assert result.tobytes() == idx.tobytes()
    assert path.read_bytes() == raw + retained_frames()[1]


@pytest.mark.parametrize('mutation', ['road', 'background', 'name', 'extended', 'padding', 'metadata', 'region', 'size'])
def test_any_payload_or_unknown_layout_is_preserved(tmp_path, mutation):
    raw = bytearray(retained_frames()[1])
    if mutation in ('road', 'background', 'name', 'extended'):
        k = {'road': 0, 'background': 1, 'name': 2, 'extended': 19}[mutation]
        raw[36 + k * 6:42 + k * 6] = b'\x00\x00\x00\x4e\x00\x02'
    else:
        raw[{'padding': 159, 'metadata': 14, 'region': 35, 'size': 1}[mutation]] ^= 1
    idx, path = index_and_spill(tmp_path, [raw], [(0, 562)])
    assert omit(0, idx, path).tobytes() == idx.tobytes()


@pytest.mark.parametrize('field,value', [('pt', 1), ('sx', 1), ('sy', 1)])
def test_divided_or_unknown_subcell_preserved(tmp_path, field, value):
    idx, path = index_and_spill(tmp_path, [retained_frames()[1]], [(0, 562)])
    idx[field] = value
    assert omit(0, idx, path).tobytes() == idx.tobytes()


def test_no_mask_empty_index_and_short_read(tmp_path):
    idx, path = index_and_spill(tmp_path, [retained_frames()[1]], [(0, 562)])
    assert build._omit_outside_mask_shells(0, idx, path, None) is idx
    assert omit(0, idx[:0], path).size == 0
    path.write_bytes(b'')
    with pytest.raises(RuntimeError, match='short shell spill read'):
        omit(0, idx, path)


def test_name_drop_probe_and_pad_precedes_omission(tmp_path, monkeypatch):
    """Replay the real shell/content bytes through E2's Python handoff only."""
    guarded = SimpleNamespace(name_drops=lambda *a: 1)
    original = SimpleNamespace(close=lambda: None)
    monkeypatch.setattr(build, '_e1spool', lambda *a: guarded)
    monkeypatch.setattr(build.cenc, 'E1Spool', lambda *a: original)
    monkeypatch.setattr(build.cenc, 'e2_stats', lambda: {'ranges': 0, 'c_s': 0, 'handoff_s': 0})
    shell = retained_frames()[0][:158]
    old = retained_frames('g_historical')[0]
    calls = []

    def replay(desc, spool, rows, lo, hi, fd, off):
        calls.append(spool)
        raw = shell if spool is guarded else old
        os.pwrite(fd, raw, off)
        idx = np.zeros(1, descriptor.E2_INDEX_DTYPE)
        idx['iy'], idx['off'], idx['len'] = 541, off, len(raw)
        cnt = dict.fromkeys(build.cenc.E2_COUNTERS, 0)
        cnt['frame_bytes'] = len(raw)
        return idx, np.zeros(0, descriptor.E2_DECLINED_DTYPE), cnt

    monkeypatch.setattr(build.cenc, 'e2', replay)
    with monkeypatch.context() as m:
        m.setattr(build, '_SPILL', {})
        job = ('unused', 0, b'', (541, 542), None, str(tmp_path), True, False, True, None, L0)
        spill, rec, stats, lines, bench, dump, _eo = build._e2_job(job)
        assert calls == [guarded, original]
        assert len(rec) == 0 and lines == dump == []
        assert stats['total'] == {'road': 0, 'background': 0, 'name': 0}
        assert Path(spill).read_bytes().endswith(shell + bytes(320 - len(shell)))
        for _, obj in build._SPILL.values():
            obj.close()


@pytest.mark.parametrize('neighbour', [(827, 866), (40, 562)])
def test_zero_record_cells_lead_to_absent_bmt_without_disc_write(tmp_path, monkeypatch, neighbour):
    idx, path = index_and_spill(tmp_path, retained_frames() + [retained_frames('g_historical')[0]],
                                list(PHASE1_CELLS) + [neighbour])
    idx = omit(0, idx, path)
    rec = np.zeros(len(idx), ft.FRAME_DTYPE)
    for k in ('ix', 'iy', 'pt', 'sx', 'sy', 'off', 'len'):
        rec[k] = idx[k]
    captured = {}

    def capture(lay, fixed, *args):
        captured['pd'] = volume.parse_pdmdh_full(dict(fixed)[6144])
        captured['rec'] = lay.rec
        # A tiny in-memory index fixture for the streamed diff walker. No
        # C encoder/copy helper, destination or disc file is ever opened.
        raw = bytearray(lay.total_size)
        for at, data in fixed:
            raw[at:at + len(data)] = data
        for offsets, blocks in args[0]:
            for at, block in zip(offsets, blocks):
                at = int(at)
                raw[at:at + len(block)] = block.tobytes()
        frame = retained_frames('g_historical')[0]
        at = int(lay.item_off[0])
        raw[at:at + len(frame)] = frame
        captured['raw'] = raw
        return None

    monkeypatch.setattr(aw, '_write_indexed', capture)
    aw.build_alldata_kwi(levels={0: aw.LevelBuild(0, ft.FrameTable([str(path)], rec))}, grid=build.ReferenceGrid.load(),
                         out_path='unused-synthetic-destination', disk_title='TEST')
    bs = next(b for b in captured['pd'].blocksets if b.level == 0 and b.blockset_index == 32)
    if neighbour == (827, 866):
        assert (bs.bmt_offset, bs.bmt_size) == (aw.EMPTY_BMT_OFFSET, aw.EMPTY_BMT_SIZE)
    else:
        table = next(t for t in captured['pd'].bmt_tables
                     if captured['pd'].blocksets[t.blockset_ordinal].blockset_index == 32)
        assert (table.entries[0].dsa, table.entries[0].size) == (0xffffffff, 0)
        assert table.entries[1].dsa != 0xffffffff
    assert captured['rec'].tobytes() == rec.tobytes()
    import io
    import hashlib
    mod = gate_module()
    with monkeypatch.context() as m:
        m.setattr(Path, 'open', lambda *a, **kw: io.BytesIO(captured['raw']))
        m.setattr(mod.fw, 'stamp', lambda fh: 1)
        def memory_read(fh, n, at):
            fh.seek(at)
            data = fh.read(n)
            assert len(data) == n
            return data
        m.setattr(mod.fw, 'pread', memory_read)
        rows = list(mod.frame_rows('virtual-index-fixture.bin'))
    assert rows == [(0, *neighbour, 320, hashlib.sha256(retained_frames('g_historical')[0]).hexdigest(), 0)]


def test_candidate_pin_is_checked_and_phase1_identity_stays_fixed(monkeypatch):
    mod = witness_module()
    pin = 'a' * 64
    monkeypatch.setattr(mod, 'stamp', lambda fh: 1)
    monkeypatch.setattr(mod, 'full_hash', lambda fh: pin)
    monkeypatch.setattr(mod, 'disc_rows', lambda *a: iter(()))
    monkeypatch.setattr(mod, 'reader', lambda: SimpleNamespace(__file__=str(PLAN / 'frame_witness.py')))
    doc = mod.disc_document(None, 'g_successor', 'synthetic', pin)
    assert doc['disc_sha256'] == pin
    assert doc['predecessor_sha256'] == mod.PINS['g_successor']
    with pytest.raises(ValueError, match='identity mismatch'):
        mod.validate_disc(doc, 'g_successor')
    with pytest.raises(ValueError, match='full pin mismatch'):
        mod.disc_document(None, 'g_successor', 'synthetic', 'b' * 64)
    with pytest.raises(ValueError, match='candidate pin requires'):
        mod.disc_document(None, 'r', 'synthetic', pin)


def test_candidate_cli_cannot_overwrite_phase1():
    mod = witness_module()
    with pytest.raises(SystemExit):
        mod.main(['probe', '--disc', 'g_successor', '--path', 'synthetic', '--expected-sha256', 'a' * 64,
                  '--out', str(PLAN / 'witnesses/g_successor.json')])


def test_source_polygons_all_west_of_their_target_frame():
    from kiwiw.spool import decode_columns
    doc = json.loads((PLAN / 'witnesses/spool.json').read_text())
    grid = build.mesh.CellGrid.from_reference(0)
    assert grid.disc_lon_lo == 90
    for source in doc['sources']:
        proof = next(v for v in doc['byte_pool'].values()
                     if v['offset'] == source['cell_offset'] and v['length'] == source['cell_length'])
        raw = bytes.fromhex(proof['hex'])
        import hashlib
        assert hashlib.sha256(raw).hexdigest() == source['cell_sha256']
        columns = decode_columns(raw)
        assert list(columns['b_class']) == [2]
        assert columns['c_lon'].max() < grid.disc_lon_lo
        assert source['routed_backgrounds'] == []
        assert source['counts']['n_roads'] == 0
    assert [s['counts']['n_names'] for s in doc['sources']] == [1, 0, 0]


def gate_module():
    sys.path.insert(0, str(PLAN))
    try:
        spec = importlib.util.spec_from_file_location('plan34_gates_test', PLAN / 'phase2_gates.py')
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    finally:
        sys.path.remove(str(PLAN))


def test_multiset_gate_keeps_duplicates_and_ignores_offsets():
    import sqlite3
    mod = gate_module()
    db = sqlite3.connect(':memory:')
    for table in ('old', 'new'):
        db.execute(f'CREATE TABLE {table} (level INT, ix INT, iy INT, n INT, sha TEXT, shell INT)')
    same = (0, 827, 866, 160, 'content', 0)
    shell = (0, 0, 541, 320, 'shell', 1)
    db.executemany('INSERT INTO old VALUES (?,?,?,?,?,?)', [same, same, shell])
    db.executemany('INSERT INTO new VALUES (?,?,?,?,?,?)', [same, same])
    assert list(mod.multiset_changes(db)) == [(0, 0, 541)]
    db.execute('DELETE FROM new WHERE rowid=1')
    assert list(mod.multiset_changes(db)) == [(0, 0, 541), (0, 827, 866)]
    db.close()


def test_gate_requires_wrapper_before_input_io(monkeypatch):
    mod = gate_module()
    def fail():
        raise ValueError('guard missing')
    monkeypatch.setattr(mod.fw, 'require_heavy_guard', fail)
    monkeypatch.setattr(mod, 'sha_file', lambda *a: pytest.fail('opened input before guard'))
    assert mod.main(['sha', '--path', 'never-open', '--out', 'never-write']) == 2


def test_retained_shell_matches_generic_level0_shape():
    for raw, (ix, iy) in zip(retained_frames(), PHASE1_CELLS):
        assert build.is_empty_shell(raw, 0, ix, iy)
        assert not build.is_empty_shell(raw, 0, ix + 1, iy)


def test_inside_mask_empty_shell_kept(tmp_path):
    cells = [(L0[0], L0[2]), (L0[1], L0[3]), (1000, 1000)]
    idx, path = index_and_spill(tmp_path, [shell_for(0, *c) for c in cells], cells)
    assert omit(0, idx, path).tobytes() == idx.tobytes()


@pytest.mark.parametrize('level', [0, 2, 4, 6, 8, 10])
def test_outside_mask_empty_shell_omitted_at_any_level(tmp_path, level):
    ix_lo, ix_hi, iy_lo, iy_hi = MASK[level]
    outside = [c for c in [(ix_lo - 1, iy_lo), (ix_hi + 1, iy_hi), (ix_lo, iy_hi + 1)] if c[0] >= 0]
    inside = (ix_lo, iy_lo)
    cells = outside + [inside]
    idx, path = index_and_spill(tmp_path, [shell_for(level, *c) for c in cells], cells)
    kept = omit(level, idx, path)
    assert [(int(r['ix']), int(r['iy'])) for r in kept] == [inside]


def test_level12_shell_shape_and_omission(tmp_path):
    raw = shell_for(12, 1, 0)
    assert len(raw) == 36 + 12 * 6 + 2 and build.is_empty_shell(raw, 12, 1, 0)
    assert not build.is_empty_shell(shell_for(0, 1, 0), 12, 1, 0)
    idx, path = index_and_spill(tmp_path, [raw], [(1, 0)])
    assert len(omit(12, idx, path)) == 0


def test_outside_mask_cell_with_any_record_kept(tmp_path):
    raw = retained_frames('g_historical')[0]
    idx, path = index_and_spill(tmp_path, [raw], [(0, 541)])
    assert omit(0, idx, path).tobytes() == idx.tobytes()


def test_padded_shell_omitted_but_nonzero_trailer_kept(tmp_path):
    padded = shell_for(0, 3, 700) + bytes(162)
    dirty = bytearray(padded)
    dirty[-1] = 1
    idx, path = index_and_spill(tmp_path, [padded, bytes(dirty)], [(3, 700), (3, 700)])
    kept = omit(0, idx, path)
    assert len(kept) == 1 and int(kept[0]['off']) == len(padded)


def run_gate_diff(tmp_path, monkeypatch, old_rows, new_rows, require_phase1=True):
    mod = gate_module()
    rows = {'old': old_rows, 'new': new_rows}
    monkeypatch.setattr(mod, 'sha_file', lambda path: 'pin-' + Path(path).name)
    monkeypatch.setattr(mod, 'frame_rows', lambda path: iter(rows[Path(path).name]))
    args = SimpleNamespace(old=tmp_path / 'old', new=tmp_path / 'new', old_sha='pin-old',
                           out=tmp_path / 'diff.json', require_phase1=require_phase1)
    try:
        mod.diff(args)
        error = None
    except ValueError as exc:
        error = exc
    return json.loads(args.out.read_text()), error


def phase1_shells():
    return [(0, ix, iy, 320 if iy == 541 else 160, f'shell{iy}', 1) for ix, iy in PHASE1_CELLS]


def test_gate_diff_lists_and_classifies_outside_mask_shell_removals(tmp_path, monkeypatch):
    keep = [(0, 827, 866, 160, 'content', 0), (0, 600, 10, 158, 'inside-shell', 1)]
    extra = (2, 10, 600, 158, 'l2-outside-shell', 1)
    doc, error = run_gate_diff(tmp_path, monkeypatch, keep + phase1_shells() + [extra], keep)
    assert error is None and doc['pass'] and doc['other_count'] == 0
    assert doc['removed_cells'] == [[0, 0, 541], [0, 0, 562], [0, 0, 563], [2, 10, 600]]
    assert doc['phase1_cells_removed'] is True


@pytest.mark.parametrize('case', ['inside_mask', 'not_shell', 'new_frame_added', 'content_changed', 'phase1_missing'])
def test_gate_diff_refuses_other_changes(tmp_path, monkeypatch, case):
    old = phase1_shells() + [(0, 827, 866, 160, 'content', 0)]
    new = [(0, 827, 866, 160, 'content', 0)]
    if case == 'inside_mask':
        old.append((0, 600, 10, 158, 'inside-shell', 1))
    elif case == 'not_shell':
        old.append((0, 5, 5, 160, 'outside-content', 0))
    elif case == 'new_frame_added':
        new.append((0, 0, 541, 158, 'shell541', 1))
    elif case == 'content_changed':
        new = [(0, 827, 866, 160, 'content2', 0)]
    else:
        old = old[1:]
    doc, error = run_gate_diff(tmp_path, monkeypatch, old, new)
    assert error is not None and doc['pass'] is False
    if case != 'phase1_missing':
        assert doc['other_count'] == 1
    else:
        assert doc['phase1_cells_removed'] is False


def test_gate_diff_wrong_predecessor_pin(tmp_path, monkeypatch):
    mod = gate_module()
    monkeypatch.setattr(mod, 'sha_file', lambda path: 'nope')
    args = SimpleNamespace(old=tmp_path / 'old', new=tmp_path / 'new', old_sha='pin-old',
                           out=tmp_path / 'diff.json', require_phase1=True)
    with pytest.raises(ValueError, match='predecessor'):
        mod.diff(args)


def test_r_check_requires_empty_slot_for_every_removed_cell(tmp_path, monkeypatch):
    mod = gate_module()
    diff = tmp_path / 'diff.json'
    cells = [[0, *c] for c in PHASE1_CELLS] + [[0, 3, 700]]
    diff.write_text(json.dumps({'pass': True, 'removed_cells': cells}))
    r = tmp_path / 'r.kwi'
    r.write_bytes(b'r')
    monkeypatch.setitem(mod.PROTECTED, 'r', (r, 'rpin'))
    monkeypatch.setattr(mod, 'sha_file', lambda path: 'rpin')
    status = {}
    monkeypatch.setattr(mod.fw, 'disc_rows', lambda fh, cs: iter(
        {'cell': list(c), 'status': status.get(c, 'empty_slot'), 'frames': [], 'reason': 'x'} for c in cs))
    out = tmp_path / 'r.json'
    mod.r_check(SimpleNamespace(diff=diff, out=out, require_phase1=True))
    assert json.loads(out.read_text())['pass'] and json.loads(out.read_text())['checked_l0'] == 4
    for bad in ('lookup_failed', 'resolved'):
        status[(3, 700)] = bad
        with pytest.raises(ValueError, match='R check failed'):
            mod.r_check(SimpleNamespace(diff=diff, out=out, require_phase1=True))
    status.clear()
    diff.write_text(json.dumps({'pass': True, 'removed_cells': cells + [[2, 10, 600]]}))
    with pytest.raises(ValueError, match='non-L0'):
        mod.r_check(SimpleNamespace(diff=diff, out=out, require_phase1=True))
    diff.write_text(json.dumps({'pass': True, 'removed_cells': cells[1:]}))
    with pytest.raises(ValueError, match='Phase 1'):
        mod.r_check(SimpleNamespace(diff=diff, out=out, require_phase1=True))
