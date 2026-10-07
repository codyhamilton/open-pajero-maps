"""Plan 58: E1Spool close + per-level cache release (no byte-path change)."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from unittest import mock

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def test_e1spool_close_nulls_views():
    from kiwiw import cenc

    spool = mock.Mock(spec=cenc.E1Spool)
    # Build a minimal stand-in with memmap-like objects
    class _FakeMM(np.ndarray):
        def __new__(cls, n=8):
            obj = np.asarray(np.zeros(n, np.uint8)).view(cls)
            obj._mmap = mock.Mock()
            return obj

    s = cenc.E1Spool.__new__(cenc.E1Spool)
    s.idx = _FakeMM()
    s.data = _FakeMM()
    s.xs = s.ys = s.offsets = s.lengths = np.zeros(1)
    s.drops = np.zeros(1)
    idx_mm = s.idx._mmap
    data_mm = s.data._mmap
    cenc.E1Spool.close(s)
    idx_mm.close.assert_called_once()
    data_mm.close.assert_called_once()
    assert s.idx is None and s.data is None
    assert s.xs is None and s.drops is None


def test_e1spool_cache_closes_previous_level(tmp_path, monkeypatch):
    """_e1spool closes the prior level's spool when the level key changes."""
    import build_alldata as ba

    closed = []

    class FakeSpool:
        def __init__(self, spool_dir, level, *, guard_names=False):
            self.level = level
            self.spool_dir = spool_dir

        def close(self):
            closed.append(self.level)

    monkeypatch.setattr(ba.cenc, "E1Spool", FakeSpool)
    ba._WORKER.clear()
    s0 = ba._e1spool(str(tmp_path), 12)
    assert s0.level == 12
    s1 = ba._e1spool(str(tmp_path), 10)
    assert s1.level == 10
    assert closed == [12]
    st = ba._release_worker_encode_caches()
    assert st["e1spool_closed"] is True
    assert closed == [12, 10]
    ba._WORKER.clear()
