#!/usr/bin/env python3
"""Bounded memory validation for the residual extension (plan 05, Phase 1, brief 1-01).

Subcommands
    (none) / run   controller: build fixtures, run paired baseline/candidate workers each in
                   its own `systemd-run --user --scope`, gate on max RSS, cgroup memory.peak,
                   growth, wall time and output SHA256s, write a results JSON.
    genfix         generate a seeded fixture directory (separate process).
    worker         one measured run, executed inside the scope (never inherits a fixture).
    finalize-run   Phase-2: three paired baseline/candidate finalize runs on 1,000,013 rows;
                   gates RSS delta (>=140626 KiB), output SHA256s, counts, part deletion, wall.
                   CLI: flock output/.heavy.lock .venv-rp/bin/python parser/tools/bench_dump_memory.py
                        finalize-run --out output/scratch-5-02/results.json

Also provides the fixture writers and the isolated replay-root machinery that the tests
(`parser/tests/test_dump_join_memory.py`) import.  The frozen baseline (vendored verbatim in
`parser/tests/fixtures/dump_join_baseline/`) is replayed only inside a replay root under
`output/scratch-5-01/`; `check_isolated` refuses to start if any path reaches the real
repository `output/` (so the real `scratch-3-12/dump_ext` cannot be overwritten).
Run the controller under `flock output/.heavy.lock`.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import importlib.util
import json
import os
import re
import shutil
import statistics
import subprocess
import sys
import time
import traceback
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
SCRATCH = REPO / 'output' / 'scratch-5-01'
BASELINE_DIR = REPO / 'parser' / 'tests' / 'fixtures' / 'dump_join_baseline'
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
import dump_join  # noqa: E402
from tools import quantisation_roundtrip as qr  # noqa: E402
from kiwiw import cenc  # noqa: E402

GROUP = dump_join.GROUP
TS = dump_join.TS
FIELDS = [{'name': n, 'type': t} for n, t in [
    ('lat', 'f64'), ('lon', 'f64'), ('err', 'f64'), ('ix', 'i32'), ('iy', 'i32'), ('vx', 'i32'), ('vy', 'i32'),
    ('reason', 'i32'), ('code', 'i32'), ('p0', 'u16'), ('p1', 'u16'), ('p2', 'u16'), ('p3', 'u16'), ('p4', 'u16'),
    ('p5', 'u16'), ('p6', 'u16'), ('depth', 'u8'), ('kind', 'u8'), ('level', 'u8'), ('shape', 'i32'),
    ('vert', 'i32'), ('onb', 'u8'), ('d_any', 'f64'), ('any_type', 'i32'), ('in_eo_same', 'u8'),
    ('in_wn_same', 'u8'), ('in_eo_any', 'u8'), ('src_ix', 'i32'), ('src_iy', 'i32'), ('src_rec', 'i32'),
    ('src_tall', 'u8'), ('src_nv', 'i32'), ('src_maxseg', 'f64'), ('d_src', 'f64'), ('dcls', 'i32'),
    ('dnv', 'i32'), ('s02_producer_verified', 'u8'), ('other_mechanism', 'u8')]]
DT = np.dtype([(f['name'], TS[f['type']]) for f in FIELDS], align=True)
SIDE_DT = np.dtype([(k, '<i4') for k in GROUP] + [('status', '<i4'), ('aux', 'u1', (26,))])
assert DT.itemsize == 152 and SIDE_DT.itemsize == 78

REL_SRC = Path('output/scratch-3-11/dump_new_ext')
REL_ASSIGN = Path('output/scratch-3-11/classify_new')
REL_SIDE = Path('output/scratch-3-12')
REL_WIT = Path('output/scratch-3-07')
KIB_BOUND = 2 * 65536 * 152 // 1024  # 19,456 KiB, Assumption 2
SEED = 20260502
SCRATCH_FIN = REPO / 'output' / 'scratch-5-02'
FINALIZE_KIND = 'background_boundary'
FINALIZE_BASELINE_DIR = REPO / 'parser' / 'tests' / 'fixtures' / 'finalize_dump_baseline'
FINALIZE_KIB_GATE = 1000013 * 144 // 1024          # 140626
FINALIZE_DEFAULT_ROWS = 1000013
FINALIZE_DEFAULT_PARTS = 8

SCRATCH_P3 = REPO / 'output' / 'scratch-5-03'
S07_BASELINE_DIR = REPO / 'parser' / 'tests' / 'fixtures' / 'extend_3_07_baseline'
TRIAGE_BASELINE_DIR = REPO / 'parser' / 'tests' / 'fixtures' / 'k1_triage_baseline'
S07_KIB_GROWTH = 65536 * (144 + 152) // 1024  # 18,944
TRIAGE_KIB_GROWTH = 65536 * 152 // 1024  # 9,728
S07_SEED = 20260503


def _finalize_env() -> dict:
    env = dict(os.environ)
    tmp = SCRATCH_FIN / 'tmp'
    tmp.mkdir(parents=True, exist_ok=True)
    env['TMPDIR'] = str(tmp)
    return env


# ---------------------------------------------------------------- fixtures
def write_fixture(fixdir, kinds: dict) -> None:
    """kinds: name -> dict(rows=structured ndarray (DT), assign=u16 ndarray, side=None|ndarray)."""
    fixdir = Path(fixdir)
    for rel in (REL_SRC, REL_ASSIGN, REL_SIDE):
        (fixdir / rel).mkdir(parents=True, exist_ok=True)
    man = {'engine': 'c', 'fields': FIELDS, 'row_size': 152, 'tool': 'bench_dump_memory', 'kinds': {}}
    for name, k in kinds.items():
        rows = np.ascontiguousarray(k['rows'])
        assert rows.dtype == DT
        (fixdir / REL_SRC / f'{name}.bin').write_bytes(rows.tobytes())
        np.ascontiguousarray(k['assign'], '<u2').tofile(fixdir / REL_ASSIGN / f'assign_{name}.u16')
        if k.get('side') is not None:
            np.save(fixdir / REL_SIDE / f'side_{name}.npy', k['side'])
        man['kinds'][name] = {'fields': FIELDS, 'file': f'{name}.bin', 'row_size': 152, 'rows': int(len(rows))}
    (fixdir / REL_SRC / 'dump_manifest.json').write_text(json.dumps(man, indent=2) + '\n')


def random_rows(rng, n: int) -> np.ndarray:
    """Rows with random bytes everywhere, incl. NaN-payload floats and nonzero padding/byte146."""
    raw = rng.integers(0, 256, (n, 152), dtype=np.uint8)
    return raw.view(DT).reshape(n)


def _gen_pool(rng, g: int) -> np.ndarray:
    kd = np.dtype([(k, DT[k]) for k in GROUP])
    pool = np.empty(g, kd)
    pool['level'] = rng.integers(0, 3, g)
    pool['ix'] = rng.integers(0, 2000, g)
    pool['iy'] = rng.integers(0, 2000, g)
    pool['code'] = rng.integers(0, 400, g)
    for i in range(7):
        pool[f'p{i}'] = rng.integers(0, 40 if i < 3 else 4, g)
    pool['shape'] = rng.integers(0, 20, g)
    return pool


def _gen_side(rng, pool: np.ndarray, n: int) -> np.ndarray:
    side = np.zeros(n, SIDE_DT)
    nhit = int(0.8 * n)
    idx = rng.integers(0, len(pool), nhit)
    for f in GROUP:
        side[f][:nhit] = pool[f][idx]
    side['ix'][nhit:] = 100000 + np.arange(n - nhit)  # exact misses
    side['status'] = rng.integers(0, 2, n)
    side['aux'] = rng.integers(0, 256, (n, 26), dtype=np.uint8)
    return side[rng.permutation(n)]


def gen_bulk(fixdir, rows: int, seed: int = SEED, side_rows: int = 216488, groups: int = 60000,
             kind: str = 'bench', chunk: int = 250000) -> dict:
    """Seeded bulk fixture (one kind). Pool and side tables depend on seed only, not on `rows`."""
    fixdir = Path(fixdir)
    for rel in (REL_SRC, REL_ASSIGN, REL_SIDE):
        (fixdir / rel).mkdir(parents=True, exist_ok=True)
    pool = _gen_pool(np.random.default_rng([seed, 1]), groups)
    side = _gen_side(np.random.default_rng([seed, 2]), pool, side_rows)
    np.save(fixdir / REL_SIDE / f'side_{kind}.npy', side)
    used = np.zeros(groups, bool)
    with open(fixdir / REL_SRC / f'{kind}.bin', 'wb') as fb, open(fixdir / REL_ASSIGN / f'assign_{kind}.u16', 'wb') as fa:
        for ci, lo in enumerate(range(0, rows, chunk)):
            n = min(chunk, rows - lo)
            rng = np.random.default_rng([seed, 3, ci])
            a = random_rows(rng, n)
            gi = rng.integers(0, groups, n)
            used[gi] = True
            for f in GROUP:
                a[f] = pool[f][gi]
            fb.write(a.tobytes())
            asg = np.where(rng.random(n) < 0.3, 65535, rng.integers(0, 500, n)).astype('<u2')
            fa.write(asg.tobytes())
        fb.flush(); os.fsync(fb.fileno()); fa.flush(); os.fsync(fa.fileno())
    man = {'engine': 'c', 'fields': FIELDS, 'row_size': 152, 'tool': 'bench_dump_memory',
           'kinds': {kind: {'fields': FIELDS, 'file': f'{kind}.bin', 'row_size': 152, 'rows': rows}}}
    (fixdir / REL_SRC / 'dump_manifest.json').write_text(json.dumps(man, indent=2) + '\n')
    sidekeys = np.empty(len(side), np.dtype([(k, '<i4') for k in GROUP]))
    for f in GROUP:
        sidekeys[f] = side[f]
    meta = {'seed': seed, 'rows': rows, 'side_rows': side_rows, 'group_pool': groups,
            'distinct_pool_keys': int(len(np.unique(pool))), 'groups_used_by_rows': int(used.sum()),
            'distinct_side_keys': int(len(np.unique(sidekeys))), 'chunk': chunk, 'kind': kind,
            'window_rows': dump_join.DEFAULT_WINDOW,
            'windows': -(-rows // dump_join.DEFAULT_WINDOW)}
    (fixdir / 'fixture.json').write_text(json.dumps(meta, indent=2) + '\n')
    for p in sorted(fixdir.rglob('*')):
        if p.is_file():
            fd = os.open(p, os.O_RDONLY); os.fsync(fd); os.close(fd)
    return meta


def finalize_genfix(fixdir, rows: int, seed: int = SEED, parts: int = FINALIZE_DEFAULT_PARTS) -> dict:
    """Seeded Phase-2 finalize fixture: one kind split into `parts` files.

    Every DUMP_ORDER key is zero so a stable sort must preserve input order.
    Observability uses unique struct-padding markers at byte offset 65 (not a
    named field). Named fields outside DUMP_ORDER stay zero — NumPy uses them
    as tie-breakers, so unique `dcls` alone would make unstable sort match
    stable and would not prove stability. `seed` is retained for meta only.
    """
    fixdir = Path(fixdir)
    d = fixdir / 'parts'
    d.mkdir(parents=True, exist_ok=True)
    arr = np.zeros(rows, dtype=cenc.K1_DUMP_DTYPE)
    pad = arr.view(np.uint8).reshape(rows, cenc.K1_DUMP_DTYPE.itemsize)
    pad[:, 65] = (np.arange(rows) % 251) + 1
    for i, chunk in enumerate(np.array_split(arr, parts)):
        chunk.tofile(d / f"part_{i:05d}_{FINALIZE_KIND}.bin")
    paths = sorted(d.glob('part_*.bin'))
    for p in paths:
        fd = os.open(p, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    fd = os.open(d, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)
    meta = {'rows': rows, 'seed': seed, 'parts': parts, 'kind': FINALIZE_KIND,
            'parts_sha256': {p.name: sha256_file(p) for p in paths}}
    (fixdir / 'fixture.json').write_text(json.dumps(meta, indent=2) + '\n')
    return meta


class IsolationError(Exception):
    pass


def baseline_witness_group() -> tuple:
    for line in (BASELINE_DIR / 'witness.py').read_text().splitlines():
        if line.startswith('GROUP = ('):
            g = ast.literal_eval(line.split('=', 1)[1].strip())
            assert g == GROUP, 'vendored witness GROUP differs from the contract GROUP'
            return g
    raise AssertionError('GROUP line not found in vendored witness.py')


def _check_sums() -> dict:
    sums = {}
    for line in (BASELINE_DIR / 'SHA256SUMS').read_text().splitlines():
        h, n = line.split()
        assert sha256_file(BASELINE_DIR / n) == h, f'vendored {n} differs from SHA256SUMS'
        sums[n] = h
    return sums


def materialise_replay_root(fixdir, root) -> Path:
    """Replay root reproducing the baseline's hard-coded relative paths; inputs are symlinks into the fixture."""
    fixdir, root = Path(fixdir).resolve(), Path(root)
    _check_sums()
    for rel in (REL_SRC, REL_ASSIGN, REL_SIDE, REL_WIT):
        (root / rel).mkdir(parents=True, exist_ok=True)
        if (fixdir / rel).is_dir():
            for p in sorted((fixdir / rel).iterdir()):
                if p.is_file():
                    os.symlink(p, root / rel / p.name)
    g = baseline_witness_group()
    (root / REL_WIT / 'witness.py').write_text(f'GROUP = {g!r}\n')
    for n in ('extend.py', 'study.py'):
        shutil.copyfile(BASELINE_DIR / n, root / n)
    return root


