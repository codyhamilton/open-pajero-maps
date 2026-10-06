"""Plan 36 Phase 3: synthetic tests for the 3-14 cause tools (no disc reads)."""
import csv
import importlib.util
import json
from pathlib import Path

import pytest

HOP = Path(__file__).resolve().parents[2] / 'docs/plans/04-c-core-orchestration/triage/oracle_chain/hop_3_14'


def _load(name):
    spec = importlib.util.spec_from_file_location('hop_' + name, HOP / f'{name}.py')
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


sx = _load('sections')
cc = _load('cells_causes')
kr = _load('k1_rows')


def _frame(road=b'RRRR', bg=b'BBBBBB', ext=None):
    n_entries = 4 if ext is not None else 3
    de = 36
    data = de + n_entries * 6
    body = road + bg + (ext or b'')
    buf = bytearray(data + len(body))
    buf[34:36] = (0).to_bytes(2, 'big')
    offs = [(data, len(road)), (data + len(road), len(bg)), None]
    if ext is not None:
        offs.append((data + len(road) + len(bg), len(ext)))
    for i, e in enumerate(offs):
        o = de + i * 6
        if e is None:
            buf[o:o + 6] = b'\xff\xff\xff\xff\x00\x00'
        else:
            buf[o:o + 4] = (e[0] >> 1).to_bytes(4, 'big')
            buf[o + 4:o + 6] = (e[1] >> 1).to_bytes(2, 'big')
    buf[data:] = body
    buf[0:2] = (len(buf) >> 1).to_bytes(2, 'big')
    return bytes(buf)


def test_split_sections_cover_frame():
    s = sx.split(_frame())
    assert s['road'] == b'RRRR' and s['background'] == b'BBBBBB' and s['name'] == b''
    assert s['rest'] == b'' and s['table'] == b''


def test_split_ext_table_moves_with_background():
    a, b = sx.split(_frame(ext=b'EE')), sx.split(_frame(bg=b'BBBBBBBB', ext=b'EE'))
    assert a['ext'] == b['ext'] == b'EE' and a['table'] != b['table'] and a['road'] == b['road']


def _leaf(fp, length, bg, name=10, table=None, h=None):
    hashes = {k: 'x' for k in sx.SECTIONS}
    hashes.update(h or {})
    return {'footprint': fp, 'length': length, 'sizes': {'background': bg, 'name': name},
            'hashes': hashes, 'table': table or [[0, 1], [0, 1], None]}


def test_ext_relocation_predicate():
    o = [_leaf('a', 100, 40, table=[[0, 1], [0, 1], None, [200, 8]], h={'background': 'p'})]
    n = [_leaf('a', 102, 42, table=[[0, 1], [0, 1], None, [202, 8]], h={'background': 'q'})]
    assert cc.p_ext_relocation({'old': o, 'new': n})
    n[0]['table'][3] = [204, 8]
    assert not cc.p_ext_relocation({'old': o, 'new': n})


def test_frame_ceiling_name_predicate():
    # bg shrinks by 66, names grow by 76: the new names would not fit with the old background
    o = [_leaf('a', 131044, 50000, name=1000, h={'background': 'p', 'name': 'm'})]
    n = [_leaf('a', 131054, 49934, name=1076, h={'background': 'q', 'name': 'n'})]
    assert cc.p_frame_ceiling_name({'old': o, 'new': n})
    n[0]['sizes']['name'] = 990          # same direction as bg: not a ceiling trade
    assert not cc.p_frame_ceiling_name({'old': o, 'new': n})


def test_division_ceiling_predicate():
    o = [_leaf(f'o{i}', 60000, 19000) for i in range(4)]
    n = [_leaf('n', 130696, 75364)]
    assert cc.p_division_ceiling({'old': o, 'new': n})        # coarsened as background shrank
    n[0]['sizes']['background'] = 80000
    assert not cc.p_division_ceiling({'old': o, 'new': n})    # coarse side has more background
    n = [_leaf(f'n{i}', 1000, 5000) for i in range(2)]
    assert not cc.p_division_ceiling({'old': o, 'new': n})    # not one quadtree step


def _rows(path, data):
    with open(path, 'w', newline='') as f:
        w = csv.writer(f, delimiter='\t', lineterminator='\n')
        w.writerow(['level', 'key', 'c0', 'c1', 'row', 'range', 'step'])
        w.writerows(data)


def test_k1_rows_compare_confined_and_not(tmp_path):
    cells = tmp_path / 'cells.tsv'
    cells.write_text('level\tix\tiy\n0\t5\t10\n')
    _rows(tmp_path / 'a.tsv', [[0, 'k', 0, 9, 10, 100, 50], [0, 'k', 0, 9, 11, 7, 7]])
    _rows(tmp_path / 'b.tsv', [[0, 'k', 0, 9, 10, 90, 52], [0, 'k', 0, 9, 11, 7, 7]])
    a = kr.main(['compare', '--old', str(tmp_path / 'a.tsv'), '--new', str(tmp_path / 'b.tsv'),
                 '--cells', str(cells), '--out', str(tmp_path / 'o1.json')])
    r = json.loads((tmp_path / 'o1.json').read_text())
    assert a == 0 and r['confined'] and r['whole_delta'] == {'range': -10, 'step': 2}
    _rows(tmp_path / 'c.tsv', [[0, 'k', 0, 9, 10, 90, 52], [0, 'k', 0, 9, 11, 8, 7]])
    b = kr.main(['compare', '--old', str(tmp_path / 'a.tsv'), '--new', str(tmp_path / 'c.tsv'),
                 '--cells', str(cells), '--out', str(tmp_path / 'o2.json')])
    r = json.loads((tmp_path / 'o2.json').read_text())
    assert b == 2 and not r['confined'] and r['delta_rows_without_changed_cell'][0]['row'] == 11


def test_k1_rows_compare_refuses_layout_change(tmp_path):
    cells = tmp_path / 'cells.tsv'
    cells.write_text('level\tix\tiy\n')
    _rows(tmp_path / 'a.tsv', [[0, 'k', 0, 9, 10, 1, 1]])
    _rows(tmp_path / 'b.tsv', [[0, 'k', 0, 9, 12, 1, 1]])
    with pytest.raises(SystemExit):
        kr.main(['compare', '--old', str(tmp_path / 'a.tsv'), '--new', str(tmp_path / 'b.tsv'),
                 '--cells', str(cells), '--out', str(tmp_path / 'o.json')])
