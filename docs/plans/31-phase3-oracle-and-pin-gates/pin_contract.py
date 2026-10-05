#!/usr/bin/env python3
"""Publish the cited successor pin contract; never run K1 or read discs/spool."""
from __future__ import annotations

import argparse
import csv
import fnmatch
import hashlib
import io
import json
import os
from pathlib import Path
import re
import subprocess

REPO = Path(__file__).resolve().parents[3]
PLAN = Path('docs/plans/31-phase3-oracle-and-pin-gates')
SUCCESSOR = '2ee3456a9aeb8607b88be4edd989a2034dd7fdd6f7846369d9dbc4c8ff20e6ae'
KINDS = ('background', 'background_boundary', 'completeness', 'interior_cover',
         'name_anchor', 'range', 'road_node', 'road_point', 'step')
LEVELS = ('0', '2', '4', '6', '8', '10', '12')
DUMP_KINDS = ('background', 'background_boundary', 'interior_cover', 'name_anchor')
# Full hashes taken from the cited artifacts, never from protected payloads.
SOURCES = {
    'compare': ('docs/plans/04-c-core-orchestration/triage/name_anchor/witnesses/successor_k1_compare.json', 'd4d5038d9d66d420e6e9788100a894006051ee28fe785ed069281b761d1d5d4b'),
    'diff': ('docs/plans/04-c-core-orchestration/triage/name_anchor/witnesses/successor_diff.json', 'a129b4f8e57643c94dea5c2b03a2bff57e9100b3fccf1f84a7181c809bf73172'),
    'record': ('docs/plans/29-k1-name-anchor-failure.md', 'ca1278f821c20b09a4ff0ca77cda6b27664cebef6291d3fff312acbfc88f3b19'),
    'report': ('output/scratch-32/k1_dump_report.json', 'ade63d88ec6b0cefb659e2ecff3db38cbb99e8e327666e0770b75529d19480dc'),
    'run': ('output/scratch-32/runs/k1_dump.json', '4d3d893aedc3488ba5898768d8aef3de0a6a47731062975321ad7a24fa78d4ad'),
    'log': ('output/scratch-32/run_p1.log', '474573a96e1cdb0fb2cff826ac9386f3d77e74e3bcbe4dfd1b1be1a00de884f2'),
    'manifest': ('output/scratch-32/dump/dump_manifest.json', 'c29ed9f0bd2fb382729f7fba2d200c9ab3b514aca8154a27e4aaa34a59536839'),
    'candidates': ('docs/plans/04-c-core-orchestration/triage/pinned_candidates.tsv', '7dfe6ed7b99e9d234e688d6855a885d3cd1a140db409dc1f726a48bd0948855a'),
    'ledger': ('docs/plans/27-independent-fix-review-truncated-pins.md', 'ba413f764e51437938970d3363d8c2c76e48a3d1efef6202dc4a2646ea9cdd12'),
}


def protected(path: Path) -> bool:
    return any('spool' in p.lower() or p.lower() == 'r' for p in path.parts) or path.suffix.lower() == '.kwi'


def read_pinned(root: Path, relative: str, expected: str) -> bytes:
    path = root / relative
    if protected(path) or protected(path.resolve()):
        raise ValueError(f'Protected input refused: {relative}')
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected:
        raise ValueError(f'SHA-256 mismatch: {relative}')
    return raw


def load_sources(root: Path, sources: dict = SOURCES) -> tuple[dict, dict]:
    data, evidence = {}, {}
    for key, (path, sha) in sources.items():
        raw = read_pinned(root, path, sha)
        data[key] = json.loads(raw) if path.endswith('.json') else raw.decode('utf-8')
        evidence[key] = {'path': path, 'sha256': sha}
    return data, evidence


def count(value):
    """Missing, negative, boolean and non-integral counts are unknown, not zero."""
    return value if type(value) is int and value >= 0 else None