def replay_paths(root) -> list[Path]:
    root = Path(root)
    out = [root, root / REL_SRC, root / REL_ASSIGN, root / REL_SIDE, root / REL_WIT, root / 'extend.py',
           root / 'study.py', root / REL_SIDE / 'dump_ext', root / REL_SIDE / 'joined_counts.json']
    for rel in (REL_SRC, REL_ASSIGN, REL_SIDE, REL_WIT):
        d = root / rel
        if d.is_dir():
            out += sorted(d.iterdir())
    return out


def check_isolated(root) -> None:
    """Refuse (raise, no side effects) if any replay path resolves into the real output/ outside scratch-5-01."""
    real_out = (REPO / 'output').resolve()
    allowed = SCRATCH.resolve()
    rr = Path(os.path.realpath(root))
    if not rr.is_relative_to(allowed) or rr == allowed:
        raise IsolationError(f'replay root {root} resolves outside {allowed}')
    for p in replay_paths(root):
        rp = Path(os.path.realpath(p))
        if (rp == real_out or rp.is_relative_to(real_out)) and not rp.is_relative_to(allowed):
            raise IsolationError(f'{p} resolves to {rp}, inside the real output/')


def _env(root=None) -> dict:
    env = dict(os.environ)
    (SCRATCH / 'tmp').mkdir(parents=True, exist_ok=True)
    env['TMPDIR'] = str(SCRATCH / 'tmp')
    if root is not None:
        env['PYTHONPATH'] = str(root)
    return env


def run_baseline(root) -> subprocess.CompletedProcess:
    check_isolated(root)
    return subprocess.run([sys.executable, 'extend.py'], cwd=root, env=_env(root), capture_output=True, text=True)


def run_candidate(root, *args) -> subprocess.CompletedProcess:
    check_isolated(root)
    env = _env()
    env.pop('PYTHONPATH', None)
    return subprocess.run([sys.executable, str(HERE / 'dump_join.py'), *args], cwd=root, env=env,
                          capture_output=True, text=True)


def sha256_file(p) -> str:
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def sha256_paths(paths) -> dict:
    """SHA256 via coreutils in a separate process."""
    paths = [str(p) for p in paths]
    if not paths:
        return {}
    r = subprocess.run(['sha256sum', *paths], capture_output=True, text=True, check=True)
    return {l.split(None, 1)[1]: l.split()[0] for l in r.stdout.splitlines()}


