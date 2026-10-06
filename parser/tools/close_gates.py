"""Encoder/build close gates checker (plan 41 Phase 2; docs/WORKFLOW.md
"Encoder/build close gates").

Light, no lock, no disc reads. Given the commit a plan's design landed at
(`--base`) and the plan's IMPLEMENTATION text, report:

  trigger  whether `git diff --name-only BASE..HEAD` touches an encoder/build
           surface (TRIGGER_PATTERNS);
  gates    when it fires, whether the IMPLEMENTATION quotes all three close
           gates as marker lines (GATES):
             (a) the full `parser/tests` summary line with the HEAD sha it ran
                 at, and no failures or errors;
             (b) the full-AU encode wall: median of three at -j4, spread and
                 the baseline it is compared with;
             (c) the AU / Perth sha gate result.

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
SHA = r'\b[0-9a-f]{7,40}\b'
GATES = {
    'a': re.compile(r'^\W*Close gate \(a\)[^\n]*\b\d+ passed\b[^\n]*' + SHA, re.M),
    'b': re.compile(r'^\W*Close gate \(b\)[^\n]*\bmedian\b[^\n]*\d(?:\.\d+)?\s*s\b[^\n]*-j\s?4\b'
                    r'[^\n]*\bspread\b[^\n]*\bbaseline\b', re.M | re.I),
    'c': re.compile(r'^\W*Close gate \(c\)[^\n]*\bAU\b[^\n]*[0-9a-f]{8}[^\n]*\bPerth\b[^\n]*[0-9a-f]{8}', re.M),
}
FAILED = re.compile(r'\b([1-9]\d*) (failed|errors?)\b')


def git(*args) -> str:
    r = subprocess.run(['git', *args], cwd=ROOT, capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(f'git {" ".join(args)}: {r.stderr.strip()}')
    return r.stdout


def triggered(paths):
    return sorted(p for p in paths if any(fnmatch.fnmatchcase(p, pat) for pat in TRIGGER_PATTERNS))


def check_text(text: str) -> dict:
    out = {}
    for k, rx in GATES.items():
        m = rx.search(text)
        line = m.group(0).strip() if m else None
        ok = bool(m)
        if ok and k == 'a' and FAILED.search(line):
            ok = False
        out[k] = {'present': ok, 'line': line}
    return out


def run(base, head, impl, impl_rev=None) -> dict:
    paths = [p for p in git('diff', '--name-only', f'{base}..{head}').splitlines() if p]
    hits = triggered(paths)
    text = git('show', f'{impl_rev}:{impl}') if impl_rev else (ROOT / impl).read_text()
    gates = check_text(text)
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
