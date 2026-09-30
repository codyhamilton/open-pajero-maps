"""3C-11 (H4): indexed assembly with no per-frame Python.

A small synthetic FrameTable that carries type-0 parcels and divided parents
(parcel types 1 and 2, several sub-frames each, several parents per block,
divided-only blocks, blocks shared with type-0 parcels, three levels) is
assembled through `build_alldata_kwi`. Two checks, both on the output alone
(Contract T: no Python oracle):

* the `ALLDATA.KWI` sha256 equals the one captured from the per-frame
  assembly this unit replaced (a port: every byte unchanged);
* the Python disc decoder (`parse_pdmdh`, `parse_parcel_mgmt_record`) reads
  every divided parent's sub-frames back at the offsets the frame table
  assigned, and every type-0 frame at its slot.
"""
from __future__ import annotations

import hashlib
import random
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from kiwiw import alldata_writer as aw
from kiwiw import cenc
from kiwiw import frame_table as ft
from kiwiw.grid import ReferenceGrid
from kiwiw.parcel_mgmt import parse_parcel_mgmt_record
from kiwiw.volume import getsector, parse_pdmdh_full

# sha256 of the ALLDATA.KWI this fixture produced under the per-frame Python
# assembly, captured before 3C-11 changed it (size 379040).
EXPECTED_SHA256 = "ac2f218dadae0abbcf4430b8561223728237404e060c6a4d93b7115ac28cc9f2"
EXPECTED_SIZE = 379040

pytestmark = pytest.mark.skipif(cenc.lib() is None, reason="C helpers unavailable")


