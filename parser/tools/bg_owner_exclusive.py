"""Plan 44: owner-exclusive identity for R01 residual rows (R-G5-4-a/b).

Producer match (old disc, encoder at 33006aa): the unique spool source whose
clip into the leaf's exact integer rectangle byte-equals the old record.

Owner-exclusive vertices (post-3-14, encoder at d35b565): vertices of that
source's clip into the leaf that (i) no other bbox-meeting source produces at
the same raw position, (ii) do not lie on the leaf rectangle boundary, and
(iii) are not R01-failing on the old disc.

The C probe is a throwaway shared library built from a pinned `_cenc.c` with
`-O2 -ffp-contract=off` (H12 arithmetic). It exposes `probe_bg` = `kw__bg_shape`
against an explicit clip rect.
"""
from __future__ import annotations

import ctypes
import hashlib
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Iterable, Optional, Sequence

import numpy as np

_PARSER = Path(__file__).resolve().parent.parent
_PROBE_C = _PARSER / "tests" / "fixtures" / "bg_eo" / "probe.c"
_CENC = _PARSER / "kiwiw" / "_cenc.c"


def _find_cc() -> str:
    from kiwiw import cbuild
    return cbuild._find_cc()


def _cflags() -> list[str]:
    from kiwiw import cbuild
    return list(cbuild.CFLAGS)


_FLEX_PROBE_SRC = r"""
/* Plan 44: probe_bg (compat, tc=288, full L0 frame) + probe_bg_flex (tc/b4/cr). */
#include "CENC_PATH"
int64_t probe_bg_flex(const double *lat, const double *lon, int64_t n,
                      int64_t tc, const double *b4, const double *rect, double cr,
                      uint8_t *out, int64_t room, int64_t *nrec) {
    return kw__bg_shape(lat, lon, n, 1, 1, tc, 0, b4, rect, cr, out, room, nrec);
}
int64_t probe_bg(const double *lat, const double *lon, int64_t n,
                 const double *rect, uint8_t *out, int64_t room, int64_t *nrec) {
    const double b4[4] = {0, 4096, 0, 4096};
    return probe_bg_flex(lat, lon, n, 288, b4, rect, 4096.0, out, room, nrec);
}
"""


def compile_probe(cenc_c: Path | str | None = None, out: Path | str | None = None) -> Path:
    """Build probe.so against `cenc_c` (default: in-tree `_cenc.c`). Returns the .so path.

    Exports probe_bg (compat) and probe_bg_flex (caller-supplied tc, b4, cr).
    """
    cenc_c = Path(cenc_c) if cenc_c else _CENC
    if out is None:
        h = hashlib.sha256(cenc_c.read_bytes() + b"|flex1").hexdigest()[:12]
        out = Path(tempfile.gettempdir()) / f"bg_oe_probe_{h}.so"
    else:
        out = Path(out)
    if out.exists() and out.stat().st_mtime >= cenc_c.stat().st_mtime:
        return out
    with tempfile.TemporaryDirectory(prefix="bg_oe_") as tmp:
        tmp = Path(tmp)
        (tmp / "kiwiw").mkdir()
        (tmp / "kiwiw" / "_cenc.c").write_bytes(cenc_c.read_bytes())
        # Headers / sibling sources pinned with cenc_c when present (else in-tree).
        _src_dir = cenc_c.parent if any(cenc_c.parent.glob("*.h")) else _PARSER / "kiwiw"
        for hdr in list(_src_dir.glob("*.h")) + [s for s in _src_dir.glob("_*.c") if s.name != "_cenc.c"]:
            (tmp / "kiwiw" / hdr.name).write_bytes(hdr.read_bytes())
        cenc_path = tmp / "kiwiw" / "_cenc.c"
        probe = tmp / "probe_flex.c"
        probe.write_text(_FLEX_PROBE_SRC.replace("CENC_PATH", str(cenc_path)))
        subprocess.run([_find_cc(), *_cflags(), "-shared", str(probe), "-lm", "-o", str(out)],
                       check=True, cwd=str(_PARSER))
    return out


