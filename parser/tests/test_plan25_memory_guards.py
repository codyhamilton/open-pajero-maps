"""Plan 25 Phase 2b: argv/peak wrapper + whole-file refuse + cell_local caps."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
TOOLS = REPO / "parser" / "tools"
sys.path.insert(0, str(TOOLS))
from whole_file_guard import (  # noqa: E402
    WHOLE_FILE_REFUSE_BYTES,
    WholeFileReadError,
    read_bytes_guarded,
    refuse_whole_file_read,
)


def test_refuse_whole_file_read_trips_on_large(tmp_path):
    p = tmp_path / "big.bin"
    p.write_bytes(b"x" * 1024)
    with pytest.raises(WholeFileReadError):
        refuse_whole_file_read(p, size=WHOLE_FILE_REFUSE_BYTES)
    with pytest.raises(WholeFileReadError):
        refuse_whole_file_read(p, size=WHOLE_FILE_REFUSE_BYTES + 1)
    assert refuse_whole_file_read(p, size=WHOLE_FILE_REFUSE_BYTES - 1) == WHOLE_FILE_REFUSE_BYTES - 1


def test_read_bytes_guarded_small_ok(tmp_path):
    p = tmp_path / "small.bin"
    p.write_bytes(b"abc")
    assert read_bytes_guarded(p) == b"abc"


def test_run_heavy_python_records_argv_and_peak(tmp_path):
    log = tmp_path / "run.json"
    cmd = [
        sys.executable, "-B", str(TOOLS / "run_heavy_python.py"),
        "--log", str(log), "--no-flock", "--cwd", str(REPO), "--",
        sys.executable, "-B", "-c", "print(42)",
    ]
    r = subprocess.run(cmd, cwd=str(REPO), capture_output=True, text=True)
    assert r.returncode == 0, r.stderr + r.stdout
    rec = json.loads(log.read_text())
    assert rec["exit"] == 0
    assert rec["argv"][-1] == "print(42)" or "print(42)" in rec["argv"]
    assert isinstance(rec["memory_peak"], int) and rec["memory_peak"] > 0
    assert isinstance(rec["max_rss_kib"], int) and rec["max_rss_kib"] > 0


def test_cell_local_refuses_uncapped():
    script = REPO / "docs/plans/14-completeness-root-cause/triage/cell_local_2-01.py"
    r = subprocess.run(
        [sys.executable, "-B", str(script)],
        cwd=str(REPO), capture_output=True, text=True,
    )
    assert r.returncode != 0
    assert "refuse uncapped" in (r.stderr + r.stdout)
