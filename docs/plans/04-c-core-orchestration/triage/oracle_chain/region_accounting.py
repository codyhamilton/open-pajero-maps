#!/usr/bin/env python3
"""Plan 36: byte-complete region accounting of an ALLDATA.KWI pair.

Each file is partitioned into the plan 07 regions: Data Volume, Management
Header Table, inline MHT targets (PDMDH = record 0, split into records /
BMT address arrays / record tail / sector pad; the record-29
language/country frame), every Parcel Management Record buffer (record
bytes + zero tail) and every Map Frame allocation (encoded payload, located
by its two-byte extent marker, + zero allocation padding). The partition
must be complete and disjoint (sum of regions = file size); otherwise the
command exits 2 after writing its report.

Old and new are compared by index path, never by offset, so relocation is
never counted as content:
  - frames by (level, blockset, block, slot path): payload hash/length,
    allocation, padding, offset;
  - PMR buffers by (level, blockset, block), after masking only leaf
    DSA/BS fields (addresses and allocations, reported separately);
  - PDMDH byte positions, classified as BMT address fields or other.
Every byte delta is named by region; `unaccounted_bytes` is the file-size
delta not explained by the named region deltas plus any partition gap.

Reads are bounded preads (one allocation at a time); run under
`parser/tools/run_heavy_python.py` and `output/.heavy.lock`.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT / 'parser'))

from kiwiw import volume  # noqa: E402
from kiwiw.bitutils import u16  # noqa: E402
from kiwiw.parcel_mgmt import parse_parcel_mgmt_record  # noqa: E402

NO_DATA = 0xFFFFFFFF
SCHEMA = 1


class PartitionError(Exception):
    pass


# ---------------------------------------------------------------- keys
def encode_key(level: int, bs: int, block: int, path: tuple = ()) -> int:
    """(level, blockset_index, block_index, slot path) -> int64; path depth <= 3."""
    if not (0 <= level < 16 and 0 <= bs < 4096 and 0 <= block < 4096) or len(path) > 3:
        raise ValueError(f'key out of range: {(level, bs, block, path)}')
    p = list(path) + [None] * (3 - len(path))
    slot = 0 if p[0] is None else p[0] + 1
    s1 = 0 if p[1] is None else p[1] + 1
    s2 = 0 if p[2] is None else p[2] + 1
    if slot >= 4096 or s1 >= 256 or s2 >= 256:
        raise ValueError(f'path out of range: {path}')
    return ((((level * 4096 + bs) * 4096 + block) * 4096 + slot) * 256 + s1) * 256 + s2


def decode_key(k: int):
    k = int(k)
    s2 = k % 256; k //= 256
    s1 = k % 256; k //= 256
    slot = k % 4096; k //= 4096
    block = k % 4096; k //= 4096
    bs = k % 4096; level = k // 4096
    path = tuple(x - 1 for x in (slot, s1, s2) if x)
    return level, bs, block, path


def key_label(k: int) -> str:
    level, bs, block, path = decode_key(k)
    return f'L{level} {bs}/{block}' + (': ' + '/'.join(map(str, path)) if path else '')


# ---------------------------------------------------------------- partition
def check_partition(regions, file_size: int) -> dict:
    """regions: iterable of (start, end, kind). Returns gaps/overlaps; complete means none."""
    rs = sorted((int(s), int(e), k) for s, e, k in regions)
    gaps, overlaps, pos = [], [], 0
    for s, e, k in rs:
        if e < s:
            raise PartitionError(f'negative region {k} [{s},{e})')
        if s > pos:
            gaps.append([pos, s])
        elif s < pos:
            overlaps.append([s, min(pos, e), k])
        pos = max(pos, e)
    if pos < file_size:
        gaps.append([pos, file_size])
    if pos > file_size:
        overlaps.append([file_size, pos, 'beyond-eof'])
    return {'regions': len(rs), 'gap_bytes': sum(b - a for a, b in gaps), 'gaps': gaps[:50],
            'overlap_count': len(overlaps), 'overlaps': overlaps[:50],
            'complete': not gaps and not overlaps}


def _walk_leaves(rec, path=()):
    """Yield (path, entry_offset, entry) for every live leaf entry; entry_offset is
    the mapinfo entry's byte offset within the block buffer."""
    for idx, entry in enumerate(rec.entries):
        if entry.dsa == NO_DATA:
            continue
        eoff = rec.offset + 4 + idx * 6
        if entry.subrecord is not None:
            yield from _walk_leaves(entry.subrecord, path + (idx,))
        elif entry.size:
            yield path + (idx,), eoff, entry


