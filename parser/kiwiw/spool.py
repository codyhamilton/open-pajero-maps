"""Binary columnar per-level spool for streamed parcel content (plan 02, phase 2).

Replaces the pickle spool (`spool_legacy.py`). Same interface: `SpoolWriter.add`
during the single extraction pass, then `SpoolReader.iter_level` / `stats` /
`levels`, plus range access (`iter_cells`) and raw columns (`cell_columns`)
for the vectorized encoders.

On-disk layout (all little-endian, fixed-width, no pickle; see
docs/plans/02-build-performance/DESIGN.md section 3)::

    <spool_dir>/level_<L>.data  -- one cell record per (ix, iy), ascending (iy, ix)
    <spool_dir>/level_<L>.idx   -- b"KWSPIDX1", then u64 ncells, u64 totals
                                   (parcels, roads, backgrounds, names), then
                                   arrays ix:i32[n], iy:i32[n], offset:u64[n],
                                   length:u64[n]

A cell record is a 9 x u64 count header (`_COUNT_KEYS`) followed by every
column in `_COLUMNS` order, each zero-padded to 8 bytes. Fields never read
downstream (`raw_offset`, `raw_bytes`) are not stored.

During extraction the same key can be flushed several times; the writer keeps
those partial records in `level_<L>.seg` and `close()` merges them (column
concatenation) into the final sorted `.data`, then removes the `.seg`.
"""
from __future__ import annotations

import mmap
import os
import struct
from collections import defaultdict
from pathlib import Path
from typing import Iterator, Optional

import numpy as np

from .model import BackgroundShape, NameRecord, RoadLink, RoadNode

IDX_MAGIC = b"KWSPIDX1"
_CONTENT_KEYS = ("roads", "backgrounds", "names")

_COUNT_KEYS = ("n_roads", "n_nodes", "n_points", "n_bgs", "n_coords", "n_names",
               "blob_bg_label", "blob_name_label", "blob_name_text")

_I32, _I64, _U16, _U8, _F64 = "<i4", "<i8", "<u2", "u1", "<f8"

# (column, dtype, count key)
_COLUMNS = (
    ("r_display_class", _I32, "n_roads"), ("r_road_type", _I32, "n_roads"),
    ("r_pseudo3d", _I32, "n_roads"), ("r_n_nodes", _I32, "n_roads"),
    ("r_link_id", _I32, "n_roads"), ("r_ordinal", _I32, "n_roads"),
    ("r_way_id", _I64, "n_roads"), ("r_flags", _U16, "n_roads"),
    ("r_nstored", _I32, "n_roads"), ("r_npts", _I32, "n_roads"),
    ("n_x", _I32, "n_nodes"), ("n_y", _I32, "n_nodes"),
    ("n_lat", _F64, "n_nodes"), ("n_lon", _F64, "n_nodes"),
    ("n_oneway", _I32, "n_nodes"), ("n_planned", _I32, "n_nodes"),
    ("n_flags", _U8, "n_nodes"),
    ("p_lat", _F64, "n_points"), ("p_lon", _F64, "n_points"),
    ("b_class", _I32, "n_bgs"), ("b_type", _I32, "n_bgs"),
    ("b_ncoords", _I32, "n_bgs"), ("b_mult", _I32, "n_bgs"),
    ("b_flags", _U8, "n_bgs"), ("b_nstored", _I32, "n_bgs"),
    ("b_label_len", _I32, "n_bgs"),
    ("c_lat", _F64, "n_coords"), ("c_lon", _F64, "n_coords"),
    ("s_type", _I32, "n_names"), ("s_code", _I32, "n_names"),
    ("s_prio", _I32, "n_names"), ("s_dsf", _I32, "n_names"),
    ("s_angflags", _I32, "n_names"), ("s_vertical", _U8, "n_names"),
    ("s_present", _U8, "n_names"), ("s_label_len", _I32, "n_names"),
    ("s_text_len", _I32, "n_names"),
    ("s_lat", _F64, "n_names"), ("s_lon", _F64, "n_names"),
    ("s_angle", _F64, "n_names"),
    ("blob_bg_label", _U8, "blob_bg_label"),
    ("blob_name_label", _U8, "blob_name_label"),
    ("blob_name_text", _U8, "blob_name_text"),
)
_HDR = struct.Struct("<9Q")
_NO_WAY = -(1 << 63)
_ROAD_FLAGS = ("altitude_flag", "route_type_guidance_flag", "route_planning_tag",
               "link_id_flag", "selected_link_flag", "toll_flag", "route_number_flag",
               "infra_link_flag", "link_id_number_flag")


