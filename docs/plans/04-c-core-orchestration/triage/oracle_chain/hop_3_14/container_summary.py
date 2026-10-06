"""Plan 36 Phase 2: publish the 3-14 container/index/padding account (no disc reads).

Validates the full `region_accounting.py account` outputs for one hop against the
plan 31 multiset cell list and the PDMDH field classification, then writes a small
committed summary. Fails closed (exit 2) unless every byte delta is named by region,
unaccounted is 0, payload delta == sum of per-cell frame deltas over the changed-cell
list, and every PDMDH byte outside BMT address fields is the BMT size field of a
PMR block whose sector size changed.

Usage: container_summary.py --region R.json --spans R.spans.tsv --cells CELLS.tsv
       --cell-diff DIFF.json --pdmdh PDMDH.json --name au|perth --out OUT.json
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[6]


def sha(path) -> str:
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 22), b''):
            h.update(chunk)
    return h.hexdigest()


def label(path) -> str:
    p = Path(path)
    try:
        return str(p.absolute().relative_to(ROOT))
    except ValueError:
        return str(p)


def summarise(region, spans, cells, cell_diff, pdmdh, name):
    a = json.loads(Path(region).read_text())
    d = json.loads(Path(cell_diff).read_text())
    pf = json.loads(Path(pdmdh).read_text())[name]
    c = a['compare']
    errors = []
    if a.get('kind') != 'region_accounting' or not a['complete_and_accounted'] or c['unaccounted_bytes'] != 0:
        errors.append('region accounting incomplete or unaccounted')
    if [a['old_sha256'], a['new_sha256']] != [d['old_sha256'], d['new_sha256']]:
        errors.append('region and cell diff belong to different hops')
    if sha(cells) != d['cells']['sha256']:
        errors.append('cell list sha differs from the cell diff record')
    named = {k: v['delta'] for k, v in c['sizes'].items() if k != 'partition_gaps'}
    if sum(named.values()) != c['file_size']['delta'] or c['sizes']['partition_gaps']['old'] or c['sizes']['partition_gaps']['new']:
        errors.append('named region deltas do not sum to the file delta')
    status, cell_delta, ncells = Counter(), 0, 0
    with open(cells) as f:
        for r in csv.DictReader(f, delimiter='\t'):
            ncells += 1
            status[r['status']] += 1
            cell_delta += int(r['new_bytes'] or 0) - int(r['old_bytes'] or 0)
    payload = c['sizes']['frame_payload']['delta']
    if cell_delta != payload:
        errors.append(f'payload delta {payload} != sum of per-cell frame deltas {cell_delta}')
    # PDMDH: every non-address differing byte is a BMT size field of a size-changed PMR block.
    outside = set(c['pdmdh']['outside_offsets'])
    if len(outside) != c['pdmdh']['outside_bmt_address_fields']:
        errors.append('PDMDH outside-offset list truncated')
    rows = pf['outside_bytes']
    size_changed = {r['old']['key'] for r in pf['bmt_entries_size_changed']}
    if ({r['offset'] for r in rows} != outside
            or any(r['field_offset_in_entry'] not in (4, 5) or r['old']['key'] not in size_changed for r in rows)):
        errors.append('PDMDH non-address bytes not all BMT size fields of size-changed PMR blocks')
    pmr_keys = set(c['pmr']['masked_content_differs_keys'])
    if pmr_keys != size_changed or c['pmr']['buffer_size_changed'] != len(size_changed):
        errors.append('PMR content changes are not exactly the size-changed BMT blocks')
    topo = {k.split(':', 1)[0] for k in c['frames']['only_old_keys'] + c['frames']['only_new_keys']}
    if len(c['frames']['only_old_keys']) != c['frames']['only_old'] or             len(c['frames']['only_new_keys']) != c['frames']['only_new'] or not topo <= size_changed:
        errors.append('leaf topology changes (only-old/only-new frames) outside the size-changed PMR blocks')
    rec_delta = sum(r['new']['record_bytes'] - r['old']['record_bytes'] for r in pf['bmt_entries_size_changed'])
    if rec_delta != c['sizes']['pmr_records']['delta']:
        errors.append('PMR record delta not explained by the size-changed blocks')
    hist = Counter()
    with open(spans) as f:
        for r in csv.DictReader(f, delimiter='\t'):
            hist[int(r['delta'])] += 1
    if sum(hist.values()) != c['frames']['padding_spans_changed'] or \
            sum(k * v for k, v in hist.items()) != c['frames']['padding_delta_spans']:
        errors.append('padding spans file disagrees with the region compare')
    f = c['frames']
    out = {
        'schema': 1, 'kind': 'hop_3_14_container_account', 'region': name,
        'old_sha256': a['old_sha256'], 'new_sha256': a['new_sha256'],
        'pass': not errors, 'errors': errors,
        'file_size': c['file_size'],
        'region_deltas': named,
        'unaccounted_bytes': c['unaccounted_bytes'],
        'partition': {'old': a['old']['partition'], 'new': a['new']['partition']},
        'frames': {k: f[k] for k in ('old', 'new', 'common', 'only_old', 'only_new', 'only_old_keys',
                                      'only_new_keys', 'payload_changed', 'payload_delta_changed_frames',
                                      'payload_delta_unchanged_frames', 'allocation_changed',
                                      'padding_spans_changed', 'padding_delta_spans', 'relocated',
                                      'alias_pattern_equal')},
        'payload_vs_cells': {'frame_payload_delta': payload, 'sum_cell_frame_deltas': cell_delta,
                             'changed_cells': ncells, 'status': dict(status), 'equal': cell_delta == payload},
        'padding_span_delta_histogram': {str(k): v for k, v in sorted(hist.items())},
        'pmr': {k: c['pmr'][k] for k in ('old', 'new', 'common', 'relocated', 'buffer_size_changed',
                                          'record_size_changed', 'masked_content_differs',
                                          'masked_content_differs_keys')},
        'pmr_size_changed_blocks': pf['bmt_entries_size_changed'],
        'pdmdh': {'differing_bytes': c['pdmdh']['differing_bytes'],
                  'in_bmt_address_fields': c['pdmdh']['in_bmt_address_fields'],
                  'outside_bmt_address_fields': c['pdmdh']['outside_bmt_address_fields'],
                  'outside_bytes': rows},
        'fixed_and_inline': {'fixed': c['fixed'], 'inline': c['inline']},
        'nonzero_padding_or_tail': {'frame_pad_nonzero': [a['old']['frame_pad_nonzero'], a['new']['frame_pad_nonzero']],
                                    'pmr_tail_nonzero': [a['old']['pmr_tail_nonzero'], a['new']['pmr_tail_nonzero']]},
        'inputs': {p: {'path': label(v), 'sha256': sha(v)} for p, v in
                   (('region', region), ('spans', spans), ('cells', cells), ('cell_diff', cell_diff), ('pdmdh', pdmdh))},
        'region_tool_sha256': a['tool_sha256'],
    }
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    for k in ('region', 'spans', 'cells', 'cell-diff', 'pdmdh', 'out'):
        ap.add_argument('--' + k, type=Path, required=True)
    ap.add_argument('--name', required=True)
    a = ap.parse_args(argv)
    if a.out.exists():
        raise SystemExit(f'container_summary: output exists: {a.out}')
    out = summarise(a.region, a.spans, a.cells, a.cell_diff, a.pdmdh, a.name)
    a.out.write_text(json.dumps(out, indent=1, sort_keys=True) + '\n')
    print(json.dumps({'out': str(a.out), 'pass': out['pass'], 'errors': out['errors']}))
    return 0 if out['pass'] else 2


if __name__ == '__main__':
    sys.exit(main())