def load_probe(so: Path | str):
    """ctypes wrapper: returns probe_bg; attaches ._flex = probe_bg_flex on the same .so."""
    lib = ctypes.CDLL(str(so))
    fn = lib.probe_bg
    fn.restype = ctypes.c_int64
    fn.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int64,
                   ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int64, ctypes.c_void_p]
    flex = lib.probe_bg_flex
    flex.restype = ctypes.c_int64
    flex.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int64, ctypes.c_int64,
                     ctypes.c_void_p, ctypes.c_void_p, ctypes.c_double,
                     ctypes.c_void_p, ctypes.c_int64, ctypes.c_void_p]
    fn._flex = flex
    fn._lib = lib
    return fn


def clip_ring(probe, ring_xy: Sequence[tuple[float, float]], rect=(0.0, 0.0, 4096.0, 4096.0),
              room: int = 1 << 20, *, tc: int | None = None,
              b4: Sequence[float] | None = None, cr: float | None = None) -> tuple[int, int, bytes]:
    """Clip a ring given in raw cell units (x=lon-axis, y=lat-axis) against `rect`.

    When tc/b4/cr are given, uses probe_bg_flex (H12 arithmetic, pinned encoder).
    Returns (size, nrec, wire_bytes). size < 0 is a decline (-1) or room exhaustion (-2).
    """
    lat = np.ascontiguousarray([y for x, y in ring_xy], dtype=np.float64)
    lon = np.ascontiguousarray([x for x, y in ring_xy], dtype=np.float64)
    r = np.ascontiguousarray(rect, dtype=np.float64)
    out = np.zeros(max(1, room), dtype=np.uint8)
    nr = ctypes.c_int64()
    if tc is not None or b4 is not None or cr is not None:
        flex = getattr(probe, "_flex", None)
        if flex is None:
            raise RuntimeError("probe has no probe_bg_flex; recompile via compile_probe")
        b4_a = np.ascontiguousarray(b4 if b4 is not None else (0.0, 4096.0, 0.0, 4096.0), dtype=np.float64)
        cr_v = float(cr if cr is not None else 4096.0)
        tc_v = int(tc if tc is not None else 288)
        size = int(flex(lat.ctypes.data, lon.ctypes.data, len(ring_xy), tc_v,
                        b4_a.ctypes.data, r.ctypes.data, cr_v,
                        out.ctypes.data, room, ctypes.byref(nr)))
    else:
        size = int(probe(lat.ctypes.data, lon.ctypes.data, len(ring_xy),
                         r.ctypes.data, out.ctypes.data, room, ctypes.byref(nr)))
    return size, int(nr.value), out[:max(0, size)].tobytes()


def wire_records(blob: bytes) -> list[bytes]:
    """Split a kw__bg_shape wire blob into its per-record byte strings."""
    import struct
    out, pos = [], 0
    while pos < len(blob):
        size = (struct.unpack_from(">H", blob, pos)[0] & 4095) * 2
        if size <= 0:
            raise ValueError(f"wire record of size 0 at {pos}")
        out.append(blob[pos:pos + size])
        pos += size
    if pos != len(blob):
        raise ValueError(f"wire blob length mismatch: consumed {pos} of {len(blob)}")
    return out


def wire_vertices(blob: bytes) -> list[tuple[int, int]]:
    """Decode raw (x, y) vertices from a kw__bg_shape wire blob (big-endian records)."""
    import struct
    from kiwiw.coordconv import decode_region_coord
    out, pos = [], 0
    while pos < len(blob):
        size, ndl, tc, flags, x, y = struct.unpack_from(">6H", blob, pos)
        size = (size & 4095) * 2
        step = 1 << (flags & 7)
        x, y = decode_region_coord(x), decode_region_coord(y)
        pts = [(x, y)]
        for k in range(ndl & 2047):
            dx, dy = struct.unpack_from("bb", blob, pos + 12 + 2 * k)
            x += step * dx
            y += step * dy
            pts.append((x, y))
        out.extend(pts)
        pos += size
    if pos != len(blob):
        raise ValueError(f"wire blob length mismatch: consumed {pos} of {len(blob)}")
    return out


def on_rect_boundary(x: int, y: int, rect: Sequence[float], eps: float = 0.0) -> bool:
    """True iff (x, y) lies on the leaf rectangle boundary (inclusive edges)."""
    x0, y0, x1, y1 = rect
    return (abs(x - x0) <= eps or abs(x - x1) <= eps or
            abs(y - y0) <= eps or abs(y - y1) <= eps)