def _h(b) -> bytes:
    return hashlib.blake2b(b, digest_size=16).digest()


# ---------------------------------------------------------------- scan one disc
def scan(path: Path, progress=print) -> dict:
    """Partition one ALLDATA.KWI; returns plain data plus numpy arrays."""
    path = Path(path)
    file_size = path.stat().st_size
    fd = os.open(path, os.O_RDONLY)
    try:
        head = os.pread(fd, volume.DATAVOL_SIZE + volume.MHT_SIZE, 0)
        hdr = volume.parse_volume_header(head[:volume.DATAVOL_SIZE])
        mht = volume.parse_management_header_table(head[volume.DATAVOL_SIZE:])
        ss, ls = hdr.sector_size, hdr.logical_sector_size
        regions = [(0, volume.DATAVOL_SIZE, 'data_volume'),
                   (volume.DATAVOL_SIZE, volume.DATAVOL_SIZE + volume.MHT_SIZE, 'mht')]
        fixed = {'data_volume': _h(head[:volume.DATAVOL_SIZE]).hex(),
                 'mht': _h(head[volume.DATAVOL_SIZE:]).hex()}
        inline = {}
        pd = pd_off = pd_buf = None
        for e in mht.entries:
            if e.name or e.dsa == NO_DATA or not e.size:
                continue
            off = volume.getsector(e.dsa, ss, ls)
            n = e.size * ls
            buf = os.pread(fd, n, off)
            if e.index == 0:
                pd_off, pd_buf = off, buf
                pd = volume.parse_pdmdh_full(buf)
            else:
                regions.append((off, off + n, f'mht_inline_{e.index}'))
                inline[str(e.index)] = {'offset': off, 'size': n, 'hash': _h(buf).hex()}
        if pd is None:
            raise PartitionError('no inline PDMDH (MHT record 0)')
        # PDMDH sub-regions
        bmt = sorted((t.offset, t.offset + len(t.entries) * pd.bmr_size * 2) for t in pd.bmt_tables)
        bmt_lo = bmt[0][0] if bmt else pd.record_size
        bmt_hi = bmt[-1][1] if bmt else pd.record_size
        if any(bmt[i][1] != bmt[i + 1][0] for i in range(len(bmt) - 1)):
            raise PartitionError('BMT arrays are not contiguous')
        if not (0 <= bmt_lo <= bmt_hi <= pd.record_size <= len(pd_buf)):
            raise PartitionError('PDMDH layout outside its record')
        for s, e, k in ((0, bmt_lo, 'pdmdh_records'), (bmt_lo, bmt_hi, 'pdmdh_bmt_arrays'),
                        (bmt_hi, pd.record_size, 'pdmdh_record_tail'),
                        (pd.record_size, len(pd_buf), 'pdmdh_sector_pad')):
            regions.append((pd_off + s, pd_off + e, k))
        addr_mask = np.zeros(len(pd_buf), bool)
        for t in pd.bmt_tables:
            for i in range(len(t.entries)):
                o = t.offset + i * pd.bmr_size * 2
                addr_mask[o:o + 4] = True
        # blocks and leaves
        levels = {lmr.level: lmr for lmr in pd.levels}
        pmr_k, pmr_off, pmr_len, pmr_rec, pmr_hash, pmr_tail_nonzero = [], [], [], [], [], 0
        lf_k, lf_off, lf_alloc = [], [], []
        for t in pd.bmt_tables:
            bsr = pd.blocksets[t.blockset_ordinal]
            lmr = levels[bsr.level]
            for bi, be in enumerate(t.entries):
                if be.dsa == NO_DATA or not be.size:
                    continue
                boff = volume.getsector(be.dsa, ss, ls)
                blen = be.size * ls
                buf = bytearray(os.pread(fd, blen, boff))
                root = parse_parcel_mgmt_record(bytes(buf), lmr)
                covered = blen - len(root.tail_raw)
                if any(root.tail_raw):
                    pmr_tail_nonzero += 1
                for lpath, eoff, entry in _walk_leaves(root):
                    lf_k.append(encode_key(bsr.level, bsr.blockset_index, bi, lpath))
                    lf_off.append(volume.getsector(entry.dsa, ss, ls))
                    lf_alloc.append(entry.size * ls)
                    buf[eoff:eoff + 6] = b'\0' * 6  # mask leaf DSA + BS only
                pmr_k.append(encode_key(bsr.level, bsr.blockset_index, bi))
                pmr_off.append(boff); pmr_len.append(blen); pmr_rec.append(covered)
                pmr_hash.append(_h(bytes(buf)))
            progress(f'region_accounting: {path.name} level {bsr.level} blockset {bsr.blockset_index}: '
                     f'{len(pmr_k)} blocks, {len(lf_k)} leaf entries')
        pmr = {'key': np.array(pmr_k, np.int64), 'off': np.array(pmr_off, np.int64),
               'len': np.array(pmr_len, np.int64), 'rec': np.array(pmr_rec, np.int64),
               'hash': np.array(pmr_hash, dtype='S16')}
        for i in range(len(pmr_k)):
            regions.append((pmr_off[i], pmr_off[i] + pmr_len[i], 'pmr'))
        # unique frame allocations (sparse L0 slots alias one frame)
        lk = np.array(lf_k, np.int64); lo = np.array(lf_off, np.int64); la = np.array(lf_alloc, np.int64)
        order = np.lexsort((lk, lo))
        lk, lo, la = lk[order], lo[order], la[order]
        first = np.ones(len(lo), bool)
        first[1:] = lo[1:] != lo[:-1]
        if np.any(la[1:][~first[1:]] != la[:-1][~first[1:]]):
            raise PartitionError('aliased leaves disagree on allocation size')
        aliases = np.diff(np.append(np.flatnonzero(first), len(lo)))
        fk, fo, fa = lk[first], lo[first], la[first]
        n = len(fk)
        fpay = np.zeros(n, np.int64); fhash = np.zeros(n, dtype='S16'); pad_nonzero = 0; bad_len = 0
        for i in range(n):
            raw = os.pread(fd, int(fa[i]), int(fo[i]))
            plen = 2 * u16(raw, 0)
            if plen > len(raw) or plen == 0:
                bad_len += 1
                plen = len(raw)
            if any(raw[plen:]):
                pad_nonzero += 1
            fpay[i] = plen
            fhash[i] = _h(raw[:plen])
            if i and i % 500000 == 0:
                progress(f'region_accounting: {path.name}: {i:,}/{n:,} frames read')
        for i in range(n):
            regions.append((int(fo[i]), int(fo[i] + fa[i]), 'frame'))
        part = check_partition(regions, file_size)
    finally:
        os.close(fd)
    sizes = {
        'data_volume': volume.DATAVOL_SIZE, 'mht': volume.MHT_SIZE,
        **{f'mht_inline_{k}': v['size'] for k, v in inline.items()},
        'pdmdh_records': bmt_lo, 'pdmdh_bmt_arrays': bmt_hi - bmt_lo,
        'pdmdh_record_tail': pd.record_size - bmt_hi, 'pdmdh_sector_pad': len(pd_buf) - pd.record_size,
        'pmr_records': int(pmr['rec'].sum()), 'pmr_tails': int((pmr['len'] - pmr['rec']).sum()),
        'frame_payload': int(fpay.sum()), 'frame_padding': int((fa - fpay).sum()),
        'partition_gaps': part['gap_bytes'],
    }
    return {'path': str(path), 'file_size': file_size, 'sector_size': ss, 'logical_sector_size': ls,
            'fixed': fixed, 'inline': inline, 'pdmdh_offset': pd_off, 'pdmdh_buf': pd_buf,
            'pdmdh_addr_mask': addr_mask, 'pmr': pmr, 'pmr_tail_nonzero': pmr_tail_nonzero,
            'frames': {'key': fk, 'off': fo, 'alloc': fa, 'payload': fpay, 'hash': fhash,
                       'aliases': aliases},
            'leaf_entries': int(len(lk)), 'frame_pad_nonzero': pad_nonzero, 'frame_bad_extent': bad_len,
            'partition': part, 'sizes': sizes}


