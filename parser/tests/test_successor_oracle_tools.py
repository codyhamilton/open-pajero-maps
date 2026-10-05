"""Synthetic controls for plan 29's confinement and K1 comparison gates."""
import importlib.util
import json
from pathlib import Path

import pytest

PLAN = Path(__file__).resolve().parents[2] / 'docs/plans/04-c-core-orchestration/triage/name_anchor'


def module(name):
    spec = importlib.util.spec_from_file_location(name, PLAN / f'{name}.py')
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_chunk_boundary_and_size_change(tmp_path):
    diff = module('diff_disc')
    a, b = tmp_path / 'a', tmp_path / 'b'
    a.write_bytes(b'abcdefgh')
    b.write_bytes(b'abXXefghZ')
    assert diff.differing_ranges(a, b, 3) == [[2, 4], [8, 9]]
    with pytest.raises(ValueError):
        diff.differing_ranges(a, b, diff.CHUNK + 1)


def test_mapping_splits_table_frame_and_padding():
    diff = module('diff_disc')
    spans = [{'start': 0, 'end': 10, 'kind': 'PDMDH'},
             {'start': 2, 'end': 4, 'kind': 'BMT', 'level': 0},
             {'start': 10, 'end': 20, 'kind': 'frame', 'level': 0,
              'cell': [0, 541], 'leaf': [928]}]
    rows = diff.mapped_ranges([[1, 22]], spans, spans)
    assert [(r['start'], r['end'], r['old']['kind']) for r in rows] == [
        (1, 2, 'PDMDH'), (2, 4, 'BMT'), (4, 10, 'PDMDH'),
        (10, 20, 'frame'), (20, 22, 'unmapped')]


def reports():
    kinds = {'name_anchor': {'checked': 3, 'failing': 1, 'worst_error_raw': 0.4},
             'completeness': {'checked': 1800514, 'failing': 0, 'worst_error_raw': 0},
             'road_node': {'checked': 7, 'failing': 0, 'worst_error_raw': 0.4}}
    old = {'totals': kinds, 'levels': {'0': {'kinds': kinds}}, 'tolerance_raw': 0.5,
           'engine': 'c', 'failing': 1, 'pass': False}
    new = json.loads(json.dumps(old))
    for scope in (new['totals'], new['levels']['0']['kinds']):
        scope['name_anchor'].update(checked=2, failing=0)
    new.update({'failing': 0, 'pass': True})
    return old, new, {'out_of_span_names_dropped': {'0': 1}}


def test_k1_success_and_collateral_controls():
    k1 = module('compare_k1')
    old, new, manifest = reports()
    assert k1.compare(old, new, manifest)['pass']
    new['levels']['0']['kinds']['road_node']['checked'] += 1
    assert not k1.compare(old, new, manifest)['pass']
    old, new, manifest = reports()
    new['totals']['name_anchor']['failing'] = 1
    assert not k1.compare(old, new, manifest)['pass']
    old, new, manifest = reports()
    manifest['out_of_span_names_dropped']['0'] = 2
    assert not k1.compare(old, new, manifest)['pass']