def _fixture_rows():
    """{level: [(ix, iy, pt, sx, sy, bytes)]} in canonical (iy, ix) stream order."""
    rng = random.Random(311)

    def frame():
        return bytes(rng.randrange(256) for _ in range(rng.choice([1, 31, 32, 33, 64, 700, 2100])))

    out: dict[int, list] = {12: [(0, 0, 0, 0, 0, frame())]}
    # level 0: 32 x 64 cells per block, 8 x 4 blocks per blockset.
    l0, taken = [], set()

    def cell(xr, yr):
        while True:
            c = (rng.randrange(*xr), rng.randrange(*yr))
            if c not in taken:
                taken.add(c)
                return c

    for _ in range(40):                     # type-0 cells over ~6 blocks
        ix, iy = cell((0, 100), (0, 140))
        l0.append((ix, iy, 0, 0, 0, frame()))
    for _ in range(45):                     # divided parents, same span (shared blocks)
        ix, iy = cell((0, 100), (0, 140))
        pt = rng.choice([1, 2])
        side = 2 if pt == 1 else 4
        for k in range(side * side):
            if rng.random() < 0.7:
                l0.append((ix, iy, pt, k % side, k // side, frame()))
    for _ in range(6):                      # a divided-only block far away
        ix, iy = cell((300, 330), (300, 360))
        pt = rng.choice([1, 2])
        side = 2 if pt == 1 else 4
        for k in range(side * side):
            if rng.random() < 0.8:
                l0.append((ix, iy, pt, k % side, k // side, frame()))
    # keep at least one parent with a missing sub-frame and one complete parent
    l0.sort(key=lambda r: (r[1], r[0]))     # stable: sub-frame order within a parent kept
    out[0] = l0
    l2 = []
    for _ in range(5):
        ix, iy = cell((500, 540), (0, 40))
        l2.append((ix, iy, 0, 0, 0, frame()))
    ix, iy = cell((500, 540), (0, 40))
    for k in range(4):
        l2.append((ix, iy, 1, k % 2, k // 2, frame()))
    l2.sort(key=lambda r: (r[1], r[0]))
    out[2] = l2
    return out


def _table(rows, tmp_path, name):
    sp = ft.ChunkSpill(str(tmp_path))
    rec = np.zeros(len(rows), ft.FRAME_DTYPE)
    for i, (ix, iy, pt, sx, sy, fb) in enumerate(rows):
        rec[i] = (ix, iy, pt, sx, sy, 0, len(fb), sp.append(fb))
    sp.close()
    return ft.merge_tables([(sp.path, rec)])


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("idxasm")
    rows = _fixture_rows()
    levels = {lvl: aw.LevelBuild(level=lvl, table=_table(r, tmp, str(lvl)))
              for lvl, r in rows.items()}
    out = tmp / "ALLDATA.KWI"
    res = aw.build_alldata_kwi(levels, ReferenceGrid.load(), disk_title="T",
                               out_path=str(out), return_bytes=False)
    return rows, out, res


def test_sha_unchanged(built):
    _rows, out, res = built
    assert hashlib.sha256(out.read_bytes()).hexdigest() == res.sha256
    assert (res.sha256, res.size) == (EXPECTED_SHA256, EXPECTED_SIZE)


def test_decoder_reads_every_frame_back(built):
    rows, out, _res = built
    grid = ReferenceGrid.load()
    data = out.read_bytes()
    from kiwiw.volume import parse_mhr_table
    from kiwiw.disc import DATAVOL_SIZE, MHR_COUNT, MHR_SIZE
    from kiwiw.volume import parse_volume_header
    hdr = parse_volume_header(data[:DATAVOL_SIZE])
    ss, ls = hdr.sector_size, hdr.logical_sector_size
    mhr = parse_mhr_table(data[DATAVOL_SIZE:DATAVOL_SIZE + MHR_COUNT * MHR_SIZE])
    off = getsector(mhr[0].dsa, ss, ls)
    zdat = data[off:off + mhr[0].size * ls]
    pdmdh = parse_pdmdh_full(zdat)
    lmr_of = {lm.level: lm for lm in pdmdh.levels}
    bmt_of = {(pdmdh.blocksets[t.blockset_ordinal].level,
               pdmdh.blocksets[t.blockset_ordinal].blockset_index): t for t in pdmdh.bmt_tables}
    seen = 0
    NO = aw.NO_DATA_DSA

    def frame_at(e):
        o = getsector(e.dsa, ss, ls)
        return data[o:o + e.size * ls]

    for lvl, lrows in rows.items():
        d = aw._level_dims(grid, lvl)
        want0, wantd = {}, {}
        for ix, iy, pt, sx, sy, fb in lrows:
            bs, bl, lx, ly = aw._locate(ix, iy, d)
            slot = ly * d["npc_lng"] + lx
            if pt == 0:
                want0[(bs, bl, slot)] = fb
            else:
                wantd.setdefault((bs, bl, slot), {})[(pt, sx, sy)] = fb
        blocks = {k[:2] for k in list(want0) + list(wantd)}
        for bs, bl in blocks:
            ent = bmt_of[(lvl, bs)].entries[bl]
            assert ent.dsa != NO
            bo = getsector(ent.dsa, ss, ls)
            buf = data[bo:bo + ent.size * ls]
            root = parse_parcel_mgmt_record(buf, lmr_of[lvl])
            for slot, e in enumerate(root.entries):
                key = (bs, bl, slot)
                if key in want0:
                    assert e.subrecord is None
                    assert frame_at(e).rstrip(b"\0") == want0.pop(key).rstrip(b"\0")
                    assert len(frame_at(e)) == -(-len(frame_at(e)) // ls) * ls
                    seen += 1
                elif key in wantd:
                    sub = e.subrecord
                    assert sub is not None and e.size == 0
                    items = wantd.pop(key)
                    pt = next(iter(items))[0]
                    assert sub.parcel_type == pt
                    gn_lng = 1 + lmr_of[lvl].n_parcels_lng[pt]
                    for pos, se in enumerate(sub.entries):
                        k = (pt, pos % gn_lng, pos // gn_lng)
                        if k in items:
                            got = frame_at(se)
                            exp = items.pop(k)
                            assert got[:len(exp)] == exp
                            assert len(got) == -(-len(exp) // ls) * ls
                            seen += 1
                        else:
                            assert se.dsa == NO and se.size == 0
                    assert not items
                else:
                    assert e.dsa == NO and e.size == 0
        assert not want0 and not wantd
    assert seen == sum(len(r) for r in rows.values())
