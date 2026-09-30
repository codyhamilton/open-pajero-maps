"""E2, the Stage 1 kernel (plan 03, 3C-07; DESIGN.md Contract B, "E2").

Layer (a) at the boundary, against the Contract T (c) goldens: each golden's
fixture spool goes through E1 (whole level, the golden's window as the
receiver window), E1's rows are routed to their targets with one stable
numpy sort, and E2 encodes the window. No build logic lives here and
nothing is compared with a Python re-implementation: the oracle is the
golden's frame bytes (`frames.bin` / `frames.tsv`).

For every golden:
  * every frame E2 emits is byte-equal to the golden's undivided frame
    (`pt == 0`) of that cell, in the golden's order;
  * E2's declined set is exactly the golden's divided parents (cells with
    any `pt != 0` frame), each declined for reason 1 (needs division);
  * a range split into two calls gives the same frames and index as one;
  * each declined cell's merged content decodes with `decode_columns` and
    re-encodes to the same bytes.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from kiwiw import cenc, descriptor
from kiwiw.spool import decode_columns, encode_columns

import build_alldata

REPO = Path(__file__).resolve().parents[2]
COMMITTED = Path(__file__).resolve().parent / "fixtures" / "goldens"
LOCAL = REPO / "output" / "goldens-3C"


def _cases():
    names = sorted(p.name for p in COMMITTED.iterdir()
                   if p.is_dir() and (p / "golden.json").exists())
    out = [pytest.param(COMMITTED / n, id=n) for n in names]
    local = COMMITTED / "local.json"
    if local.exists():
        out += [pytest.param(LOCAL / n, id=f"local-{n}") for n in json.loads(local.read_text())["goldens"]]
    return out


def _golden_frames(g: Path):
    rows = [ln.split("\t") for ln in (g / "frames.tsv").read_text().splitlines() if ln]
    blob = (g / "frames.bin").read_bytes()
    out = []
    for r in rows:
        ix, iy, pt, off, ln = int(r[1]), int(r[2]), int(r[3]), int(r[6]), int(r[7])
        out.append((ix, iy, pt, blob[off:off + ln]))
    return out


def _setup(g: Path):
    meta = json.loads((g / "golden.json").read_text())
    level = meta["level"]
    ix0, iy0, ix1, iy1 = meta["window"]
    win = (ix0, ix1 - 1, iy0, iy1 - 1)          # half-open -> inclusive (as the build)
    mask = build_alldata.load_parcel_mask()
    budgets = build_alldata._load_level_kind_budgets().get(level) or {}
    desc = descriptor.build_for_spool(
        g / "spool", level, mask_rect=mask.get(level), window=win,
        threshold=build_alldata._load_level_thresholds()[level],
        kind_limits={"road": budgets.get("road"), "bg": budgets.get("background"),
                     "name": budgets.get("name")})
    sp = cenc.E1Spool(g / "spool", level)
    rows, _c = cenc.e1(desc, sp, None, None)
    # routing: one stable sort by target (iy, ix); E1's source order is kept
    rows = rows[np.lexsort((rows["tix"], rows["tiy"]))]
    return level, win, desc, sp, rows


def _run(desc, sp, rows, bounds, path: Path):
    """E2 over consecutive target-row ranges `bounds` (edges; None = open),
    each range's frames appended to `path`. Returns (index, declined, blobs)."""
    idx, dec, blobs = [], [], []
    with open(path, "wb") as fh:
        off = 0
        for lo, hi in zip(bounds[:-1], bounds[1:]):
            a = 0 if lo is None else int(np.searchsorted(rows["tiy"], lo))
            b = len(rows) if hi is None else int(np.searchsorted(rows["tiy"], hi))
            ix, de, blob, cnt = cenc.e2(desc, sp, rows[a:b], lo, hi, fh.fileno(), off)
            assert ix.dtype == descriptor.E2_INDEX_DTYPE
            assert de.dtype == descriptor.E2_DECLINED_DTYPE
            assert cnt["frame_bytes"] == int(ix["len"].sum())
            off += cnt["frame_bytes"]
            idx.append(ix); dec.append(de); blobs.append((de, blob))
    return np.concatenate(idx), np.concatenate(dec), blobs, path.read_bytes()


