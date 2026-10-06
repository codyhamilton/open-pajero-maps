"""Encoder/build close gates checker (plan 41 Phase 2; docs/WORKFLOW.md
"Encoder/build close gates").

Light, no lock, no disc reads. Given the commit a plan's design landed at
(`--base`) and the plan's IMPLEMENTATION text, report:

  trigger  whether `git diff --name-only BASE..HEAD` touches an encoder/build
           surface (TRIGGER_PATTERNS);
  gates    when it fires, whether the IMPLEMENTATION quotes all three close
           gates as marker lines (GATES):
             (a) the full `parser/tests` summary line with the sha it ran at
                 ("at <sha>"), no failures, errors, deselection or file/-k
                 filter; the sha must be a commit in BASE..HEAD at or after the
                 last trigger-surface change (else `stale`);
             (b) the full-AU encode wall: median of three at -j4, spread and
                 the baseline it is compared with;
             (c) the AU / Perth sha gate result, with no FAIL/MISMATCH/differ.
           The last marker line per gate is judged; fields may come in any order.

Exit 0 when the trigger does not fire or all gates are present, 1 when a gate
is missing, 2 on a usage or git error. `--impl-rev REV` reads the IMPLEMENTATION
as of REV (for closed plans whose folder is gone).

Usage: close_gates.py --base SHA [--head REV] --impl PATH [--impl-rev REV]
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TRIGGER_PATTERNS = (
    'parser/kiwiw/*.c', 'parser/kiwiw/*.h', 'parser/kiwiw/cenc.py', 'parser/build_alldata.py',
    'parser/kiwiw/alldata_writer.py', 'parser/kiwiw/disc.py', 'parser/tests/fixtures/goldens/*',
)
LINE = re.compile(r'^\W*Close gate \(([abc])\)[^\n]*', re.M | re.I)
# Every field is a lookahead, so phrasing order is free. The LAST marker line per gate is judged
# (the one current at close; a red-then-green history passes on its green line).
NEED = {
    'a': [re.compile(r'\b\d+ passed\b'), re.compile(r'\bat\s+`?([0-9a-f]{7,40})\b')],
    'b': [re.compile(r'-j\s?4\b'), re.compile(r'\bmedian\b[^\n]*?\d(?:\.\d+)?\s*s(?:ec)?\b', re.I),
          re.compile(r'\bof\s*(?:[3-9]|[1-9]\d+)\b', re.I), re.compile(r'\bspread\s*:?\s*\d', re.I),
          re.compile(r'\bbaseline\s*:?\s*\d', re.I)],
    'c': [re.compile(r'\bAU\b[^\n]*[0-9a-f]{8}[^\n]*\bPerth\b[^\n]*[0-9a-f]{8}', re.I)],
}
# Gate (a) must be the unrestricted suite: no failures/errors, nothing deselected, no file or -k filter.
REJECT = {
    'a': re.compile(r'\b[1-9]\d* (?:failed|errors?|deselected)\b|parser/tests/\S+\.py|\s-k\s', re.I),
    'c': re.compile(r'\b(?:FAIL\w*|MISMATCH\w*|differ\w*)\b', re.I),
}
FAILED = REJECT['a']  # back-compat name


def git(*args) -> str:
    r = subprocess.run(['git', *args], cwd=ROOT, capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(f'git {" ".join(args)}: {r.stderr.strip()}')
    return r.stdout


def _ok(*args) -> bool:
    return subprocess.run(['git', *args], cwd=ROOT, capture_output=True).returncode == 0


def triggered(paths):
    return sorted(p for p in paths if any(fnmatch.fnmatchcase(p, pat) for pat in TRIGGER_PATTERNS))


def check_text(text: str) -> dict:
    last = {}
    for m in LINE.finditer(text):
        last[m.group(1).lower()] = m.group(0).strip()
    out = {}
    for k in ('a', 'b', 'c'):
        line = last.get(k)
        why = None
        if line is None:
            why = 'no marker line'
        elif not all(rx.search(line) for rx in NEED[k]):
            why = 'field missing'
        elif k in REJECT and REJECT[k].search(line):
            why = 'rejected (failure, restriction or mismatch)'
        rec = {'present': why is None, 'line': line, 'why': why}
        if k == 'a' and line:
            m = NEED['a'][1].search(line)
            rec['sha'] = m.group(1) if m else None
        out[k] = rec
    return out


def check_sha(gate: dict, base: str, head: str, hits) -> None:
    """Gate (a)'s sha must be a commit in base..head at or after the last trigger-surface change."""
    sha = gate.get('sha')
    full = git('rev-parse', '--verify', '--quiet', f'{sha}^{{commit}}').strip() if sha and _ok(
        'rev-parse', '--verify', '--quiet', f'{sha}^{{commit}}') else None
    if not full:
        gate.update(present=False, why='sha does not resolve to a commit')
        return
    if not (_ok('merge-base', '--is-ancestor', base, full) and _ok('merge-base', '--is-ancestor', full, head)):
        gate.update(present=False, why='sha outside base..head')
        return
    last = git('log', '-1', '--format=%H', f'{base}..{head}', '--', *hits).strip()
    if last and not _ok('merge-base', '--is-ancestor', last, full):
        gate.update(present=False, why=f'stale: suite ran before trigger-surface commit {last[:7]}')


def run(base, head, impl, impl_rev=None) -> dict:
    paths = [p for p in git('diff', '--name-only', f'{base}..{head}').splitlines() if p]
    hits = triggered(paths)
    text = git('show', f'{impl_rev}:{impl}') if impl_rev else (ROOT / impl).read_text()
    gates = check_text(text)
    if hits and gates['a']['present']:
        check_sha(gates['a'], base, head, hits)
    missing = [k for k, v in gates.items() if not v['present']] if hits else []
    return {'base': base, 'head': git('rev-parse', '--short', head).strip(), 'impl': impl,
            'impl_rev': impl_rev, 'trigger': bool(hits), 'trigger_paths': hits, 'gates': gates,
            'missing': missing, 'pass': not missing}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--base', required=True)
    ap.add_argument('--head', default='HEAD')
    ap.add_argument('--impl', required=True, help='IMPLEMENTATION path relative to the repo root')
    ap.add_argument('--impl-rev')
    a = ap.parse_args(argv)
    try:
        res = run(a.base, a.head, a.impl, a.impl_rev)
    except (RuntimeError, OSError) as e:
        print(f'close_gates: {e}', file=sys.stderr)
        return 2
    print(json.dumps(res, indent=1, sort_keys=True))
    return 0 if res['pass'] else 1


if __name__ == '__main__':
    sys.exit(main())
