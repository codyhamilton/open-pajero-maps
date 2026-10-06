"""Plan 37 Phase 1: synthetic tests for the F2 per-row identity join."""
from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "docs/plans/04-c-core-orchestration/triage/per_rule_phase1_f2_identity.py"
spec = importlib.util.spec_from_file_location("f2_identity", SCRIPT)
f2 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(f2)

NAT = list(f2.NATIVE)


def _write(tmp: Path, rows):
    """rows: (ix, rule, added, changed)."""
    a = ["\t".join(NAT + ["dump_row", "rule_id", "cause"])]
    m = ["\t".join(NAT + ["dump_row", "in_historic_188", "in_added_89"])]
    c = ["level\tix\tiy\tstatus"]
    for i, (ix, rule, added, changed) in enumerate(rows):
        key = ["0", str(ix), "7", "288"] + ["0"] * 7 + ["-1", "-1"]
        a.append("\t".join(key + [str(i), rule, "x"]))
        m.append("\t".join(key + [str(i), "0", str(int(added))]))
        if changed:
            c.append(f"0\t{ix}\t7\tchanged")
    c.append("0\t99999\t7\tchanged")
    for name, lines in (("a.tsv", a), ("m.tsv", m), ("c.tsv", c)):
        (tmp / name).write_text("\n".join(lines) + "\n")
    return tmp / "a.tsv", tmp / "m.tsv", tmp / "c.tsv"


def test_forced_zero_is_o04_o05_on_changed_cells(tmp_path):
    rows = [(1, "O05", 0, 1), (2, "O05", 0, 0), (3, "O04", 1, 1), (4, "O04", 0, 1),
            (5, "O01", 0, 1), (6, "NO_RULE", 0, 1), (7, "O04", 0, 0)]
    res = f2.run(*_write(tmp_path, rows), check_cells_pin=False)
    assert res["forced_zero"]["by_rule"] == {"O05": 1, "O04": 2}
    assert res["forced_zero"]["by_rule_set"] == {"O04/added": 1, "O04/shared": 1, "O05/shared": 1}
    assert sorted(r["dump_row"] for r in res["forced_rows"]) == [0, 2, 3]
    assert res["predicted_317"]["NO_RULE"] == 1 + 3
    assert res["non_forced_rules_on_changed_cells"] == {"NO_RULE": 1, "O01": 1}
    assert res["inputs"]["changed_cells"]["rows"] == 6  # five row cells plus one unrelated
    assert res["match"] is False  # synthetic counts are not the 3-15/3-17 yardsticks


def test_mismatched_partition_row_is_rejected(tmp_path):
    a, m, c = _write(tmp_path, [(1, "O05", 0, 1)])
    m.write_text(m.read_text().replace("\t0\t0\t0\n", "\t5\t0\t0\n"))
    try:
        f2.run(a, m, c, check_cells_pin=False)
    except ValueError:
        return
    raise AssertionError("expected a ValueError for a dump_row mismatch")


def test_cells_pin_enforced(tmp_path):
    try:
        f2.run(*_write(tmp_path, [(1, "O05", 0, 1)]))
    except ValueError as e:
        assert "sha" in str(e)
        return
    raise AssertionError("expected the cell-list pin to fail")
