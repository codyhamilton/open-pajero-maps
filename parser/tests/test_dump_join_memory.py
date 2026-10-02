"""Bounded residual extension vs the vendored baseline (plan 05, Phase 1, brief 1-01).

Small fixtures only (a few thousand rows); no heavy job.  The baseline (`extend.py`, vendored
verbatim) is replayed in isolated roots under `output/scratch-5-01/`; the candidate is
`parser/tools/dump_join.py`.  Equality is SHA256 of every dump bin, manifest, counts file and
the EXTENDED/MOVED stdout.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

TOOLS = Path(__file__).resolve().parent.parent / "tools"
sys.path.insert(0, str(TOOLS))
import bench_dump_memory as B  # noqa: E402
import dump_join as J  # noqa: E402

TESTDIR = B.SCRATCH / f"tests-{os.getpid()}"


@pytest.fixture(scope="module", autouse=True)
def _scratch():
    TESTDIR.mkdir(parents=True, exist_ok=True)
    yield
    shutil.rmtree(TESTDIR, ignore_errors=True)


_n = [0]


def fresh(fixdir, name):
    _n[0] += 1
    return B.materialise_replay_root(fixdir, TESTDIR / f"{name}-{_n[0]}")


def mkrows(rng, n, pool, miss_frac=0.2):
    a = B.random_rows(rng, n)
    gi = rng.integers(0, len(pool), n)
    for f in B.GROUP:
        a[f] = pool[f][gi]
    miss = rng.random(n) < miss_frac
    a["ix"][miss] = 900000 + np.arange(miss.sum())
    return a


def assign_mix(rng, n, frac=0.4):
    return np.where(rng.random(n) < frac, 65535, rng.integers(0, 500, n)).astype("<u2")


@pytest.fixture(scope="module")
def allcases():
    rng = np.random.default_rng(5)
    pool = B._gen_pool(rng, 40)
    kinds = {}
    side = B._gen_side(rng, pool, 300)  # statuses 0/1, misses, duplicates with conflicting statuses
    kinds["k_status"] = dict(rows=mkrows(rng, 5003, pool), assign=assign_mix(rng, 5003), side=side)
    kinds["k_noside"] = dict(rows=mkrows(rng, 701, pool), assign=assign_mix(rng, 701), side=None)
    kinds["k_emptyside"] = dict(rows=mkrows(rng, 130, pool), assign=assign_mix(rng, 130), side=np.zeros(0, B.SIDE_DT))
    s1 = B._gen_side(rng, pool, 90)
    s1["status"] = 1
    kinds["k_allone"] = dict(rows=mkrows(rng, 257, pool, 0.0), assign=np.full(257, 65535, "<u2"), side=s1)
    s0 = B._gen_side(rng, pool, 90)
    s0["status"] = 0
    kinds["k_allzero"] = dict(rows=mkrows(rng, 65, pool, 0.0), assign=assign_mix(rng, 65), side=s0)
    fix = TESTDIR / "fix-allcases"
    B.write_fixture(fix, kinds)
    # sanity: the source really has nonzero byte146 and NaN payload floats
    raw = np.frombuffer(kinds["k_status"]["rows"].tobytes(), "u1").reshape(-1, 152)
    assert raw[:, 146].any()
    r = kinds["k_status"]["rows"]
    assert any(np.isnan(r[f]).any() for f in ("lat", "lon", "err", "d_any", "src_maxseg", "d_src"))
    return fix


@pytest.fixture(scope="module")
def baseline_out(allcases):
    root = fresh(allcases, "base")
    r = B.run_baseline(root)
    assert r.returncode == 0, r.stderr
    return root, B.output_hashes(root), r.stdout


def test_vendored_baseline_hashes_and_group():
    sums = B._check_sums()
    assert set(sums) == {"extend.py", "study.py", "witness.py"}
    assert B.baseline_witness_group() == J.GROUP


@pytest.mark.parametrize("window", [None, 1, 65536, 997])
def test_candidate_matches_baseline_all_cases(allcases, baseline_out, window):
    _, bh, bout = baseline_out
    root = fresh(allcases, "cand")
    r = B.run_candidate(root, *(["--window-rows", str(window)] if window else []))
    assert r.returncode == 0, r.stderr
    assert B.output_hashes(root) == bh
    assert r.stdout == bout
    # byte146 is always written from the flag: the baseline fixture has nonzero source byte146
    out = np.fromfile(root / J.DEFAULT_DST / "k_status.bin", "u1").reshape(-1, 152)
    assert set(np.unique(out[:, 146])) <= {0, 1}
    assert {0, 1} == set(np.unique(out[:, 146]))
    assert not np.fromfile(root / J.DEFAULT_DST / "k_noside.bin", "u1").reshape(-1, 152)[:, 146].any()
    assert not np.fromfile(root / J.DEFAULT_DST / "k_emptyside.bin", "u1").reshape(-1, 152)[:, 146].any()


def test_window_sizes_identical_bytes(allcases):
    hashes = []
    for w in (1, 65536, 1001):
        root = fresh(allcases, "win")
        assert B.run_candidate(root, "--window-rows", str(w)).returncode == 0
        hashes.append(B.output_hashes(root))
    assert hashes[0] == hashes[1] == hashes[2]


def test_collide_after_wrap():
    rng = np.random.default_rng(11)
    pool = B._gen_pool(rng, 120)
    n_wrap, n_dup = 30, 40
    filler = B._gen_side(rng, pool, 600)
    filler["status"] = 0
    # (a) i32 values that only collide after the narrowing cast: level 256+k -> u8 k, p0 65536+k -> u16 k
    wrap_keys = pool[:n_wrap].copy()
    wrap_keys["ix"] = 700000 + np.arange(n_wrap)  # unique to these rows, so no other side row can match
    wrapped = np.zeros(n_wrap, B.SIDE_DT)
    for f in B.GROUP:
        wrapped[f] = wrap_keys[f]
    wrapped["level"] = wrap_keys["level"].astype(np.int32) + 256
    wrapped["p0"] = wrap_keys["p0"].astype(np.int32) + 65536
    wrapped["status"] = 1
    # (b) duplicate keys with conflicting statuses, interleaved in the side table
    dup_keys = pool[n_wrap:n_wrap + n_dup].copy()
    dup_keys["iy"] = 800000 + np.arange(n_dup)
    dups = np.zeros(2 * n_dup, B.SIDE_DT)
    for f in B.GROUP:
        dups[f][0::2] = dup_keys[f]
        dups[f][1::2] = dup_keys[f]
    dups["status"][0::2] = np.arange(n_dup) % 2
    dups["status"][1::2] = 1 - np.arange(n_dup) % 2
    side = np.concatenate([filler, wrapped, dups])
    side = side[rng.permutation(len(side))]
    rows = B.random_rows(rng, n_wrap + n_dup + 20)
    allkeys = np.concatenate([wrap_keys, dup_keys, pool[100:110]])
    allkeys = np.concatenate([allkeys, allkeys[:10]])[: len(rows)]
    for f in B.GROUP:
        rows[f] = allkeys[f]
    fix = TESTDIR / "fix-wrap"
    B.write_fixture(fix, {"w": dict(rows=rows, assign=np.full(len(rows), 65535, "<u2"), side=side)})
    # the unwrapped i32 keys alone would miss: only the cast makes them collide
    assert (wrapped["level"] >= 256).all() and (wrapped["p0"] >= 65536).all()
    # the non-stable sort really permutes some duplicate ties (so the test exercises tie order)
    kd = np.dtype([(k, B.DT[k]) for k in B.GROUP])
    sk = np.empty(len(side), kd)
    for f in B.GROUP:
        sk[f] = side[f]
    assert not np.array_equal(np.argsort(sk), np.argsort(sk, kind="stable"))
    broot = fresh(fix, "wrap-base")
    rb = B.run_baseline(broot)
    assert rb.returncode == 0, rb.stderr
    croot = fresh(fix, "wrap-cand")
    rc = B.run_candidate(croot)
    assert rc.returncode == 0, rc.stderr
    assert B.output_hashes(croot) == B.output_hashes(broot)
    assert rc.stdout == rb.stdout
    out = np.fromfile(croot / J.DEFAULT_DST / "w.bin", "u1").reshape(-1, 152)
    assert (out[:n_wrap, 146] == 1).all()  # wrapped keys matched their status-1 record
    assert {0, 1} == set(np.unique(out[n_wrap:n_wrap + n_dup, 146]))


def _empty_fixture(name):
    fix = TESTDIR / name
    B.write_fixture(fix, {"e": dict(rows=np.zeros(0, B.DT), assign=np.zeros(0, "<u2"), side=None)})
    return fix


def test_empty_kind_rejected_by_baseline_and_candidate_separately():
    fix = _empty_fixture("fix-empty")
    broot = fresh(fix, "empty-base")
    rb = B.run_baseline(broot)
    assert rb.returncode != 0 and "ValueError" in rb.stderr  # np.memmap rejects the zero-length file
    assert not (broot / J.DEFAULT_COUNTS).exists()
    croot = fresh(fix, "empty-cand")
    rc = B.run_candidate(croot)
    assert rc.returncode != 0 and "zero-row" in rc.stderr
    assert not (croot / J.DEFAULT_DST).exists()  # candidate validates before writing anything
    assert not (croot / J.DEFAULT_COUNTS).exists()


def test_validation_before_writing(allcases):
    # source length not a multiple of the row size
    root = fresh(allcases, "badlen")
    src = root / "output/scratch-3-11/dump_new_ext/k_noside.bin"
    real = src.resolve()
    bad = TESTDIR / "badlen.bin"
    bad.write_bytes(real.read_bytes()[:-5])
    src.unlink()
    os.symlink(bad, src)
    r = B.run_candidate(root)
    assert r.returncode != 0 and "whole number" in r.stderr
    assert not (root / J.DEFAULT_DST).exists() and not (root / J.DEFAULT_COUNTS).exists()
    # assignment length mismatch (a later kind: nothing may be written for any kind)
    root = fresh(allcases, "badassign")
    a = root / "output/scratch-3-11/classify_new/assign_k_allzero.u16"
    short = TESTDIR / "short.u16"
    short.write_bytes(a.resolve().read_bytes()[:-2])
    a.unlink()
    os.symlink(short, a)
    r = B.run_candidate(root)
    assert r.returncode != 0 and "assignment length" in r.stderr
    assert not (root / J.DEFAULT_DST).exists()
    # destination that is the source itself is refused, source untouched
    root = fresh(allcases, "selfdst")
    r = B.run_candidate(root, "--dst", str(root / J.DEFAULT_SRC))
    assert r.returncode != 0
    assert B.sha256_file(root / J.DEFAULT_SRC / "k_status.bin") == B.sha256_file(allcases / J.DEFAULT_SRC / "k_status.bin")


def test_layout_validation():
    fields = [dict(f) for f in B.FIELDS]
    assert J.layout_dtype(fields).itemsize == 152
    ov = [dict(f) for f in fields]
    ov[-2]["type"] = "u16"  # s02_producer_verified now covers 144-145
    ov[-1]["type"] = "u16"  # other_mechanism now at 146-147: byte146 is not padding
    with pytest.raises(ValueError, match="not padding"):
        J.layout_dtype(ov)
    with pytest.raises(ValueError, match="row size"):
        J.layout_dtype(fields[:-2])
    with pytest.raises(ValueError, match="key field"):
        J.layout_dtype([f for f in fields if f["name"] != "shape"] + [dict(name="zz", type="i32")])


def test_verify_mode_and_corruption(allcases):
    root = fresh(allcases, "verify")
    r = B.run_candidate(root, "--verify", "--window-rows", "500")
    assert r.returncode == 0, r.stderr
    r = B.run_candidate(root, "--verify-only", "--window-rows", "500")
    assert r.returncode == 0 and "VERIFIED k_status" in r.stdout
    dst = root / J.DEFAULT_DST / "k_status.bin"
    for off in (152 * 1200 + 10, 152 * 1200 + 147, 152 * 4999 + 146):  # data byte, tail padding, flag byte
        orig = dst.read_bytes()
        b = bytearray(orig)
        b[off] ^= 0xFF
        dst.write_bytes(bytes(b))
        r = B.run_candidate(root, "--verify-only", "--window-rows", "500")
        assert r.returncode == 1 and "VERIFY FAILED" in r.stderr and "window" in r.stderr, (off, r.stderr)
        dst.write_bytes(orig)
    assert B.run_candidate(root, "--verify-only").returncode == 0


def test_help():
    r = subprocess.run([sys.executable, str(TOOLS / "dump_join.py"), "--help"], capture_output=True, text=True)
    assert r.returncode == 0 and "--verify" in r.stdout


def test_replay_root_refusal(allcases):
    real = B.REPO / "output" / "scratch-3-12"
    before = sorted(p.name for p in real.iterdir()) if real.exists() else None
    stat_before = os.stat(real).st_mtime_ns if real.exists() else None
    root = fresh(allcases, "refuse")
    # a replay-root path that is a symlink into the real output/ outside scratch-5-01
    link = root / J.DEFAULT_DST
    os.symlink(real / "dump_ext", link)
    with pytest.raises(B.IsolationError):
        B.check_isolated(root)
    with pytest.raises(B.IsolationError):
        B.run_baseline(root)
    with pytest.raises(B.IsolationError):
        B.run_candidate(root)
    r = subprocess.run([sys.executable, str(TOOLS / "bench_dump_memory.py"), "check-root", "--root", str(root)],
                       capture_output=True, text=True)
    assert r.returncode != 0 and "REFUSED" in r.stderr
    # the repository root itself (relative paths would hit the real output/scratch-3-12)
    with pytest.raises(B.IsolationError):
        B.check_isolated(B.REPO)
    link.unlink()
    shutil.rmtree(root / "output" / "scratch-3-12")
    os.symlink(real, root / "output" / "scratch-3-12")
    with pytest.raises(B.IsolationError):
        B.check_isolated(root)
    assert (sorted(p.name for p in real.iterdir()) if real.exists() else None) == before
    assert (os.stat(real).st_mtime_ns if real.exists() else None) == stat_before
    (root / "output" / "scratch-3-12").unlink()
    B.materialise_replay_root(allcases, root / "ok")
    B.check_isolated(root / "ok")
