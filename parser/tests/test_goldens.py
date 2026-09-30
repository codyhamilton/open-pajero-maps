"""Contract T (c) goldens (3C-03): the windowed build on each closed fixture
spool must reproduce the captured frames byte for byte.

The test drives `build_alldata.py --spool <fixture> --window ... --frame-dump
...` as a subprocess, so it tests the build, not any module, and survives the
port unchanged. Goldens were captured by `parser/tools/golden_capture.py`.

Committed goldens live under `parser/tests/fixtures/goldens/<name>/`. Goldens
too large to commit are listed in `fixtures/goldens/local.json` and live under
`output/goldens-3C/<name>/` (see `docs/provenance.md`); they skip when absent.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
BUILD = REPO / "parser" / "build_alldata.py"
COMMITTED = REPO / "parser" / "tests" / "fixtures" / "goldens"
LOCAL = REPO / "output" / "goldens-3C"


def _committed() -> list[str]:
    return sorted(p.parent.name for p in COMMITTED.glob("*/golden.json"))


def _local() -> list[str]:
    f = COMMITTED / "local.json"
    return sorted(json.loads(f.read_text())["goldens"]) if f.exists() else []


def _cases():
    cases = [pytest.param(COMMITTED / n, 1, id=n) for n in _committed()]
    cases += [pytest.param(LOCAL / n, 1, id=f"local-{n}") for n in _local()]
    if _committed():  # one -j 4 run on the largest committed golden
        big = max(_committed(), key=lambda n: (COMMITTED / n / "frames.bin").stat().st_size)
        cases.append(pytest.param(COMMITTED / big, 4, id=f"{big}-j4"))
    return cases


@pytest.mark.parametrize("golden,jobs", _cases())
def test_golden(golden: Path, jobs: int, tmp_path: Path):
    if not (golden / "golden.json").exists() or not (golden / "spool").is_dir():
        pytest.skip(f"local golden {golden.name} absent: regenerate it with "
                    f"parser/tools/golden_capture.py (docs/provenance.md, 3C-03)")
    meta = json.loads((golden / "golden.json").read_text())
    cmd = [sys.executable, str(BUILD), "--spool", str(golden / "spool"),
           "--out", str(tmp_path / "ALLDATA.KWI"),
           "--window", str(meta["level"]), *map(str, meta["window"]),
           "--frame-dump", str(tmp_path / "frames"), "-j", str(jobs)]
    r = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-3000:]

    got_rows = (tmp_path / "frames.tsv").read_text().splitlines()
    got = (tmp_path / "frames.bin").read_bytes()
    want_rows = (golden / "frames.tsv").read_text().splitlines()
    want = (golden / "frames.bin").read_bytes()

    assert len(got_rows) == meta["frames"] == len(want_rows)
    for g, w in zip(got_rows, want_rows):
        assert g == w, f"frame differs:\n got  {g}\n want {w}"
    assert [row.split()[8] for row in got_rows] == meta["frame_sha256"]
    for row in got_rows:  # every frame's bytes hash to its recorded sha256
        f = row.split()
        off, n = int(f[6]), int(f[7])
        assert hashlib.sha256(got[off:off + n]).hexdigest() == f[8]
    assert hashlib.sha256(got).hexdigest() == meta["total_sha256"]
    assert got == want
