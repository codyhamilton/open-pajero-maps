"""D1 frame decoders (plan 04, Phase 2, brief 2-01): `_d1.c` reproduces every
field of `parcel.decode_parcel` (and the road/background/name sub-decoders) on
the goldens' frames, field for field, floats bit-exact, and fails on exactly
the frames the Python decoder raises on.

Python is the oracle (one of the two permitted Python-oracle uses, DESIGN.md
Phase 2). The D1 columns are rebuilt into the model dataclasses here and both
sides are flattened by one dataclass-walking helper, so a field added to the
model without D1 support fails (it keeps its default on the D1 side).
"""
from __future__ import annotations

import dataclasses
import json
import random
import struct
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from kiwiw import cenc
from kiwiw.model import (BackgroundElement, BackgroundFrame, BackgroundShape,
                         BoundingBox, MapFrame, MapFrameHeader, MeshLocation,
                         NameFrame, NameList, NameRecord, Parcel, RoadFrame,
                         RoadLink, RoadNode)
from kiwiw.parcel import decode_parcel

pytestmark = pytest.mark.skipif(cenc._load_lib() is None, reason="no C compiler")

REPO = Path(__file__).resolve().parents[2]
COMMITTED = REPO / "parser" / "tests" / "fixtures" / "goldens"
LOCAL = REPO / "output" / "goldens-3C"


def _goldens() -> list[tuple[str, Path]]:
    out = [(p.parent.name, p.parent) for p in sorted(COMMITTED.glob("*/golden.json"))]
    f = COMMITTED / "local.json"
    if f.exists():
        for n in sorted(json.loads(f.read_text())["goldens"]):
            if (LOCAL / n / "frames.bin").exists():
                out.append((f"local-{n}", LOCAL / n))
    return out


def _frames(g: Path) -> tuple[bytes, list[tuple[int, int]]]:
    blob = (g / "frames.bin").read_bytes()
    rows = [r.split() for r in (g / "frames.tsv").read_text().splitlines()]
    return blob, [(int(r[6]), int(r[7])) for r in rows]


# --------------------------------------------------------------- flattening

def flatten(obj, path: str, out: dict) -> None:
    """Every leaf of a model object as `path -> (type name, value)`; floats as
    their IEEE-754 bit pattern, so equality is bit-exact."""
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        for f in dataclasses.fields(obj):
            flatten(getattr(obj, f.name), f"{path}.{f.name}", out)
    elif isinstance(obj, (list, tuple)):
        out[f"{path}.len"] = (type(obj).__name__, len(obj))
        for i, v in enumerate(obj):
            flatten(v, f"{path}[{i}]", out)
    elif isinstance(obj, dict):
        out[f"{path}.keys"] = ("dict", tuple(sorted(obj)))
        for k in sorted(obj):
            flatten(obj[k], f"{path}[{k}]", out)
    elif isinstance(obj, float):
        out[path] = ("float", struct.pack("<d", obj).hex())
    else:
        out[path] = (type(obj).__name__, obj)


def assert_same(want: Parcel, got: Parcel, what: str) -> None:
    a, b = {}, {}
    flatten(want, "parcel", a)
    flatten(got, "parcel", b)
    for k in a:
        assert k in b, f"{what}: field {k} missing from D1"
        assert a[k] == b[k], f"{what}: field {k}: python {a[k]!r} != D1 {b[k]!r}"
    extra = sorted(set(b) - set(a))
    assert not extra, f"{what}: D1 has fields python lacks: {extra[:5]}"


# ------------------------------------------------- D1 columns -> model objects

