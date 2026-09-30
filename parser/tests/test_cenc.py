"""C build kernel schema binding (plan 03): `_cenc.c`'s column table matches the
spool's. The build-path encoders are covered by `test_e2.py`'s goldens and the
C unit binary (`test_c_units.py`); no test compares C against a Python
encoder (Contract T)."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from kiwiw import cenc, spool

pytestmark = pytest.mark.skipif(cenc._load_lib() is None, reason="no C compiler")


def test_column_table_matches_spool():
    lib = cenc._load_lib()
    import ctypes
    lib.kw_ncols.restype = lib.kw_col_size.restype = lib.kw_col_key.restype = ctypes.c_int
    lib.kw_col_size.argtypes = lib.kw_col_key.argtypes = [ctypes.c_int]
    assert lib.kw_ncols() == len(spool._COLUMNS)
    for i, (name, dt, key) in enumerate(spool._COLUMNS):
        assert lib.kw_col_size(i) == spool.np.dtype(dt).itemsize, name
        assert lib.kw_col_key(i) == spool._COUNT_KEYS.index(key), name