def output_hashes(root) -> dict:
    root = Path(root)
    d = root / REL_SIDE / 'dump_ext'
    files = sorted(d.iterdir()) if d.is_dir() else []
    cj = root / REL_SIDE / 'joined_counts.json'
    if cj.exists():
        files.append(cj)
    h = sha256_paths(files)
    return {Path(k).relative_to(root).as_posix(): v for k, v in h.items()}


# ---------------------------------------------------------------- worker
def _cgroup_snapshot() -> dict:
    snap = {}
    try:
        line = [l for l in Path('/proc/self/cgroup').read_text().splitlines() if l.startswith('0::')][0]
        cg = Path('/sys/fs/cgroup') / line[3:].lstrip('/')
        snap['cgroup'] = str(cg)
        snap['memory_peak'] = int((cg / 'memory.peak').read_text())
        snap['memory_current'] = int((cg / 'memory.current').read_text())
        st = dict(l.split() for l in (cg / 'memory.stat').read_text().splitlines())
        for k in ('anon', 'file', 'file_dirty', 'file_writeback', 'file_mapped'):
            snap[k] = int(st[k])
        snap['memory_pressure'] = (cg / 'memory.pressure').read_text()
    except Exception as e:  # reported, then gated as missing
        snap['error'] = repr(e)
    return snap


def worker(mode: str, root: str, marker: str) -> int:
    import runpy
    t0 = time.perf_counter()
    os.chdir(root)
    rc = 0
    try:
        if mode == 'baseline':
            sys.path.insert(0, root)
            sys.argv = ['extend.py']
            runpy.run_path('extend.py', run_name='__main__')
        else:
            rc = dump_join.main(['--verify'] if mode == 'candidate-verify' else [])
    except SystemExit as e:
        rc = int(e.code or 0)
    wall = time.perf_counter() - t0
    snap = _cgroup_snapshot()  # tiny trailer after the transformation; memory.peak is a high-water mark
    snap.update(mode=mode, transform_wall_s=wall, rc=rc)
    Path(marker, 'cgroup.json').write_text(json.dumps(snap, indent=2))
    return rc


def _preread(paths) -> None:
    for p in paths:
        fd = os.open(p, os.O_RDONLY)
        try:
            while os.read(fd, 8 << 20):
                pass
            os.posix_fadvise(fd, 0, 0, os.POSIX_FADV_WILLNEED)
        finally:
            os.close(fd)


def _parse_time(p: Path) -> dict:
    t = p.read_text()
    rss = int(re.search(r'Maximum resident set size \(kbytes\): (\d+)', t).group(1))
    el = re.search(r'Elapsed \(wall clock\) time \(h:mm:ss or m:ss\): ([\d:.]+)', t).group(1)
    secs = 0.0
    for part in el.split(':'):
        secs = secs * 60 + float(part)
    return {'max_rss_kib': rss, 'time_v_elapsed_s': secs}


def run_scoped(mode: str, fixdir: Path, tag: str, unit_seq: int) -> dict:
    rundir = SCRATCH / 'bench' / f'run-{tag}'
    shutil.rmtree(rundir, ignore_errors=True)
    root = materialise_replay_root(fixdir, rundir / 'root')
    check_isolated(root)
    marker = rundir / 'marker'
    marker.mkdir(parents=True)
    _preread([p.resolve() for p in replay_paths(root) if p.is_file()])
    unit = f'dumpjoin-bench-{os.getpid()}-{unit_seq}'
    cmd = ['systemd-run', '--user', '--scope', '--quiet', '-p', 'MemoryAccounting=yes', f'--unit={unit}', '--',
           '/usr/bin/time', '-v', '-o', str(marker / 'time.txt'), sys.executable, str(Path(__file__).resolve()),
           'worker', '--mode', mode, '--root', str(root), '--marker', str(marker)]
    t0 = time.perf_counter()
    with open(marker / 'stdout.txt', 'w') as so, open(marker / 'stderr.txt', 'w') as se:
        p = subprocess.run(cmd, stdout=so, stderr=se, env=_env(root if mode == 'baseline' else None))
    wall = time.perf_counter() - t0
    res = {'mode': mode, 'tag': tag, 'unit': unit, 'exit': p.returncode, 'wall_s': wall}
    try:
        res.update(_parse_time(marker / 'time.txt'))
        res['cgroup'] = json.loads((marker / 'cgroup.json').read_text())
    except Exception as e:
        res['marker_error'] = repr(e)
    res['stdout_sha256'] = sha256_file(marker / 'stdout.txt')
    res['output_sha256'] = output_hashes(root)
    shutil.rmtree(rundir, ignore_errors=True)
    return res


# ---------------------------------------------------------------- phase 2: finalize
def finalize_output_hashes(dump_dir) -> dict:
    d = Path(dump_dir)
    out = {}
    for name in (f'{FINALIZE_KIND}.bin', 'dump_manifest.json'):
        p = d / name
        if p.exists():
            out[name] = sha256_file(p)
    return out


def finalize_worker(mode: str, root: str, marker: str, ntasks: int) -> int:
    t0 = time.perf_counter()
    logs = []
    log = logs.append
    rc, counts = 0, {}
    try:
        if mode == 'baseline':
            spec = importlib.util.spec_from_file_location(
                'finalize_dump_baseline', FINALIZE_BASELINE_DIR / 'finalize_dump_baseline.py')
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            counts = mod.finalize_dump_baseline(Path(root), [FINALIZE_KIND], ntasks, log)
        else:
            counts = qr._finalize_dump(Path(root), [FINALIZE_KIND], ntasks, log)
    except Exception:
        log(traceback.format_exc())
        rc = 1
    wall = time.perf_counter() - t0
    snap = _cgroup_snapshot()
    snap.update(mode=mode, finalize_wall_s=wall, rc=rc)
    marker = Path(marker)
    marker.mkdir(parents=True, exist_ok=True)
    (marker / 'cgroup.json').write_text(json.dumps(snap, indent=2))
    (marker / 'counts.json').write_text(json.dumps(counts, indent=2))
    (marker / 'log.txt').write_text('\n'.join(logs))
    return rc