def build_parcel(cols, i: int, region: bytes, loc: MeshLocation) -> Parcel:
    """Rebuild frame `i`'s `Parcel` from the D1 columns (raw fields sliced
    from `region` by their (offset, length) pairs)."""
    T = cols.t
    fr = T["frame"][i]
    base = int(fr["off"])

    def raw(rel, n, at=0):
        a = base + at + int(rel)
        return bytes(region[a:a + int(n)])

    def sl(name, first, n):
        return T[name][int(first):int(first) + int(n)]

    mf = sl("mfde", fr["mfde_first"], fr["mfde_n"])
    parcel = Parcel(location=loc)
    parcel.frame = MapFrame(
        header=MapFrameHeader(
            raw_bytes=raw(0, 36), llpid_lat=float(fr["llpid_lat"]),
            llpid_lon=float(fr["llpid_lon"]), llcode_cx=int(fr["llcode_cx"]),
            llcode_cy=int(fr["llcode_cy"]), nregion=int(fr["nregion"])),
        region_list_raw=raw(fr["region_list_off"], fr["region_list_len"]),
        mfde_raw=[(int(m["raw_off"]), int(m["raw_size"])) for m in mf],
        ext_frame_raw={k: raw(m["ext_off"], m["ext_len"]) for k, m in enumerate(mf)
                       if m["has_ext"]},
        tail_raw=raw(fr["tail_off"], fr["tail_len"]),
        frame_size=int(fr["frame_size"]))

    if fr["has_bg"]:
        bb = int(fr["bg_base"])
        bg = BackgroundFrame(header_size_raw=int(fr["bg_header_size_raw"]),
                             frame_size=int(fr["bg_size"]))
        for e in sl("bgelem", fr["bgelem_first"], fr["bgelem_n"]):
            bg.elements.append(BackgroundElement(
                raw_offset_word=int(e["raw_offset_word"]),
                raw_size_word=int(e["raw_size_word"]), n_raw=int(e["n_raw"]),
                unit_table_raw=[(int(u["boff_word"]), int(u["val"]))
                                for u in sl("bgunit", e["unit_first"], e["unit_n"])]))
        for s in sl("bgshape", fr["bgshape_first"], fr["bgshape_n"]):
            code = int(s["type_code"])
            bg.shapes.append(BackgroundShape(
                shape_class=int(s["shape_class"]), type_code=code,
                type_label=cols.bg_labels[code], n_coords=int(s["n_coords"]),
                mult_const=int(s["mult_const"]), underground=bool(s["underground"]),
                pen_up=bool(s["pen_up"]),
                coords=[(float(c["lat"]), float(c["lon"]))
                        for c in sl("bgcoord", s["coord_first"], s["coord_n"])],
                raw_offset=int(s["raw_off"]), raw_bytes=raw(s["raw_off"], s["raw_len"], bb)))
        parcel.background = bg

    if fr["has_road"]:
        rb = int(fr["road_base"])
        rd = RoadFrame(
            n_intersections=int(fr["n_intersections"]),
            n_display_classes=int(fr["n_display_classes"]),
            n_additional_data=int(fr["n_additional_data"]),
            route_planning_level=int(fr["route_planning_level"]),
            frame_size=int(fr["road_size"]), header_size_raw=int(fr["road_header_size_raw"]),
            lvl_field_raw=int(fr["lvl_field_raw"]))
        for dc, d in enumerate(sl("dclass", fr["dclass_first"], fr["dclass_n"])):
            rd.display_class_table.append((int(d["raw_offset_word"]), int(d["raw_count_word"])))
            if d["has_flags"]:
                rd.display_class_flags[dc] = raw(d["flags_off"], d["flags_len"], rb)
        for k in sl("link", fr["link_first"], fr["link_n"]):
            rd.links.append(RoadLink(
                display_class=int(k["display_class"]), road_type=int(k["road_type"]),
                altitude_flag=bool(k["altitude_flag"]),
                route_type_guidance_flag=bool(k["route_type_guidance_flag"]),
                pseudo3d_updown=int(k["pseudo3d_updown"]),
                route_planning_tag=bool(k["route_planning_tag"]),
                link_id_flag=bool(k["link_id_flag"]),
                selected_link_flag=bool(k["selected_link_flag"]),
                toll_flag=bool(k["toll_flag"]), route_number_flag=bool(k["route_number_flag"]),
                infra_link_flag=bool(k["infra_link_flag"]),
                link_id_number_flag=bool(k["link_id_number_flag"]),
                n_nodes=int(k["n_nodes"]),
                nodes=[RoadNode(x=int(n["x"]), y=int(n["y"]), lat=float(n["lat"]),
                                lon=float(n["lon"]), oneway=int(n["oneway"]),
                                planned=int(n["planned"]), tunnel=bool(n["tunnel"]),
                                bridge=bool(n["bridge"]))
                       for n in sl("node", k["node_first"], k["n_nodes"])],
                points=[(float(p["lat"]), float(p["lon"]))
                        for p in sl("point", k["point_first"], k["n_points"])],
                raw_offset=int(k["raw_off"]), raw_bytes=raw(k["raw_off"], k["raw_len"], rb)))
        for a in sl("addl", fr["addl_first"], fr["addl_n"]):
            rd.additional_data_table.append((int(a["raw_offset_word"]), int(a["raw_size_word"])))
        for j, a in enumerate(sl("addl", fr["addl_first"], fr["addl_n"])):
            if a["has_raw"]:
                rd.additional_data_raw[j] = raw(a["data_off"], a["data_len"], rb)
        parcel.road = rd

    if fr["has_name"]:
        nb = int(fr["name_base"])
        nm = NameFrame(header_size_raw=int(fr["name_header_size_raw"]),
                       frame_size=int(fr["name_size"]))
        for nl in sl("nlist", fr["nlist_first"], fr["nlist_n"]):
            nm.lists.append(NameList(raw_offset_word=int(nl["raw_offset_word"]),
                                     raw_count_word=int(nl["raw_count_word"])))
        for r in sl("nrec", fr["nrec_first"], fr["nrec_n"]):
            st, code = int(r["string_type"]), int(r["type_code"])
            nm.records.append(NameRecord(
                string_type=st, type_code=code, type_label=cols.name_labels[(st, code)],
                priority=int(r["priority"]), vertical=bool(r["vertical"]),
                display_scale_flag=int(r["display_scale_flag"]),
                text=raw(r["text_off"], r["text_len"], nb).decode("latin-1"),
                lat=float(r["lat"]) if r["has_latlon"] else None,
                lon=float(r["lon"]) if r["has_latlon"] else None,
                angle_deg=int(r["angle_deg"]) if r["has_angle"] else None,
                angle_flags=int(r["angle_flags"]),
                raw_offset=int(r["raw_off"]), raw_bytes=raw(r["raw_off"], r["raw_len"], nb)))
        parcel.name = nm
    return parcel