def _empty_content() -> dict:
    return {"roads": [], "backgrounds": [], "names": []}


def _data_path(spool_dir: Path, level: int) -> Path:
    return spool_dir / f"level_{level}.data"


def _idx_path(spool_dir: Path, level: int) -> Path:
    return spool_dir / f"level_{level}.idx"


def _seg_path(spool_dir: Path, level: int) -> Path:
    return spool_dir / f"level_{level}.seg"


def _pad8(n: int) -> int:
    return (8 - n % 8) % 8


# ---------------------------------------------------------------------------
# content objects <-> columns
# ---------------------------------------------------------------------------

def content_to_columns(content: dict) -> dict[str, np.ndarray]:
    roads = content.get("roads") or []
    bgs = content.get("backgrounds") or []
    names = content.get("names") or []
    nodes = [n for r in roads for n in r.nodes]
    pts = [p for r in roads for p in r.points]
    coords = [c for b in bgs for c in b.coords]
    bg_labels = [b.type_label.encode("utf-8") for b in bgs]
    nm_labels = [s.type_label.encode("utf-8") for s in names]
    nm_texts = [s.text.encode("utf-8") for s in names]

    def col(vals, dt):
        return np.array(vals, dtype=dt)

    def flags(r):
        f = 0
        for i, name in enumerate(_ROAD_FLAGS):
            if getattr(r, name):
                f |= 1 << i
        return f

    c: dict[str, np.ndarray] = {}
    c["r_display_class"] = col([r.display_class for r in roads], _I32)
    c["r_road_type"] = col([r.road_type for r in roads], _I32)
    c["r_pseudo3d"] = col([r.pseudo3d_updown for r in roads], _I32)
    c["r_n_nodes"] = col([r.n_nodes for r in roads], _I32)
    c["r_link_id"] = col([r.link_id for r in roads], _I32)
    c["r_ordinal"] = col([r.ordinal for r in roads], _I32)
    c["r_way_id"] = col([_NO_WAY if r.osm_way_id is None else r.osm_way_id
                         for r in roads], _I64)
    c["r_flags"] = col([flags(r) for r in roads], _U16)
    c["r_nstored"] = col([len(r.nodes) for r in roads], _I32)
    c["r_npts"] = col([len(r.points) for r in roads], _I32)
    c["n_x"] = col([n.x for n in nodes], _I32)
    c["n_y"] = col([n.y for n in nodes], _I32)
    c["n_lat"] = col([n.lat for n in nodes], _F64)
    c["n_lon"] = col([n.lon for n in nodes], _F64)
    c["n_oneway"] = col([n.oneway for n in nodes], _I32)
    c["n_planned"] = col([n.planned for n in nodes], _I32)
    c["n_flags"] = col([int(bool(n.tunnel)) | (int(bool(n.bridge)) << 1)
                        for n in nodes], _U8)
    c["p_lat"] = col([p[0] for p in pts], _F64)
    c["p_lon"] = col([p[1] for p in pts], _F64)
    c["b_class"] = col([b.shape_class for b in bgs], _I32)
    c["b_type"] = col([b.type_code for b in bgs], _I32)
    c["b_ncoords"] = col([b.n_coords for b in bgs], _I32)
    c["b_mult"] = col([b.mult_const for b in bgs], _I32)
    c["b_flags"] = col([int(bool(b.underground)) | (int(bool(b.pen_up)) << 1)
                        for b in bgs], _U8)
    c["b_nstored"] = col([len(b.coords) for b in bgs], _I32)
    c["b_label_len"] = col([len(x) for x in bg_labels], _I32)
    c["c_lat"] = col([x[0] for x in coords], _F64)
    c["c_lon"] = col([x[1] for x in coords], _F64)
    c["s_type"] = col([s.string_type for s in names], _I32)
    c["s_code"] = col([s.type_code for s in names], _I32)
    c["s_prio"] = col([s.priority for s in names], _I32)
    c["s_dsf"] = col([s.display_scale_flag for s in names], _I32)
    c["s_angflags"] = col([s.angle_flags for s in names], _I32)
    c["s_vertical"] = col([int(bool(s.vertical)) for s in names], _U8)
    c["s_present"] = col([(s.lat is not None) | ((s.lon is not None) << 1)
                          | ((s.angle_deg is not None) << 2) for s in names], _U8)
    c["s_label_len"] = col([len(x) for x in nm_labels], _I32)
    c["s_text_len"] = col([len(x) for x in nm_texts], _I32)
    c["s_lat"] = col([0.0 if s.lat is None else s.lat for s in names], _F64)
    c["s_lon"] = col([0.0 if s.lon is None else s.lon for s in names], _F64)
    c["s_angle"] = col([0.0 if s.angle_deg is None else s.angle_deg for s in names], _F64)
    c["blob_bg_label"] = np.frombuffer(b"".join(bg_labels), dtype=_U8)
    c["blob_name_label"] = np.frombuffer(b"".join(nm_labels), dtype=_U8)
    c["blob_name_text"] = np.frombuffer(b"".join(nm_texts), dtype=_U8)
    return c


