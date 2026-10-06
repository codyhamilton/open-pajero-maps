"""Synthetic oracle-chain controls; no real disc or spool is read."""
import csv
import importlib.util
import json
from pathlib import Path
import struct
import sqlite3
from types import SimpleNamespace

import pytest

PLAN = Path(__file__).resolve().parents[2] / 'docs/plans/04-c-core-orchestration/triage/oracle_chain'
spec = importlib.util.spec_from_file_location('oracle_chain', PLAN / 'oracle_chain.py')
chain = importlib.util.module_from_spec(spec)
spec.loader.exec_module(chain)


def image(path, frames, relocation=0, divided=False, children=(b'childA', b'childB')):
    """Handwritten minimal volume, independent of the production assembler."""
    data = bytearray(6144 + relocation)

    def put(offset, fmt, *values):
        struct.pack_into('>' + fmt, data, offset, *values)

    def dsa(offset):
        assert offset % 32 == 0
        return ((offset // 2048) << 8) | ((offset % 2048) // 32)

    put(472, 'HH', 32, 2048)
    put(2048, 'IH', dsa(4096), 4)
    # PDMDH: one level, one blockset, one block, two base cells.
    put(4096, 'H', 15)
    put(4096 + 20, 'HHHHH', 20, 10, 3, 1, 1)
    lm = 4096 + 30
    data[lm + 29] = 1  # two normal parcels in longitude
    data[lm + 31] = 1  # two divided children in longitude
    put(lm + 36, 'HH', 35, 0)
    put(4096 + 70, 'HII', 0, 40, 3)
    put(4096 + 80, 'IH', dsa(5120), 2)
    for i, payload in enumerate(frames):
        if payload is None:
            put(5124 + i * 6, 'IH', 0xFFFFFFFF, 0)
            continue
        pos = 5504 + i * 32 + relocation
        put(5124 + i * 6, 'IH', dsa(pos), 1)
        put(pos, 'H', 4)
        data[pos + 2:pos + 8] = payload
    if divided:
        # Root cell 0 contains a two-leaf subrecord at block-relative 16.
        put(5124, 'IH', 8, 0)
        put(5136, 'H', 1 << 8)
        for i in range(2):
            pos = 5568 + i * 32 + relocation
            put(5140 + i * 6, 'IH', dsa(pos), 1)
            put(pos, 'H', 4)
            data[pos + 2:pos + 8] = children[i]
    path.write_bytes(data)
    return path


def measure(tmp_path, old, new, stem='diff'):
    return chain.diff(old, new, chain.sha(old), chain.sha(new),
                      tmp_path / (stem + '.json'), tmp_path / (stem + '.tsv'),
                      tmp_path / (stem + '-work'))


def test_relocated_frames_compare_by_cell_not_offset(tmp_path):
    old = image(tmp_path/'old.bin', [b'AAAAAA', b'BBBBBB'])
    new = image(tmp_path/'new.bin', [b'AAAAAA', b'CCCCCC'], relocation=64)
    result = measure(tmp_path, old, new)
    assert result['old_size'] != result['new_size']
    assert result['counts'] == {'changed':1, 'added':0, 'removed':0}
    assert result['counts_by_level'] == {'0': {'changed':1}}
    assert result['protected_unchanged']
    with Path(result['cells']['path']).open() as f:
        rows = list(csv.DictReader(f, delimiter='\t'))
    assert [(r['level'],r['ix'],r['iy']) for r in rows] == [('0','1','0')]
    assert result['unexplained_count'] == 1
    # Publish must validate the list, not just trust the summary.
    row = chain.measured_row(tmp_path/'diff.json', chain.sha(old), chain.sha(new), {})
    assert row['changed_count'] == 1


def test_relocation_and_padding_alone_leave_cell_set_empty(tmp_path):
    old = image(tmp_path/'old.bin', [b'AAAAAA', b'BBBBBB'])
    new = image(tmp_path/'new.bin', [b'AAAAAA', b'BBBBBB'], relocation=64)
    data = bytearray(new.read_bytes())
    data[5540] = 99  # unreachable padding
    new.write_bytes(data)
    result = measure(tmp_path, old, new)
    assert result['counts'] == {'changed':0, 'added':0, 'removed':0}
    assert 'outside' in result['residuals'][1]


def test_divided_children_map_to_containing_base_cell(tmp_path):
    path = image(tmp_path/'divided.bin', [b'AAAAAA', b'BBBBBB'], divided=True)
    frames = list(chain.iter_frames(path))
    assert [(r[1],r[2],r[5]) for r in frames] == [(0,0,'0.0'),(0,0,'0.1'),(1,0,'1')]


def test_added_removed_cells_are_not_lost(tmp_path):
    old = image(tmp_path/'old.bin', [b'AAAAAA', None])
    new = image(tmp_path/'new.bin', [None, b'BBBBBB'])
    result = measure(tmp_path, old, new)
    assert result['counts'] == {'changed':0,'added':1,'removed':1}
    assert result['unexplained_count'] == 2


def test_integrated_root_and_sparse_alias_membership(tmp_path):
    from kiwiw.parcel_mgmt import parse_parcel_mgmt_record
    lm = SimpleNamespace(n_parcels_lng=[3,1,0,0], n_parcels_lat=[0,0,0,0])
    buf = struct.pack('>HHIHIH', 1<<8, 0, 100, 1, 100, 1)
    root = parse_parcel_mgmt_record(buf, lm)
    assert [(x,y) for x,y,_,_ in chain.tree_leaves(root,lm)] == [(0,0),(2,0)]
    # Equal frame addresses retain two occupied slot identities.
    assert len(list(chain.tree_leaves(root,lm))) == 2


def test_cell_signatures_use_frame_multisets_across_levels():
    with sqlite3.connect(':memory:') as db:
        db.execute('CREATE TABLE frames (side TEXT,level INTEGER,ix INTEGER,iy INTEGER,length INTEGER,hash TEXT)')
        db.executemany('INSERT INTO frames VALUES (?,?,?,?,?,?)', [
            ('old',0,4,5,8,'a'),('old',0,4,5,6,'b'),
            ('new',0,4,5,6,'b'),('new',0,4,5,8,'a'),
            ('old',2,0,1,8,'c'),('new',2,0,1,8,'d'),
            ('old',6,0,0,8,'e'),('new',8,0,0,8,'f')])
        changes = list(chain.changed_cells(chain.cell_signatures(db,'old'),chain.cell_signatures(db,'new')))
    assert [(key,status) for key,status,_,_ in changes] == [
        ((2,0,1),'changed'),((6,0,0),'removed'),((8,0,0),'added')]


def test_sha_mismatch_and_output_reuse_fail_closed(tmp_path):
    old = image(tmp_path/'old.bin', [b'AAAAAA', None])
    new = image(tmp_path/'new.bin', [b'BBBBBB', None])
    with pytest.raises(ValueError, match='SHA mismatch'):
        chain.diff(old,new,'0'*64,chain.sha(new),tmp_path/'x.json',tmp_path/'x.tsv',tmp_path/'work')
    assert not (tmp_path/'work').exists()
    measure(tmp_path,old,new)
    with pytest.raises(ValueError, match='already exists'):
        measure(tmp_path,old,new)


def test_protected_rehash_detects_midrun_mutation(tmp_path, monkeypatch):
    old = image(tmp_path/'old.bin', [b'AAAAAA', None])
    new = image(tmp_path/'new.bin', [b'BBBBBB', None])
    real = chain.iter_frames

    def mutate(path):
        yield from real(path)
        if path == new:
            with new.open('ab') as f:
                f.write(b'X')

    monkeypatch.setattr(chain,'iter_frames',mutate)
    with pytest.raises(ValueError, match='changed during'):
        measure(tmp_path,old,new)
    assert not (tmp_path/'diff.json').exists()


def test_bad_frame_length_is_disclosed(tmp_path):
    p = image(tmp_path/'a.bin',[b'AAAAAA',None])
    data = bytearray(p.read_bytes())
    data[5504:5506] = b'\xff\xff'
    p.write_bytes(data)
    frame = next(chain.iter_frames(p))
    assert frame[3] == 32 and frame[7] is True


def test_bounded_reader_rejects_short_or_oversized_reads(tmp_path):
    path = tmp_path/'small.bin'
    path.write_bytes(b'1234')
    with path.open('rb') as f:
        with pytest.raises(ValueError, match='bound'):
            chain.read_exact(f,0,chain.CHUNK+1)
        with pytest.raises(ValueError, match='short'):
            chain.read_exact(f,1,4)


def test_list_tampering_and_wrong_hop_rejected(tmp_path):
    old = image(tmp_path/'a.bin',[b'AAAAAA',None])
    new = image(tmp_path/'b.bin',[b'BBBBBB',None])
    m = measure(tmp_path,old,new)
    with pytest.raises(ValueError, match='another hop'):
        chain.measured_row(tmp_path/'diff.json','0'*64,chain.sha(new),{})
    with Path(m['cells']['path']).open('a') as f:
        f.write('0\t5\t0\tchanged\t8\t8\ta\tb\t1\t1\n')
    with pytest.raises(ValueError, match='SHA mismatch'):
        chain.measured_row(tmp_path/'diff.json',chain.sha(old),chain.sha(new),{})


def test_retained_list_verification_and_missing_gate_publication(tmp_path,monkeypatch):
    scratch = tmp_path/'scratch'
    scratch.mkdir()
    data = ''.join(f'0:{i}:0\n' for i in range(37)).encode()
    (scratch/'Gnew.diff_cells.txt').write_bytes(data)
    (scratch/'Gnew.expected37.txt').write_bytes(data)
    monkeypatch.setattr(chain,'LIST37_SHA',chain.sha(scratch/'Gnew.diff_cells.txt'))
    chain.write_json(scratch/'Gnew.scan.json',{'dup_class_elems':[[[0,i,0],[]] for i in range(37)],
                                            'multi_unit_elems':41,'mism':[],'max_unit_decl':4095})
    # The synthetic publish uses synthetic signing records and witness too.
    record = tmp_path/'record.md'
    record.write_text(chain.P0+'\n'+chain.P1+'\n')
    monkeypatch.setattr(chain,'SIGN_RECORD',record)
    monkeypatch.setattr(chain,'PLAN29_RECORD',record)
    anchor = tmp_path/'anchor'
    monkeypatch.setattr(chain,'NAME_ANCHOR',anchor)
    target = {'kind':'frame','level':0,'cell':[0,541],'leaf':[928]}
    chain.write_json(anchor/'witnesses/successor_diff.json',{
        'old_sha256':chain.AU2,'new_sha256':chain.AU3,'old_size':200,'new_size':200,
        'changed_leaf_list':[target],'confined_to_cell_0_541':True,'changed_bytes':146,
        'confinement_rule':'synthetic','changed_ranges':[{'start':0,'end':146,'old':target,'new':target}]})
    result = chain.publish(scratch,tmp_path/'published')
    assert not result['phase3_closed']
    assert result['hops'][0]['changed_count'] == 37
    assert result['hops'][1]['changed_count'] is None
    assert result['hops'][1]['unexplained_count'] is None
    assert result['hops'][1]['recorded_changed_count'] == 246123
    assert result['hops'][3]['changed_leaf_count'] == 1
    assert len(result['hops']) == 6
    (scratch/'Gnew.expected37.txt').write_text('0:1:2\n')
    with pytest.raises(ValueError, match='list SHA mismatch'):
        chain.retained37(scratch)


@pytest.mark.parametrize('mutation', ['side','overlap','total','hop'])
def test_successor_confinement_negatives(tmp_path,mutation):
    target = {'kind':'frame','level':0,'cell':[0,541],'leaf':[928]}
    w = {'old_sha256':chain.AU2,'new_sha256':chain.AU3,'old_size':200,'new_size':200,
         'changed_leaf_list':[target],'confined_to_cell_0_541':True,'changed_bytes':146,
         'changed_ranges':[{'start':0,'end':146,'old':target,'new':target}]}
    if mutation == 'side':
        w['changed_ranges'][0]['new'] = dict(target,cell=[1,541])
    elif mutation == 'overlap':
        w['changed_ranges'].append(w['changed_ranges'][0])
    elif mutation == 'total':
        w['changed_bytes'] = 145
    else:
        w['new_sha256'] = chain.AU1
    path = tmp_path/'w.json'
    chain.write_json(path,w)
    with pytest.raises(ValueError):
        chain.successor_witness(path)


def routed(tmp_path, old, new, stem='routed'):
    base = measure(tmp_path, old, new, stem + '-base')
    return chain.routed_diff(old, new, chain.sha(old), chain.sha(new), tmp_path / (stem + '-base.json'),
                             tmp_path / (stem + '.json'), tmp_path / (stem + '.tsv'), tmp_path / (stem + '-work')), base


def test_routed_diff_detects_divided_payload_swap_missed_by_multiset(tmp_path):
    old = image(tmp_path / 'old.kwi', [b'rootAA', b'rootBB'], divided=True)
    new = image(tmp_path / 'new.kwi', [b'rootAA', b'rootBB'], divided=True, children=(b'childB', b'childA'))
    result, base = routed(tmp_path, old, new)
    assert base['unexplained_count'] == 0
    assert result['routed_only_count'] == 1 and result['routed_only_cells'] == [[0, 0, 0]]
    assert result['baseline_cells_missing_from_routed'] == 0
    assert result['multiset_list_complete_under_routing'] is False


def test_routed_diff_invariant_under_relocation_and_padding(tmp_path):
    old = image(tmp_path / 'old.kwi', [b'rootAA', b'rootBB'], divided=True)
    new = image(tmp_path / 'new.kwi', [b'rootAA', b'rootBB'], relocation=2048, divided=True)
    raw = bytearray(new.read_bytes())
    raw[5568 + 2048 + 8:5568 + 2048 + 16] = b'padding!'  # beyond the 8-byte frame
    new.write_bytes(raw)
    result, base = routed(tmp_path, old, new)
    assert base['unexplained_count'] == 0 and result['routed_changed_total'] == 0
    assert result['multiset_list_complete_under_routing'] is True


def test_routed_diff_contains_every_multiset_change(tmp_path):
    old = image(tmp_path / 'old.kwi', [b'rootAA', b'rootBB'], divided=True)
    new = image(tmp_path / 'new.kwi', [b'rootAA', b'rootCC'], divided=True)
    result, base = routed(tmp_path, old, new)
    assert base['unexplained_count'] == 1
    assert result['routed_changed_total'] == 1 and result['routed_only_count'] == 0
    assert result['multiset_list_complete_under_routing'] is True


def test_routed_signature_detects_changed_footprint():
    with sqlite3.connect(':memory:') as db:
        db.execute('CREATE TABLE frames(side TEXT, level INTEGER, ix INTEGER, iy INTEGER, '
                   'footprint TEXT, length INTEGER, hash TEXT)')
        db.executemany('INSERT INTO frames VALUES (?,?,?,?,?,?,?)', [
            ('old', 0, 0, 0, '0:0:1/2:1', 8, 'a'), ('old', 0, 0, 0, '1/2:0:1/2:1', 8, 'b'),
            ('new', 0, 0, 0, '0:0:1/4:1', 8, 'a'), ('new', 0, 0, 0, '1/2:0:1/2:1', 8, 'b')])
        assert list(chain.routed_signatures(db, 'old')) != list(chain.routed_signatures(db, 'new'))


def test_routed_diff_rejects_wrong_or_tampered_baseline(tmp_path):
    old = image(tmp_path / 'old.kwi', [b'rootAA', b'rootBB'], divided=True)
    new = image(tmp_path / 'new.kwi', [b'rootAA', b'rootCC'], divided=True)
    measure(tmp_path, old, new, 'b')
    with (tmp_path / 'b.tsv').open('a') as f:
        f.write('0\t9\t9\tchanged\t\t\t\t\t0\t0\n')
    with pytest.raises(ValueError, match='hash mismatch'):
        chain.routed_diff(old, new, chain.sha(old), chain.sha(new), tmp_path / 'b.json',
                          tmp_path / 'r.json', tmp_path / 'r.tsv', tmp_path / 'r-work')
    with pytest.raises(ValueError, match='different hop'):
        chain.routed_diff(old, new, chain.sha(new), chain.sha(old), tmp_path / 'b.json',
                          tmp_path / 'r2.json', tmp_path / 'r2.tsv', tmp_path / 'r2-work')
