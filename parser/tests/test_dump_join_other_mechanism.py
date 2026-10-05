"""Small byte-exact fixtures for the completeness byte-145 adapter."""
import csv
import hashlib
import json
import re
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'parser/tools'))
import dump_join as J


# Original 144-byte dump contract; fixtures must work without saved scratch.
BASE_FIELDS = [{'name': name, 'type': typ} for name, typ in [
    ('lat', 'f64'), ('lon', 'f64'), ('err', 'f64'),
    ('ix', 'i32'), ('iy', 'i32'), ('vx', 'i32'), ('vy', 'i32'),
    ('reason', 'i32'), ('code', 'i32'),
    *[(f'p{i}', 'u16') for i in range(7)],
    ('depth', 'u8'), ('kind', 'u8'), ('level', 'u8'),
    ('shape', 'i32'), ('vert', 'i32'), ('onb', 'u8'),
    ('d_any', 'f64'), ('any_type', 'i32'),
    ('in_eo_same', 'u8'), ('in_wn_same', 'u8'), ('in_eo_any', 'u8'),
    ('src_ix', 'i32'), ('src_iy', 'i32'), ('src_rec', 'i32'),
    ('src_tall', 'u8'), ('src_nv', 'i32'), ('src_maxseg', 'f64'),
    ('d_src', 'f64'), ('dcls', 'i32'), ('dnv', 'i32'),
]]


@pytest.fixture
def source(tmp_path):
    fields = BASE_FIELDS
    dt = np.dtype([(f['name'], J.TS[f['type']]) for f in fields], align=True)
    src = tmp_path / 'src'
    src.mkdir()
    # Nonzero padding and NaN payload bits must survive, not just named values.
    raw = np.arange(5 * 144, dtype='u1').reshape(5, 144)
    rows = np.frombuffer(raw, dt)
    for i, row in enumerate(rows):
        for k in (*J.GROUP, 'vert'):
            row[k] = 0
        row['ix'], row['shape'], row['vert'] = 20, -1, i
    (src / 'completeness.bin').write_bytes(raw.tobytes())
    man = {'fields': fields, 'row_size': 144, 'kinds': {
        'completeness': {'file': 'completeness.bin', 'rows': 5, 'row_size': 144, 'fields': fields}}}
    (src / 'dump_manifest.json').write_text(json.dumps(man))
    side = tmp_path / 'side.tsv'
    with side.open('w') as fh:
        w = csv.DictWriter(fh, fieldnames=[*J.GROUP, 'vert', 'dump_row', 'other_mechanism'], delimiter='\t')
        w.writeheader()
        for i in reversed(range(5)):
            w.writerow({**{k: int(rows[i][k]) for k in (*J.GROUP, 'vert')},
                        'dump_row': i, 'other_mechanism': [0, 4, 5, 7, 8][i]})
    return src, side, raw.copy(), hashlib.sha256(raw).hexdigest()


@pytest.mark.parametrize('window', [1, 2, 25])
def test_byte145_full_key_and_raw_preservation(source, tmp_path, window):
    src, side, raw, sha = source
    dst = tmp_path / 'dst'
    assert J.main(['--mode', 'other_mechanism', '--src', str(src), '--side', str(side),
                   '--dst', str(dst), '--source-sha256', sha, '--window-rows', str(window)]) == 0
    got = np.frombuffer((dst / 'completeness.bin').read_bytes(), 'u1').reshape(-1, 152)
    assert np.array_equal(got[:, :144], raw)
    assert got[:, 145].tolist() == [0, 4, 5, 7, 8]
    assert not got[:, 144].any() and not got[:, 146:].any()
    man = json.loads((dst / 'dump_manifest.json').read_text())
    dt = np.dtype([(f['name'], J.TS[f['type']]) for f in man['fields']], align=True)
    assert dt.fields['other_mechanism'][1] == 145
    assert man['row_size'] == 152 and man['kinds']['completeness']['rows'] == 5
    assert man['extension_other_mechanism']['original_144_bytes_verified']


def test_noncontiguous_window(source, tmp_path):
    src, side, raw, sha = source
    with side.open() as fh:
        selected = [r for r in csv.DictReader(fh, delimiter='\t') if int(r['dump_row']) in (1, 3)]
    with side.open('w') as fh:
        w = csv.DictWriter(fh, fieldnames=selected[0].keys(), delimiter='\t')
        w.writeheader()
        w.writerows(selected)
    J.extend_other_mechanism(src, side, tmp_path / 'dst', 1, source_sha256=sha, keys=[1, 3])
    got = np.frombuffer((tmp_path / 'dst/completeness.bin').read_bytes(), 'u1').reshape(-1, 152)
    assert np.array_equal(got[:, :144], raw[[1, 3]])
    assert got[:, 145].tolist() == [4, 7]
    man = json.loads((tmp_path / 'dst/dump_manifest.json').read_text())
    assert man['extension_other_mechanism']['source_dump_rows'] == [1, 3]