def _counts(cols: dict[str, np.ndarray]) -> tuple[int, ...]:
    return (len(cols["r_display_class"]), len(cols["n_x"]), len(cols["p_lat"]),
            len(cols["b_class"]), len(cols["c_lat"]), len(cols["s_type"]),
            len(cols["blob_bg_label"]), len(cols["blob_name_label"]),
            len(cols["blob_name_text"]))


def encode_columns(cols: dict[str, np.ndarray]) -> bytes:
    parts = [_HDR.pack(*_counts(cols))]
    for name, dt, _key in _COLUMNS:
        b = np.ascontiguousarray(cols[name], dtype=dt).tobytes()
        parts.append(b)
        parts.append(bytes(_pad8(len(b))))
    return b"".join(parts)


def decode_columns(buf, offset: int = 0) -> dict[str, np.ndarray]:
    """Zero-copy column views of the cell record at `offset` of `buf`."""
    counts = dict(zip(_COUNT_KEYS, _HDR.unpack_from(buf, offset)))
    pos = offset + _HDR.size
    cols: dict[str, np.ndarray] = {}
    for name, dt, key in _COLUMNS:
        n = counts[key]
        arr = np.frombuffer(buf, dtype=dt, count=n, offset=pos)
        cols[name] = arr
        pos += arr.nbytes + _pad8(arr.nbytes)
    return cols


def merge_columns(parts: list[dict[str, np.ndarray]]) -> dict[str, np.ndarray]:
    if len(parts) == 1:
        return parts[0]
    return {name: np.concatenate([p[name] for p in parts]) for name, _dt, _k in _COLUMNS}


