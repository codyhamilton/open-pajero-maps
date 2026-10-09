"""Plan 63: producer_tie helpers."""
import sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parent), str(HERE.parent / "tools")]
import producer_tie as pt  # noqa: E402


def h(cid, blob, dec):
    return {"cid": cid, "clip_blob_sha256": blob, "decide": dec}


def test_tie_class():
    assert pt.tie_class([h([0, 1, 2, 0], "a", "build")])[0] == "T0"
    assert pt.tie_class([])[0] == "T0"
    assert pt.tie_class([h([0, 1, 2, 0], "a", "build"), h([0, 1, 2, 1], "a", "build")])[0] == "T1"
    assert pt.tie_class([h([0, 1, 2, 0], "a", "build"), h([0, 1, 2, 1], "b", "build")])[0] == "T2"
    c, r = pt.tie_class([h([0, 1, 2, 0], "a", "build"), h([0, 1, 2, 1], "a", "no_oe")])
    assert c == "T2" and "decide verdicts differ" in r


def test_lowest_key():
    assert pt.lowest_key([h([0, 5, 2, 1], "a", ""), h([0, 5, 2, 0], "a", "")]) == (0, 5, 2)
    assert pt.lowest_key([]) is None


def test_duplicate_pairs():
    recs = [(0, 288, b"x"), (1, 288, b"P"), (2, 288, b"y"), (3, 288, b"P"), (4, 291, b"P")]
    assert pt.duplicate_pairs(recs, [1, 3]) == [[1, 3]]
    assert pt.duplicate_pairs(recs, [4]) == [[4]]