# ---------------------------------------------------------------- compare
def _join(ka, kb):
    """Indices of common keys (ia, ib) plus only-a / only-b index arrays. Keys must be unique."""
    common, ia, ib = np.intersect1d(ka, kb, assume_unique=True, return_indices=True)
    only_a = np.setdiff1d(np.arange(len(ka)), ia)
    only_b = np.setdiff1d(np.arange(len(kb)), ib)
    return ia, ib, only_a, only_b


def compare(a: dict, b: dict) -> tuple[dict, list]:
    out = {}
    out['fixed'] = {k: {'equal': a['fixed'][k] == b['fixed'][k]} for k in a['fixed']}
    out['inline'] = {k: {'old_size': a['inline'][k]['size'], 'new_size': b['inline'].get(k, {}).get('size'),
                         'equal': a['inline'][k]['hash'] == b['inline'].get(k, {}).get('hash'),
                         'relocated': a['inline'][k]['offset'] != b['inline'].get(k, {}).get('offset')}
                     for k in a['inline']}
    pa, pb = np.frombuffer(a['pdmdh_buf'], np.uint8), np.frombuffer(b['pdmdh_buf'], np.uint8)
    if len(pa) == len(pb):
        diff = pa != pb
        in_addr = diff & a['pdmdh_addr_mask'] & b['pdmdh_addr_mask']
        out['pdmdh'] = {'same_size': True, 'differing_bytes': int(diff.sum()),
                        'in_bmt_address_fields': int(in_addr.sum()),
                        'outside_bmt_address_fields': int((diff & ~in_addr).sum()),
                        'outside_offsets': np.flatnonzero(diff & ~in_addr)[:50].tolist()}
    else:
        out['pdmdh'] = {'same_size': False, 'old_size': len(pa), 'new_size': len(pb)}
    A, B = a['pmr'], b['pmr']
    ia, ib, oa, ob = _join(A['key'], B['key'])
    out['pmr'] = {'old': int(len(A['key'])), 'new': int(len(B['key'])), 'common': int(len(ia)),
                  'only_old': int(len(oa)), 'only_new': int(len(ob)),
                  'relocated': int((A['off'][ia] != B['off'][ib]).sum()),
                  'buffer_size_changed': int((A['len'][ia] != B['len'][ib]).sum()),
                  'record_size_changed': int((A['rec'][ia] != B['rec'][ib]).sum()),
                  'masked_content_differs': int((A['hash'][ia] != B['hash'][ib]).sum()),
                  'masked_content_differs_keys': [key_label(k) for k in A['key'][ia][A['hash'][ia] != B['hash'][ib]][:50]]}
    FA, FB = a['frames'], b['frames']
    ia, ib, oa, ob = _join(FA['key'], FB['key'])
    pay_ch = FA['hash'][ia] != FB['hash'][ib]
    pad_a, pad_b = FA['alloc'] - FA['payload'], FB['alloc'] - FB['payload']
    pad_ch = pad_a[ia] != pad_b[ib]
    alloc_ch = FA['alloc'][ia] != FB['alloc'][ib]
    out['frames'] = {
        'old': int(len(FA['key'])), 'new': int(len(FB['key'])), 'common': int(len(ia)),
        'only_old': int(len(oa)), 'only_new': int(len(ob)),
        'only_old_keys': [key_label(k) for k in FA['key'][oa][:50]],
        'only_new_keys': [key_label(k) for k in FB['key'][ob][:50]],
        'relocated': int((FA['off'][ia] != FB['off'][ib]).sum()),
        'payload_changed': int(pay_ch.sum()),
        'payload_delta_changed_frames': int((FB['payload'][ib][pay_ch] - FA['payload'][ia][pay_ch]).sum()),
        'payload_delta_unchanged_frames': int((FB['payload'][ib][~pay_ch] - FA['payload'][ia][~pay_ch]).sum()),
        'allocation_changed': int(alloc_ch.sum()),
        'padding_spans_changed': int(pad_ch.sum()),
        'padding_delta_spans': int((pad_b[ib][pad_ch] - pad_a[ia][pad_ch]).sum()),
        'alias_pattern_equal': bool(np.array_equal(FA['aliases'][ia], FB['aliases'][ib])),
    }
    spans = []
    for i, j in zip(ia[pad_ch], ib[pad_ch]):
        spans.append({'key': key_label(FA['key'][i]),
                      'old_pad_offset': int(FA['off'][i] + FA['payload'][i]), 'old_bytes': int(pad_a[i]),
                      'new_pad_offset': int(FB['off'][j] + FB['payload'][j]), 'new_bytes': int(pad_b[j]),
                      'delta': int(pad_b[j] - pad_a[i]),
                      'payload_old': int(FA['payload'][i]), 'payload_new': int(FB['payload'][j]),
                      'alloc_old': int(FA['alloc'][i]), 'alloc_new': int(FB['alloc'][j])})
    sa, sb = a['sizes'], b['sizes']
    kinds = sorted(set(sa) | set(sb))
    out['sizes'] = {k: {'old': sa.get(k, 0), 'new': sb.get(k, 0), 'delta': sb.get(k, 0) - sa.get(k, 0)} for k in kinds}
    named = sum(v['delta'] for k, v in out['sizes'].items() if k != 'partition_gaps')
    out['file_size'] = {'old': a['file_size'], 'new': b['file_size'], 'delta': b['file_size'] - a['file_size']}
    out['unaccounted_bytes'] = (out['file_size']['delta'] - named) + sa['partition_gaps'] + sb['partition_gaps']
    return out, spans


