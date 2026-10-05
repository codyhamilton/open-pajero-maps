#!/usr/bin/env python3
"""Assert the successor K1 contract; run through Execute's heavy Python guard."""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
BASELINE = ROOT / 'output/scratch-14/runs/rem01_k1_live.json'


def load(path):
    return json.loads(Path(path).read_text())


def compare(baseline, new, manifest):
    errors = []
    def check(ok, message):
        if not ok:
            errors.append(message)
    drops = manifest['out_of_span_names_dropped']
    check(drops == {lv: int(lv == '0') for lv in baseline['levels']},
          'drop counts must equal Phase 1: L0=1, other levels=0')
    check(set(new['levels']) == set(baseline['levels']), 'level set differs')
    check(new.get('engine') == 'c', 'successor K1 engine must be c')
    check(new['tolerance_raw'] == baseline['tolerance_raw'] == 0.5, 'tolerance differs')
    comparisons = {}
    scopes = [('totals', baseline['totals'], new['totals'], sum(drops.values()))]
    scopes += [(lv, old['kinds'], new['levels'].get(lv, {}).get('kinds', {}), drops.get(lv, 0))
               for lv, old in baseline['levels'].items()]
    for scope, old, current, dropped in scopes:
        check(set(old) == set(current), f'{scope}: kind set differs')
        comparisons[scope] = {}
        for kind, before in old.items():
            after = current.get(kind, {})
            expected = dict(before)
            if kind == 'name_anchor':
                expected.update(checked=before['checked'] - dropped, failing=0)
                ok = all(after.get(k) == expected[k] for k in ('checked', 'failing'))
            elif kind == 'range':
                # Each decoded name anchor is also one range-check vertex
                # (parser/kiwiw/_k1.c range_item for name records), so a
                # dropped name lowers range checked by exactly one; failing
                # and worst error must be unchanged (Execute amendment).
                expected.update(checked=before['checked'] - dropped)
                ok = after == expected
            else:
                ok = after == expected
            check(ok, f'{scope}/{kind}: {after} != {expected}')
            comparisons[scope][kind] = {'baseline': before, 'new': after, 'expected': expected, 'equal': ok}
    completeness = new['totals'].get('completeness', {})
    check((completeness.get('checked'), completeness.get('failing')) == (1800514, 0),
          'completeness must be 1800514 checked / 0 failing')
    check(new.get('pass') is True and new.get('failing') == 0,
          'successor K1 must report pass=true, failing=0')
    check(sum(k['failing'] for k in new['totals'].values()) == 0, 'a kind still fails')
    return {'pass': not errors, 'errors': errors, 'drops_per_level': drops,
            'expected_k1_exit': 0, 'comparisons': comparisons}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--baseline-run', type=Path, default=BASELINE)
    ap.add_argument('--new', type=Path, required=True)
    ap.add_argument('--manifest', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    run = load(args.baseline_run)
    argv = run['argv']
    baseline_path = Path(argv[argv.index('--out') + 1])
    if not baseline_path.is_absolute():
        baseline_path = Path(run['cwd']) / baseline_path
    result = compare(load(baseline_path), load(args.new), load(args.manifest))
    if run['exit'] != 1:
        result['errors'].append('baseline run must have historical K1 exit 1')
        result['pass'] = False
    result.update(baseline_run=str(args.baseline_run), baseline_report=str(baseline_path),
                  new_report=str(args.new))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'comparisons'}, sort_keys=True))
    return 0 if result['pass'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
