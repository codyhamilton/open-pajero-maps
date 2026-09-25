"""pytest entry point for layer (b), the C unit-test binary (Contract T,
plan 03 3C-02). Builds `parser/kiwiw/ctest/*.c` on demand through
`kiwiw.cbuild` and runs it; `pytest parser/tests` stays the single entry
point (Contract T (b))."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from kiwiw import cbuild


def _run_ctest_bin() -> subprocess.CompletedProcess:
    binary = cbuild.build_test_bin()
    return subprocess.run([str(binary)], capture_output=True, text=True)


def test_c_unit_binary_all_cases_pass():
    proc = _run_ctest_bin()
    lines = proc.stdout.splitlines()
    cases = [ln for ln in lines if ln.startswith("CASE ")]
    failures = [ln for ln in cases if " FAIL" in ln]
    assert cases, f"no CASE lines in output; stdout={proc.stdout!r} stderr={proc.stderr!r}"
    assert proc.returncode == 0 and not failures, (
        f"C unit test binary reported failures (exit {proc.returncode}):\n"
        + "\n".join(failures or cases) + f"\nstderr={proc.stderr}")
