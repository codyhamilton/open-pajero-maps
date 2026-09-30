"""E2, the Stage 1 kernel (plan 03, 3C-07; DESIGN.md Contract B, "E2").

Layer (a) at the boundary, against the Contract T (c) goldens: each golden's
fixture spool goes through E1 (whole level, the golden's window as the
receiver window), E1's rows are routed to their targets with one stable
numpy sort, and E2 encodes the window. No build logic lives here and
nothing is compared with a Python re-implementation: the oracle is the
golden's frame bytes (`frames.bin` / `frames.tsv`).

For every golden (3C-09: E2 divides, retiles, trims and halos itself):
  * every frame E2 emits -- undivided (`pt == 0`) and divided sub-frames
    (`pt`, `sx`, `sy`) alike -- is byte-equal to the golden's frame, in the
    golden's order;
  * E2's declined list is empty;
  * E2's trim and name-halo counters equal the golden's manifest
    (`trimmed_items`, `halo_names`);
  * a range split into two calls gives the same frames and index as one.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from kiwiw import cenc, descriptor

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
        ix, iy, pt, sx, sy = (int(v) for v in r[1:6])
        off, ln = int(r[6]), int(r[7])
        out.append((ix, iy, pt, sx, sy, blob[off:off + ln]))
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
        threshold=build_alldata._load_level_thresholds()[level], name_halo=(level == 0),
        kind_limits={"road": budgets.get("road"), "bg": budgets.get("background"),
                     "name": budgets.get("name")})
    sp = cenc.E1Spool(g / "spool", level)
    rows, _c = cenc.e1(desc, sp, None, None)
    # routing: one stable sort by target (iy, ix); E1's source order is kept
    rows = rows[np.lexsort((rows["tix"], rows["tiy"]))]
    return level, win, desc, sp, rows


def _run(desc, sp, rows, bounds, path: Path):
    """E2 over consecutive target-row ranges `bounds` (edges; None = open),
    each range's frames appended to `path`. Returns (index, declined,
    counters summed over the ranges, frame bytes)."""
    idx, dec, cnts = [], [], []
    with open(path, "wb") as fh:
        off = 0
        for lo, hi in zip(bounds[:-1], bounds[1:]):
            a = 0 if lo is None else int(np.searchsorted(rows["tiy"], lo))
            b = len(rows) if hi is None else int(np.searchsorted(rows["tiy"], hi))
            res = cenc.e2(desc, sp, rows[a:b], lo, hi, fh.fileno(), off)
            ix, de, cnt = res[0], res[1], res[-1]
            assert ix.dtype == descriptor.E2_INDEX_DTYPE
            assert de.dtype == descriptor.E2_DECLINED_DTYPE
            assert cnt["frame_bytes"] == int(ix["len"].sum())
            off += cnt["frame_bytes"]
            idx.append(ix); dec.append(de); cnts.append(cnt)
    return np.concatenate(idx), np.concatenate(dec), cnts, path.read_bytes()


def _trim_manifest(level, cnts):
    """The manifest's `trimmed_items` / `halo_names` blocks from E2's
    counters, assembled as `build_alldata.run` does."""
    st: dict = {}
    for c in cnts:
        build_alldata._merge_stats(st, build_alldata._e2_trim_stats(c))
    return build_alldata._trim_manifest_blocks(level, st)


@pytest.mark.parametrize("golden", _cases())
def test_e2_matches_golden(golden: Path, tmp_path: Path):
    if not golden.exists():
        pytest.skip(f"local golden {golden.name} absent (see docs/provenance.md)")
    level, win, desc, sp, rows = _setup(golden)
    gold = _golden_frames(golden)
    idx, dec, cnts, fbytes = _run(desc, sp, rows, [None, None], tmp_path / "one.bin")

    # frames: every golden frame (undivided and divided), in the golden's order
    got = [(int(r["ix"]), int(r["iy"]), int(r["pt"]), int(r["sx"]), int(r["sy"]),
            fbytes[int(r["off"]):int(r["off"]) + int(r["len"])]) for r in idx]
    assert [g[:5] for g in got] == [w[:5] for w in gold]
    for g, w in zip(got, gold):
        assert g[5] == w[5], f"frame {g[:5]} differs from the golden"
    assert (idx["level"] == level).all()
    assert (idx["road"] + idx["bg"] + idx["name"] <= idx["len"]).all()

    # declined: none -- E2 alone produces every frame
    assert len(dec) == 0, [(int(r["ix"]), int(r["iy"]), int(r["reason"])) for r in dec]

    # trim / halo counters equal the golden's manifest
    meta = json.loads((golden / "golden.json").read_text())["manifest"]
    trimmed, halo = _trim_manifest(level, cnts)
    assert trimmed == meta.get("trimmed_items", {})
    assert halo == meta.get("halo_names", {})

    # a split range gives the same frames and index
    mid = (win[2] + win[3] + 1) // 2
    idx2, dec2, _c, fbytes2 = _run(desc, sp, rows, [None, mid, None], tmp_path / "two.bin")
    assert idx2.tobytes() == idx.tobytes()
    assert len(dec2) == 0
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


def test_c_column_names_match_spool():
    """E2 addresses spool columns by its own enum and checks each name
    against `_cenc.c`'s table at descriptor parse; that table is `spool._COLUMNS`."""
    from kiwiw import spool
    lib = cenc._load_lib()
    assert lib.kw_ncols() == len(spool._COLUMNS)
    for i, (name, _dt, _key) in enumerate(spool._COLUMNS):
        assert lib.kw_col_name(i) == name.encode(), (i, name)
    assert lib.kw_col_name(len(spool._COLUMNS)) is None