@pytest.mark.parametrize("golden", _cases())
def test_e2_matches_golden(golden: Path, tmp_path: Path):
    if not golden.exists():
        pytest.skip(f"local golden {golden.name} absent (see docs/provenance.md)")
    level, win, desc, sp, rows = _setup(golden)
    gold = _golden_frames(golden)
    idx, dec, blobs, fbytes = _run(desc, sp, rows, [None, None], tmp_path / "one.bin")

    # frames: E2's undivided frames, in stream order, equal the golden's pt==0 frames
    want = [(ix, iy, fb) for ix, iy, pt, fb in gold if pt == 0]
    got = [(int(r["ix"]), int(r["iy"]), fbytes[int(r["off"]):int(r["off"]) + int(r["len"])])
           for r in idx]
    assert [(a, b) for a, b, _ in got] == [(a, b) for a, b, _ in want]
    for (ix, iy, g), (_, _, w) in zip(got, want):
        assert g == w, f"frame ({ix},{iy}) differs from the golden"
    assert (idx["level"] == level).all() and not idx["pt"].any()
    assert not idx["sx"].any() and not idx["sy"].any()
    assert (idx["road"] + idx["bg"] + idx["name"] <= idx["len"]).all()

    # declined: exactly the golden's divided parents, reason 1
    parents = sorted({(iy, ix) for ix, iy, pt, _ in gold if pt != 0})
    assert [(int(r["iy"]), int(r["ix"])) for r in dec] == parents
    assert (dec["reason"] == 1).all()

    # declined merged content: decodes and round-trips through encode_columns
    for de, blob in blobs:
        for r in de:
            rec = blob[int(r["off"]):int(r["off"]) + int(r["len"])].tobytes()
            assert encode_columns(decode_columns(rec)) == rec

    # a split range gives the same frames and index
    mid = (win[2] + win[3] + 1) // 2
    idx2, dec2, _b, fbytes2 = _run(desc, sp, rows, [None, mid, None], tmp_path / "two.bin")
    assert idx2.tobytes() == idx.tobytes()
    assert dec2[["ix", "iy", "reason", "len"]].tobytes() == dec[["ix", "iy", "reason", "len"]].tobytes()
    assert fbytes2 == fbytes
    sp.close()


def test_e2_rejects_unrouted_rows(tmp_path: Path):
    """Rows whose target lies outside the call's row range (or out of
    order) are a caller error, never silently dropped."""
    g = COMMITTED / "l0_interior_borrowed"
    level, win, desc, sp, rows = _setup(g)
    assert len(rows) > 0
    with open(tmp_path / "f.bin", "wb") as fh:
        with pytest.raises(cenc.E2Error):
            cenc.e2(desc, sp, rows, None, int(rows["tiy"].min()), fh.fileno(), 0)
        if len(rows) > 1:
            with pytest.raises(cenc.E2Error):
                cenc.e2(desc, sp, rows[::-1].copy(), None, None, fh.fileno(), 0)
    sp.close()


def test_e2_rejects_foreign_column_table(tmp_path: Path):
    """The per-cell encoders are bound to `_cenc.c`'s COLS[] schema, so a
    descriptor whose column table differs is refused, not misread."""
    g = COMMITTED / "l0_sparse"
    level, win, desc, sp, rows = _setup(g)
    bad = bytearray(desc)
    cols_off = int.from_bytes(desc[152:156], "little")
    bad[cols_off] = 2 if bad[cols_off] != 2 else 4     # first column's element size
    with open(tmp_path / "f.bin", "wb") as fh, pytest.raises(cenc.E2Error, match="COLS"):
        cenc.e2(bytes(bad), sp, rows, None, None, fh.fileno(), 0)
    sp.close()