# ------------------------------------------------------------------ fixtures

def _variants(blob: bytes, spans, seed: str):
    """(frame bytes, bounds, nbm, nem) cases: every golden frame under a few
    pseudo-random bounds/ranges, plus truncated and byte-corrupted copies."""
    rng = random.Random(seed)
    cases = []

    def bounds(coord_range):
        lat = rng.uniform(-44.0, -10.0)
        lon = rng.uniform(112.0, 154.0)
        dl = rng.uniform(0.001, 0.4)
        return BoundingBox(lat, lat + dl, lon, lon + dl * rng.uniform(0.5, 2.0),
                           coord_range=coord_range)

    for off, n in spans:
        data = blob[off:off + n]
        for rng_v, nbm, nem in ((4096, 3, 0), (32768, 3, 9), (8192, 3, 9)):
            cases.append((data, bounds(rng_v), nbm, nem))
        cases.append((data, bounds(None), 3, 0))                  # no coord_range
        for cut in sorted({0, 1, 9, 35, 36, 37, 60, 100, n // 3, n // 2, n - 1}):
            if 0 <= cut < n:
                cases.append((data[:cut], bounds(4096), 3, 0))
        for _ in range(24):                                       # corrupted copies
            b = bytearray(data)
            for _k in range(rng.choice((1, 1, 2, 4))):
                pos = rng.randrange(min(len(b), 400)) if rng.random() < 0.7 \
                    else rng.randrange(len(b))
                b[pos] = rng.randrange(256)
            cases.append((bytes(b), bounds(4096), 3, 0))
    return cases


def _run(cases):
    """Concatenate `cases` into one region, run D1 once, and compare each."""
    region = b"".join(c[0] for c in cases)
    leaf = np.zeros(len(cases), cenc.D1_LEAF_DTYPE)
    pos = 0
    for i, (data, bb, nbm, nem) in enumerate(cases):
        leaf[i] = (pos, bb.lat_lo, bb.lat_hi, bb.lon_lo, bb.lon_hi, len(data),
                   bb.coord_range or 0, nbm, nem)
        pos += len(data)
    return region, cenc.d1_frames(np.frombuffer(region, np.uint8), leaf)


@pytest.mark.parametrize("name,gdir", _goldens() or [pytest.param("none", None, marks=pytest.mark.skip)],
                         ids=lambda v: v if isinstance(v, str) else None)
def test_d1_equals_python(name, gdir):
    blob, spans = _frames(gdir)
    cases = _variants(blob, spans, name)
    region, cols = _run(cases)
    ok = failed = 0
    for i, (data, bb, nbm, nem) in enumerate(cases):
        loc = MeshLocation(level=0, parcel_type=0, blockset_index=0, block_index=0,
                           parcel_index=0, bounds=bb, sector_addr=0, size_logical_sectors=0)
        try:
            want = decode_parcel(loc, data, n_basic_map=nbm, n_ext_map=nem)
        except Exception:  # noqa: BLE001 -- any raise is "leaf did not decode"
            want = None
        status = int(cols.t["frame"][i]["status"])
        if want is None:
            failed += 1
            assert status != 0, f"{name} case {i}: python raised, D1 decoded"
            continue
        ok += 1
        assert status == 0, f"{name} case {i}: D1 failed (status {status}), python decoded"
        assert_same(want, build_parcel(cols, i, region, loc), f"{name} case {i}")
    assert ok >= len(spans) * 3          # the real frames decode under every variant
    assert failed >= len(spans)          # and the error path was exercised


def test_d1_one_call_per_range():
    name, gdir = _goldens()[0]
    blob, spans = _frames(gdir)
    cases = _variants(blob, spans, "stats")[:30]
    # Explicit large cap_hint: EO-recaptured goldens (3-14) can need more
    # vertex/walk capacity than the default hint, which would grow-retry and
    # inflate the call counter. Contract under test is still one call/range
    # when the hint is genuinely big enough.
    region = b"".join(c[0] for c in cases)
    leaf = np.zeros(len(cases), cenc.D1_LEAF_DTYPE)
    pos = 0
    for i, (data, bb, nbm, nem) in enumerate(cases):
        leaf[i] = (pos, bb.lat_lo, bb.lat_hi, bb.lon_lo, bb.lon_hi, len(data),
                   bb.coord_range or 0, nbm, nem)
        pos += len(data)
    before = cenc.d1_stats()
    cenc.d1_frames(np.frombuffer(region, np.uint8), leaf, cap_hint=1 << 21)
    after = cenc.d1_stats()
    assert after["ranges"] - before["ranges"] == 1
    assert after["calls"] - before["calls"] == 1           # the hint was big enough
    assert after["frames"] - before["frames"] == len(cases)
    assert after["rows"] > before["rows"]
    assert after["c_s"] > before["c_s"]


def test_d1_grow_retry_gives_same_columns():
    name, gdir = _goldens()[0]
    blob, spans = _frames(gdir)
    cases = _variants(blob, spans, "grow")[:12]
    region = b"".join(c[0] for c in cases)
    leaf = np.zeros(len(cases), cenc.D1_LEAF_DTYPE)
    pos = 0
    for i, (data, bb, nbm, nem) in enumerate(cases):
        leaf[i] = (pos, bb.lat_lo, bb.lat_hi, bb.lon_lo, bb.lon_hi, len(data),
                   bb.coord_range or 0, nbm, nem)
        pos += len(data)
    reg = np.frombuffer(region, np.uint8)
    big = cenc.d1_frames(reg, leaf)
    c0 = cenc.d1_stats()["calls"]
    small = cenc.d1_frames(reg, leaf, cap_hint=1)
    assert cenc.d1_stats()["calls"] - c0 >= 2               # grew and repeated
    for t in big.t:
        assert big.t[t].tobytes() == small.t[t].tobytes(), t   # byte-identical (padding too)


def test_d1_bad_leaf_row_is_an_error():
    leaf = np.zeros(1, cenc.D1_LEAF_DTYPE)
    leaf[0]["off"], leaf[0]["len"] = 10, 100
    with pytest.raises(cenc.D1Error):
        cenc.d1_frames(np.zeros(50, np.uint8), leaf)
