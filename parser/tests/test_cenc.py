"""C build kernel schema binding (plan 03): `_cenc.c`'s column table matches the
spool's. The build-path encoders are covered by `test_e2.py`'s goldens and the
C unit binary (`test_c_units.py`); no test compares C against a Python
encoder (Contract T)."""
from __future__ import annotations

import sys
import ctypes
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from kiwiw import cbuild, cenc, spool


def test_column_table_matches_spool():
    lib = cenc._load_lib()
    import ctypes
    lib.kw_ncols.restype = lib.kw_col_size.restype = lib.kw_col_key.restype = ctypes.c_int
    lib.kw_col_size.argtypes = lib.kw_col_key.argtypes = [ctypes.c_int]
    assert lib.kw_ncols() == len(spool._COLUMNS)
    for i, (name, dt, key) in enumerate(spool._COLUMNS):
        assert lib.kw_col_size(i) == spool.np.dtype(dt).itemsize, name
        assert lib.kw_col_key(i) == spool._COUNT_KEYS.index(key), name


@pytest.fixture
def fresh_loader(monkeypatch):
    monkeypatch.setattr(cenc, "_lib", None)
    monkeypatch.setattr(cenc, "_tried", False)
    monkeypatch.setattr(cbuild, "build_ext", lambda: None)
    return monkeypatch


def _assembly_library():
    return SimpleNamespace(**{name: SimpleNamespace() for name in
                             ("kw_col_name", "kw_copy_frames", "kw_write_rows")})


def test_load_open_error_preserves_cause(fresh_loader):
    cause = OSError("invalid shared library")

    def fail_open(path):
        raise cause

    fresh_loader.setattr(ctypes, "CDLL", fail_open)
    with pytest.raises(cbuild.BuildError) as caught:
        cenc.lib()
    assert caught.value.__cause__ is cause
    assert str(cenc._SO) in str(caught.value)
    assert cenc._lib is None and not cenc._tried


@pytest.mark.parametrize("missing", ["kw_col_name", "kw_copy_frames", "kw_write_rows"])
def test_load_missing_assembly_symbol(fresh_loader, missing):
    lib = _assembly_library()
    delattr(lib, missing)
    fresh_loader.setattr(ctypes, "CDLL", lambda path: lib)
    with pytest.raises(cbuild.BuildError) as caught:
        cenc.lib()
    assert isinstance(caught.value.__cause__, AttributeError)
    assert missing in str(caught.value)
    assert str(cenc._SO) in str(caught.value)
    assert cenc._lib is None and not cenc._tried


def test_load_compiler_error_propagates(fresh_loader):
    cause = cbuild.BuildError("no compiler")

    def fail_build():
        raise cause

    fresh_loader.setattr(cbuild, "build_ext", fail_build)
    with pytest.raises(cbuild.BuildError) as caught:
        cenc.lib()
    assert caught.value is cause
    assert cenc._lib is None and not cenc._tried


def test_load_retries_after_repaired_library(fresh_loader):
    broken = _assembly_library()
    del broken.kw_write_rows
    valid = _assembly_library()
    attempts = iter([broken, valid])
    fresh_loader.setattr(ctypes, "CDLL", lambda path: next(attempts))
    with pytest.raises(cbuild.BuildError):
        cenc.lib()
    assert cenc.lib() is valid


def test_load_success_configures_and_caches(fresh_loader):
    lib = _assembly_library()
    builds, opens = [], []
    fresh_loader.setattr(cbuild, "build_ext", lambda: builds.append(True))

    def open_lib(path):
        opens.append(path)
        return lib

    fresh_loader.setattr(ctypes, "CDLL", open_lib)
    assert cenc.lib() is cenc.lib() is lib
    assert builds == [True] and opens == [str(cenc._SO)]
    assert lib.kw_col_name.restype is ctypes.c_char_p
    assert lib.kw_col_name.argtypes == [ctypes.c_int]
    assert lib.kw_copy_frames.restype is lib.kw_write_rows.restype is ctypes.c_int64
    assert lib.kw_copy_frames.argtypes == [ctypes.c_int, ctypes.c_int64,
        ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p,
        ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int64]
    assert lib.kw_write_rows.argtypes == [ctypes.c_int, ctypes.c_int64,
        ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int64, ctypes.c_int64]
