"""Synthetic pin-contract controls. No real disc, spool, or K1 invocation."""
import csv
import hashlib
import importlib.util
import io
import json
from pathlib import Path

import pytest

PLAN = Path(__file__).resolve().parents[2] / 'docs/plans/04-c-core-orchestration/triage/oracle_chain'
spec = importlib.util.spec_from_file_location('pin_contract', PLAN / 'pin_contract.py')
pins = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pins)


def measurements():
    # Deliberately small, independently specified counts, including an unchecked kind.
    totals = {kind: {'checked': 0 if kind == 'road_point' else 7, 'failing': 0} for kind in pins.KINDS}
    comparisons = {'totals': {kind: {'new': dict(v), 'equal': True} for kind, v in totals.items()}}
    levels = {}
    for level in pins.LEVELS:
        kinds = {kind: {'checked': value['checked'] if level == '0' else 0, 'failing': 0} for kind, value in totals.items()}
        comparisons[level] = {kind: {'new': dict(v), 'equal': True} for kind, v in kinds.items()}
        levels[level] = {'kinds': kinds}
    compare = {'comparisons': comparisons, 'pass': True, 'errors': [], 'expected_k1_exit': 0,
               'new_report': 'output/scratch-29/k1_live.json'}
    report = {'totals': totals, 'levels': levels, 'pass': True, 'failing': 0,
              'timing': {'workers': 6}, 'engine': 'c', 'dump': dict.fromkeys(pins.DUMP_KINDS, 0)}
    return compare, report


def candidates():
    stream = io.StringIO()
    fields = ['kind', 'level', 'ix', 'iy', 'type', *[f'p{i}' for i in range(7)], 'shape', 'rows']
    writer = csv.DictWriter(stream, fieldnames=fields, delimiter='\t', lineterminator='\n')
    writer.writeheader()
    for i in range(100):
        row = dict.fromkeys(fields, '0')
        row.update(kind='background_boundary', ix=str(i), rows='1')
        writer.writerow(row)
    stream.write('# TOTAL_GROUPS=26650\tTOTAL_ROWS=1939931\tSHOWN=100\tTRUNCATED=yes\n')
    return stream.getvalue()


@pytest.fixture
def cited(tmp_path, monkeypatch):
    compare, report = measurements()
    manifest = {'kinds': {kind: {'file': f'{kind}.bin', 'rows': 0} for kind in pins.DUMP_KINDS}}
    values = {'compare': compare, 'report': report, 'manifest': manifest,
              'diff': {'new_sha256': pins.SUCCESSOR, 'new': 'output/scratch-29/G_new/ALLDATA.KWI'},
              'record': f'Signed successor {pins.SUCCESSOR}', 'candidates': candidates(), 'log': 'EXIT k1 0\n'}
    values['ledger'] = hashlib.sha256(values['candidates'].encode()).hexdigest()
    values['run'] = {'exit': 0, 'argv': ['python', '--disc', values['diff']['new'],
                      '--out', pins.SOURCES['report'][0], '--dump-failures', 'output/scratch-32/dump',
                      '--engine', 'c', '-j', '6', '--dump-kinds', 'interior_cover,name_anchor,background,background_boundary']}
    sources = {}
    for key, (name, _) in pins.SOURCES.items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        raw = json.dumps(values[key]).encode() if name.endswith('.json') else values[key].encode()
        path.write_bytes(raw)
        sources[key] = (name, hashlib.sha256(raw).hexdigest())
    for kind in pins.DUMP_KINDS:
        (tmp_path / 'output/scratch-32/dump' / f'{kind}.bin').write_bytes(b'')
    (tmp_path / pins.PLAN).mkdir(parents=True)
    monkeypatch.setattr(pins, 'git_inventory', lambda root: {'matching_commits': [], 'tracked_matches': []})
    return tmp_path, sources


def test_publish_cites_all_kinds_and_keeps_historical_identity_unproven(cited):
    root, sources = cited
    result = pins.publish(root, sources)
    assert result['live_contract']['status'] == 'live-empty'
    assert result['live_contract']['live_failing_set'] == []
    assert result['live_contract']['live_pinned_failure_set'] == []
    assert result['live_contract']['set_equality'] is True
    historical = result['historical_candidates']
    assert historical['disposition'] == 'residual-not-required-for-live-close'
    assert historical['exhaustive_set_equality'] is None
    assert (historical['shown_groups'], historical['total_groups'], historical['total_rows']) == (100, 26650, 1939931)
    assert result['phase3_closed'] is False
    assert len(result['dump_bins']) == 4
    rows = list(csv.DictReader((root / pins.PLAN / 'pin_contract.tsv').open(), delimiter='\t'))
    assert {r['kind'] for r in rows} == set(pins.KINDS)
    assert all(r['source_sha256'] == sources['compare'][1] for r in rows)
    assert json.loads((root / pins.PLAN / 'pin_contract.json').read_text()) == result


@pytest.mark.parametrize('bad', [None, -1, True, '0', 0.0, 1])
def test_missing_invalid_or_positive_failure_never_defaults_to_empty(bad):
    compare, report = measurements()
    compare['comparisons']['totals']['name_anchor']['new']['failing'] = bad
    evidence = {k: {'path': k, 'sha256': '0' * 64} for k in ['compare', 'report']}
    rows, live = pins.live_contract(compare, report, evidence)
    assert live['status'] == 'open'
    assert live['open_kinds'] == ['name_anchor']
    assert live['set_equality'] is None
    assert live['live_pinned_failure_set'] is None
    assert next(r for r in rows if r['kind'] == 'name_anchor')['status'] == 'open'