def live_contract(compare: dict, report: dict, evidence: dict) -> tuple[list, dict]:
    comparisons = compare.get('comparisons', {})
    totals = comparisons.get('totals', {})
    report_totals = report.get('totals', {})
    kinds = sorted(set(KINDS) | set(totals) | set(report_totals))
    rows = []
    global_issues = []
    if compare.get('pass') is not True or compare.get('errors') != [] or compare.get('expected_k1_exit') != 0:
        global_issues.append('plan-29 comparison did not pass')
    if report.get('pass') is not True or count(report.get('failing')) != 0:
        global_issues.append('plan-32 report did not pass with zero aggregate failures')
    if report.get('engine') != 'c' or report.get('timing', {}).get('workers') != 6:
        global_issues.append('plan-32 report is not C K1 at -j6')
    for kind in kinds:
        entry = totals.get(kind, {})
        new = entry.get('new', {})
        checked, failing = count(new.get('checked')), count(new.get('failing'))
        issues = list(global_issues)
        if checked is None or failing is None:
            issues.append('missing or invalid successor total count')
        if failing is not None and failing > 0:
            issues.append('positive successor failure count')
        if entry.get('equal') is not True:
            issues.append('plan-29 expected/new comparison is not equal')
        for field, value in [('checked', checked), ('failing', failing)]:
            other = count(report_totals.get(kind, {}).get(field))
            if value is None or other is None or value != other:
                issues.append(f'plan-32 {field} count missing or inconsistent')
            for label, levels, nested in [('plan-29', comparisons, True), ('plan-32', report.get('levels', {}), False)]:
                values = []
                for level in LEVELS:
                    level_data = levels.get(level, {})
                    item = (level_data if nested else level_data.get('kinds', {})).get(kind, {})
                    values.append(count((item.get('new', {}) if nested else item).get(field)))
                    if nested and item.get('equal') is not True:
                        issues.append(f'{label} L{level} comparison missing or unequal')
                if any(v is None for v in values) or value is None or sum(values) != value:
                    issues.append(f'{label} {field} level census missing or inconsistent')
        rows.append({'kind': kind, 'checked': checked, 'failing': failing,
                     'source_path': evidence['compare']['path'],
                     'source_sha256': evidence['compare']['sha256'],
                     'corroborating_path': evidence['report']['path'],
                     'corroborating_sha256': evidence['report']['sha256'],
                     'status': 'open' if issues else 'empty', 'issues': sorted(set(issues))})
    empty = all(row['status'] == 'empty' for row in rows)
    return rows, {
        'status': 'live-empty' if empty else 'open',
        'open_kinds': [r['kind'] for r in rows if r['status'] == 'open'],
        'live_failing_set': [] if empty else None,
        'live_pinned_failure_set': [] if empty else None,
        'set_equality': True if empty else None,
        'rule': 'Future close compares the live failing set on the disc in force with the live pinned-failure set. Zero failures in every kind implies both sets are empty; missing or positive counts leave that kind open.',
        'scope': 'Cited successor measurements only; not a fresh K1 run or a Phase 3 close.',
    }


def verify_binding(data: dict, evidence: dict, root: Path) -> list:
    """Bind cited report paths to the recorded successor; do not hash its bytes."""
    diff, run = data['diff'], data['run']
    if diff.get('new_sha256') != SUCCESSOR or SUCCESSOR not in data['record']:
        raise ValueError('Recorded successor pin mismatch')
    argv = run.get('argv', [])
    expected = {'--disc': diff['new'], '--out': evidence['report']['path'],
                '--dump-failures': str(Path(evidence['manifest']['path']).parent),
                '--engine': 'c', '-j': '6', '--dump-kinds': 'interior_cover,name_anchor,background,background_boundary'}
    for option, value in expected.items():
        if argv.count(option) != 1 or argv.index(option) + 1 >= len(argv) or argv[argv.index(option) + 1] != value:
            raise ValueError(f'Run binding mismatch: {option}')
    if run.get('exit') != 0 or 'EXIT k1 0' not in data['log']:
        raise ValueError('Cited K1 run did not exit zero')
    if data['compare'].get('new_report') != 'output/scratch-29/k1_live.json':
        raise ValueError('Plan-29 comparison references a different report')
    manifest_kinds = data['manifest'].get('kinds', {})
    if set(manifest_kinds) != set(DUMP_KINDS):
        raise ValueError('Unexpected dump kind coverage')
    bins = []
    for kind in DUMP_KINDS:
        entry = manifest_kinds[kind]
        # Stat the prescribed bin only; never open a bin or a manifest-chosen path.
        name = f'{kind}.bin'
        if entry.get('file') != name or count(entry.get('rows')) != 0:
            raise ValueError(f'Nonempty or invalid dump manifest: {kind}')
        path = root / Path(evidence['manifest']['path']).parent / name
        if protected(path.resolve()) or not path.is_file() or path.stat().st_size != 0:
            raise ValueError(f'Nonempty or missing dump bin: {kind}')
        if count(data['report'].get('dump', {}).get(kind)) != 0:
            raise ValueError(f'Report dump count is not zero: {kind}')
        bins.append({'kind': kind, 'path': str(Path(evidence['manifest']['path']).parent / name),
                     'bytes': 0, 'manifest_rows': 0, 'inspection': 'stat only; not opened'})
    return bins