def columns_to_content(cols: dict[str, np.ndarray]) -> dict:
    """Rebuild the `{"roads","backgrounds","names"}` object content."""
    L = {k: v.tolist() for k, v in cols.items() if not k.startswith("blob_")}
    roads = []
    ni = pi = 0
    for i in range(len(L["r_display_class"])):
        ns, npts = L["r_nstored"][i], L["r_npts"][i]
        nodes = [RoadNode(x=L["n_x"][j], y=L["n_y"][j], lat=L["n_lat"][j],
                          lon=L["n_lon"][j], oneway=L["n_oneway"][j],
                          planned=L["n_planned"][j],
                          tunnel=bool(L["n_flags"][j] & 1), bridge=bool(L["n_flags"][j] & 2))
                 for j in range(ni, ni + ns)]
        points = list(zip(L["p_lat"][pi:pi + npts], L["p_lon"][pi:pi + npts]))
        ni += ns
        pi += npts
        f = L["r_flags"][i]
        way = L["r_way_id"][i]
        roads.append(RoadLink(
            display_class=L["r_display_class"][i], road_type=L["r_road_type"][i],
            altitude_flag=bool(f & 1), route_type_guidance_flag=bool(f & 2),
            pseudo3d_updown=L["r_pseudo3d"][i], route_planning_tag=bool(f & 4),
            link_id_flag=bool(f & 8), selected_link_flag=bool(f & 16),
            toll_flag=bool(f & 32), route_number_flag=bool(f & 64),
            infra_link_flag=bool(f & 128), link_id_number_flag=bool(f & 256),
            n_nodes=L["r_n_nodes"][i], nodes=nodes, points=points,
            link_id=L["r_link_id"][i], osm_way_id=None if way == _NO_WAY else way,
            ordinal=L["r_ordinal"][i]))
    bg_blob = cols["blob_bg_label"].tobytes()
    bgs = []
    ci = bo = 0
    for i in range(len(L["b_class"])):
        n, ll = L["b_nstored"][i], L["b_label_len"][i]
        fl = L["b_flags"][i]
        bgs.append(BackgroundShape(
            shape_class=L["b_class"][i], type_code=L["b_type"][i],
            type_label=bg_blob[bo:bo + ll].decode("utf-8"), n_coords=L["b_ncoords"][i],
            mult_const=L["b_mult"][i], underground=bool(fl & 1), pen_up=bool(fl & 2),
            coords=list(zip(L["c_lat"][ci:ci + n], L["c_lon"][ci:ci + n]))))
        ci += n
        bo += ll
    lab_blob = cols["blob_name_label"].tobytes()
    txt_blob = cols["blob_name_text"].tobytes()
    names = []
    lo = to = 0
    for i in range(len(L["s_type"])):
        ll, tl = L["s_label_len"][i], L["s_text_len"][i]
        pr = L["s_present"][i]
        names.append(NameRecord(
            string_type=L["s_type"][i], type_code=L["s_code"][i],
            type_label=lab_blob[lo:lo + ll].decode("utf-8"), priority=L["s_prio"][i],
            vertical=bool(L["s_vertical"][i]), display_scale_flag=L["s_dsf"][i],
            text=txt_blob[to:to + tl].decode("utf-8"),
            lat=L["s_lat"][i] if pr & 1 else None, lon=L["s_lon"][i] if pr & 2 else None,
            angle_deg=L["s_angle"][i] if pr & 4 else None,
            angle_flags=L["s_angflags"][i]))
        lo += ll
        to += tl
    return {"roads": roads, "backgrounds": bgs, "names": names}


# ---------------------------------------------------------------------------
# writer / reader
# ---------------------------------------------------------------------------

_SEG_HDR = struct.Struct("<iiQ")


