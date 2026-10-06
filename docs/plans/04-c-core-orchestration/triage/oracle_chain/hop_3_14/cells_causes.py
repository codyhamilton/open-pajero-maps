"""Plan 36 Phase 3: per-cell cause classes for the 3-14 hop (no disc reads).

Inputs (all sha-pinned in the summary):
  sections-<region>.tsv  sections.py, one row per changed cell
  detail-<region>.json   detail.py, per-leaf section sizes and entry tables for
                         every cell whose pattern is not background-only
  mech.json              whole-disc mechanism facts: shas of the endpoint
                         rebuilds and of the EO-only / chord-only builds
  chord cell lists       oracle_chain diff of 013586b5 -> chord-only build

Mechanism (whole disc): the EO-only build (33006aa + d35b565 `_cenc.c` hunks
1-4) is byte-identical to the 3-14 disc, so every changed cell is caused by the
EO hunks; the chord hunk (5) adds 0 bytes when EO is present. Per cell, a class
is assigned only when its byte predicate holds (CLASSES). All predicates are
evaluated for every cell; they are disjoint by section pattern (each requires
a different (footprints_equal, sections_changed) pair) and the tool refuses a
cell where two hold. A cell failing all of them is `unattributed`.

Usage: cells_causes.py --region AU --sections S.tsv --detail D.json --mech M.json
                       --chord-cells C.tsv --out cells_causes-au.tsv.gz --summary summary-au.json
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
import gzip
import hashlib
import io
import json
from pathlib import Path
import sys

CEILING = 131070
NEAR = 64
CLASSES = {
    'eo_bg_stitch': 'footprints equal; only the background sub-frame bytes differ (header, region list, '
                    'ext table, road, name, ext and uncovered bytes identical per leaf).',
    'eo_bg_stitch_ext_relocation': 'footprints equal; background and the raw ext entry table differ; per leaf '
                                   'every ext entry (index >= 3) keeps its presence and size and its offset moves '
                                   'by exactly that leaf\'s background size delta; ext bytes identical.',
    'eo_frame_ceiling_name': 'footprints equal; only background and name sections differ; in every leaf whose '
                             'name differs both frames are within 64 B of 131,070, the name size moves opposite to '
                             'the background size, and the side with more name bytes would exceed 131,070 with the '
                             'other side\'s background (len - name + name_other > 131,070).',
    'eo_division_ceiling': 'footprints differ by one quadtree step (leaf count ratio 4); the coarser side\'s largest '
                           'frame is within |delta background bytes| of 131,070; the coarser side is the side with '
                           'fewer background bytes. Caveat: background sums compare different topologies (the '
                           'finer side carries per-leaf duplication), so this bounds plausibility; it does not show '
                           'the coarse frame crossed the ceiling. The causal link is the whole-disc EO-only '
                           'counterfactual.',
}


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def leaves_pairwise(o, n):
    return len(o) == len(n) and [r['footprint'] for r in o] == [r['footprint'] for r in n]


def p_ext_relocation(c):
    o, n = c['old'], c['new']
    if not leaves_pairwise(o, n):
        return False
    for a, b in zip(o, n):
        for s in ('header', 'regions', 'road', 'name', 'ext', 'rest'):
            if a['hashes'][s] != b['hashes'][s]:
                return False
        d = b['sizes']['background'] - a['sizes']['background']
        ta, tb = a['table'], b['table']
        if len(ta) != len(tb):
            return False
        for i in range(3, len(ta)):
            ea, eb = ta[i], tb[i]
            if (ea is None) != (eb is None):
                return False
            if ea is not None and (ea[1] != eb[1] or eb[0] - ea[0] != d):
                return False
    return True


def p_frame_ceiling_name(c):
    o, n = c['old'], c['new']
    if not leaves_pairwise(o, n):
        return False
    hit = False
    for a, b in zip(o, n):
        for s in ('header', 'regions', 'table', 'road', 'ext', 'rest'):
            if a['hashes'][s] != b['hashes'][s]:
                return False
        if a['hashes']['name'] == b['hashes']['name']:
            continue
        hit = True
        dn = b['sizes']['name'] - a['sizes']['name']
        db = b['sizes']['background'] - a['sizes']['background']
        if min(a['length'], b['length']) < CEILING - NEAR or dn == 0 or db == 0 or (dn > 0) == (db > 0):
            return False
        big, small = (b, a) if dn > 0 else (a, b)
        # the side with more name bytes, carrying the other side's background
        if big['length'] - big['sizes']['background'] + small['sizes']['background'] <= CEILING:
            return False
    return hit


def p_division_ceiling(c):
    o, n = c['old'], c['new']
    if not o or not n or leaves_pairwise(o, n):
        return False
    lo, ln = len(o), len(n)
    if max(lo, ln) != 4 * min(lo, ln):
        return False
    bo = sum(r['sizes']['background'] for r in o)
    bn = sum(r['sizes']['background'] for r in n)
    coarse, cb, fb = (o, bo, bn) if lo < ln else (n, bn, bo)
    if cb >= fb:
        return False
    return CEILING - max(r['length'] for r in coarse) <= abs(bn - bo)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--region', required=True)
    for k in ('sections', 'detail', 'mech', 'chord-cells', 'out', 'summary'):
        ap.add_argument('--' + k, type=Path, required=True)
    a = ap.parse_args(argv)
    if a.out.exists() or a.summary.exists():
        raise SystemExit('cells_causes: output exists')
    mech = json.loads(a.mech.read_text())
    reg = mech['regions'][a.region]
    if not (reg['eo_only_sha256'] == reg['new_sha256'] and reg['endpoint_old_rebuild_sha256'] == reg['old_sha256']
            and reg['endpoint_new_rebuild_sha256'] == reg['new_sha256']):
        raise SystemExit('cells_causes: mechanism facts do not hold')
    detail = json.loads(a.detail.read_text())
    if [detail['old_sha256'], detail['new_sha256']] != [reg['old_sha256'], reg['new_sha256']]:
        raise SystemExit('cells_causes: detail belongs to another hop')
    det = {tuple(c['cell']): c for c in detail['cells']}
    with open(a.chord_cells) as f:
        chord = {(int(r['level']), int(r['ix']), int(r['iy'])) for r in csv.DictReader(f, delimiter='\t')}
    counts, unattributed, rows, by_level = Counter(), [], [], {}
    special = {}
    with open(a.sections) as f:
        for r in csv.DictReader(f, delimiter='\t'):
            key = (int(r['level']), int(r['ix']), int(r['iy']))
            pat, fpe = r['sections_changed'], r['footprints_equal'] == '1'
            # every predicate is evaluated; the detail predicates need the cell's detail record
            c = det.get(key)
            if pat != 'background' and c is None:
                raise SystemExit(f'cells_causes: no detail for non-background cell {key}')
            hold = []
            if fpe and pat == 'background':
                hold.append('eo_bg_stitch')
            if c is not None and fpe and pat == 'table+background' and p_ext_relocation(c):
                hold.append('eo_bg_stitch_ext_relocation')
            if c is not None and fpe and pat == 'background+name' and p_frame_ceiling_name(c):
                hold.append('eo_frame_ceiling_name')
            if c is not None and not fpe and p_division_ceiling(c):
                hold.append('eo_division_ceiling')
            if len(hold) > 1:
                raise SystemExit(f'cells_causes: predicates not disjoint at {key}: {hold}')
            cls = hold[0] if hold else 'unattributed'
            if cls == 'unattributed':
                unattributed.append(list(key))
            counts[cls] += 1
            by_level.setdefault(str(key[0]), Counter())[cls] += 1
            if cls not in ('eo_bg_stitch', 'eo_bg_stitch_ext_relocation'):
                special[cls] = special.get(cls, []) + [list(key)]
            rows.append([*key, cls, r['footprints_equal'], pat, r['old_leaves'], r['new_leaves'],
                         int(key in chord)])
    buf = io.StringIO()
    w = csv.writer(buf, delimiter='\t', lineterminator='\n')
    w.writerow(['level', 'ix', 'iy', 'class', 'footprints_equal', 'sections_changed', 'old_leaves', 'new_leaves',
                'chord_only_build_changes_cell'])
    w.writerows(rows)
    raw = buf.getvalue().encode()
    with open(a.out, 'wb') as f:
        f.write(gzip.compress(raw, compresslevel=9, mtime=0))
    summary = {'schema': 1, 'kind': 'hop_3_14_cells_causes', 'region': a.region,
               'old_sha256': reg['old_sha256'], 'new_sha256': reg['new_sha256'],
               'cells': len(rows), 'classes': dict(counts.most_common()),
               'classes_by_level': {k: dict(v) for k, v in sorted(by_level.items())},
               'unattributed': unattributed, 'non_stitch_cells': special,
               'predicates': CLASSES, 'mechanism': {
                   'cause': 'd35b565 _cenc.c hunks 1-4 (EO-aware bg_shape stitch via eo_clip)',
                   'eo_only_build_equals_new_disc': True,
                   'chord_hunk_bytes_with_eo_present': 0,
                   'chord_only_build_sha256': reg['chord_only_sha256'],
                   'chord_only_build_changed_cells_vs_old': len(chord),
                   'cells_also_changed_by_chord_only_build': sum(r[-1] for r in rows)},
               'inputs': {'sections': {'path': str(a.sections), 'sha256': sha(a.sections)},
                          'detail': {'path': str(a.detail), 'sha256': sha(a.detail)},
                          'mech': {'path': str(a.mech), 'sha256': sha(a.mech)},
                          'chord_cells': {'path': str(a.chord_cells), 'sha256': sha(a.chord_cells)},
                          'cells_list_sha256': json.loads(a.mech.read_text())['regions'][a.region]['cells_list_sha256']},
               'out': {'path': a.out.name, 'sha256_gz': sha(a.out), 'sha256_tsv': hashlib.sha256(raw).hexdigest()},
               'tool_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    a.summary.write_text(json.dumps(summary, indent=1, sort_keys=True) + '\n')
    print(json.dumps({k: summary[k] for k in ('region', 'cells', 'classes', 'unattributed')}))
    return 0 if not unattributed else 2


if __name__ == '__main__':
    sys.exit(main())
