"""Plan 36: synthetic tests for the region-accounting tool (no reference disc)."""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import sys

import pytest

_PARSER = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PARSER))
sys.path.insert(0, str(_PARSER / 'tests' / 'fixtures' / 'harness'))
import e2_fixture  # noqa: E402
from kiwiw import alldata_writer as aw  # noqa: E402
from kiwiw.grid import ReferenceGrid  # noqa: E402

TOOL = _PARSER.parent / 'docs/plans/04-c-core-orchestration/triage/oracle_chain/region_accounting.py'
spec = importlib.util.spec_from_file_location('region_accounting', TOOL)
ra = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ra)

CELLS = [(512, 0), (513, 0), (520, 10)]


def _frames(tmp_path):
    return e2_fixture.e2_frames(tmp_path / 'e2', 0, empty=CELLS)


def _grow(frame: bytes, extra: int) -> bytes:
    """Append `extra` bytes and fix the two-byte extent marker (length in words)."""
    assert extra % 2 == 0
    out = bytearray(frame) + bytes(range(1, extra + 1))
    out[0:2] = (len(out) // 2).to_bytes(2, 'big')
    return bytes(out)


def _disc(tmp_path, name, frames):
    d = tmp_path / name
    d.mkdir()
    out = d / 'ALLDATA.KWI'
    aw.build_alldata_kwi({0: e2_fixture.level_build(d, 0, frames)}, ReferenceGrid.load(),
                         disk_title='TEST', out_path=str(out))
    return out, hashlib.sha256(out.read_bytes()).hexdigest()


def _account(tmp_path, a, b):
    out = tmp_path / f'acct-{a[0].parent.name}-{b[0].parent.name}.json'
    rc = ra.account(a[0], b[0], a[1], b[1], out, tmp_path / (out.stem + '.tsv'))
    return rc, json.loads(out.read_text())


def test_key_roundtrip():
    for k in [(0, 0, 0, ()), (0, 38, 14, (507, 6)), (12, 4095, 4095, (4094, 254, 254)), (2, 5, 7, (3,))]:
        assert ra.decode_key(ra.encode_key(*k)) == k
    with pytest.raises(ValueError):
        ra.encode_key(0, 0, 0, (1, 2, 3, 4))


def test_partition_detects_gaps_and_overlaps():
    assert ra.check_partition([(0, 10, 'a'), (10, 20, 'b')], 20)['complete']
    gap = ra.check_partition([(0, 10, 'a'), (12, 20, 'b')], 20)
    assert not gap['complete'] and gap['gap_bytes'] == 2
    ov = ra.check_partition([(0, 10, 'a'), (8, 20, 'b')], 20)
    assert not ov['complete'] and ov['overlap_count'] == 1
    tail = ra.check_partition([(0, 10, 'a')], 16)
    assert tail['gap_bytes'] == 6


def test_identical_discs_fully_accounted(tmp_path):
    f = _frames(tmp_path)
    a = _disc(tmp_path, 'a', f)
    b = _disc(tmp_path, 'b', f)
    rc, doc = _account(tmp_path, a, b)
    assert rc == 0 and doc['complete_and_accounted']
    c = doc['compare']
    assert c['unaccounted_bytes'] == 0 and c['file_size']['delta'] == 0
    assert c['frames']['payload_changed'] == 0 and c['frames']['padding_spans_changed'] == 0
    assert c['pmr']['masked_content_differs'] == 0 and c['pdmdh']['differing_bytes'] == 0
    assert doc['old']['partition']['complete'] and doc['old']['partition']['gap_bytes'] == 0
    assert doc['old']['frames_unique'] == len(CELLS)
    s = doc['old']['sizes']
    assert sum(v for k, v in s.items() if k != 'partition_gaps') == doc['old']['file_size']


@pytest.mark.parametrize('extra', [4, 40])
def test_grown_frame_named_as_payload_and_padding(tmp_path, extra):
    f = _frames(tmp_path)
    g = dict(f)
    g[(513, 0)] = _grow(f[(513, 0)], extra)
    a = _disc(tmp_path, 'a', f)
    b = _disc(tmp_path, 'b', g)
    rc, doc = _account(tmp_path, a, b)
    c = doc['compare']
    assert rc == 0 and c['unaccounted_bytes'] == 0
    assert c['frames']['payload_changed'] == 1
    assert c['frames']['payload_delta_changed_frames'] == extra
    assert c['sizes']['frame_payload']['delta'] == extra
    old_len, new_len = len(f[(513, 0)]), len(g[(513, 0)])
    alloc = lambda n: -(-n // 32) * 32  # noqa: E731
    assert c['sizes']['frame_padding']['delta'] == (alloc(new_len) - new_len) - (alloc(old_len) - old_len)
    assert c['file_size']['delta'] == sum(v['delta'] for k, v in c['sizes'].items() if k != 'partition_gaps')
    # relocation and the changed BS field never count as PMR content
    assert c['pmr']['masked_content_differs'] == 0
    assert c['pdmdh']['outside_bmt_address_fields'] == 0


def test_sha_mismatch_refused(tmp_path):
    f = _frames(tmp_path)
    a = _disc(tmp_path, 'a', f)
    with pytest.raises(SystemExit):
        ra.account(a[0], a[0], '0' * 64, a[1], tmp_path / 'x.json')