class SpoolWriter:
    """Single-writer-process append-only spooler, bucketed per level.

    Call `add(level, ix, iy, roads=..., backgrounds=..., names=...)` as
    content is produced; buffers are flushed to a per-level segment file once
    a level's buffered item count reaches `flush_threshold`, and finally by
    `close()`, which merges segments into the sorted `.data` + `.idx`.
    """

    def __init__(self, spool_dir, flush_threshold: int = 200_000):
        self.spool_dir = Path(spool_dir)
        self.spool_dir.mkdir(parents=True, exist_ok=True)
        self.flush_threshold = flush_threshold
        self._buffers: dict[int, dict[tuple[int, int], dict]] = defaultdict(dict)
        self._buffer_counts: dict[int, int] = defaultdict(int)
        self._files: dict[int, "object"] = {}
        self._pos: dict[int, int] = defaultdict(int)
        self._segs: dict[int, dict[tuple[int, int], list[tuple[int, int]]]] = \
            defaultdict(lambda: defaultdict(list))
        self._levels_seen: set[int] = set()
        self._closed = False

    def _file_for(self, level: int):
        f = self._files.get(level)
        if f is None:
            f = open(_seg_path(self.spool_dir, level), "wb")
            self._files[level] = f
        return f

    def add(self, level: int, ix: int, iy: int,
            roads: Optional[list] = None,
            backgrounds: Optional[list] = None,
            names: Optional[list] = None) -> None:
        if self._closed:
            raise RuntimeError("SpoolWriter is closed")
        n_new = len(roads or []) + len(backgrounds or []) + len(names or [])
        if n_new == 0:
            return
        buf = self._buffers[level]
        content = buf.get((ix, iy))
        if content is None:
            content = _empty_content()
            buf[(ix, iy)] = content
        if roads:
            content["roads"].extend(roads)
        if backgrounds:
            content["backgrounds"].extend(backgrounds)
        if names:
            content["names"].extend(names)
        self._buffer_counts[level] += n_new
        if self._buffer_counts[level] >= self.flush_threshold:
            self._flush_level(level)

    def _flush_level(self, level: int) -> None:
        buf = self._buffers.get(level)
        if not buf:
            return
        f = self._file_for(level)
        segs = self._segs[level]
        for (ix, iy), content in buf.items():
            rec = encode_columns(content_to_columns(content))
            f.write(_SEG_HDR.pack(ix, iy, len(rec)))
            segs[(ix, iy)].append((self._pos[level] + _SEG_HDR.size, len(rec)))
            f.write(rec)
            self._pos[level] += _SEG_HDR.size + len(rec)
        f.flush()
        buf.clear()
        self._buffer_counts[level] = 0
        self._levels_seen.add(level)

    def flush_all(self) -> None:
        for level in list(self._buffers):
            self._flush_level(level)

    def _finalize_index(self, level: int) -> None:
        segs = self._segs[level]
        keys = sorted(segs, key=lambda k: (k[1], k[0]))
        totals = [len(keys), 0, 0, 0]
        offsets = np.zeros(len(keys), dtype="<u8")
        lengths = np.zeros(len(keys), dtype="<u8")
        with open(_seg_path(self.spool_dir, level), "rb") as sf, \
                open(_data_path(self.spool_dir, level), "wb") as out:
            sm = mmap.mmap(sf.fileno(), 0, access=mmap.ACCESS_READ)
            pos = 0
            merged = None
            for i, key in enumerate(keys):
                merged = merge_columns([decode_columns(sm, off) for off, _n in segs[key]])
                rec = encode_columns(merged)
                out.write(rec)
                offsets[i], lengths[i] = pos, len(rec)
                pos += len(rec)
                totals[1] += len(merged["r_display_class"])
                totals[2] += len(merged["b_class"])
                totals[3] += len(merged["s_type"])
            merged = None  # drop numpy views so the mmap can close
            sm.close()
        with open(_idx_path(self.spool_dir, level), "wb") as fh:
            fh.write(IDX_MAGIC)
            fh.write(struct.pack("<5Q", len(keys), *totals))
            fh.write(np.array([k[0] for k in keys], dtype="<i4").tobytes())
            fh.write(np.array([k[1] for k in keys], dtype="<i4").tobytes())
            fh.write(offsets.tobytes())
            fh.write(lengths.tobytes())
        os.remove(_seg_path(self.spool_dir, level))

    def close(self) -> None:
        if self._closed:
            return
        self.flush_all()
        for f in self._files.values():
            f.close()
        for level in sorted(self._levels_seen):
            self._finalize_index(level)
        self._closed = True

    def __enter__(self) -> "SpoolWriter":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()


class _LevelIndex:
    __slots__ = ("n", "totals", "ix", "iy", "offset", "length")


