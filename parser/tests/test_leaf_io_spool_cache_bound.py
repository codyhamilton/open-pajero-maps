"""Plan 57: spool cell/key cache clear + max-entries bound (no OE/cover change)."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
P5 = (
    ROOT.parent
    / "docs/plans/04-c-core-orchestration/triage/historical_bg/p5_owner_exclusive"
)
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(P5))


def _load_leaf_io():
    spec = importlib.util.spec_from_file_location("leaf_io_p57", P5 / "leaf_io.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def leaf_io():
    mod = _load_leaf_io()
    mod.clear_spool_caches()
    mod.set_spool_cell_cache_max(0)
    mod.set_refuse_whole_level(False)
    yield mod
    mod.clear_spool_caches()
    mod.set_spool_cell_cache_max(0)
    mod.set_refuse_whole_level(False)


def test_clear_spool_caches_drops_entries(leaf_io):
    leaf_io._SPOOL_KEY_CACHE[(0, "/tmp")] = [(1, 2)]
    leaf_io._SPOOL_CELL_CACHE[(0, "/tmp", 1, 2)] = {"backgrounds": []}
    assert leaf_io.spool_cache_stats()["key_entries"] == 1
    assert leaf_io.spool_cache_stats()["cell_entries"] == 1
    leaf_io.clear_spool_caches()
    st = leaf_io.spool_cache_stats()
    assert st["key_entries"] == 0
    assert st["cell_entries"] == 0


def test_max_entries_clears_cell_cache_when_over(leaf_io):
    leaf_io.set_spool_cell_cache_max(3)
    for i in range(5):
        leaf_io._SPOOL_CELL_CACHE[(0, "/tmp", i, 0)] = {"i": i}
        leaf_io._maybe_bound_cell_cache()
    # After 4th insert len was 4 > 3 → clear; 5th insert alone remains (or cleared again).
    st = leaf_io.spool_cache_stats()
    assert st["cell_max"] == 3
    assert st["cell_entries"] <= 3


def test_without_max_cache_grows(leaf_io):
    leaf_io.set_spool_cell_cache_max(0)
    for i in range(20):
        leaf_io._SPOOL_CELL_CACHE[(0, "/tmp", i, 0)] = {"i": i}
        leaf_io._maybe_bound_cell_cache()
    assert leaf_io.spool_cache_stats()["cell_entries"] == 20


def test_refuse_whole_level(leaf_io):
    leaf_io.set_refuse_whole_level(True)

    class _Fake:
        spool_dir = "/tmp"

        def iter_level(self, level):
            return iter([])

    with pytest.raises(RuntimeError, match="refused under mass/control"):
        leaf_io.spool_level_cells(_Fake(), 0)


def test_control_and_mass_expose_cache_flags():
    """Plan 57: control/mass argparse advertise clear-every + max-cells (wiring smoke)."""
    import ast
    from pathlib import Path

    p5 = (
        Path(__file__).resolve().parents[1].parent
        / "docs/plans/04-c-core-orchestration/triage/historical_bg/p5_owner_exclusive"
    )
    for name in ("control.py", "mass_decide.py"):
        src = (p5 / name).read_text()
        assert "--cache-clear-every" in src, name
        assert "--cache-max-cells" in src, name
        ast.parse(src)
