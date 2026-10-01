"""Perf inventory enforcement (plan 04, Phase 1, brief 1-01).

`parser/perf_inventory.json` classifies every non-test Python module under
`parser/` as orchestration, c-now, c-later or retired (plan 04 `DESIGN.md`,
Domain: Python orchestration, "Inventory"). This test fails for any module
absent from it, any entry naming a missing file, an unknown class, a
`c-now`/`retired` entry without a phase in 2-5, or any other entry with one.
Test modules under `parser/tests/` are covered by the single glob entry.
"""
from __future__ import annotations

import json
import unittest
from pathlib import Path

PARSER = Path(__file__).resolve().parent.parent
ROOT = PARSER.parent
INVENTORY = PARSER / "perf_inventory.json"
TESTS_GLOB = "parser/tests/**/*.py"
CLASSES = {"orchestration", "c-now", "c-later", "retired"}
PHASED = {"c-now", "retired"}


def _load() -> list[dict]:
    return json.loads(INVENTORY.read_text())["modules"]


def _modules() -> set[str]:
    out = set()
    for p in PARSER.rglob("*.py"):
        rel = p.relative_to(ROOT)
        if "__pycache__" in rel.parts or rel.parts[:2] == ("parser", "tests"):
            continue
        out.add(rel.as_posix())
    return out


class PerfInventoryTest(unittest.TestCase):
    def test_inventory_covers_every_module(self):
        entries = _load()
        paths = {e["path"] for e in entries if e["path"] != TESTS_GLOB}
        mods = _modules()
        missing = sorted(mods - paths)
        stale = sorted(p for p in paths - mods if not (ROOT / p).is_file())
        self.assertEqual(missing, [], f"modules missing from perf_inventory.json: {missing}")
        self.assertEqual(stale, [], f"inventory entries naming missing files: {stale}")

    def test_no_duplicates_and_one_glob(self):
        paths = [e["path"] for e in _load()]
        dups = sorted({p for p in paths if paths.count(p) > 1})
        self.assertEqual(dups, [], f"duplicate inventory entries: {dups}")
        globs = [p for p in paths if "*" in p]
        self.assertEqual(globs, [TESTS_GLOB], f"only the tests glob is allowed: {globs}")

    def test_classes_and_phases(self):
        bad_class, bad_phase, bad_reason = [], [], []
        for e in _load():
            p, c, ph = e["path"], e.get("class"), e.get("phase")
            if c not in CLASSES:
                bad_class.append(p)
                continue
            if c in PHASED and ph not in (2, 3, 4, 5):
                bad_phase.append(p)
            if c not in PHASED and ph is not None:
                bad_phase.append(p)
            if not str(e.get("reason", "")).strip():
                bad_reason.append(p)
        self.assertEqual(bad_class, [], f"entries with a class outside {sorted(CLASSES)}: {bad_class}")
        self.assertEqual(bad_phase, [], f"entries with a wrong phase for their class: {bad_phase}")
        self.assertEqual(bad_reason, [], f"entries with no reason: {bad_reason}")

    def test_tests_glob_is_orchestration(self):
        g = [e for e in _load() if e["path"] == TESTS_GLOB]
        self.assertEqual(len(g), 1)
        self.assertEqual(g[0]["class"], "orchestration")


if __name__ == "__main__":
    unittest.main()
