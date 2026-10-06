"""Plan 41 Phase 2: close-gate checker (synthetic text and trigger tests, plus
the plan 34 worked example when the history is present)."""
import importlib.util
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('close_gates', ROOT / 'parser/tools/close_gates.py')
cg = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cg)

GOOD = """
- Close gate (a) full suite: `.venv-rp/bin/python -m pytest -q parser/tests` -> 1370 passed, 7 skipped in 410s at abc1234
- Close gate (b) encode wall: median 58.2 s of 3 at -j4 (spread 1.9 s) vs baseline 115.99 s (plan 35 P1)
- Close gate (c) sha gate: AU 4e6b0de7 PASS, Perth 04be2f6e PASS
"""


def test_all_gates_present():
    g = cg.check_text(GOOD)
    assert all(v['present'] for v in g.values())


def test_failing_suite_line_is_not_a_gate():
    g = cg.check_text(GOOD.replace('1370 passed', '1 failed, 1369 passed'))
    assert not g['a']['present'] and g['b']['present']
    g = cg.check_text(GOOD.replace('1370 passed', '1370 passed, 2 errors'))
    assert not g['a']['present']


@pytest.mark.parametrize('cut,gate', [('at abc1234', 'a'), ('-j4', 'b'), ('baseline', 'b'),
                                      ('spread 1.9 s', 'b'), ('Perth 04be2f6e', 'c')])
def test_gate_needs_every_field(cut, gate):
    assert not cg.check_text(GOOD.replace(cut, ''))[gate]['present']


def test_trigger_patterns():
    hits = cg.triggered(['parser/kiwiw/_cenc.c', 'parser/kiwiw/_k1.h', 'parser/build_alldata.py',
                         'parser/tests/fixtures/goldens/l0_dense/frames.bin', 'docs/OVERVIEW.md',
                         'parser/tools/close_gates.py', 'parser/kiwiw/spool.py'])
    assert hits == ['parser/build_alldata.py', 'parser/kiwiw/_cenc.c', 'parser/kiwiw/_k1.h',
                    'parser/tests/fixtures/goldens/l0_dense/frames.bin']


def _has(rev):
    return subprocess.run(['git', 'cat-file', '-e', rev], cwd=ROOT, capture_output=True).returncode == 0


@pytest.mark.skipif(not (_has('9fb00da') and _has('4ab27e8')), reason='plan 34 history not present')
def test_plan34_close_is_missing_gates():
    r = cg.run('9fb00da', '4ab27e8', 'docs/plans/34-l0-empty-slot-frame-parity/IMPLEMENTATION.md', '4ab27e8')
    assert r['trigger'] and 'parser/build_alldata.py' in r['trigger_paths']
    assert 'a' in r['missing'] and not r['pass']
