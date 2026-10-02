#!/usr/bin/env python3
"""Bounded memory validation for the residual extension (plan 05, Phase 1, brief 1-01).

Subcommands
    (none) / run   controller: build fixtures, run paired baseline/candidate workers each in
                   its own `systemd-run --user --scope`, gate on max RSS, cgroup memory.peak,
                   growth, wall time and output SHA256s, write a results JSON.
    genfix         generate a seeded fixture directory (separate process).
    worker         one measured run, executed inside the scope (never inherits a fixture).

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
import json
import os
import re
import shutil
import statistics
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
SCRATCH = REPO / 'output' / 'scratch-5-01'
BASELINE_DIR = REPO / 'parser' / 'tests' / 'fixtures' / 'dump_join_baseline'
sys.path.insert(0, str(HERE))
import dump_join  # noqa: E402

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


# ---------------------------------------------------------------- replay root
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


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    sub = ap.add_subparsers(dest='cmd')
    g = sub.add_parser('genfix'); g.add_argument('--dir', required=True); g.add_argument('--rows', type=int, required=True); g.add_argument('--seed', type=int, default=SEED)
    w = sub.add_parser('worker'); w.add_argument('--mode', required=True, choices=['baseline', 'candidate', 'candidate-verify']); w.add_argument('--root', required=True); w.add_argument('--marker', required=True)
    c = sub.add_parser('check-root', help='exit non-zero if a replay root would reach the real output/'); c.add_argument('--root', required=True)
    ap.add_argument('--out', default=str(SCRATCH / 'results.json'))
    ap.add_argument('--rows', type=int, default=1000013)
    ap.add_argument('--rows2', type=int, default=2000013)
    ap.add_argument('--pairs', type=int, default=3)
    ap.add_argument('--seed', type=int, default=SEED)
    a = ap.parse_args(argv)
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
    return controller(Path(a.out), a.rows, a.rows2, a.pairs, a.seed)


if __name__ == '__main__':
    sys.exit(main())