def historical_view(text: str, ledger: str, sha: str) -> dict:
    if sha not in ledger:
        raise ValueError('Candidate SHA-256 is absent from plan-27 ledger')
    footer = [line for line in text.splitlines() if line.startswith('# TOTAL_GROUPS=')]
    if len(footer) != 1:
        raise ValueError('Missing or ambiguous candidate footer')
    fields = dict(re.findall(r'(TOTAL_GROUPS|TOTAL_ROWS|SHOWN|TRUNCATED)=([^\s]+)', footer[0]))
    if fields != {'TOTAL_GROUPS': '26650', 'TOTAL_ROWS': '1939931', 'SHOWN': '100', 'TRUNCATED': 'yes'}:
        raise ValueError('Candidate footer differs from signed historical totals')
    rows = list(csv.DictReader(io.StringIO('\n'.join(line for line in text.splitlines() if not line.startswith('#'))), delimiter='\t'))
    expected_columns = {'kind', 'level', 'ix', 'iy', 'type', 'p0', 'p1', 'p2', 'p3', 'p4', 'p5', 'p6', 'shape', 'rows'}
    if any(set(row) != expected_columns or any(v is None for v in row.values()) for row in rows):
        raise ValueError('Invalid candidate columns')
    if len(rows) != 100 or len({tuple(sorted(row.items())) for row in rows}) != 100:
        raise ValueError('Candidate view is not 100 distinct shown rows')
    identities = [tuple(v for k, v in row.items() if k != 'rows') for row in rows]
    if len(set(identities)) != 100 or any(not row.get('rows', '').isdigit() for row in rows):
        raise ValueError('Invalid or duplicate candidate groups')
    return {'shown_groups': 100, 'total_groups': 26650, 'total_rows': 1939931,
            'truncated': True, 'exhaustive_set_equality': None,
            'totals_scope': 'Historical footer claims; exhaustive identities not reproduced.'}


def inventory(root: Path) -> dict:
    """Follow directory symlinks at any depth, deduplicating inode identities."""
    pending, visited, matches, excluded, errors = [root], set(), [], [], []
    while pending:
        path = pending.pop()
        try:
            if protected(path) or protected(path.resolve()):
                excluded.append(str(path))
                continue
            st = path.stat()
            identity = (st.st_dev, st.st_ino)
            if identity in visited:
                continue
            visited.add(identity)
            with os.scandir(path) as entries:
                for entry in entries:
                    if entry.is_dir(follow_symlinks=True):
                        pending.append(Path(entry.path))
                    elif any(fnmatch.fnmatchcase(entry.name, pattern) for pattern in ('enumerate_*.tsv', 'pins_*.tsv')):
                        matches.append(entry.path)
        except OSError as exc:
            errors.append({'path': str(path), 'error': str(exc)})
    return {'root': str(root), 'resolved_root': str(root.resolve()),
            'follow_symlinks': True, 'depth_limit': None,
            'visited_directories': len(visited), 'matches': sorted(matches),
            'excluded_protected_directory_count': len(excluded),
            'excluded_examples': sorted(excluded)[:5],
            'exclusion_rule': 'Paths resolving to spool-named components, R directories or KWI files are never entered/opened.',
            'errors': errors, 'scope_limit': 'No search inside protected spool/R paths or outside this output root.'}