class SpoolReader:
    """Reads a spool directory written by `SpoolWriter` (per-cell `pread`)."""

    def __init__(self, spool_dir):
        self.spool_dir = Path(spool_dir)
        self._idx: dict[int, Optional[_LevelIndex]] = {}
        self._fd: dict[int, int] = {}

    def _load_idx(self, level: int) -> Optional[_LevelIndex]:
        if level in self._idx:
            return self._idx[level]
        p = _idx_path(self.spool_dir, level)
        if not p.exists():
            self._idx[level] = None
            return None
        raw = p.read_bytes()
        if raw[:8] != IDX_MAGIC:
            raise ValueError(f"{p}: not a binary spool index (legacy pickle spool? "
                             f"run parser/tools/convert_spool.py)")
        n, *totals = struct.unpack_from("<5Q", raw, 8)
        pos = 8 + 40
        ix = _LevelIndex()
        ix.n = n
        ix.totals = dict(zip(("parcels", "roads", "backgrounds", "names"), totals))
        ix.ix = np.frombuffer(raw, "<i4", n, pos)
        ix.iy = np.frombuffer(raw, "<i4", n, pos + 4 * n)
        ix.offset = np.frombuffer(raw, "<u8", n, pos + 8 * n)
        ix.length = np.frombuffer(raw, "<u8", n, pos + 16 * n)
        self._idx[level] = ix
        return ix

    def _read_cell(self, level: int, offset: int, length: int) -> bytes:
        # pread, not mmap: mapped file pages count toward the process RSS the
        # build is budgeted on, and a level-0 spool is multiple GB.
        fd = self._fd.get(level)
        if fd is None:
            fd = os.open(_data_path(self.spool_dir, level), os.O_RDONLY)
            self._fd[level] = fd
        return os.pread(fd, length, offset)

    def close(self) -> None:
        for fd in self._fd.values():
            os.close(fd)
        self._fd.clear()

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass

    def n_cells(self, level: int) -> int:
        idx = self._load_idx(level)
        return 0 if idx is None else idx.n

    def cell_keys(self, level: int) -> list[tuple[int, int]]:
        """Sorted `(ix, iy)` of every non-empty cell (ascending `(iy, ix)`)."""
        idx = self._load_idx(level)
        if idx is None:
            return []
        return list(zip(idx.ix.tolist(), idx.iy.tolist()))

    def iter_cell_columns(self, level: int, start: int = 0, stop: Optional[int] = None
                          ) -> Iterator[tuple[int, int, dict[str, np.ndarray]]]:
        idx = self._load_idx(level)
        if idx is None:
            return
        stop = idx.n if stop is None else min(stop, idx.n)
        ixs, iys = idx.ix.tolist(), idx.iy.tolist()
        offs, lens = idx.offset.tolist(), idx.length.tolist()
        for i in range(start, stop):
            yield ixs[i], iys[i], decode_columns(self._read_cell(level, offs[i], lens[i]))

    def iter_cells(self, level: int, start: int = 0, stop: Optional[int] = None
                   ) -> Iterator[tuple[int, int, dict]]:
        """Yield `(ix, iy, content)` for cells `start..stop` of the level's
        ascending `(iy, ix)` cell list."""
        for ix, iy, cols in self.iter_cell_columns(level, start, stop):
            yield ix, iy, columns_to_content(cols)

    def iter_level(self, level: int) -> Iterator[tuple[int, int, dict]]:
        """Yield `(ix, iy, content)` for every non-empty parcel at `level`,
        in ascending `(iy, ix)` order."""
        return self.iter_cells(level)

    def stats(self, level: int) -> dict:
        """Return `{"parcels": int, "roads": int, "backgrounds": int, "names": int}`
        for `level`, or all-zero if the level has no spooled content."""
        idx = self._load_idx(level)
        if idx is None:
            return {"parcels": 0, "roads": 0, "backgrounds": 0, "names": 0}
        return dict(idx.totals)

    def levels(self) -> list[int]:
        """Levels with an index file in this spool directory."""
        out = []
        for p in sorted(self.spool_dir.glob("level_*.idx")):
            try:
                out.append(int(p.stem.split("_", 1)[1]))
            except (IndexError, ValueError):
                continue
        return sorted(out)
