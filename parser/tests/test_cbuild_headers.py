"""Tests for 3-01: `cbuild`'s content hash must cover `parser/kiwiw/*.h`, so a
header-only edit (`_k1.h`, `_d1.h`) rebuilds the extension and the C test
binary instead of running against a stale product."""
from __future__ import annotations

import ctypes
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from kiwiw import cbuild

pytestmark = pytest.mark.skipif(
    shutil.which("gcc") is None and shutil.which("cc") is None,
    reason="no C compiler",
)

A_C = '#include "b.h"\nint val(void) { return VAL; }\n'
B_H = "#define VAL {n}\n"
TEST_C = ('#include "b.h"\n'
          '#include <stdio.h>\n'
          'int main(void) { printf("%d\\n", VAL); return 0; }\n')


def _write(p: Path, text: str) -> Path:
    p.write_text(text)
    return p


def _hash_mtime(out: Path) -> int:
    return cbuild._hash_path(out).stat().st_mtime_ns


def test_build_ext_rebuilds_on_header_change(tmp_path: Path) -> None:
    a_c = _write(tmp_path / "a.c", A_C)
    b_h = _write(tmp_path / "b.h", B_H.format(n=1))
    out = tmp_path / "x.so"

    cbuild.build_ext(sources=(a_c,), out=out, headers=(b_h,))

    before = _hash_mtime(out)
    cbuild.build_ext(sources=(a_c,), out=out, headers=(b_h,))
    assert _hash_mtime(out) == before, "second identical build must not rebuild"

    _write(b_h, B_H.format(n=2))
    assert cbuild.is_stale(out, (a_c, b_h), cbuild.CFLAGS)

    cbuild.build_ext(sources=(a_c,), out=out, headers=(b_h,))
    lib = ctypes.CDLL(str(out))
    assert lib.val() == 2


def test_build_test_bin_rebuilds_on_header_change(tmp_path: Path) -> None:
    ctest = tmp_path / "ctest"
    ctest.mkdir()
    _write(ctest / "t.c", TEST_C)
    b_h = _write(ctest / "b.h", B_H.format(n=1))
    out = tmp_path / "ctest_bin"

    cbuild.build_test_bin(ctest_dir=ctest, out=out, ext_sources=(),
                          headers=(b_h,))
    first = subprocess.run([str(out)], capture_output=True, text=True)
    assert first.stdout.strip() == "1"

    before = _hash_mtime(out)
    cbuild.build_test_bin(ctest_dir=ctest, out=out, ext_sources=(),
                          headers=(b_h,))
    assert _hash_mtime(out) == before, "second identical build must not rebuild"

    _write(b_h, B_H.format(n=2))
    cbuild.build_test_bin(ctest_dir=ctest, out=out, ext_sources=(),
                          headers=(b_h,))
    second = subprocess.run([str(out)], capture_output=True, text=True)
    assert second.stdout.strip() == "2"


def test_ext_headers_includes_real_tree_headers() -> None:
    names = {p.name for p in cbuild._ext_headers()}
    assert "_k1.h" in names
    assert "_d1.h" in names