def git_inventory(root: Path) -> dict:
    patterns = [':(glob)**/enumerate_*.tsv', ':(glob)**/pins_*.tsv']
    commands = [['git', 'log', '--all', '--format=%H', '--', *patterns],
                ['git', 'ls-files', '--', *patterns], ['git', 'rev-parse', 'HEAD']]
    outputs = [subprocess.run(cmd, cwd=root, check=True, text=True, capture_output=True).stdout.splitlines() for cmd in commands]
    return {'commands': commands, 'head': outputs[2][0],
            'matching_commits': sorted(set(outputs[0])), 'tracked_matches': outputs[1],
            'scope': 'All locally available refs; no fetch, unreachable-object search, or content fabrication.'}


def build(root: Path, sources: dict = SOURCES) -> dict:
    data, evidence = load_sources(root, sources)
    bins = verify_binding(data, evidence, root)
    rows, live = live_contract(data['compare'], data['report'], evidence)
    historical = historical_view(data['candidates'], data['ledger'], evidence['candidates']['sha256'])
    historical['output_inventory'] = inventory(root / 'output')
    scan = historical['output_inventory']
    own_fixtures = (root / 'output/scratch-31/tests-p2').resolve()
    scan['synthetic_test_matches'] = [p for p in scan['matches'] if Path(p).resolve().is_relative_to(own_fixtures)]
    scan['historical_recovery_candidates'] = [p for p in scan['matches'] if p not in scan['synthetic_test_matches']]
    scan['synthetic_match_rule'] = 'Matches resolving beneath this unit\'s synthetic --basetemp are fixtures, never recovered historical enumerations.'
    historical['git_inventory'] = git_inventory(root)
    historical['disposition'] = 'residual-not-required-for-live-close' if live['status'] == 'live-empty' else 'residual-unverifiable'
    historical['identity_status'] = 'unverifiable'
    historical['root_cause'] = 'The signed TSV deliberately contains only 100/26650 groups. Full enumerations are non-committed scratch; no exhaustive historical spool-assignment equality proof has been recovered. Non-fixture inventory matches, if any, are candidates only until their hashes and historical assignment joins are verified.'
    historical['live_close_requirement'] = 'Historical S02 rows are not required for the cited live-empty close pin contract.' if live['status'] == 'live-empty' else 'Live-empty exemption unavailable while any kind remains open.'
    return {'schema_version': 1, 'disc_in_force_sha256': SUCCESSOR,
            'measurement_mode': 'cited evidence; no disc/spool opened, no K1 run',
            'disc_binding': 'Plan-29 signed record and successor diff pin; plan-32 wrapper argv names that recorded successor path. Report and manifest contain no disc digest; no fresh byte attestation is claimed.',
            'sources': evidence, 'kinds': rows, 'live_contract': live,
            'dump_bins': bins, 'historical_candidates': historical,
            'phase3_closed': False,
            'remaining': ['PSS <= -j6 live gate remains a blocker.', 'Other-kind joins are handled by plan 32, outside this unit.', 'Plan-31 Phase-1 3-14 cause-attribution residual remains.'],
            'future_check': 'A future 3-90 check 4 must compare live failing identities on the then-current disc in force with its pinned-failure identities. These cited empty sets apply only to this successor; positive or missing counts require evidence, never a default empty set.'}


def publish(root: Path = REPO, sources: dict = SOURCES) -> dict:
    result = build(root, sources)  # Validate every cited hash before writing either artifact.
    directory = root / PLAN
    (directory / 'pin_contract.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    fields = ['kind', 'checked', 'failing', 'source_path', 'source_sha256',
              'corroborating_path', 'corroborating_sha256', 'status']
    with (directory / 'pin_contract.tsv').open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, delimiter='\t', lineterminator='\n', extrasaction='ignore')
        writer.writeheader()
        writer.writerows(result['kinds'])
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['publish'])
    parser.parse_args()
    result = publish()
    print(json.dumps({'live_contract': result['live_contract']['status'],
                      'historical_disposition': result['historical_candidates']['disposition'],
                      'kind_count': len(result['kinds'])}))


if __name__ == '__main__':
    main()