@pytest.mark.parametrize('bad', ['hash', 'key', 'missing', 'duplicate', 'code', 'self'])
def test_refuses_invalid_input_before_writing(source, tmp_path, bad):
    src, side, raw, sha = source
    with side.open() as fh:
        rows = list(csv.DictReader(fh, delimiter='\t'))
    if bad == 'hash':
        sha = '0' * 64
    elif bad == 'key':
        rows[0]['vert'] = '42'
    elif bad == 'missing':
        rows.pop()
    elif bad == 'duplicate':
        rows.append(rows[0])
    elif bad == 'code':
        rows[0]['other_mechanism'] = '99'
    with side.open('w') as fh:
        w = csv.DictWriter(fh, fieldnames=rows[0].keys(), delimiter='\t')
        w.writeheader()
        w.writerows(rows)
    dst = src if bad == 'self' else tmp_path / 'dst'
    with pytest.raises(ValueError):
        J.extend_other_mechanism(src, side, dst, 2, source_sha256=sha)
    assert (src / 'completeness.bin').read_bytes() == raw.tobytes()
    if dst != src:
        assert not dst.exists()


@pytest.mark.parametrize('target,input_name', [
    ('completeness.bin', 'completeness.bin'),
    ('dump_manifest.json', 'dump_manifest.json'),
    ('completeness.bin', 'side'),
])
def test_refuses_hardlinked_inputs_before_writing(source, tmp_path, target, input_name):
    src, side, raw, sha = source
    protected = [src / 'completeness.bin', src / 'dump_manifest.json', side]
    before = {p: p.read_bytes() for p in protected}
    dst = tmp_path / 'dst'
    dst.mkdir()
    (dst / target).hardlink_to(side if input_name == 'side' else src / input_name)
    with pytest.raises(ValueError, match='aliases an input'):
        J.extend_other_mechanism(src, side, dst, 2, source_sha256=sha)
    assert all(p.read_bytes() == before[p] for p in protected)


@pytest.fixture(scope='module')
def producer():
    import importlib.util
    path = ROOT / 'docs/plans/28-phase1-per-rule-classify-recovery/triage/completeness_mechanism.py'
    spec = importlib.util.spec_from_file_location('p28_fixture', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_exact_topology_contacts_and_crossings(producer):
    square = [(0., 0.), (4., 0.), (4., 4.), (0., 4.)]
    assert producer.ring_audit(square)['simple']
    crossing = [(0., 0.), (4., 4.), (0., 4.), (4., 0.)]
    audit = producer.ring_audit(crossing)
    assert audit['crossings'] == [(0, 2)] and not audit['simple']
    touching = square + [(0., 0.), (-4., 0.), (-4., -4.), (0., -4.)]
    assert not producer.ring_audit(touching)['simple']
    overlap = [(0., 0.), (4., 0.), (2., 0.), (2., 4.), (0., 4.)]
    assert not producer.ring_audit(overlap)['simple']


def test_degenerate_and_collapsing_predicates(producer):
    class EmptyProbe:
        def run(self, *args):
            return 0, 0
    row = {'level': 0, 'ix': 0, 'iy': 0, 'code': 288, 'dump_row': 0}
    lat = producer.qr.Lattice(0)
    def witness(coords):
        x, y = np.asarray(coords).T
        return {'raw_coords': coords, 'ncoord': len(coords),
                'bbox_raw': [x.min(), x.max(), y.min(), y.max()], 'shape_ref': 'fixture',
                'mc': 1, 'flags': 0, 'branches': ['b'], 'c_original_records': 0, 'faces': []}
    # One-cell rings do not get branch b. Extend past a cell edge to demand it.
    degenerate = [(10., 10.), (10., 5000.), (10., 3000.), (10., 10.)]
    result = producer.predicate_demander(witness(degenerate), row, lat, EmptyProbe(), {})
    assert result['predicates'] == {'4': True, '5': False, '7': False}
    sliver = [(10., 10.), (10.1, 5000.), (10.2, 10.), (10., 10.)]
    result = producer.predicate_demander(witness(sliver), row, lat, EmptyProbe(), {})
    assert result['predicates'] == {'4': False, '5': True, '7': False}


def test_projection_keeps_exact_rule_objects(producer, tmp_path):
    producer.project(tmp_path)
    hashes = json.loads((tmp_path / 'projection_hashes.json').read_text())
    target = (tmp_path / 'rules_completeness_projection.json').read_text()
    source = (producer.OLD / 'rules_other.json').read_text()
    decoder = json.JSONDecoder()
    for document in (source, target):
        for match in re.finditer(r'\{\s*"id"', document):
            obj, end = decoder.raw_decode(document, match.start())
            if obj['kind'] == 'completeness':
                raw = document[match.start():end]
                assert hashlib.sha256(raw.encode()).hexdigest() == hashes['rule_object_sha256'][obj['id']]
    assert json.loads(target)['rules'] == producer.rule_source()[1]


def test_all_demanders_first_match_and_multi_match(producer):
    _, rules = producer.rule_source()
    def w(*codes):
        return {'predicates': {str(c): c in codes for c in (4, 5, 7)}}
    assert producer.choose_mechanism([w(4), w(5)], {'predicate_8': False}, rules)[0] == 0
    code, matches, _ = producer.choose_mechanism([w(5, 7), w(5, 7)], {'predicate_8': False}, rules)
    assert code == 7 and [r['id'] for r in matches] == ['O04', 'O05']
    assert producer.choose_mechanism([w()], {'predicate_8': True}, rules)[0] == 8
    with pytest.raises(ValueError, match='no demanders'):
        producer.choose_mechanism([], {'predicate_8': False}, rules)
