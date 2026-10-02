"""3-11: `enc_bg` splits a class whose record count exceeds the 12-bit unit
count (4095) into several same-class units of at most 4095 records.

Synthetic cells are built through the real boundary (fixture spool -> E1 ->
E2, `e2_fixture.e2_frames`) and read back with the existing decoders
(`boundary.decode_frame`, the Python reader D1 mirrors) and with C D1
(`kiwiw.cenc.d1_frames`).  Nothing here computes an expected frame byte; the
only byte-exact assertion is against a fixture captured from HEAD (the
`<4096` path must not move).
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent / "fixtures" / "harness"))

import boundary  # noqa: E402
import e2_fixture  # noqa: E402
from kiwiw import cenc  # noqa: E402
from kiwiw.bitutils import extract  # noqa: E402
from kiwiw.model import BackgroundShape  # noqa: E402

LEVEL = 0
IX, IY = 1780, 814
UNDER_4096_FIXTURE = (Path(__file__).resolve().parent / "fixtures" / "bg_split"
                      / "under_4096_100.bin")


def _shapes(n: int) -> list[BackgroundShape]:
    b = e2_fixture.cell_bounds(LEVEL, IX, IY)
    clat = (b.lat_lo + b.lat_hi) / 2
    clon = (b.lon_lo + b.lon_hi) / 2
    dlat = (b.lat_hi - b.lat_lo) / 64
    dlon = (b.lon_hi - b.lon_lo) / 64
    out = []
    for i in range(n):
        ox = ((i % 32) - 16) * dlon / 8
        oy = ((i // 32) % 32 - 16) * dlat / 8
        pts = [(clat + oy, clon + ox),
               (clat + oy + dlat, clon + ox),
               (clat + oy, clon + ox + dlon)]
        out.append(BackgroundShape(shape_class=2, type_code=288, type_label="",
                                   n_coords=len(pts), mult_const=1,
                                   underground=False, pen_up=False, coords=pts))
    return out


def _frame(n: int, tmp_path: Path) -> tuple[bytes, object]:
    frames = e2_fixture.e2_frames(tmp_path, LEVEL, {(IX, IY): {"backgrounds": _shapes(n)}})
    return frames[(IX, IY)], e2_fixture.cell_bounds(LEVEL, IX, IY)


def _units(parcel) -> list[tuple[int, int]]:
    """(class, declared count) of every unit in every background element."""
    return [(extract(int(v), 14, 15), extract(int(v), 0, 11))
            for el in parcel.background.elements for (_boff, v) in el.unit_table_raw]


def test_6415_records_split_into_two_units(tmp_path):
    fb, bounds = _frame(6415, tmp_path)
    parcel = boundary.decode_frame(fb, bounds)
    assert _units(parcel) == [(2, 4095), (2, 2320)]
    assert len(parcel.background.shapes) == 6415
    assert len(fb) <= 131070


def test_exact_4095_stays_one_unit_and_4096_splits(tmp_path):
    fb5, b5 = _frame(4095, tmp_path)
    p5 = boundary.decode_frame(fb5, b5)
    assert _units(p5) == [(2, 4095)]
    assert len(p5.background.shapes) == 4095

    fb6, b6 = _frame(4096, tmp_path)
    p6 = boundary.decode_frame(fb6, b6)
    assert _units(p6) == [(2, 4095), (2, 1)]
    assert len(p6.background.shapes) == 4096


def test_d1_decodes_all_6415_records(tmp_path):
    fb, bounds = _frame(6415, tmp_path)
    leaf = np.zeros(1, cenc.D1_LEAF_DTYPE)
    leaf[0] = (0, bounds.lat_lo, bounds.lat_hi, bounds.lon_lo, bounds.lon_hi,
               len(fb), bounds.coord_range or 0, 3, 9)
    cols = cenc.d1_frames(np.frombuffer(fb, np.uint8), leaf)
    assert int(cols.t["frame"][0]["status"]) == 0
    assert len(cols.t["bgshape"]) == 6415
    assert len(cols.t["bgcoord"]) == sum(
        int(s["n_coords"]) + 1 for s in cols.t["bgshape"])
    units = [(int(v) >> 14, int(v) & 0xFFF) for v in cols.t["bgunit"]["val"]]
    assert units == [(2, 4095), (2, 2320)]


def test_under_4096_is_byte_identical_to_head(tmp_path):
    if not UNDER_4096_FIXTURE.exists():
        pytest.skip(f"missing {UNDER_4096_FIXTURE}; see docs/provenance.md")
    fb, _bounds = _frame(100, tmp_path)
    assert fb == UNDER_4096_FIXTURE.read_bytes()
