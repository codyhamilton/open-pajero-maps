"""Bounded 3-07 s02 extension vs vendored baseline (plan 05 Phase 3)."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

PARSER = Path(__file__).resolve().parent.parent
TOOLS = PARSER / "tools"
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(PARSER))
import dump_join as J  # noqa: E402
from kiwiw import cenc  # noqa: E402

BASELINE_DIR = PARSER / "tests" / "fixtures" / "extend_3_07_baseline"
SCRATCH = PARSER.parent / "output" / "scratch-5-03"
GROUP = J.GROUP
INT32_MIN = J.INT32_MIN
OLD = cenc.K1_DUMP_DTYPE
assert OLD.itemsize == 144


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


@pytest.fixture(scope="module", autouse=True)
def _scratch():
    SCRATCH.mkdir(parents=True, exist_ok=True)
    d = SCRATCH / f"tests-s02-{os.getpid()}"
    d.mkdir(parents=True, exist_ok=True)
    yield d
    shutil.rmtree(d, ignore_errors=True)


def _type_map():
    out = {}
    for nm in OLD.names:
        dt = OLD.fields[nm][0]
        if dt == np.dtype("<f8"):
            out[nm] = "f64"
        elif dt == np.dtype("<i4"):
            out[nm] = "i32"
        elif dt == np.dtype("<u2"):
            out[nm] = "u16"
        else:
            out[nm] = "u8"
    return out


def _side_dt():
    return np.dtype([(k, "<i4") for k in GROUP] + [
        ("hx", "<i4"), ("hy", "<i4"), ("rec", "<i4"), ("tall", "<i4"), ("nv", "<i4"),
        ("closing", "<i4"), ("crossing_count", "<i4"), ("status", "<i4"), ("rows", "<i8")])


def _write_s02_fixture(root: Path, n: int = 5003, seed: int = 9):
    rng = np.random.default_rng(seed)
    dump = root / "output" / "scratch-3-03" / "dump"
    side_root = root / "output" / "scratch-3-07"
    dump.mkdir(parents=True, exist_ok=True)
    side_root.mkdir(parents=True, exist_ok=True)
    type_map = _type_map()
    rows_bb = np.zeros(n, OLD)
    rows_bb["level"] = 0
    rows_bb["code"] = 291
    rows_bb["src_ix"] = INT32_MIN
    rows_bb["ix"] = rng.integers(0, 40, n)
    rows_bb["iy"] = rng.integers(0, 40, n)
    rows_bb["shape"] = rng.integers(0, 15, n)
    for p in ("p0", "p1", "p2", "p3", "p4", "p5", "p6"):
        rows_bb[p] = rng.integers(0, 6, n)
    rows_bb["lat"] = rng.normal(size=n)
    rows_bb["d_any"] = np.where(rng.random(n) < 0.1, np.nan, rng.random(n))
    out = rng.random(n) < 0.25
    rows_bb["level"][out] = 1
    rows_bb["code"][out] = 100
    rows_bb["src_ix"][out] = 0
    (dump / "background_boundary.bin").write_bytes(rows_bb.tobytes())
    other = np.zeros(64, OLD)
    other["code"] = 1
    (dump / "background.bin").write_bytes(other.tobytes())
    fields = [{"name": nm, "type": type_map[nm]} for nm in OLD.names]
    kinds = {
        "background_boundary": {"rows": n, "row_size": 144, "file": "background_boundary.bin",
                                "fields": fields},
        "background": {"rows": 64, "row_size": 144, "file": "background.bin", "fields": fields},
    }
    (dump / "dump_manifest.json").write_text(json.dumps(
        {"fields": fields, "kinds": kinds, "row_size": 144}, indent=2))

    scope = (rows_bb["level"] == 0) & (rows_bb["code"] == 291) & (rows_bb["src_ix"] == INT32_MIN)
    # unique GROUP keys among in-scope rows
    kd = np.dtype([(k, OLD[k]) for k in GROUP])
    keys = np.empty(int(scope.sum()), kd)
    for k in GROUP:
        keys[k] = rows_bb[k][scope]
    ukey, inv, counts = np.unique(keys, return_inverse=True, return_counts=True)
    # status==1 for even unique keys; status==0 for odd (still listed so cast/miss paths exist)
    side = np.zeros(len(ukey) + 5, _side_dt())
    for i in range(len(ukey)):
        for k in GROUP:
            side[k][i] = int(ukey[k][i])
        if i % 2 == 0:
            side["status"][i] = 1
            side["rows"][i] = int(counts[i])  # aggregate assert weight == dump matches
        else:
            side["status"][i] = 0
            side["rows"][i] = int(counts[i])
    # miss keys (status 1 but not in dump) must NOT be included — would break aggregate assert
    for j in range(5):
        i = len(ukey) + j
        side["ix"][i] = 900000 + j
        side["status"][i] = 0
        side["rows"][i] = 1
    # stable-sort duplicate: append a status=0 duplicate of a status=1 key (leftmost status=1 wins)
    if len(ukey):
        side = np.concatenate([side, side[:1]])
        side["status"][-1] = 0
        side["rows"][-1] = 0
    np.save(side_root / "side_background_boundary.npy", side)
    (side_root / "witness.py").write_text(
        "from pathlib import Path\n"
        "import json, numpy as np\n"
        "ROOT = Path('output/scratch-3-07')\n"
        "DUMP = Path('output/scratch-3-03/dump')\n"
        f"GROUP = {GROUP!r}\n"
        "def dump(kind):\n"
        "    doc=json.loads((DUMP/'dump_manifest.json').read_text())\n"
        "    kinds={'f64':'<f8','i32':'<i4','u16':'<u2','u8':'u1'}\n"
        "    dt=np.dtype([(f['name'],kinds[f['type']]) for f in doc['fields']],align=True)\n"
        "    return np.memmap(DUMP/doc['kinds'][kind]['file'],dtype=dt,mode='r')\n"
    )
    shutil.copyfile(BASELINE_DIR / "extend_dump_attempt3.py", root / "extend_dump_attempt3.py")
    return root


def _hashes(dst: Path) -> dict:
    return {p.relative_to(dst).as_posix(): _sha(p)
            for p in sorted(dst.rglob("*")) if p.is_file()}


def test_vendored_s02_baseline_hash():
    line = (BASELINE_DIR / "SHA256SUMS").read_text().splitlines()[0]
    h, n = line.split()
    assert n == "extend_dump_attempt3.py"
    assert _sha(BASELINE_DIR / n) == h


@pytest.mark.parametrize("window", [None, 1, 65536, 997])
def test_s02_candidate_matches_baseline(_scratch, window):
    root = _scratch / f"fix-{window}"
    if root.exists():
        shutil.rmtree(root)
    _write_s02_fixture(root)
    env = dict(os.environ)
    rb = subprocess.run([sys.executable, "extend_dump_attempt3.py"], cwd=root, env=env,
                        capture_output=True, text=True)
    assert rb.returncode == 0, rb.stderr + rb.stdout
    base_dst = root / "output" / "scratch-3-07" / "dump_attempt3"
    base_copy = _scratch / f"base-out-{window}"
    if base_copy.exists():
        shutil.rmtree(base_copy)
    shutil.copytree(base_dst, base_copy)
    shutil.rmtree(base_dst)
    args = [sys.executable, str(TOOLS / "dump_join.py"), "--mode", "s02",
            "--dump", "output/scratch-3-03/dump",
            "--side", "output/scratch-3-07/side_background_boundary.npy",
            "--s02-dst", "output/scratch-3-07/dump_attempt3"]
    if window is not None:
        args += ["--window-rows", str(window)]
    rc = subprocess.run(args, cwd=root, capture_output=True, text=True)
    assert rc.returncode == 0, rc.stderr + rc.stdout
    assert _hashes(base_dst) == _hashes(base_copy)


def test_s02_empty_kind_rejected(_scratch):
    """Zero-row mapped kinds must be rejected (Assumption 7), not empty successes."""
    root = _scratch / "empty-kind"
    root.mkdir(parents=True, exist_ok=True)
    dump = root / "dump"
    dump.mkdir()
    # non-empty background_boundary, empty second kind file
    n = 64
    rows = np.zeros(n, OLD)
    rows["level"] = 0
    rows["code"] = 291
    rows["src_ix"] = INT32_MIN
    (dump / "background_boundary.bin").write_bytes(rows.tobytes())
    (dump / "empty_kind.bin").write_bytes(b"")
    fields = [{"name": nm, "type": "i32" if OLD.fields[nm][0] == np.dtype("<i4") else
               ("f64" if OLD.fields[nm][0] == np.dtype("<f8") else
                ("u16" if OLD.fields[nm][0] == np.dtype("<u2") else "u8"))}
              for nm in OLD.names]
    kinds = {
        "background_boundary": {"rows": n, "row_size": 144, "file": "background_boundary.bin",
                                "fields": fields},
        "empty_kind": {"rows": 0, "row_size": 144, "file": "empty_kind.bin", "fields": fields},
    }
    (dump / "dump_manifest.json").write_text(json.dumps(
        {"fields": fields, "kinds": kinds, "row_size": 144}, indent=2))
    side = np.zeros(1, _side_dt())
    side["status"][0] = 0
    side_path = root / "side.npy"
    np.save(side_path, side)
    dst = root / "dst"
    import pytest as _pytest
    with _pytest.raises(ValueError, match="zero-row"):
        J.extend_s02_producer(dump, side_path, dst, window_rows=16)