@pytest.mark.parametrize('change', ['missing_total', 'missing_checked', 'missing_level', 'level_failure', 'report_mismatch', 'unequal', 'extra_kind'])
def test_partial_or_conflicting_kind_census_remains_open(change):
    compare, report = measurements()
    if change == 'missing_total':
        del compare['comparisons']['totals']['background']
    elif change == 'missing_checked':
        del compare['comparisons']['totals']['background']['new']['checked']
    elif change == 'missing_level':
        del report['levels']['12']['kinds']['background']
    elif change == 'level_failure':
        compare['comparisons']['0']['background']['new']['failing'] = 1
    elif change == 'report_mismatch':
        report['totals']['background']['checked'] = 99
    elif change == 'unequal':
        compare['comparisons']['totals']['background']['equal'] = False
    else:
        report['totals']['unknown_kind'] = {'checked': 1, 'failing': 0}
    evidence = {k: {'path': k, 'sha256': '0' * 64} for k in ['compare', 'report']}
    _, live = pins.live_contract(compare, report, evidence)
    assert live['status'] == 'open'
    assert ('unknown_kind' if change == 'extra_kind' else 'background') in live['open_kinds']


def test_hash_mismatch_does_not_replace_published_artifacts(cited):
    root, sources = cited
    pins.publish(root, sources)
    before = [(root / pins.PLAN / name).read_bytes() for name in ['pin_contract.json', 'pin_contract.tsv']]
    (root / sources['compare'][0]).write_text('{}')
    with pytest.raises(ValueError, match='SHA-256 mismatch'):
        pins.publish(root, sources)
    assert before == [(root / pins.PLAN / name).read_bytes() for name in ['pin_contract.json', 'pin_contract.tsv']]


def test_own_synthetic_matches_are_not_promoted_to_historical_recovery(cited):
    root, sources = cited
    fixture = root / 'output/scratch-31/tests-p2/retained/enumerate_fixture.tsv'
    fixture.parent.mkdir(parents=True)
    fixture.write_text('synthetic')
    link = root / 'output/fixture_link'
    link.symlink_to(fixture.parent, target_is_directory=True)
    result = pins.build(root, sources)
    scan = result['historical_candidates']['output_inventory']
    assert len(scan['matches']) == len(scan['synthetic_test_matches']) == 1
    assert scan['historical_recovery_candidates'] == []
    assert result['historical_candidates']['exhaustive_set_equality'] is None


@pytest.mark.parametrize('change', ['disc_pin', 'run_path', 'exit', 'dump_rows', 'bin_bytes', 'bin_missing'])
def test_cited_binding_and_empty_bin_controls(cited, change):
    root, sources = cited
    data, evidence = pins.load_sources(root, sources)
    if change == 'disc_pin':
        data['diff']['new_sha256'] = '1' * 64
    elif change == 'run_path':
        data['run']['argv'][2] = 'other.bin'
    elif change == 'exit':
        data['run']['exit'] = 1
    elif change == 'dump_rows':
        data['manifest']['kinds']['background']['rows'] = 1
    elif change == 'bin_bytes':
        (root / 'output/scratch-32/dump/background.bin').write_bytes(b'x')
    else:
        (root / 'output/scratch-32/dump/background.bin').unlink()
    with pytest.raises(ValueError):
        pins.verify_binding(data, evidence, root)


@pytest.mark.parametrize('change', ['footer', 'shown', 'duplicate', 'ledger'])
def test_historical_view_requires_signed_footer_and_distinct_groups(change):
    text = candidates()
    sha = '2' * 64
    ledger = sha
    if change == 'footer':
        text = text.replace('TOTAL_GROUPS=26650', 'TOTAL_GROUPS=100')
    elif change == 'shown':
        text = '\n'.join(text.splitlines()[1:])
    elif change == 'duplicate':
        lines = text.splitlines(); lines[2] = lines[1]; text = '\n'.join(lines)
    else:
        ledger = 'absent'
    with pytest.raises(ValueError):
        pins.historical_view(text, ledger, sha)


def test_inventory_follows_symlinks_at_depth_and_avoids_loops_and_protected_dirs(tmp_path):
    output = tmp_path / 'output'; output.mkdir()
    target = tmp_path / 'retained/a/b/c'; target.mkdir(parents=True)
    (target / 'enumerate_background.tsv').write_text('synthetic candidate')
    (target / 'pins_names.tsv').write_text('synthetic candidate')
    (output / 'link').symlink_to(target.parent.parent, target_is_directory=True)
    (target / 'loop').symlink_to(output, target_is_directory=True)
    for name in ['spool', 'R']:
        path = output / name; path.mkdir()
        (path / 'enumerate_forbidden.tsv').write_text('must not be inventoried')
    result = pins.inventory(output)
    assert sorted(Path(p).name for p in result['matches']) == ['enumerate_background.tsv', 'pins_names.tsv']
    assert result['excluded_protected_directory_count'] == 2
    assert result['errors'] == []


def test_read_refuses_disc_and_symlink_to_protected_path_before_opening(tmp_path):
    # The forbidden target need not exist: refusal must precede any open.
    (tmp_path / 'report.json').symlink_to(tmp_path / 'ALLDATA.KWI')
    for name in ['ALLDATA.KWI', 'report.json']:
        with pytest.raises(ValueError, match='Protected input refused'):
            pins.read_pinned(tmp_path, name, '0' * 64)