def owner_exclusive_vertices(
    source_verts: Sequence[tuple[int, int]],
    other_verts: Iterable[Sequence[tuple[int, int]]],
    rect: Sequence[float],
    failing: Optional[set[tuple[int, int]]] = None,
) -> list[tuple[int, int]]:
    """Vertices of `source_verts` that no neighbour supplies, not on `rect` edge,
    and not in `failing` (R01-failing positions on the old disc)."""
    held = {p for vs in other_verts for p in vs}
    fail = failing or set()
    out = []
    for p in source_verts:
        if p in held or p in fail or on_rect_boundary(p[0], p[1], rect):
            continue
        out.append(p)
    return out


def identity_bearing_vertices(
    record_verts: Sequence[tuple[int, int]],
    rect: Sequence[float],
    failing: Optional[set[tuple[int, int]]] = None,
) -> list[tuple[int, int]]:
    """Old-record verts that are not on `rect` boundary and not R01-failing.

    Used by unique-fragment producer matching (revised design 44 after 0551ed2).
    """
    fail = failing or set()
    out = []
    for x, y in record_verts:
        pt = (int(x), int(y))
        if pt in fail or on_rect_boundary(pt[0], pt[1], rect):
            continue
        out.append(pt)
    return out


def find_producer(
    probe,
    record_bytes: bytes,
    candidates: Sequence[tuple[object, Sequence[tuple[float, float]]]],
    rect=(0.0, 0.0, 4096.0, 4096.0),
    *,
    tc: int | None = None,
    b4: Sequence[float] | None = None,
    cr: float | None = None,
    record_verts: Optional[Sequence[tuple[int, int]]] = None,
    failing: Optional[set[tuple[int, int]]] = None,
    clip_cache: Optional[dict] = None,
    piecewise: bool = False,
) -> tuple[str, Optional[object]]:
    """Return producer class under revised design 44.

    unique-byte | unique-fragment | producer-ambiguous | producer_none.
    Pass `record_verts` (disc record vertices) to enable unique-fragment.
    piecewise=True (plan 46): a byte hit is the record equal to ANY one record of the
    clip blob (a clip may emit several pieces; each is its own leaf record). Default
    False keeps the design-44/45 whole-blob comparison unchanged.
    """
    clips: list[tuple[object, set[tuple[int, int]], bytes]] = []
    byte_hits: list[object] = []
    for cid, ring in candidates:
        # clip_cache: caller-scoped memo keyed (cid, tc); valid only while rect/b4/cr
        # are fixed (one leaf). Results are identical to an uncached clip.
        ck = (cid, tc)
        hit = clip_cache.get(ck) if clip_cache is not None else None
        if hit is None:
            size, _nrec, blob = clip_ring(probe, ring, rect=rect, tc=tc, b4=b4, cr=cr)
            vset = {(int(x), int(y)) for x, y in wire_vertices(blob)} if size > 0 else None
            hit = (size, blob, vset)
            if clip_cache is not None:
                clip_cache[ck] = hit
        size, blob, vset = hit
        if size <= 0:
            continue
        clips.append((cid, vset, blob))
        if blob == record_bytes or (piecewise and record_bytes and record_bytes in wire_records(blob)):
            byte_hits.append(cid)
    if len(byte_hits) == 1:
        return "unique-byte", byte_hits[0]
    if len(byte_hits) > 1:
        return "producer-ambiguous", None

    if record_verts is None:
        return "producer_none", None
    ib = identity_bearing_vertices(record_verts, rect, failing=failing)
    if not ib:
        return "producer_none", None
    cover = [cid for cid, vset, _ in clips if all(v in vset for v in ib)]
    if len(cover) > 1:
        return "producer-ambiguous", None
    if len(cover) == 0:
        return "producer_none", None
    cid = cover[0]
    others: set[tuple[int, int]] = set()
    for oid, oset, _ in clips:
        if oid == cid:
            continue
        others |= oset
    if any(v not in others for v in ib):
        return "unique-fragment", cid
    return "producer_none", None


def bbox_meets_rect(ring_xy: Sequence[tuple[float, float]], rect: Sequence[float]) -> bool:
    """Axis-aligned bbox of `ring_xy` intersects the closed rectangle `rect`."""
    if not ring_xy:
        return False
    xs = [p[0] for p in ring_xy]
    ys = [p[1] for p in ring_xy]
    x0, y0, x1, y1 = rect
    return not (max(xs) < x0 or min(xs) > x1 or max(ys) < y0 or min(ys) > y1)
