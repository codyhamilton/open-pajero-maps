#!/usr/bin/env python3
"""Fresh plan-28 completeness measurement; never restores inherited 3-08 bytes.

Light only: committed demand enumeration + one saved proof at a time + current
production bg_shape on in-memory rings. No SpoolReader, disc open, cell build,
or call into a research script's main. Missing evidence is fatal, never code 0.
Full runs require explicit --all-rows and the operator's run_heavy_python guard.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import sys
from collections import Counter, defaultdict
from fractions import Fraction
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
OLD = ROOT / 'docs/plans/04-c-core-orchestration/triage'
SCRATCH = ROOT / 'output/scratch-28'
BASE = ROOT / 'output/scratch-14/dump_raw'
PROOFS = ROOT / 'output/scratch-14/attribution/proofs'
DISC_SHA = '4ed9cd801bdd70992a9b7bd090803ffae349515f87546f044b21157e68e99d72'
# This build is the byte-identical G_new contract, with the 3-11 count split.
CENC_SHA = '5c43e00dd0c6215123e6713423e8a8981d95ea9e06d95cbbd5e1b7b2249e2af0'
sys.path[:0] = [str(ROOT / 'parser'), str(ROOT / 'parser/tools'), str(OLD)]
import dump_join as join
import quantisation_roundtrip as qr
import k1_representable as topology
from kiwiw import dump_io

spec = importlib.util.spec_from_file_location('p28_repair', OLD / 'complete_repair_2-02.py')
repair = importlib.util.module_from_spec(spec)
spec.loader.exec_module(repair)
NATIVE = join.OTHER_NATIVE
SIDE_FIELDS = [*NATIVE, 'dump_row', 'other_mechanism', 'demander_ids',
               'predicate_inputs', 'path', 'matching_rules', 'multi_match',
               'in_historic_188', 'in_added_89']


def digest(path):
    return join._digest(path)


def jcompact(value):
    return json.dumps(value, separators=(',', ':'), sort_keys=True, allow_nan=False)


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n')


def read_tsv(path):
    with path.open() as fh:
        return list(csv.DictReader(fh, delimiter='\t'))


def write_tsv(path, fields, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w') as fh:
        w = csv.DictWriter(fh, fieldnames=fields, delimiter='\t', lineterminator='\n')
        w.writeheader()
        w.writerows(rows)


def key(row):
    return tuple(int(row[k]) for k in NATIVE)


def scratch_path(path):
    if not path.resolve().is_relative_to(SCRATCH.resolve()):
        raise ValueError(f'scratch destination outside scratch-28: {path}')
    return path


def verify_baseline():
    src = BASE / 'completeness.bin'
    if src.stat().st_size != 776 * 144 or digest(src) != join.BASELINE_SHA256:
        raise ValueError('saved baseline does not match the 776-row sha256 pin')
    man = json.loads((BASE / 'dump_manifest.json').read_text())
    if set(man['kinds']) != {'completeness'} or man['kinds']['completeness']['rows'] != 776:
        raise ValueError('baseline manifest count/kinds mismatch')
    return np.dtype([(f['name'], join.TS[f['type']]) for f in man['fields']], align=True)


def rule_source():
    source = OLD / 'rules_other.json'
    doc = json.loads(source.read_text())
    rules = [r for r in doc['rules'] if r['kind'] == 'completeness']
    if [r['id'] for r in rules] != ['O01', 'O04', 'O05', 'O06']:
        raise ValueError('source completeness rules/order changed')
    if [r['where'] for r in rules] != [[["other_mechanism", "==", c]] for c in (4, 7, 5, 8)]:
        raise ValueError('source predicates changed')
    return source, rules


def project(out):
    """Keep each complete source rule JSON object as an exact byte slice."""
    source, rules = rule_source()
    raw = source.read_text()
    dec = json.JSONDecoder()
    pos = raw.index('[', raw.index('"rules"')) + 1
    objects = []
    while True:
        while raw[pos].isspace() or raw[pos] == ',':
            pos += 1
        if raw[pos] == ']':
            break
        obj, end = dec.raw_decode(raw, pos)
        if obj['kind'] == 'completeness':
            objects.append(raw[pos:end])
        pos = end
    projected = '{\n  "version": 1,\n  "rules": [\n    ' + ',\n    '.join(objects) + '\n  ]\n}\n'
    if json.loads(projected)['rules'] != rules:
        raise ValueError('projection differs from source rules')
    out.mkdir(parents=True, exist_ok=True)
    target = out / 'per_rule_rules_completeness_projection.json'
    target.write_text(projected)
    write_json(out / 'per_rule_projection_hashes.json', {
        'source': str(source.relative_to(ROOT)), 'source_sha256': digest(source),
        'projection': str(target), 'projection_sha256': digest(target),
        'rule_order': [r['id'] for r in rules], 'raw_rule_objects_preserved': True,
        'rule_object_sha256': {r['id']: hashlib.sha256(o.encode()).hexdigest()
                               for r, o in zip(rules, objects)}})
    print('PROJECTED O01,O04,O05,O06; exact rule object bytes; both hashes recorded')


def ring_points(coords):
    poly = [tuple(map(float, p)) for p in coords]
    if len(poly) > 1 and poly[0] == poly[-1]:
        poly.pop()
    if len(poly) < 3 or not np.isfinite(np.asarray(poly)).all():
        raise ValueError('invalid saved source ring')
    return poly


def ring_audit(poly):
    """Exact rational predicates: proper crossings, touches/overlaps, area2."""
    fr = repair._as_frac(poly)
    contacts, simple = topology._contacts(fr)
    crossings = [(i, j) for i, j, pt in contacts
                 if pt not in (fr[i], fr[(i + 1) % len(fr)], fr[j], fr[(j + 1) % len(fr)])]
    touches = [(i, j) for i, j, pt in contacts if (i, j) not in crossings
               and not (((i + 1) % len(fr) == j or (j + 1) % len(fr) == i)
                        and pt in (fr[i], fr[(i + 1) % len(fr)])
                        and pt in (fr[j], fr[(j + 1) % len(fr)]))]
    area2 = sum((a[0] * b[1] - b[0] * a[1]
                 for a, b in zip(fr, fr[1:] + fr[:1])), Fraction(0))
    return {'crossings': crossings, 'simple': bool(simple), 'area2_exact': str(area2),
            'area2_zero': area2 == 0, 'nonadjacent_contact_or_overlap': bool(touches)}


def demanded(poly, row, mc):
    """Actual raw checker demand (a/b/c), with no representability filter."""
    arr = np.asarray(poly)
    sh = qr.Shapes(arr[:, 0], arr[:, 1], np.array([0, len(poly)]),
                   np.array([int(row['code'])]), np.array([2]), np.array([mc]))
    region = qr.Region.__new__(qr.Region)
    region.shapes, region._polys = sh, None
    ix, iy, tc = (int(row[k]) for k in ('ix', 'iy', 'code'))
    req = qr._required_cells(region, [(ix, iy)], ix, ix, iy, iy)
    return (ix, iy, tc) in req


def current_records(poly, d, row, lat, probe):
    arr = np.asarray(poly, np.float64)
    slat = lat.lat0 + arr[:, 1] / qr.RAW * lat.cell_lat
    slon = lat.lon0 + arr[:, 0] / qr.RAW * lat.cell_lon
    rc, nr = probe.run(slat, slon, int(d['mc']), int(row['code']), int(d['flags']),
                       repair.cell_b4(lat, int(row['ix']), int(row['iy'])))
    if rc < 0:
        raise ValueError(f'C bg_shape error {rc} on dump_row {row["dump_row"]}')
    return {'bytes': rc, 'records': nr}


def predicate_demander(d, row, lat, probe, audit_cache):
    poly = ring_points(d['raw_coords'])
    if len(d['raw_coords']) != int(d['ncoord']):
        raise ValueError('saved coordinate count mismatch')
    xs, ys = np.asarray(poly).T
    bbox = [float(xs.min()), float(xs.max()), float(ys.min()), float(ys.max())]
    if bbox != d['bbox_raw'] or not demanded(poly, row, int(d['mc'])):
        raise ValueError('saved bbox or demander does not agree with raw checker')
    cachekey = jcompact(poly)
    if cachekey not in audit_cache:
        audit_cache[cachekey] = ring_audit(poly)
    audit = audit_cache[cachekey]
    bbox_zero = bbox[0] == bbox[1] or bbox[2] == bbox[3]
    no_interior = bbox_zero  # exact zero extent proves no 2D interior.
    original = current_records(poly, d, row, lat, probe)
    if original['records'] != int(d['c_original_records']):
        raise ValueError('current C probe disagrees with saved original-record proof')
    clipped = repair.clip_rect(poly, int(row['ix']) * qr.RAW, int(row['iy']) * qr.RAW,
                              (int(row['ix']) + 1) * qr.RAW, (int(row['iy']) + 1) * qr.RAW)
    q, area2, emits = repair.encoder_piece_densified(clipped, int(d['mc']))
    p4 = bbox_zero and audit['area2_zero'] and no_interior and d['branches'] == ['b']
    p5 = audit['simple'] and area2 == 0 and not emits and original['records'] == 0
    # Explicit closure + a crossing of the closing edge; remove ONLY the stored
    # penultimate coordinate (last nonduplicate point of the normalized ring).
    closed = d['raw_coords'][0] == d['raw_coords'][-1]
    closing_cross = any(len(poly) - 1 in pair for pair in audit['crossings'])
    repaired = None
    p7 = False
    if closed and closing_cross and original['records'] == 0:
        short = poly[:-1]
        if len(short) >= 3:
            sa = ring_audit(short)
            cshort = current_records(short, d, row, lat, probe)
            requires = demanded(short, row, int(d['mc']))
            repaired = {'deleted_stored_coordinate': len(d['raw_coords']) - 2,
                        'crossings': sa['crossings'], 'simple': sa['simple'],
                        'required': requires, 'c_probe': cshort,
                        'missing_mismatch': requires and cshort['records'] == 0}
            p7 = not sa['crossings'] and not repaired['missing_mismatch']
    return {'demander_id': d['shape_ref'], 'branches': d['branches'], 'bbox_raw': bbox,
            'bbox_zero': bbox_zero, 'no_interior': no_interior, 'ncoord': d['ncoord'],
            **audit, 'mc': d['mc'], 'flags': d['flags'], 'clip_q': q, 'clip_area2': area2,
            'clip_emits': bool(emits), 'c_original_probe': original,
            'saved_c_original_records': d['c_original_records'],
            'saved_face_area2': [f['area2'] for f in d['faces']],
            'saved_face_c_records': [f['c_records'] for f in d['faces']],
            'explicitly_closed': closed, 'closing_edge_crossing': closing_cross,
            'penultimate_repair_probe': repaired,
            'predicates': {'4': bool(p4), '5': bool(p5), '7': bool(p7)}}


def choose_mechanism(witnesses, count_inputs, rules):
    if not witnesses:
        raise ValueError('no demanders is not negative mechanism evidence')
    predicates = {c: all(w['predicates'][str(c)] for w in witnesses) for c in (4, 7, 5)}
    predicates[8] = count_inputs['predicate_8']
    matches = [r for r in rules if predicates[r['where'][0][2]]]
    code = matches[0]['where'][0][2] if matches else 0
    return code, matches, predicates


def count_contract():
    """Under the pinned current builder, declared = physical per split unit.

    O06's first conjunct (12-bit wrap) is false independent of ring geometry.
    This is a source-contract proof, not a guessed count from decoded records.
    G_new's byte-identical current-contract re-encode is recorded in plan 14.
    A different encoder pin needs a fresh physical-count witness, never zero.
    """
    src = ROOT / 'parser/kiwiw/_cenc.c'
    if digest(src) != CENC_SHA:
        raise ValueError('current encoder pin changed; revalidate count-split contract')
    raw = src.read_text()
    for expression in ('class_n[c] + 4094) / 4095', 'rem > 4095 ? 4095 : rem', 'rem -= u;'):
        if expression not in raw:
            raise ValueError('count split contract absent')
    return {'predicate_8': False, 'wrap': False, 'unit_physical_equals_declared': True,
            'max_declared_class_count': 4095, 'cenc_sha256': CENC_SHA,
            'basis': 'enc_bg splits each physical class into units <=4095; no wrap',
            'disc_contract_reference': 'docs/plans/14-completeness-root-cause.md (byte-identical re-encode)'}


def produce(args):
    dt = verify_baseline()
    if dt.itemsize != 144:
        raise ValueError('unexpected source layout')
    keys = None if args.keys is None else [int(k) for k in args.keys.split(',')]
    if keys is None and args.max_rows is None and not args.all_rows:
        raise ValueError('require --keys, --max-rows or --all-rows')
    selected = join.other_selection(776, keys, args.max_rows)
    _, rules = rule_source()
    evidence = {int(r['dump_row']): r for r in read_tsv(OLD / 'completeness_evidence.tsv')}
    members = {key(r): r for r in read_tsv(OLD / 'phase3_membership.tsv')}
    enum = defaultdict(list)
    for r in read_tsv(OLD / 'demand_attribution_3-01.tsv'):
        enum[int(r['dump_row'])].append(r)
    if len(evidence) != 776 or len(members) != 776 or sum(map(len, enum.values())) != 799:
        raise ValueError('committed evidence/enumeration universe changed')
    counts = count_contract()
    summary = json.loads((ROOT / 'output/scratch-14/attribution/summary.json').read_text())
    if summary['errors'] or summary['checker_disagreements'] or summary['keys'] != 776:
        raise ValueError('saved demand audit is incomplete')
    probe = repair.CProbe(scratch_path(args.scratch) / 'cprobe')
    # Positive production-C control makes a zero-only/miscompiled probe fail.
    lat0 = qr.Lattice(0)
    square = [(100., 100.), (300., 100.), (300., 300.), (100., 300.)]
    control = current_records(square, {'mc': 1, 'flags': 0},
                              {'level': 0, 'ix': 0, 'iy': 0, 'code': 288, 'dump_row': -1}, lat0, probe)
    if control['records'] < 1:
        raise ValueError('positive C probe control failed')
    rows, proof_hashes, audit_cache = [], {}, {}
    with (BASE / 'completeness.bin').open('rb') as fh:
        for rid in selected:
            row = evidence[rid]
            fh.seek(rid * 144)
            native = np.frombuffer(fh.read(144), dt, count=1)[0]
            if key(row) != tuple(int(native[k]) for k in NATIVE) or key(row) not in members:
                raise ValueError(f'committed native key mismatch at {rid}')
            path = PROOFS / f'{rid}.json'
            proof = json.loads(path.read_text())
            proof_hashes[str(rid)] = digest(path)
            if (proof['dump_row'] != rid or proof['disc_sha256'] != DISC_SHA
                    or proof.get('error') or proof['checker_disagreement']
                    or not proof['required_self_check']):
                raise ValueError(f'invalid saved demand proof at {rid}')
            for name in ('level', 'ix', 'iy'):
                if int(proof[name]) != int(row[name]):
                    raise ValueError(f'proof key mismatch at {rid}')
            if int(proof['type']) != int(row['code']):
                raise ValueError(f'proof type mismatch at {rid}')
            ds = proof['demanders']
            actual = {(d['shape_ref'], d['branch']) for d in ds}
            expected = {(d['shape_ref'], d['branch']) for d in enum[rid]}
            if not ds or actual != expected or len(ds) != len(enum[rid]):
                raise ValueError(f'demander enumeration mismatch at {rid}')
            for d in ds:
                erow = next(e for e in enum[rid] if e['shape_ref'] == d['shape_ref'])
                if (int(erow['c_records']) != int(d['c_records'])
                        or erow['representable'] != str(d['representable'])):
                    raise ValueError(f'demander result mismatch at {rid}')
            lat = qr.Lattice(int(row['level']))
            witnesses = [predicate_demander(d, row, lat, probe, audit_cache) for d in ds]
            code, matches, predicates = choose_mechanism(witnesses, counts, rules)
            inputs = {'demanders': witnesses, 'count_contract': counts,
                      'all_demander_predicates': predicates, 'proof': str(path.relative_to(ROOT)),
                      'proof_sha256': proof_hashes[str(rid)], 'meeting_sources': '3-01 demander set',
                      'non_demanding_source_audit_needed': False}
            rows.append({**{k: row[k] for k in NATIVE}, 'dump_row': rid, 'other_mechanism': code,
                         'demander_ids': jcompact([d['shape_ref'] for d in ds]),
                         'predicate_inputs': jcompact(inputs), 'path': 'light',
                         'matching_rules': ','.join(r['id'] for r in matches),
                         'multi_match': int(len(matches) > 1),
                         'in_historic_188': row['in_historic_188'], 'in_added_89': row['in_added_89']})
            # Keep memory bounded by one proof + source audits in this small window.
            audit_cache.clear()
    args.out.mkdir(parents=True, exist_ok=True)
    write_tsv(args.out / 'per_rule_completeness_mechanism.tsv', SIDE_FIELDS, rows)
    write_json(args.out / 'per_rule_mechanism_run.json', {
        'source_sha256': join.BASELINE_SHA256, 'rows': len(rows), 'source_dump_rows': selected,
        'paths': dict(Counter(r['path'] for r in rows)), 'codes': dict(Counter(r['other_mechanism'] for r in rows)),
        'positive_control': control, 'cenc_sha256': probe.cenc_sha, 'compile': probe.cmd,
        'proof_sha256': proof_hashes, 'legacy_contract_control': 'skipped (optional)',
        'inputs_sha256': {str(p.relative_to(ROOT)): digest(p) for p in [
            OLD / 'demand_attribution_3-01.tsv', OLD / 'completeness_evidence.tsv',
            OLD / 'phase3_membership.tsv', OLD / 'rules_other.json',
            ROOT / 'parser/tools/quantisation_roundtrip.py', ROOT / 'parser/tools/k1_representable.py',
            OLD / 'complete_repair_2-02.py', OLD / 'cell_local_2-01.py']}})
    print(f'PRODUCED {len(rows)} rows, no evidence-gap; codes {dict(Counter(r["other_mechanism"] for r in rows))}')


def publish(args):
    """Join actual classifier array to source identities and generate controls."""
    verify_baseline()
    side = read_tsv(args.triage / 'per_rule_completeness_mechanism.tsv')
    man = json.loads((args.dump / 'dump_manifest.json').read_text())
    ext = man['extension_other_mechanism']
    if (ext['source_sha256'] != join.BASELINE_SHA256
            or not ext['original_144_bytes_verified'] or not ext['byte144_zero']
            or ext['side_sha256'] != digest(args.triage / 'per_rule_completeness_mechanism.tsv')
            or ext['destination_sha256'] != digest(args.dump / 'completeness.bin')):
        raise ValueError('extended dump provenance does not match')
    projection = args.triage / 'per_rule_rules_completeness_projection.json'
    hashes = json.loads((args.triage / 'per_rule_projection_hashes.json').read_text())
    source, source_rules = rule_source()
    rules = json.loads(projection.read_text())['rules']
    if (hashes['source_sha256'] != digest(source) or hashes['projection_sha256'] != digest(projection)
            or rules != source_rules or digest(args.classify / 'rules.json') != digest(projection)):
        raise ValueError('classify rules are not the hash-recorded source projection')
    ids = ext['source_dump_rows']
    if len(side) != len(ids) or [int(r['dump_row']) for r in side] != ids:
        raise ValueError('side table/window row mapping mismatch')
    n = man['kinds']['completeness']['rows']
    assignment = args.classify / 'assign_completeness.u16'
    if assignment.stat().st_size != 2 * n or n != len(ids):
        raise ValueError('classify array length mismatch')
    evidence = {key(r): r for r in read_tsv(OLD / 'completeness_evidence.tsv')}
    fields = [*NATIVE, 'dump_row', 'rule_id', 'cause']
    rows = []
    with dump_io.AssignReader(assignment, n, args.window_rows) as reader:
        for lo in range(0, n, args.window_rows):
            codes = reader.read_window(lo, min(args.window_rows, n - lo))
            for i, code in enumerate(codes):
                r = side[lo + i]
                idx = int(code)
                rule = None if idx == 65535 else rules[idx]
                # Check the real array's assignment against first-match semantics.
                matches = [x for x in rules if int(r['other_mechanism']) == x['where'][0][2]]
                expected = matches[0] if matches else None
                if rule != expected or key(r) not in evidence:
                    raise ValueError('classifier/native-key mismatch')
                rows.append({**{k: r[k] for k in NATIVE}, 'dump_row': r['dump_row'],
                             'rule_id': rule['id'] if rule else 'NO_RULE',
                             'cause': rule['cause'] if rule else 'unclassified'})
            del codes
    counts = Counter(r['rule_id'] for r in rows)
    partition = (args.classify / 'partition.txt').read_text()
    status = 'PARTITION FAIL' if counts['NO_RULE'] else 'PARTITION OK'
    if not partition.rstrip().endswith(status):
        raise ValueError('partition output disagrees with assignment array')
    count_rows = read_tsv(args.classify / 'cause_counts.tsv')
    classifier_counts = Counter()
    for r in count_rows:
        classifier_counts[r['rule_id']] += int(r['rows'])
    if classifier_counts != Counter({k: v for k, v in counts.items() if k != 'NO_RULE'}):
        raise ValueError('cause_counts does not match native assignment array')
    write_tsv(args.triage / 'per_rule_classify_assignment.tsv', fields, rows)
    full = ids == list(range(776))
    lines = ['# Plan 28 Phase 1 controls', '',
             f'Generated from {n} real classify assignments; scope: {"full baseline" if full else "window only"}.',
             f'Source sha256: `{join.BASELINE_SHA256}`; original 144 bytes verified; byte144 zero.',
             f'Classifier outcome: `{status}` (exit {1 if counts["NO_RULE"] else 0}).',
             'This is a fresh current-contract measurement, not restored 3-08 bytes.',
             'Legacy-contract control skipped (optional; no legacy build).', '',
             '| Rule | Measured | 3-15 yardstick | 3-17 inherited-byte yardstick |',
             '| --- | ---: | ---: | ---: |']
    y15 = {'O01': 363, 'O04': 7, 'O05': 132, 'O06': 0, 'NO_RULE': 274}
    y17 = {'O01': 363, 'O04': 3, 'O05': 102, 'O06': 0, 'NO_RULE': 308}
    for rid in y15:
        lines.append(f'| {rid} | {counts[rid]} | {y15[rid]} | {y17[rid]} |')
    lines += ['', f'3-15 aggregate comparison: {"PASS" if dict(counts) == {k:v for k,v in y15.items() if v} and full else "FAIL" if full else "NOT RUN (window)"}.',
              f'3-17 aggregate comparison: {"PASS" if dict(counts) == {k:v for k,v in y17.items() if v} and full else "FAIL" if full else "NOT RUN (window)"}.', '',
              '**Design contradiction:** 3-15 → 3-17 is O05 −30, O04 −4, NO_RULE +34.',
              'The quoted explanation names only 30 O05 + 1 O04 = 31 forced-zero rows.',
              'Three rows remain unexplained by that statement; counts and codes are not adjusted.',
              'The deleted inherited byte table has no complete surviving per-row reference here.',
              'An aggregate count does not identify which rows differ; all rows in each differing',
              'rule bucket are listed as comparison candidates below, not proven identity mismatches.', '']
    mismatches = []
    historic = [r for r in rows if int(evidence[key(r)]['in_historic_188'])]
    added = [r for r in rows if int(evidence[key(r)]['in_added_89'])]
    hc, ac = Counter(r['rule_id'] for r in historic), Counter(r['rule_id'] for r in added)
    lines += [f'Historic control: {len(historic)}/188 selected; counts `{dict(hc)}`; ' +
              ('PASS' if full and hc == {'NO_RULE': 188} else 'FAIL' if full else 'WINDOW'),
              f'Added control: {len(added)}/89 selected; counts `{dict(ac)}`; ' +
              ('PASS' if full and ac == {'O04': 3, 'NO_RULE': 86} else 'FAIL' if full else 'WINDOW'), '']
    for r in historic:
        if r['rule_id'] != 'NO_RULE':
            mismatches.append((r, 'historic expected NO_RULE'))
    for r in rows:
        e = evidence[key(r)]
        if not int(e['in_historic_188']) and not int(e['in_added_89']) and r['rule_id'] == 'NO_RULE':
            mismatches.append((r, 'neither-set prediction expects a rule assignment'))
    for r in added:
        if r['rule_id'] not in ('O04', 'NO_RULE'):
            mismatches.append((r, 'added expected O04 or NO_RULE'))
    for r in rows:
        if full and (counts[r['rule_id']] != y15[r['rule_id']] or counts[r['rule_id']] != y17[r['rule_id']]):
            mismatches.append((r, 'aggregate comparison candidate; identity expectation unavailable'))
    side_by_row = {int(r['dump_row']): r for r in side}
    lines += ['## Per-row control mismatches and aggregate comparison candidates', '']
    if not mismatches:
        lines += ['None in the selected window.' if not full else 'None.']
    for r, reason in mismatches:
        s = side_by_row[int(r['dump_row'])]
        lines += [f'- dump_row {r["dump_row"]}, native key `{key(r)}`, actual `{r["rule_id"]}`: {reason}.',
                  f'  Predicate inputs: `{s["predicate_inputs"]}`']
    multi = [r for r in side if int(r['multi_match'])]
    lines += ['', '## Multi-match rows (first source-rule match wins)', '']
    if not multi:
        lines += ['None.']
    for s in multi:
        lines += [f'- dump_row {s["dump_row"]}: `{s["matching_rules"]}`; inputs `{s["predicate_inputs"]}`']
    (args.triage / 'per_rule_phase1_controls.md').write_text('\n'.join(lines) + '\n')
    write_json(args.triage / 'per_rule_classify_run.json', {
        'rows': n, 'full_baseline': full, 'rule_counts': dict(counts),
        'classifier_exit_expected': 1 if counts['NO_RULE'] else 0,
        'assignment_sha256': digest(assignment), 'projection_sha256': digest(projection),
        'classifier_sha256': digest(ROOT / 'parser/tools/k1_triage.py'),
        'partition_sha256': digest(args.classify / 'partition.txt'),
        'historic_counts': dict(hc), 'added_counts': dict(ac),
        'identity_mismatch_rows': sorted({int(r['dump_row']) for r, reason in mismatches
                                         if not reason.startswith('aggregate')}),
        'comparison_candidates': sorted({int(r['dump_row']) for r, reason in mismatches
                                        if reason.startswith('aggregate')}),
        'yardstick_arithmetic_contradiction': '34 row count difference vs 31 forced-zero explanation'})
    print(f'PUBLISHED {n} native assignments; counts {dict(counts)}; {status}')


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest='command', required=True)
    p = sub.add_parser('produce')
    p.add_argument('--keys', help='comma-separated original dump_row ids')
    p.add_argument('--max-rows', type=int)
    p.add_argument('--all-rows', action='store_true')
    p.add_argument('--out', type=Path, default=HERE)
    p.add_argument('--scratch', type=Path, default=SCRATCH)
    p = sub.add_parser('projection')
    p.add_argument('--out', type=Path, default=HERE)
    p = sub.add_parser('publish')
    p.add_argument('--triage', type=Path, default=HERE)
    p.add_argument('--dump', type=Path, default=SCRATCH / 'dump_mech')
    p.add_argument('--classify', type=Path, default=SCRATCH / 'classify')
    p.add_argument('--window-rows', type=int, default=25)
    args = ap.parse_args(argv)
    try:
        if args.command == 'produce':
            produce(args)
        elif args.command == 'projection':
            project(args.out)
        else:
            if args.window_rows < 1:
                raise ValueError('window_rows must be positive')
            publish(args)
    except (ValueError, KeyError, OSError) as exc:
        print(f'completeness_mechanism: {exc}', file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
