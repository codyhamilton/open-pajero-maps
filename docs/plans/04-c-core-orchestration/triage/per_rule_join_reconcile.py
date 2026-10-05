#!/usr/bin/env python3
"""Join saved plan-28 assignments to plan-14 proofs, using full native keys.

Light, stdlib-only: reads committed TSVs and rules JSON, never opens a referenced
proof, spool or disc, imports no research scripts and runs no geometry probe.
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
OLD = ROOT / 'docs/plans/04-c-core-orchestration/triage'
NATIVE = ['level', 'ix', 'iy', 'code', *[f'p{i}' for i in range(7)], 'shape', 'vert']
G1 = 'g-omits-cell-local-dvd-type'
G2 = 'r-absent-complete-repair-zero'
MEMBERS1 = '2-01_g-omits-cell-local-dvd-type_members.tsv'
MEMBERS2 = '2-02_r-absent-complete-repair-zero_members.tsv'
BASE_FIELDS = [*NATIVE, 'dump_row', 'rule_id', 'cause', 'plan14_group',
               'plan14_group_id', 'plan14_disposition', 'demander_verdict',
               'proof_references', 'R_polygon_count', 'R_presence',
               'R_cell_local_verdict', 'R_cell_local_presence', 'verdict']
DISC_FIELDS = [*BASE_FIELDS, 'repair_operation', 'current_contract',
               'original_c_records', 'eo_repaired_c_records',
               'repair_c_records', 'repair_representable', 'repair_required',
               'repair_missing_mismatch', 'discriminator_inputs', 'explanation',
               'spool_successor', 'in_added_89']


def require(condition, message):
    if not condition:
        raise ValueError(message)


def compact(value):
    return json.dumps(value, separators=(',', ':'), sort_keys=True, allow_nan=False)


def read_tsv(path):
    with path.open(newline='') as fh:
        return list(csv.DictReader(fh, delimiter='\t'))


def native(row):
    return tuple(int(row[field]) for field in NATIVE)


def index(rows, label):
    result = {native(row): row for row in rows}
    require(len(result) == len(rows), f'{label}: duplicate native keys')
    require(len({r['dump_row'] for r in rows}) == len(rows),
            f'{label}: duplicate dump_row')
    return result


def reference(name, dump_row):
    return f'docs/plans/04-c-core-orchestration/triage/{name}#dump_row={dump_row}'


def write_tsv(path, fields, rows):
    with path.open('w', newline='') as fh:
        writer = csv.DictWriter(fh, fieldnames=fields, delimiter='\t', lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)


def discriminate(base, mechanism, inputs, member):
    """An absent/incomplete counterfactual stays conflict-open, never inferred."""
    details = []
    settled = base['rule_id'] == 'O04' and bool(inputs['demanders'])
    for demander in inputs['demanders']:
        probe = demander.get('penultimate_repair_probe')
        original = demander.get('c_original_probe', {})
        usable = (
            isinstance(probe, dict) and probe.get('simple') is True
            and probe.get('crossings') == []
            and probe.get('deleted_stored_coordinate') == demander['ncoord'] - 2
            and probe.get('missing_mismatch') is False
            and isinstance(probe.get('required'), bool)
            and isinstance(probe.get('c_probe', {}).get('records'), int)
            and probe['c_probe']['records'] >= 0
            and original.get('records') == 0
            and demander.get('closing_edge_crossing') is True
        )
        if usable:
            records = probe['c_probe']['records']
            usable = probe['required'] == (records > 0)
        settled = settled and usable
        details.append({'demander_id': demander['demander_id'],
                        'original_c_probe': original,
                        'original_crossings': demander['crossings'],
                        'penultimate_repair_probe': probe,
                        'settled': usable})
    base['verdict'] = 'conflict-proven' if settled else 'conflict-open'
    probes = [d['penultimate_repair_probe'] for d in details]
    repairs = [p['c_probe']['records'] for p in probes] if settled else []
    required = [p['required'] for p in probes] if settled else []
    explanation = (
        'Original ring and all original EO faces emit zero; the checker '
        'disposition concerns that original geometry. Penultimate deletion '
        'changes the source: ' +
        ('a representable piece is emitted' if any(repairs) else
         'no representable piece remains and the demand disappears') +
        '. R presence is recorded separately; spool cause is retained.'
        if settled else
        'Saved counterfactual does not settle this cause; keep conflict-open. '
        'A bounded current-contract repair probe is required.'
    )
    return {
        **base, 'repair_operation': 'delete only penultimate stored coordinate'
        if base['rule_id'] == 'O04' else 'build repair counterfactual unavailable',
        'current_contract': compact(inputs['count_contract']),
        'original_c_records': compact([d['original_c_probe'].get('records') for d in details]),
        'eo_repaired_c_records': member.get('c_records_repaired', 'not in 2-02 seed table'),
        'repair_c_records': compact(repairs) if settled else 'unknown',
        'repair_representable': str(any(repairs)).lower() if settled else 'unknown',
        'repair_required': compact(required) if settled else 'unknown',
        'repair_missing_mismatch': 'false' if settled else 'unknown',
        'discriminator_inputs': compact(details), 'explanation': explanation,
        'spool_successor': str(base['cause'] == 'spool').lower(),
        'in_added_89': mechanism['in_added_89'],
    }


def reconcile(output_dir):
    assignments = index(read_tsv(HERE / 'per_rule_classify_assignment.tsv'), 'assignments')
    mechanisms = index(read_tsv(HERE / 'per_rule_completeness_mechanism.tsv'), 'mechanisms')
    membership = index(read_tsv(OLD / 'phase3_membership.tsv'), 'membership')
    evidence = index(read_tsv(OLD / 'completeness_evidence.tsv'), 'evidence')
    m1 = index(read_tsv(OLD / MEMBERS1), '2-01')
    m2 = index(read_tsv(OLD / MEMBERS2), '2-02 seeds')
    for label, table in [('assignments', assignments), ('mechanisms', mechanisms),
                         ('evidence', evidence)]:
        require(set(table) == set(membership), f'{label}: key set differs from membership')
        require(all(table[k]['dump_row'] == membership[k]['dump_row'] for k in table),
                f'{label}: dump_row disagrees at a native key')
    require(len(membership) == 776, 'membership must contain 776 unique keys')
    require({int(r['dump_row']) for r in membership.values()} == set(range(776)),
            'membership dump_row coverage must be 0..775')
    require(Counter(r['phase3_group'] for r in membership.values()) == {G1: 342, G2: 434},
            'membership must use amended 342 + 434 groups')
    require(set(m1) == {k for k, r in membership.items() if r['phase3_group'] == G1},
            '2-01 proof coverage differs')
    require(set(m2) == {k for k, r in membership.items()
                       if r['phase3_group'] == G2 and r['dump_row'] not in {'335', '765'}},
            '2-02 seed proof coverage differs')
    attribution = defaultdict(list)
    for row in read_tsv(OLD / 'demand_attribution_3-01.tsv'):
        attribution[row['dump_row']].append(row)
    require(set(attribution) == {r['dump_row'] for r in membership.values()},
            'demander coverage differs')
    contribution_rows = read_tsv(OLD / 'r_contribution_3-02.tsv')
    contribution = {r['dump_row']: r for r in contribution_rows}
    require(len(contribution) == len(contribution_rows), 'duplicate R contribution rows')
    require(set(contribution) == {r['dump_row'] for r in membership.values()
                                 if r['phase3_group'] == G2 and r['dump_row'] != '335'},
            'R contribution coverage differs')
    rules = {r['id']: r for r in json.loads((OLD / 'rules_other.json').read_text())['rules']}
    codes = {'O01': 4, 'O04': 7, 'O05': 5, 'O06': 8, 'NO_RULE': 0}
    joined, discriminators = [], []
    for key, assigned in sorted(assignments.items(), key=lambda item: int(item[1]['dump_row'])):
        row_id = assigned['dump_row']
        rule, cause = assigned['rule_id'], assigned['cause']
        require(rule in codes, f'{row_id}: unknown rule')
        if rule != 'NO_RULE':
            require(cause == rules[rule]['cause'], f'{row_id}: rule cause differs')
        mechanism = mechanisms[key]
        require(int(mechanism['other_mechanism']) == codes[rule], f'{row_id}: rule/code mismatch')
        inputs = json.loads(mechanism['predicate_inputs'])
        demanders = attribution[row_id]
        require(set(json.loads(mechanism['demander_ids'])) == {d['shape_ref'] for d in demanders},
                f'{row_id}: saved demander IDs differ')
        require({d['demander_id'] for d in inputs['demanders']} == {d['shape_ref'] for d in demanders},
                f'{row_id}: predicate demander IDs differ')
        for d in demanders:
            require(tuple(int(d[f]) for f in ['level', 'ix', 'iy', 'type']) == key[:4],
                    f'{row_id}: attribution cell/type mismatch')
            require(d['all_demanders_unrepresentable'] == '1'
                    and d['representable'] == 'False' and d['c_records'] == '0',
                    f'{row_id}: original demander is not proven unrepresentable')
        group = membership[key]['phase3_group']
        ev = evidence[key]
        refs = [reference('phase3_membership.tsv', row_id),
                reference('demand_attribution_3-01.tsv', row_id), inputs['proof'],
                f'docs/plans/04-c-core-orchestration/triage/per_rule_classify_assignment.tsv#dump_row={row_id}',
                f'docs/plans/04-c-core-orchestration/triage/per_rule_completeness_mechanism.tsv#dump_row={row_id}',
                ev['R_witness'], ev['G_witness'], ev['spool_K1_requirement_witness'],
                'docs/design/k1-completeness.md', 'docs/plans/14-completeness-root-cause.md']
        member = m1.get(key, m2.get(key, {}))
        if member:
            require(member['dump_row'] == row_id, f'{row_id}: member ID mismatch')
            require(member['R_polygon_count'] == ev['R_polygon_count'], f'{row_id}: R count differs')
        if group == G1:
            require(member['encoder_emits'] == 'False'
                    and int(member['r_meeting_polygons']) > 0, f'{row_id}: 2-01 proof differs')
            refs += [reference(MEMBERS1, row_id), member['r_proof_path']]
            r_local = 'present:cell-local R polygon proven by 2-01'
        elif row_id == '335':
            require(int(ev['R_polygon_count']) == 0 and all(d['c_tol_only'] == 'True'
                    and d['branch'] == 'c' for d in demanders), '335: TOL-only ruling differs')
            refs += ['docs/plans/04-c-core-orchestration/triage/phase3_groups.md#design-ruling-on-dump_row-335-2026-10-06']
            r_local = 'absent:F2 Design ruling; TOL-only centre-hit trigger'
        else:
            rc = contribution[row_id]
            require(tuple(json.loads(rc['key'])) == key[:4], f'{row_id}: R contribution key differs')
            require(rc['R_polygon_count'] == ev['R_polygon_count']
                    and rc['verdict'] == 'proven' and rc['c_records'] == '0',
                    f'{row_id}: R contribution is not proven zero')
            refs += [reference('r_contribution_3-02.tsv', row_id), rc['proof_path']]
            r_local = 'absent:' + rc['mechanism']
            if row_id == '765':
                refs += ['docs/plans/04-c-core-orchestration/triage/phase3_groups.md']
            else:
                require(member['c_records_original'] == '0' and member['c_records_repaired'] == '0',
                        f'{row_id}: original EO repair is not zero')
                refs += [reference(MEMBERS2, row_id), member['proof_path']]
        base = {**{f: assigned[f] for f in [*NATIVE, 'dump_row', 'rule_id', 'cause']},
                'plan14_group': group, 'plan14_group_id': '2-01' if group == G1 else '2-02 amended',
                'plan14_disposition': 'checker:3-03 representability filter; all original demanders unrepresentable',
                'demander_verdict': compact(demanders), 'proof_references': compact(refs),
                'R_polygon_count': ev['R_polygon_count'],
                'R_presence': str(int(ev['R_polygon_count']) > 0).lower(),
                'R_cell_local_verdict': r_local, 'R_cell_local_presence': str(group == G1).lower(),
                'verdict': 'consistent'}
        if rule in {'O04', 'O06'}:
            discriminators.append(discriminate(base, mechanism, inputs, member))
        else:
            require(rule == 'NO_RULE' or cause == 'checker', f'{row_id}: unsupported cause')
        joined.append(base)
    counts = Counter((r['rule_id'], r['plan14_group'], r['verdict']) for r in joined)
    require(sum(counts.values()) == 776, 'cross-tab must sum to 776')
    require({native(r) for r in discriminators} ==
            {native(r) for r in joined if r['rule_id'] in {'O04', 'O06'}},
            'discriminator key coverage differs')
    predictions = {
        'every_2_01_row_rule_assigned': all(r['rule_id'] != 'NO_RULE' for r in joined if r['plan14_group'] == G1),
        'NO_RULE_subset_2_02': all(r['plan14_group'] == G2 for r in joined if r['rule_id'] == 'NO_RULE'),
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    write_tsv(output_dir / 'per_rule_phase2_join.tsv', BASE_FIELDS, joined)
    write_tsv(output_dir / 'per_rule_phase2_crosstab.tsv', ['rule_id', 'plan14_group', 'verdict', 'count'],
              [dict(zip(['rule_id', 'plan14_group', 'verdict', 'count'], (*key, n)))
               for key, n in sorted(counts.items())])
    write_tsv(output_dir / 'per_rule_phase2_discriminators.tsv', DISC_FIELDS, discriminators)
    print(compact({'rows': len(joined), 'unique_keys': len(assignments),
                   'membership_key_set_equal': True, 'crosstab_sum': sum(counts.values()),
                   'discriminator_rows': len(discriminators),
                   'verdicts': dict(Counter(r['verdict'] for r in joined)),
                   'predictions': {p: 'PASS' if v else 'FAIL' for p, v in predictions.items()},
                   'conflict_open_rows': [r['dump_row'] for r in joined if r['verdict'] == 'conflict-open']}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=HERE)
    args = parser.parse_args()
    destination = args.output_dir.resolve()
    require(destination == HERE or destination.is_relative_to((ROOT / 'output/scratch-28').resolve()),
            'output directory must be triage or scratch-28')
    reconcile(destination)


if __name__ == '__main__':
    main()