def finalize_controller(out, rows: int, pairs: int, seed: int, parts: int) -> int:
    SCRATCH_FIN.mkdir(parents=True, exist_ok=True)
    fixdir = SCRATCH_FIN / 'fixture'
    meta_p = fixdir / 'fixture.json'
    meta = json.loads(meta_p.read_text()) if meta_p.exists() else {}
    if meta.get('rows') != rows or meta.get('seed') != seed or meta.get('parts') != parts:
        shutil.rmtree(fixdir, ignore_errors=True)
        subprocess.run([sys.executable, str(Path(__file__).resolve()), 'finalize-genfix', '--dir', str(fixdir),
                        '--rows', str(rows), '--seed', str(seed), '--parts', str(parts)], check=True, env=_finalize_env())
    fixture_parts = fixdir / 'parts'
    fixture_paths = sorted(fixture_parts.glob('part_*.bin'))
    _preread(fixture_paths)
    input_sha256 = {Path(k).name: v for k, v in sha256_paths(fixture_paths).items()}

    base, cand = [], []
    for i in range(pairs):
        order = ['baseline', 'candidate'] if i % 2 == 0 else ['candidate', 'baseline']
        for mode in order:
            rundir = SCRATCH_FIN / 'runs' / f'run-{i}-{mode}'
            shutil.rmtree(rundir, ignore_errors=True)
            dumpdir = rundir / 'dump'
            shutil.copytree(fixture_parts, dumpdir)
            marker = rundir / 'marker'
            marker.mkdir(parents=True, exist_ok=True)
            for fp in sorted(dumpdir.glob('part_*.bin')):
                fd = os.open(fp, os.O_RDONLY)
                try:
                    os.fsync(fd)
                finally:
                    os.close(fd)
            _preread(sorted(dumpdir.glob('part_*.bin')))
            unit = f'finalize-bench-{os.getpid()}-{i}-{mode}'
            cmd = ['systemd-run', '--user', '--scope', '--quiet', '-p', 'MemoryAccounting=yes', f'--unit={unit}', '--',
                   '/usr/bin/time', '-v', '-o', str(marker / 'time.txt'), sys.executable,
                   str(Path(__file__).resolve()), 'finalize-worker', '--mode', mode, '--root', str(dumpdir),
                   '--marker', str(marker), '--ntasks', str(parts)]
            with open(marker / 'stdout.txt', 'w') as so, open(marker / 'stderr.txt', 'w') as se:
                p = subprocess.run(cmd, stdout=so, stderr=se, env=_finalize_env())
            rec = {'pair': i, 'mode': mode, 'unit': unit, 'exit': p.returncode}
            try:
                rec.update(_parse_time(marker / 'time.txt'))
                rec['cgroup'] = json.loads((marker / 'cgroup.json').read_text())
                rec['counts'] = json.loads((marker / 'counts.json').read_text())
            except Exception as e:
                rec['marker_error'] = repr(e)
            rec['output_sha256'] = finalize_output_hashes(dumpdir)
            rec['parts_left'] = [q.name for q in dumpdir.glob('part_*.bin')]
            shutil.rmtree(rundir, ignore_errors=True)
            (base if mode == 'baseline' else cand).append(rec)
            print(f'pair {i} {mode}: exit={rec["exit"]} rss={rec.get("max_rss_kib")} '
                  f'wall={rec.get("finalize_wall_s", rec.get("time_v_elapsed_s"))}', flush=True)

    gates, fails = {}, []

    def gate(name, ok, detail):
        gates[name] = {'pass': bool(ok), 'detail': detail}
        if not ok:
            fails.append(name)

    for i in range(pairs):
        b, c = base[i], cand[i]
        gate(f'pair{i}_exit0', b['exit'] == 0 and c['exit'] == 0, f'baseline {b["exit"]}, candidate {c["exit"]}')
        b_rss, c_rss = b.get('max_rss_kib'), c.get('max_rss_kib')
        ok = b_rss is not None and c_rss is not None and (b_rss - c_rss) >= FINALIZE_KIB_GATE
        gate(f'pair{i}_rss_delta', ok, f'base {b_rss} KiB - cand {c_rss} KiB (gate {FINALIZE_KIB_GATE} KiB)')
        gate(f'pair{i}_output_sha_equal', b.get('output_sha256') == c.get('output_sha256'),
             f'cand {c.get("output_sha256")} vs base {b.get("output_sha256")}')
        gate(f'pair{i}_counts_equal', b.get('counts') == c.get('counts'),
             f'cand {c.get("counts")} vs base {b.get("counts")}')
        gate(f'pair{i}_parts_deleted', b.get('parts_left') == [] and c.get('parts_left') == [],
             f'baseline left {b.get("parts_left")}, candidate left {c.get("parts_left")}')

    def wall_s(r):
        return r.get('finalize_wall_s', r.get('time_v_elapsed_s'))

    bw = [wall_s(r) for r in base if wall_s(r) is not None]
    cw = [wall_s(r) for r in cand if wall_s(r) is not None]
    if bw and cw:
        mb, mc = statistics.median(bw), statistics.median(cw)
        gate('median_wall_le_2x', mc <= 2 * mb, f'cand median {mc:.3f}s vs base median {mb:.3f}s ratio {mc / mb:.3f}')
    else:
        gate('median_wall_le_2x', False, 'missing finalize_wall_s')

    results = {
        'python': sys.version, 'numpy': np.__version__,
        'baseline_source_sha256': sha256_file(FINALIZE_BASELINE_DIR / 'finalize_dump_baseline.py'),
        'seed': seed, 'rows': rows, 'parts': parts, 'pairs': pairs,
        'fixture_input_sha256': input_sha256,
        'baseline_runs': base, 'candidate_runs': cand,
        'gates': gates, 'failed': fails,
        'time_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, indent=2) + '\n')
    for k, v in gates.items():
        print(('PASS ' if v['pass'] else 'FAIL ') + k, v['detail'], flush=True)
    return 1 if fails else 0


# ---------------------------------------------------------------- controller
def _fixture(name: str, rows: int, seed: int) -> tuple[Path, dict]:
    d = SCRATCH / 'bench' / name
    meta_p = d / 'fixture.json'
    if meta_p.exists() and json.loads(meta_p.read_text()).get('rows') == rows and json.loads(meta_p.read_text()).get('seed') == seed:
        meta = json.loads(meta_p.read_text())
    else:
        shutil.rmtree(d, ignore_errors=True)
        subprocess.run([sys.executable, str(Path(__file__).resolve()), 'genfix', '--dir', str(d), '--rows', str(rows),
                        '--seed', str(seed)], check=True, env=_env())
        meta = json.loads(meta_p.read_text())
    files = [p for p in sorted(d.rglob('*')) if p.is_file() and p.name != 'fixture.json']
    meta['input_sha256'] = {Path(k).relative_to(d).as_posix(): v for k, v in sha256_paths(files).items()}
    return d, meta


def _med(xs):
    return statistics.median(xs)


def controller(out: Path, rows: int, rows2: int, pairs: int, seed: int) -> int:
    SCRATCH.mkdir(parents=True, exist_ok=True)
    fix1, meta1 = _fixture('fixture-1m', rows, seed)
    fix2, meta2 = _fixture('fixture-2m', rows2, seed)
    sums = _check_sums()
    seq = 0
    base, cand = [], []
    for i in range(pairs):
        for mode, lst in (('baseline', base), ('candidate', cand)):
            seq += 1
            r = run_scoped(mode, fix1, f'{mode}-{i}', seq)
            lst.append(r)
            print(f'pair {i} {mode}: exit={r["exit"]} rss={r.get("max_rss_kib")} peak={r.get("cgroup", {}).get("memory_peak")} wall={r["wall_s"]:.1f}s', flush=True)
    seq += 1
    c2 = run_scoped('candidate', fix2, 'candidate-2m', seq)
    seq += 1
    cv = run_scoped('candidate-verify', fix1, 'candidate-verify', seq)
    for r in (c2, cv):
        print(f'{r["mode"]}: exit={r["exit"]} rss={r.get("max_rss_kib")} peak={r.get("cgroup", {}).get("memory_peak")} wall={r["wall_s"]:.1f}s', flush=True)

    def rss(r): return r.get('max_rss_kib')
    def peak(r): return r.get('cgroup', {}).get('memory_peak')
    gates, fails = {}, []

    def gate(name, ok, detail):
        gates[name] = {'pass': bool(ok), 'detail': detail}
        if not ok:
            fails.append(name)

    complete = all(r['exit'] == 0 and rss(r) is not None and peak(r) is not None for r in base + cand + [c2, cv])
    gate('all_workers_exit0_and_measured', complete, 'every worker exit 0 with max RSS and memory.peak recorded')
    if complete:
        for i, (b, c) in enumerate(zip(base, cand)):
            gate(f'pair{i}_rss_le_half', rss(c) <= 0.5 * rss(b), f'cand {rss(c)} KiB vs base {rss(b)} KiB ratio {rss(c) / rss(b):.4f}')
            gate(f'pair{i}_peak_le_half', peak(c) <= 0.5 * peak(b), f'cand {peak(c)} vs base {peak(b)} ratio {peak(c) / peak(b):.4f}')
            gate(f'pair{i}_output_sha_equal', b['output_sha256'] == c['output_sha256'] and b['stdout_sha256'] == c['stdout_sha256'],
                 'dump bins, manifest, counts and stdout')
        ref_rss, ref_peak = _med([rss(c) for c in cand]), _med([peak(c) for c in cand])
        gate('doubled_rss_growth', rss(c2) - ref_rss <= KIB_BOUND,
             f'{rss(c2) - ref_rss} KiB over median 1M candidate (vs min {rss(c2) - min(rss(c) for c in cand)}, vs max {rss(c2) - max(rss(c) for c in cand)}); bound {KIB_BOUND}')
        gate('doubled_peak_growth', (peak(c2) - ref_peak) <= KIB_BOUND * 1024,
             f'{(peak(c2) - ref_peak) / 1024:.0f} KiB over median 1M candidate (vs min {(peak(c2) - min(peak(c) for c in cand)) / 1024:.0f}, vs max {(peak(c2) - max(peak(c) for c in cand)) / 1024:.0f}); bound {KIB_BOUND}')
        mb, mc = _med([r['wall_s'] for r in base]), _med([r['wall_s'] for r in cand])
        gate('median_wall_le_2x', mc <= 2 * mb, f'cand median {mc:.2f}s vs base median {mb:.2f}s ratio {mc / mb:.3f}')
        gate('verify_rss_le_half', rss(cv) <= 0.5 * min(rss(b) for b in base), f'verify {rss(cv)} KiB')
        gate('verify_peak_le_half', peak(cv) <= 0.5 * min(peak(b) for b in base), f'verify {peak(cv)}')
        gate('verify_output_sha_equal', cv['output_sha256'] == cand[0]['output_sha256'], 'verify-mode outputs equal candidate outputs')
    pk = [peak(b) for b in base if peak(b)]
    spread = (max(pk) - min(pk)) / _med(pk) if pk else None
    results = {
        'baseline_source_sha256': sums, 'seed': seed, 'python': sys.version, 'numpy': np.__version__,
        'window_rows': dump_join.DEFAULT_WINDOW, 'fixture_1m': meta1, 'fixture_2m': meta2,
        'baseline_runs': base, 'candidate_runs': cand, 'candidate_2m': c2, 'candidate_verify': cv,
        'baseline_peak_spread_fraction': spread, 'baseline_peak_spread_exceeds_10pct': bool(spread and spread > 0.10),
        'median_wall_s': {'baseline': _med([r['wall_s'] for r in base]), 'candidate': _med([r['wall_s'] for r in cand])},
        'gates': gates, 'failed': fails, 'time_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, indent=2) + '\n')
    for k, v in gates.items():
        print(('PASS ' if v['pass'] else 'FAIL ') + k, v['detail'], flush=True)
    print('baseline memory.peak spread fraction:', spread, flush=True)
    return 1 if fails else 0



# ---------------------------------------------------------------- Phase 3: 3-07 + triage
def _p3_env(root=None) -> dict:
    env = dict(os.environ)
    (SCRATCH_P3 / 'tmp').mkdir(parents=True, exist_ok=True)
    env['TMPDIR'] = str(SCRATCH_P3 / 'tmp')
    if root is not None:
        env['PYTHONPATH'] = str(root)
    return env


def s07_genfixture(fixdir, rows: int, seed: int = S07_SEED) -> dict:
    """Deterministic 144-byte dump + side table; zero-flag growth keeps side weights valid."""
    from kiwiw import cenc
    OLD = cenc.K1_DUMP_DTYPE
    INT32_MIN = np.iinfo(np.int32).min
    rng = np.random.default_rng(seed)
    fixdir = Path(fixdir)
    dump = fixdir / 'dump'
    dump.mkdir(parents=True, exist_ok=True)
    type_map = {}
    for nm in OLD.names:
        dt = OLD.fields[nm][0]
        type_map[nm] = ('f64' if dt == np.dtype('<f8') else
                        'i32' if dt == np.dtype('<i4') else
                        'u16' if dt == np.dtype('<u2') else 'u8')
    fields = [{'name': nm, 'type': type_map[nm]} for nm in OLD.names]
    bb = np.zeros(rows, OLD)
    bb['level'] = 0
    bb['code'] = 291
    bb['src_ix'] = INT32_MIN
    # fixed group population independent of row count (growth gate)
    g = 20000
    bb['ix'] = rng.integers(0, 200, rows)
    bb['iy'] = rng.integers(0, 200, rows)
    bb['shape'] = rng.integers(0, g // 100, rows)
    for p in ('p0', 'p1', 'p2', 'p3', 'p4', 'p5', 'p6'):
        bb[p] = rng.integers(0, 8, rows)
    bb['lat'] = rng.normal(size=rows)
    # ~40% out of scope (zero-flag growth rows)
    out = np.zeros(rows, bool)
    out[rows // 5:] = rng.random(rows - rows // 5) < 0.5
    bb['level'][out] = 1
    bb['code'][out] = 100
    bb['src_ix'][out] = 0
    (dump / 'background_boundary.bin').write_bytes(bb.tobytes())
    # tiny second kind
    other = np.zeros(8, OLD)
    (dump / 'background.bin').write_bytes(other.tobytes())
    kinds = {
        'background_boundary': {'rows': rows, 'row_size': 144, 'file': 'background_boundary.bin', 'fields': fields},
        'background': {'rows': 8, 'row_size': 144, 'file': 'background.bin', 'fields': fields},
    }
    (dump / 'dump_manifest.json').write_text(json.dumps({'fields': fields, 'kinds': kinds, 'row_size': 144}, indent=2))
    scope = (bb['level'] == 0) & (bb['code'] == 291) & (bb['src_ix'] == INT32_MIN)
    kd = np.dtype([(k, OLD[k]) for k in GROUP])
    keys = np.empty(int(scope.sum()), kd)
    for k in GROUP:
        keys[k] = bb[k][scope]
    ukey, inv, counts = np.unique(keys, return_inverse=True, return_counts=True)
    # cap unique side keys for fixed cardinality across growth
    max_u = min(len(ukey), 50000)
    ukey, counts = ukey[:max_u], counts[:max_u]
    side_dt = np.dtype([(k, '<i4') for k in GROUP] + [
        ('hx', '<i4'), ('hy', '<i4'), ('rec', '<i4'), ('tall', '<i4'), ('nv', '<i4'),
        ('closing', '<i4'), ('crossing_count', '<i4'), ('status', '<i4'), ('rows', '<i8')])
    side = np.zeros(len(ukey), side_dt)
    for i in range(len(ukey)):
        for k in GROUP:
            side[k][i] = int(ukey[k][i])
        side['status'][i] = 1 if (i % 2 == 0) else 0
        side['rows'][i] = int(counts[i]) if side['status'][i] == 1 else 0
    # For growth fixtures, recompute rows weights only for keys present; status-1 weights
    # must equal dump matches for those keys. Rebuild rows from this fixture's counts.
    np.save(fixdir / 'side_background_boundary.npy', side)
    # fsync
    for f in dump.iterdir():
        fd = os.open(f, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    meta = {'rows': rows, 'seed': seed, 'side_rows': len(side), 'groups': int(len(ukey)),
            'status1': int((side['status'] == 1).sum())}
    (fixdir / 'fixture.json').write_text(json.dumps(meta, indent=2) + '\n')
    return meta


def s07_materialise(fixdir, root) -> Path:
    fixdir, root = Path(fixdir), Path(root)
    dump_dst = root / 'output' / 'scratch-3-03' / 'dump'
    side_root = root / 'output' / 'scratch-3-07'
    dump_dst.mkdir(parents=True, exist_ok=True)
    side_root.mkdir(parents=True, exist_ok=True)
    for p in (fixdir / 'dump').iterdir():
        os.symlink(p.resolve(), dump_dst / p.name)
    os.symlink((fixdir / 'side_background_boundary.npy').resolve(),
               side_root / 'side_background_boundary.npy')
    (side_root / 'witness.py').write_text(
        "from pathlib import Path\nimport json, numpy as np\n"
        "ROOT = Path('output/scratch-3-07')\nDUMP = Path('output/scratch-3-03/dump')\n"
        f"GROUP = {GROUP!r}\n"
        "def dump(kind):\n"
        "    doc=json.loads((DUMP/'dump_manifest.json').read_text())\n"
        "    kinds={'f64':'<f8','i32':'<i4','u16':'<u2','u8':'u1'}\n"
        "    dt=np.dtype([(f['name'],kinds[f['type']]) for f in doc['fields']],align=True)\n"
        "    return np.memmap(DUMP/doc['kinds'][kind]['file'],dtype=dt,mode='r')\n")
    shutil.copyfile(S07_BASELINE_DIR / 'extend_dump_attempt3.py', root / 'extend_dump_attempt3.py')
    return root


def s07_check_isolated(root) -> None:
    real_out = (REPO / 'output').resolve()
    allowed = SCRATCH_P3.resolve()
    rr = Path(os.path.realpath(root))
    if not rr.is_relative_to(allowed):
        raise IsolationError(f'replay root {root} outside {allowed}')
    for dirpath, _dns, fns in os.walk(root):
        for fn in fns:
            rp = Path(os.path.realpath(Path(dirpath) / fn))
            if (rp == real_out or rp.is_relative_to(real_out)) and not rp.is_relative_to(allowed):
                raise IsolationError(f'{fn} resolves to {rp}')


def s07_worker(mode: str, root: str, marker: str) -> int:
    t0 = time.perf_counter()
    os.chdir(root)
    rc = 0
    try:
        if mode == 'baseline':
            import runpy
            sys.path.insert(0, str(Path(root) / 'output' / 'scratch-3-07'))
            sys.argv = ['extend_dump_attempt3.py']
            runpy.run_path('extend_dump_attempt3.py', run_name='__main__')
        else:
            rc = dump_join.main(['--mode', 's02',
                                 '--dump', 'output/scratch-3-03/dump',
                                 '--side', 'output/scratch-3-07/side_background_boundary.npy',
                                 '--s02-dst', 'output/scratch-3-07/dump_attempt3'])
    except SystemExit as e:
        rc = int(e.code or 0)
    except Exception:
        traceback.print_exc()
        rc = 1
    wall = time.perf_counter() - t0
    snap = _cgroup_snapshot()
    snap.update(mode=mode, transform_wall_s=wall, rc=rc)
    Path(marker, 'cgroup.json').write_text(json.dumps(snap, indent=2))
    return rc


def s07_output_hashes(root) -> dict:
    d = Path(root) / 'output' / 'scratch-3-07' / 'dump_attempt3'
    files = sorted(p for p in d.rglob('*') if p.is_file()) if d.is_dir() else []
    h = sha256_paths(files)
    return {Path(k).relative_to(d).as_posix(): v for k, v in h.items()}


def s07_run_scoped(mode: str, fixdir: Path, tag: str, unit_seq: int) -> dict:
    rundir = SCRATCH_P3 / 'bench' / f's07-{tag}'
    shutil.rmtree(rundir, ignore_errors=True)
    root = s07_materialise(fixdir, rundir / 'root')
    s07_check_isolated(root)
    marker = rundir / 'marker'
    marker.mkdir(parents=True)
    paths = [p for p in (fixdir / 'dump').iterdir()] + [fixdir / 'side_background_boundary.npy']
    _preread([p.resolve() for p in paths])
    unit = f's07-bench-{os.getpid()}-{unit_seq}'
    cmd = ['systemd-run', '--user', '--scope', '--quiet', '-p', 'MemoryAccounting=yes', f'--unit={unit}', '--',
           '/usr/bin/time', '-v', '-o', str(marker / 'time.txt'), sys.executable, str(Path(__file__).resolve()),
           's07-worker', '--mode', mode, '--root', str(root), '--marker', str(marker)]
    t0 = time.perf_counter()
    with open(marker / 'stdout.txt', 'w') as so, open(marker / 'stderr.txt', 'w') as se:
        p = subprocess.run(cmd, stdout=so, stderr=se, env=_p3_env(root if mode == 'baseline' else None))
    wall = time.perf_counter() - t0
    tv = _parse_time(marker / 'time.txt')
    cg = json.loads((marker / 'cgroup.json').read_text()) if (marker / 'cgroup.json').exists() else {}
    hashes = s07_output_hashes(root) if p.returncode == 0 and cg.get('rc', 1) == 0 else {}
    return {'mode': mode, 'proc_rc': p.returncode, 'worker_rc': cg.get('rc'), 'max_rss_kib': tv['max_rss_kib'],
            'time_v_elapsed_s': tv['time_v_elapsed_s'], 'controller_wall_s': wall,
            'memory_peak': cg.get('memory_peak'), 'anon': cg.get('anon'), 'file_dirty': cg.get('file_dirty'),
            'hashes': hashes, 'cgroup': cg}


def s07_controller(out: Path, rows: int, rows2: int, pairs: int, seed: int) -> int:
    SCRATCH_P3.mkdir(parents=True, exist_ok=True)
    fix1 = SCRATCH_P3 / 'fixture-1m'
    fix2 = SCRATCH_P3 / 'fixture-2m'
    shutil.rmtree(fix1, ignore_errors=True)
    shutil.rmtree(fix2, ignore_errors=True)
    m1 = s07_genfixture(fix1, rows, seed)
    m2 = s07_genfixture(fix2, rows2, seed)
    pairs_out = []
    ok = True
    for i in range(pairs):
        b = s07_run_scoped('baseline', fix1, f'p{i}-base', i * 2)
        c = s07_run_scoped('candidate', fix1, f'p{i}-cand', i * 2 + 1)
        ratio_rss = c['max_rss_kib'] / b['max_rss_kib'] if b['max_rss_kib'] else None
        ratio_peak = (c['memory_peak'] / b['memory_peak']) if b.get('memory_peak') and c.get('memory_peak') else None
        sha_eq = c['hashes'] == b['hashes'] and bool(c['hashes'])
        gate = (c['proc_rc'] == 0 and c.get('worker_rc') == 0 and b['proc_rc'] == 0 and b.get('worker_rc') == 0
                and ratio_rss is not None and ratio_rss <= 0.5
                and ratio_peak is not None and ratio_peak <= 0.5 and sha_eq)
        ok = ok and gate
        pairs_out.append({'i': i, 'baseline': b, 'candidate': c, 'ratio_rss': ratio_rss,
                          'ratio_peak': ratio_peak, 'sha_equal': sha_eq, 'gate': gate})
        print(f"s07 pair{i}: rss {ratio_rss:.3f} peak {ratio_peak:.3f} sha={sha_eq} gate={gate}", flush=True)
    g = s07_run_scoped('candidate', fix2, 'growth', 100)
    # compare growth to median 1M candidate
    c1 = [p['candidate'] for p in pairs_out]
    med_rss = _med([x['max_rss_kib'] for x in c1])
    med_peak = _med([x['memory_peak'] for x in c1])
    grow_rss = g['max_rss_kib'] - med_rss
    grow_peak = (g['memory_peak'] - med_peak) / 1024 if g.get('memory_peak') and med_peak else None
    growth_ok = grow_rss <= S07_KIB_GROWTH and (grow_peak is not None and grow_peak <= S07_KIB_GROWTH)
    wall_ok = _med([p['candidate']['time_v_elapsed_s'] for p in pairs_out]) <= 2 * _med(
        [p['baseline']['time_v_elapsed_s'] for p in pairs_out])
    ok = ok and growth_ok and wall_ok and g['proc_rc'] == 0
    doc = {'phase': 3, 'mode': 's07', 'fixture': m1, 'fixture2': m2, 'pairs': pairs_out,
           'growth': {'run': g, 'delta_rss_kib': grow_rss, 'delta_peak_kib': grow_peak,
                      'bound_kib': S07_KIB_GROWTH, 'ok': growth_ok},
           'wall_ok': wall_ok, 'ok': ok}
    Path(out).write_text(json.dumps(doc, indent=2) + '\n')
    print('s07_controller', 'PASS' if ok else 'FAIL', flush=True)
    return 0 if ok else 1


def triage_genfixture(fixdir, rows: int, seed: int = S07_SEED) -> dict:
    """152-byte fixed-cardinality triage dump (one kind).

    All GROUP / src key fields are drawn from a fixed pool so doubling rows does
    not grow retained aggregation cardinalities (DESIGN Phase 3 growth gate).
    """
    fixdir = Path(fixdir)
    dump = fixdir / 'dump'
    dump.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(seed)
    arr = random_rows(rng, rows)
    # Tiny fixed pools so 1M and 2M share the same retained cardinalities.
    # Saturate retained cardinalities well below 1M rows (pairs ⊆ src×group).
    arr['level'] = rng.integers(0, 2, rows, dtype=arr.dtype['level'])
    arr['code'] = rng.integers(1, 3, rows, dtype=arr.dtype['code'])
    arr['ix'] = rng.integers(0, 4, rows, dtype=arr.dtype['ix'])
    arr['iy'] = rng.integers(0, 4, rows, dtype=arr.dtype['iy'])
    arr['shape'] = rng.integers(0, 4, rows, dtype=arr.dtype['shape'])
    for name in ('p0', 'p1', 'p2', 'p3', 'p4', 'p5', 'p6'):
        arr[name] = 0
    arr['src_ix'] = np.where(rng.random(rows) < 0.2, np.int32(-2147483648),
                             rng.integers(0, 4, rows, dtype=np.int32))
    arr['src_iy'] = np.where(arr['src_ix'] == -2147483648, np.int32(-2147483648),
                             rng.integers(0, 4, rows, dtype=np.int32))
    arr['src_rec'] = rng.integers(0, 2, rows, dtype=arr.dtype['src_rec'])
    arr['src_tall'] = rng.integers(0, 2, rows, dtype=arr.dtype['src_tall'])
    arr['src_nv'] = rng.integers(0, 2, rows, dtype=arr.dtype['src_nv'])
    arr['src_maxseg'] = np.where(arr['src_ix'] == -2147483648, np.nan, 0.0)
    (dump / 'background_boundary.bin').write_bytes(arr.tobytes())
    fields = [{'name': f['name'], 'type': f['type']} for f in FIELDS]
    kinds = {'background_boundary': {'rows': rows, 'row_size': 152,
                                     'file': 'background_boundary.bin', 'fields': fields}}
    (dump / 'dump_manifest.json').write_text(json.dumps(
        {'fields': fields, 'kinds': kinds, 'row_size': 152}, indent=2, sort_keys=True))
    rules = {'version': 1, 'rules': [
        {'id': 'R0', 'cause': 'spool', 'kind': 'background_boundary',
         'where': [['level', '==', 0]], 'note': 't'},
        {'id': 'R1', 'cause': 'build', 'kind': 'background_boundary',
         'where': [['level', '==', 1]], 'note': 't'},
    ]}
    (fixdir / 'rules.json').write_text(json.dumps(rules))
    for f in list(dump.iterdir()) + [fixdir / 'rules.json']:
        fd = os.open(f, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    meta = {'rows': rows, 'seed': seed}
    (fixdir / 'fixture.json').write_text(json.dumps(meta, indent=2) + '\n')
    return meta


def triage_worker(mode: str, cmd: str, dump: str, out: str, marker: str, rules: str = '',
                  assign: str = '', rule: str = '') -> int:
    t0 = time.perf_counter()
    rc = 0
    try:
        if mode == 'baseline':
            sys.path.insert(0, str(TRIAGE_BASELINE_DIR))
            import k1_triage_memmap as T  # noqa: E402
        else:
            from tools import k1_triage as T  # noqa: E402
        argv = [cmd, '--dump', dump, '--out', out] if cmd != 'enumerate' else [
            cmd, '--dump', dump, '--assign', assign, '--rule', rule, '--out', out]
        if cmd == 'classify':
            argv = [cmd, '--dump', dump, '--rules', rules, '--out', out]
        if mode == 'candidate' and cmd != 'enumerate':
            argv += ['--window-rows', str(dump_join.DEFAULT_WINDOW)]
        if mode == 'candidate' and cmd == 'enumerate':
            argv += ['--window-rows', str(dump_join.DEFAULT_WINDOW)]
        rc = T.main(argv)
    except SystemExit as e:
        rc = int(e.code or 0)
    except Exception:
        traceback.print_exc()
        rc = 1
    wall = time.perf_counter() - t0
    snap = _cgroup_snapshot()
    snap.update(mode=mode, cmd=cmd, transform_wall_s=wall, rc=rc)
    Path(marker, 'cgroup.json').write_text(json.dumps(snap, indent=2))
    return rc


def triage_dir_hashes(path: Path) -> dict:
    files = sorted(p for p in Path(path).rglob('*') if p.is_file())
    h = sha256_paths(files)
    return {Path(k).relative_to(path).as_posix(): v for k, v in h.items()}


def triage_run_scoped(mode: str, cmd: str, fixdir: Path, tag: str, unit_seq: int,
                      assign_dir: Path | None = None) -> dict:
    rundir = SCRATCH_P3 / 'bench' / f'triage-{tag}'
    shutil.rmtree(rundir, ignore_errors=True)
    rundir.mkdir(parents=True)
    marker = rundir / 'marker'
    marker.mkdir()
    out = rundir / 'out'
    dump = str((fixdir / 'dump').resolve())
    rules = str((fixdir / 'rules.json').resolve())
    _preread([Path(dump) / 'background_boundary.bin', Path(rules)])
    unit = f'triage-bench-{os.getpid()}-{unit_seq}'
    args = [sys.executable, str(Path(__file__).resolve()), 'triage-worker',
            '--mode', mode, '--cmd', cmd, '--dump', dump, '--out', str(out),
            '--marker', str(marker), '--rules', rules]
    if cmd == 'enumerate':
        args += ['--assign', str(assign_dir.resolve()), '--rule', 'R0',
                 '--out', str(rundir / 'enum.tsv')]
        # out file is enum.tsv; adjust
        args[args.index('--out') + 1] = str(rundir / 'enum.tsv')
    cmd_line = ['systemd-run', '--user', '--scope', '--quiet', '-p', 'MemoryAccounting=yes',
                f'--unit={unit}', '--', '/usr/bin/time', '-v', '-o', str(marker / 'time.txt'), *args]
    t0 = time.perf_counter()
    with open(marker / 'stdout.txt', 'w') as so, open(marker / 'stderr.txt', 'w') as se:
        p = subprocess.run(cmd_line, stdout=so, stderr=se, env=_p3_env())
    wall = time.perf_counter() - t0
    tv = _parse_time(marker / 'time.txt')
    cg = json.loads((marker / 'cgroup.json').read_text()) if (marker / 'cgroup.json').exists() else {}
    target = out if cmd != 'enumerate' else (rundir / 'enum.tsv')
    hashes = triage_dir_hashes(target if target.is_dir() else target.parent) if (
        p.returncode == 0 and cg.get('rc', 1) == 0) else {}
    if cmd == 'enumerate' and target.is_file():
        hashes = {target.name: sha256_file(target)}
    return {'mode': mode, 'cmd': cmd, 'proc_rc': p.returncode, 'worker_rc': cg.get('rc'),
            'max_rss_kib': tv['max_rss_kib'], 'time_v_elapsed_s': tv['time_v_elapsed_s'],
            'controller_wall_s': wall, 'memory_peak': cg.get('memory_peak'),
            'hashes': hashes, 'out': str(out if cmd != 'enumerate' else rundir / 'enum.tsv'),
            'cgroup': cg}


def triage_controller(out: Path, rows: int, rows2: int, pairs: int, seed: int) -> int:
    SCRATCH_P3.mkdir(parents=True, exist_ok=True)
    fix1 = SCRATCH_P3 / 'triage-fixture-1m'
    fix2 = SCRATCH_P3 / 'triage-fixture-2m'
    shutil.rmtree(fix1, ignore_errors=True)
    shutil.rmtree(fix2, ignore_errors=True)
    m1 = triage_genfixture(fix1, rows, seed)
    m2 = triage_genfixture(fix2, rows2, seed)
    results = {'phase': 3, 'mode': 'triage', 'fixture': m1, 'fixture2': m2, 'commands': {}}
    ok = True
    seq = 0
    for cmd in ('summary', 'classify', 'enumerate'):
        pairs_out = []
        # prepare assign for enumerate from a candidate classify once per fixture size
        assign_dir = None
        if cmd == 'enumerate':
            prep = triage_run_scoped('candidate', 'classify', fix1, 'enum-prep', seq)
            seq += 1
            assign_dir = Path(prep['out'])
            if prep['proc_rc'] != 0 or prep.get('worker_rc') not in (0, None):
                ok = False
        for i in range(pairs):
            b = triage_run_scoped('baseline', cmd, fix1, f'{cmd}-p{i}-base', seq,
                                  assign_dir=assign_dir)
            seq += 1
            c = triage_run_scoped('candidate', cmd, fix1, f'{cmd}-p{i}-cand', seq,
                                  assign_dir=assign_dir)
            seq += 1
            ratio_rss = c['max_rss_kib'] / b['max_rss_kib'] if b['max_rss_kib'] else None
            ratio_peak = (c['memory_peak'] / b['memory_peak']) if b.get('memory_peak') and c.get('memory_peak') else None
            sha_eq = c['hashes'] == b['hashes'] and bool(c['hashes'])
            gate = (c['proc_rc'] == 0 and b['proc_rc'] == 0 and c.get('worker_rc') == 0
                    and b.get('worker_rc') == 0 and ratio_rss is not None and ratio_rss <= 0.5
                    and ratio_peak is not None and ratio_peak <= 0.5 and sha_eq)
            # classify may return rc=1 on partition fail; our complete rules should be 0
            ok = ok and gate
            pairs_out.append({'i': i, 'baseline': {k: v for k, v in b.items() if k != 'cgroup'},
                              'candidate': {k: v for k, v in c.items() if k != 'cgroup'},
                              'ratio_rss': ratio_rss, 'ratio_peak': ratio_peak,
                              'sha_equal': sha_eq, 'gate': gate})
            print(f"triage {cmd} pair{i}: rss {ratio_rss:.3f} peak {ratio_peak:.3f} "
                  f"sha={sha_eq} gate={gate}", flush=True)
        assign_growth = assign_dir
        if cmd == 'enumerate':
            # Growth fixture has 2M rows; assign must match that length (not the 1M prep).
            prep2 = triage_run_scoped('candidate', 'classify', fix2, 'enum-growth-prep', seq)
            seq += 1
            assign_growth = Path(prep2['out'])
            if prep2['proc_rc'] != 0 or prep2.get('worker_rc') not in (0, None):
                ok = False
        g = triage_run_scoped('candidate', cmd, fix2, f'{cmd}-growth', seq,
                              assign_dir=assign_growth)
        seq += 1
        c1 = [p['candidate'] for p in pairs_out]
        med_rss = _med([x['max_rss_kib'] for x in c1])
        med_peak = _med([x['memory_peak'] for x in c1])
        grow_rss = g['max_rss_kib'] - med_rss
        grow_peak = (g['memory_peak'] - med_peak) / 1024 if g.get('memory_peak') and med_peak else None
        growth_ok = (g['proc_rc'] == 0 and g.get('worker_rc') == 0
                     and grow_rss <= TRIAGE_KIB_GROWTH
                     and grow_peak is not None and grow_peak <= TRIAGE_KIB_GROWTH)
        wall_ok = _med([p['candidate']['time_v_elapsed_s'] for p in pairs_out]) <= 2 * _med(
            [p['baseline']['time_v_elapsed_s'] for p in pairs_out])
        ok = ok and growth_ok and wall_ok
        results['commands'][cmd] = {'pairs': pairs_out,
                                    'growth': {'delta_rss_kib': grow_rss, 'delta_peak_kib': grow_peak,
                                               'bound_kib': TRIAGE_KIB_GROWTH, 'ok': growth_ok,
                                               'proc_rc': g['proc_rc'], 'worker_rc': g.get('worker_rc'),
                                               'max_rss_kib': g['max_rss_kib'],
                                               'memory_peak': g.get('memory_peak')},
                                    'wall_ok': wall_ok}
    results['ok'] = ok
    Path(out).write_text(json.dumps(results, indent=2) + '\n')
    print('triage_controller', 'PASS' if ok else 'FAIL', flush=True)
    return 0 if ok else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    sub = ap.add_subparsers(dest='cmd')
    g = sub.add_parser('genfix'); g.add_argument('--dir', required=True); g.add_argument('--rows', type=int, required=True); g.add_argument('--seed', type=int, default=SEED)
    w = sub.add_parser('worker'); w.add_argument('--mode', required=True, choices=['baseline', 'candidate', 'candidate-verify']); w.add_argument('--root', required=True); w.add_argument('--marker', required=True)
    c = sub.add_parser('check-root', help='exit non-zero if a replay root would reach the real output/'); c.add_argument('--root', required=True)
    fg = sub.add_parser('finalize-genfix'); fg.add_argument('--dir', required=True); fg.add_argument('--rows', type=int, required=True); fg.add_argument('--seed', type=int, default=SEED); fg.add_argument('--parts', type=int, default=FINALIZE_DEFAULT_PARTS)
    fw = sub.add_parser('finalize-worker'); fw.add_argument('--mode', required=True, choices=['baseline', 'candidate']); fw.add_argument('--root', required=True); fw.add_argument('--marker', required=True); fw.add_argument('--ntasks', type=int, required=True)
    fr = sub.add_parser('finalize-run', help='Phase-2 controller; run under flock output/.heavy.lock'); fr.add_argument('--out', default=str(SCRATCH_FIN / 'finalize_results.json')); fr.add_argument('--rows', type=int, default=FINALIZE_DEFAULT_ROWS); fr.add_argument('--pairs', type=int, default=3); fr.add_argument('--seed', type=int, default=SEED); fr.add_argument('--parts', type=int, default=FINALIZE_DEFAULT_PARTS)
    s7w = sub.add_parser('s07-worker'); s7w.add_argument('--mode', required=True); s7w.add_argument('--root', required=True); s7w.add_argument('--marker', required=True)
    s7r = sub.add_parser('s07-run', help='Phase-3 3-07 controller; run under flock'); s7r.add_argument('--out', default=str(SCRATCH_P3 / 's07_results.json')); s7r.add_argument('--rows', type=int, default=1000013); s7r.add_argument('--rows2', type=int, default=2000013); s7r.add_argument('--pairs', type=int, default=3); s7r.add_argument('--seed', type=int, default=S07_SEED)
    tw = sub.add_parser('triage-worker'); tw.add_argument('--mode', required=True); tw.add_argument('--cmd', dest='triage_cmd', required=True); tw.add_argument('--dump', required=True); tw.add_argument('--out', required=True); tw.add_argument('--marker', required=True); tw.add_argument('--rules', default=''); tw.add_argument('--assign', default=''); tw.add_argument('--rule', default='')
    tr = sub.add_parser('triage-run', help='Phase-3 triage controller; run under flock'); tr.add_argument('--out', default=str(SCRATCH_P3 / 'triage_results.json')); tr.add_argument('--rows', type=int, default=1000013); tr.add_argument('--rows2', type=int, default=2000013); tr.add_argument('--pairs', type=int, default=3); tr.add_argument('--seed', type=int, default=S07_SEED)
    ap.add_argument('--out', default=str(SCRATCH / 'results.json'))
    ap.add_argument('--rows', type=int, default=1000013)
    ap.add_argument('--rows2', type=int, default=2000013)
    ap.add_argument('--pairs', type=int, default=3)
    ap.add_argument('--seed', type=int, default=SEED)
    a = ap.parse_args(argv)
    if a.cmd == 'finalize-run':
        return finalize_controller(Path(a.out), a.rows, a.pairs, a.seed, a.parts)
    if a.cmd == 'finalize-genfix':
        print(json.dumps(finalize_genfix(a.dir, a.rows, a.seed, a.parts)))
        return 0
    if a.cmd == 'finalize-worker':
        return finalize_worker(a.mode, a.root, a.marker, a.ntasks)
    if a.cmd == 'genfix':
        print(json.dumps(gen_bulk(a.dir, a.rows, a.seed)))
        return 0
    if a.cmd == 'check-root':
        try:
            check_isolated(a.root)
        except IsolationError as e:
            print('REFUSED:', e, file=sys.stderr)
            return 2
        return 0
    if a.cmd == 'worker':
        return worker(a.mode, a.root, a.marker)
    if a.cmd == 's07-worker':
        return s07_worker(a.mode, a.root, a.marker)
    if a.cmd == 's07-run':
        return s07_controller(Path(a.out), a.rows, a.rows2, a.pairs, a.seed)
    if a.cmd == 'triage-worker':
        return triage_worker(a.mode, a.triage_cmd, a.dump, a.out, a.marker, a.rules, a.assign, a.rule)
    if a.cmd == 'triage-run':
        return triage_controller(Path(a.out), a.rows, a.rows2, a.pairs, a.seed)
    return controller(Path(a.out), a.rows, a.rows2, a.pairs, a.seed)


if __name__ == '__main__':
    sys.exit(main())
