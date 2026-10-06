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


@pytest.mark.parametrize('bad', [
    'Close gate (a) full suite: 53 passed, 1317 deselected at abc1234',
    'Close gate (a) pytest parser/tests/test_x.py -> 53 passed at abc1234',
    'Close gate (a) pytest parser/tests -k parcel -> 53 passed at abc1234',
    'Close gate (a) 1370 passed on 20261006',
])
def test_gate_a_rejects_restricted_or_shaless(bad):
    assert not cg.check_text(bad)['a']['present']


@pytest.mark.parametrize('bad', ['Close gate (c) sha gate: AU 4e6b0de7 FAIL, Perth 04be2f6e MISMATCH',
                                 'Close gate (c) AU 4e6b0de7 PASS, Perth 04be2f6e differs'])
def test_gate_c_rejects_failure(bad):
    assert not cg.check_text(bad)['c']['present']


@pytest.mark.parametrize('bad', ['Close gate (b) median 58 s at -j4 (spread TBD) vs baseline TBD',
                                 'Close gate (b) median 58.2 s of 1 at -j4 (spread 0 s) vs baseline 116 s'])
def test_gate_b_needs_values_and_three_runs(bad):
    assert not cg.check_text(bad)['b']['present']


def test_phrasing_freedom_and_last_line_wins():
    text = GOOD.replace('58.2 s of 3 at -j4', '58.2 sec of 3').replace('encode wall:', 'encode wall at -j4:')
    text = text.replace('AU 4e6b0de7 PASS, Perth', 'au 4e6b0de7 pass, perth')
    text = 'Close gate (a) full suite: 1 failed, 1369 passed at abc1234\n' + text  # red then green
    g = cg.check_text(text)
    assert all(v['present'] for v in g.values()), g
    g = cg.check_text(GOOD + 'Close gate (a) full suite: 1 failed, 1369 passed at abc1234\n')  # green then red
    assert not g['a']['present']


def test_sha_resolution_and_stale(tmp_path, monkeypatch):
    def sh(*a):
        return subprocess.run(['git', '-c', 'user.name=t', '-c', 'user.email=t@t', *a], cwd=tmp_path,
                              check=True, capture_output=True, text=True).stdout.strip()
    sh('init', '-q')
    (tmp_path / 'docs').mkdir()
    (tmp_path / 'docs/D.md').write_text('d\n'); sh('add', '.'); sh('commit', '-qm', 'base')
    base = sh('rev-parse', 'HEAD')
    (tmp_path / 'docs/I.md').write_text('i\n'); sh('add', '.'); sh('commit', '-qm', 'early')
    early = sh('rev-parse', '--short', 'HEAD')
    (tmp_path / 'parser').mkdir()
    (tmp_path / 'parser/build_alldata.py').write_text('x\n'); sh('add', '.'); sh('commit', '-qm', 'enc')
    enc = sh('rev-parse', '--short', 'HEAD')
    monkeypatch.setattr(cg, 'ROOT', tmp_path)

    def at(sha):
        (tmp_path / 'docs/I.md').write_text(GOOD.replace('abc1234', sha))
        return cg.run(base, 'HEAD', 'docs/I.md')
    r = at(early)
    assert r['trigger'] and not r['pass'] and r['gates']['a']['why'].startswith('stale')
    r = at('abc1234')
    assert not r['pass'] and 'resolve' in r['gates']['a']['why']
    assert at(enc)['pass']
