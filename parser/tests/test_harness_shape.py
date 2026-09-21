"""BMT keyed comparison / DSA ordering (`harness/checks/shape.py`)."""
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace as NS

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from harness.checks import shape

EMPTY = 0xFFFFFFFF


def _pd(tables):
    """tables: list of ((level, blockset), [dsa, ...])."""
    blocksets = [NS(level=k[0], blockset_index=k[1]) for k, _ in tables]
    bmt = [NS(blockset_ordinal=i, entries=[NS(dsa=d, size=1) for d in dsas])
           for i, (_, dsas) in enumerate(tables)]
    return NS(blocksets=blocksets, bmt_tables=bmt)


R = [((0, 0), [10, 20]), ((0, 1), [30, EMPTY, 40])]


def test_identical_passes():
    assert shape.bmt_key_diffs(shape.bmt_keys(_pd(R)), _pd(R), _pd(R)) == []


def test_extra_table_named():
    g = _pd(R + [((0, 2), [50])])
    d = shape.bmt_key_diffs(shape.bmt_keys(_pd(R)), g, _pd(R))
    assert any("level 0, blockset 2" in x and "generated only" in x for x in d)


def test_reordered_tables_flagged():
    g = _pd([R[1], R[0]])
    d = shape.bmt_key_diffs(shape.bmt_keys(_pd(R)), g, _pd(R))
    assert any("different order" in x for x in d)


def test_non_monotonic_dsa_flagged():
    g = _pd([((0, 0), [10, 20]), ((0, 1), [15, EMPTY, 40])])
    d = shape.bmt_key_diffs(shape.bmt_keys(_pd(R)), g, _pd(R))
    assert any("DSA order" in x and "level 0, blockset 1" in x for x in d)


def test_empty_pattern_and_missing_table():
    g = _pd([((0, 0), [10, EMPTY])])
    d = shape.bmt_key_diffs(shape.bmt_keys(_pd(R)), g, _pd(R))
    assert any("missing from generated" in x for x in d)
    assert any("empty pattern" in x for x in d)