def _disc_summary(s: dict) -> dict:
    return {k: s[k] for k in ('path', 'file_size', 'sector_size', 'logical_sector_size', 'leaf_entries',
                              'frame_pad_nonzero', 'frame_bad_extent', 'pmr_tail_nonzero', 'partition', 'sizes')} | {
        'frames_unique': int(len(s['frames']['key'])), 'pmr_buffers': int(len(s['pmr']['key'])),
        'pdmdh_offset': s['pdmdh_offset']}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 24), b''):
            h.update(chunk)
    return h.hexdigest()


def account(old: Path, new: Path, old_sha: str, new_sha: str, out: Path, spans_out: Path | None = None) -> int:
    out = Path(out)
    if out.exists() or (spans_out and Path(spans_out).exists()):
        raise SystemExit(f'region_accounting: output exists; choose a new path: {out}')
    for p, want in ((old, old_sha), (new, new_sha)):
        got = sha256(Path(p))
        if got != want:
            raise SystemExit(f'region_accounting: sha mismatch for {p}: {got} != {want}')
    a, b = scan(Path(old)), scan(Path(new))
    cmp_, spans = compare(a, b)
    ok = a['partition']['complete'] and b['partition']['complete'] and cmp_['unaccounted_bytes'] == 0 \
        and not a['frame_bad_extent'] and not b['frame_bad_extent']
    doc = {'schema': SCHEMA, 'kind': 'region_accounting', 'old_sha256': old_sha, 'new_sha256': new_sha,
           'old': _disc_summary(a), 'new': _disc_summary(b), 'compare': cmp_,
           'padding_spans': spans, 'complete_and_accounted': ok,
           'tool_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, indent=1, sort_keys=True) + '\n')
    if spans_out:
        with open(spans_out, 'w', newline='') as f:
            w = csv.writer(f, delimiter='\t', lineterminator='\n')
            cols = ['key', 'old_pad_offset', 'old_bytes', 'new_pad_offset', 'new_bytes', 'delta',
                    'payload_old', 'payload_new', 'alloc_old', 'alloc_new']
            w.writerow(cols)
            for s in sorted(spans, key=lambda s: s['old_pad_offset']):
                w.writerow([s[c] for c in cols])
    print(json.dumps({'out': str(out), 'complete_and_accounted': ok,
                      'unaccounted_bytes': cmp_['unaccounted_bytes'],
                      'file_delta': cmp_['file_size']['delta'],
                      'padding_spans_changed': cmp_['frames']['padding_spans_changed'],
                      'payload_changed': cmp_['frames']['payload_changed']}))
    return 0 if ok else 2


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='command', required=True)
    p = sub.add_parser('account', help='Execute-only: partition and compare two discs')
    p.add_argument('--old', type=Path, required=True)
    p.add_argument('--new', type=Path, required=True)
    p.add_argument('--old-sha', required=True)
    p.add_argument('--new-sha', required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--spans', type=Path, default=None)
    args = ap.parse_args(argv)
    return account(args.old, args.new, args.old_sha, args.new_sha, args.out, args.spans)


if __name__ == '__main__':
    sys.exit(main())
