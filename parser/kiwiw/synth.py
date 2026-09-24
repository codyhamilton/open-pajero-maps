"""Pure from-scratch binary encoders for road/background/name/map frames.

Unlike the copy-and-patch encoders in road_writer.py, background_writer.py,
and name_writer.py (which require ``raw_bytes`` from real disc data), these
functions build frame bytes purely from semantic fields -- suitable for
OSM-derived objects that have ``raw_bytes=b""``.

The output bytes are parseable by the existing decoders (road.py,
background.py, name.py, parcel.py) and decode back to semantically
equivalent IR objects.

Binary format references:
  - road.py decode_road_frame()
  - background.py decode_background_frame()
  - name.py decode_name_frame()
  - parcel.py decode_parcel()
"""
from __future__ import annotations

from collections import defaultdict


from . import cenc as _cenc
from . import clip as _clip
from .bitutils import geo_secs_bytes
from .coordconv import encode_region_coord, latlon_to_xy
from .model import BackgroundShape, BoundingBox, NameRecord, RoadLink

_MAP_FRAME_HEADER_SIZE = 36


def _u16(v: int) -> bytes:
    if not 0 <= v <= 0xFFFF:
        raise ValueError(f"{v} does not fit in u16")
    return bytes((v >> 8, v & 0xFF))


def _u32(v: int) -> bytes:
    if not 0 <= v <= 0xFFFFFFFF:
        raise ValueError(f"{v} does not fit in u32")
    return bytes(((v >> 24) & 0xFF, (v >> 16) & 0xFF, (v >> 8) & 0xFF, v & 0xFF))


def frame_range(bounds: BoundingBox, coord_range: int | None = None) -> int:
    """The coordinate range an encoder converts at: `coord_range` when
    given, else `bounds.coord_range`; `ValueError` when neither is set (no
    default range exists). Both encoders (this module and `cenc`/`_cenc.c`)
    resolve it here, so they agree."""
    if coord_range is not None:
        return coord_range
    return bounds.require_range()


def _coord_max(coord_range: int) -> int:
    """Clamp ceiling: the frame's inclusive edge. Every real range (<= 16384,
    `coordconv.range_for`) fits the 3-bit region word, so no packing cap
    applies (`coordconv.encode_region_coord` rejects one that would not)."""
    return coord_range


def _clamp_coord(v: int, coord_range: int) -> int:
    """Clamp to the frame's inclusive interval [0, coord_range]."""
    return max(0, min(_coord_max(coord_range), v))


# ---------------------------------------------------------------------------
# Road
# ---------------------------------------------------------------------------

def encode_road_link_bytes(link: RoadLink, bounds: BoundingBox, *,
                           coord_range: int | None = None) -> bytes:
    """Encode a RoadLink to bytes from semantic fields (no raw_bytes needed).

    Produces a record parseable by ``road.decode_road_frame()``. Each node
    is encoded as a 6-byte node record; no intermediate delta points are
    emitted (nip = 0 for all nodes).
    """
    nodes = link.nodes
    cr = frame_range(bounds, coord_range)
    n_nodes = len(nodes)
    if n_nodes == 0:
        raise ValueError("RoadLink must have at least one node")

    # Header layout:
    #   bytes 0-3: u32 hdr
    #     bits  0: 7 = noff / 2    (noff = byte offset to first node record)
    #     bits 16:27 = total_len/2 (total record length)
    #   bytes 4-5: u16, bits 0:10 = n_nodes
    #   bytes 6-7: u16 (shape_len; unused by decoder, set to 0)
    #   bytes 8-13: 6 zero bytes (undecoded header region)
    #   bytes 14-15: u16 lattr
    # Then n_nodes * 6-byte node records.

    noff = 16            # nodes start right after the 16-byte header
    total_len = noff + n_nodes * 6
    assert noff % 2 == 0 and total_len % 2 == 0

    hdr_u32 = (noff // 2) | ((total_len // 2) << 16)

    lattr = (
        int(link.altitude_flag)
        | (int(link.route_type_guidance_flag) << 1)
        | (link.pseudo3d_updown << 2)
        | (int(link.route_planning_tag) << 4)
        # bit 5: undecoded on disc, leave 0
        | (int(link.link_id_flag) << 6)
        | (int(link.selected_link_flag) << 7)
        | (int(link.toll_flag) << 8)
        | (int(link.route_number_flag) << 9)
        | (int(link.infra_link_flag) << 10)
        | (int(link.link_id_number_flag) << 11)
        | (link.road_type << 12)
    )

    out = bytearray()
    out += _u32(hdr_u32)
    out += _u16(n_nodes & 0x7FF)  # bits 0:10
    out += _u16(0)                 # shape_len word (unused)
    out += bytes(6)                # undecoded header bytes 8-13
    out += _u16(lattr)

    for node in nodes:
        # Always from lat/lon at this frame's range: node.x/.y (the spool's
        # n_x/n_y) were computed at another range/orientation and are not read.
        xc, yc = latlon_to_xy(node.lat, node.lon, bounds, coord_range=cr)
        xc = _clamp_coord(xc, cr)
        yc = _clamp_coord(yc, cr)

        nodeattr = (
            0                        # nip = 0 (no intermediate points)
            # bit 10: undecoded, 0
            | (int(node.bridge) << 11)
            | (int(node.tunnel) << 12)
            | (node.planned << 13)
            | (node.oneway << 15)
        )
        out += _u16(nodeattr)
        out += _u16(encode_region_coord(xc, coord_range=cr))
        out += _u16(encode_region_coord(yc, coord_range=cr))

    assert len(out) == total_len
    return bytes(out)


def build_road_frame_bytes(links: list[RoadLink], bounds: BoundingBox, *,
                           coord_range: int | None = None) -> bytes:
    """Build a complete Road Data Frame binary from a list of RoadLinks.

    Groups links by display_class; each display class gets its own section
    (2-byte flags word + consecutive link records). The output is parseable
    by ``road.decode_road_frame()``.
    """
    if not links:
        # Minimal empty frame: 8-byte header, no display classes.
        return bytes(8)

    # Group links by display_class.
    dc_links: dict[int, list[RoadLink]] = defaultdict(list)
    for lk in links:
        dc_links[lk.display_class].append(lk)
    max_dc = max(dc_links.keys())
    # The DC table must have entries for ALL slots 0..max_dc (not just the
    # occupied ones) because the decoder assigns display_class from the loop
    # index (_dc in range(ndc)), not from a stored field.  Empty slots use
    # raw_offset_word=0xFFFF (the "not present" sentinel, decoded by sws as
    # 0xFFFF which the reader checks verbatim).
    all_dcs = list(range(max_dc + 1))
    n_dc = len(all_dcs)

    # Encode every link record for the occupied DCs.
    dc_link_bytes: dict[int, list[bytes]] = {}
    for dc in dc_links:
        dc_link_bytes[dc] = [encode_road_link_bytes(lk, bounds, coord_range=coord_range)
                             for lk in dc_links[dc]]

    # Layout:
    #   8-byte common header
    #   n_dc * 4 bytes: display-class table
    #   Then one section per occupied DC: 2-byte flags + link records
    header_end = 8 + n_dc * 4      # always even (8 even, 4*k even)

    dc_section_offsets: dict[int, int] = {}  # only for occupied DCs
    cursor = header_end
    for dc in all_dcs:
        if dc in dc_links:
            dc_section_offsets[dc] = cursor
            cursor += 2  # 2-byte flags word
            for lb in dc_link_bytes[dc]:
                cursor += len(lb)       # link lengths are always even

    total_size = cursor
    if total_size % 2:
        total_size += 1

    buf = bytearray(total_size)

    # Common header (bytes 0-7):
    #   [0-1] header_size_raw = 0 (unused by reader)
    #   [2-3] n_intersections = 0
    #   [4]   n_display_classes
    #   [5]   n_additional_data = 0
    #   [6-7] lvl_field_raw = 0
    buf[4] = n_dc

    # Display-class table entries (4 bytes each, starting at offset 8).
    for i, dc in enumerate(all_dcs):
        tbl_off = 8 + i * 4
        if dc in dc_section_offsets:
            section_off = dc_section_offsets[dc]
            n_links = len(dc_links[dc])
            assert section_off % 2 == 0
            raw_offset_word = section_off // 2    # unsws: decoded sws(v) = section_off
            raw_count_word = n_links & 0xFFF      # bits 0:11 = npoly
        else:
            # Empty slot: use 0xFFFF sentinel for offset, 0 for count.
            raw_offset_word = 0xFFFF
            raw_count_word = 0
        buf[tbl_off]     = (raw_offset_word >> 8) & 0xFF
        buf[tbl_off + 1] = raw_offset_word & 0xFF
        buf[tbl_off + 2] = (raw_count_word >> 8) & 0xFF
        buf[tbl_off + 3] = raw_count_word & 0xFF

    # Display-class sections (occupied DCs only, in ascending DC order).
    for dc in all_dcs:
        if dc not in dc_section_offsets:
            continue
        section_off = dc_section_offsets[dc]
        # 2-byte flags = 0x0000 (already zero in bytearray)
        pos = section_off + 2
        for lb in dc_link_bytes[dc]:
            buf[pos:pos + len(lb)] = lb
            pos += len(lb)

    return bytes(buf)


# ---------------------------------------------------------------------------
# Background
# ---------------------------------------------------------------------------

def _mult_exp(mc: int) -> int:
    """The addl word's bits 0:2 (a 3-bit exponent, `mult_const` in 1..128)
    for a given `mult_const`."""
    mult_exp = 0
    mc_check = 1
    while mc_check < mc:
        mc_check <<= 1
        mult_exp += 1
    return mult_exp


def _bg_mult(shape: BackgroundShape) -> tuple[int, int]:
    """(mult, exponent): the shape's base/fallback `mult_const` (>= 1, from
    extraction, currently always 1 -- see `osm_to_parcel_geometry._make_
    background_shape`) and the addl word's bits 0:2. `encode_background_
    shape_records_scalar` may still write an individual piece at a larger,
    per-piece `mult_const` when `clip.shape_pieces` proves it safe (3-11,
    `clip._rect_mult`); that decision is made per piece, not here."""
    mc = shape.mult_const if shape.mult_const >= 1 else 1
    return mc, _mult_exp(mc)


def _bg_piece_record(piece, shape: BackgroundShape, cr: int, mc: int, mult_exp: int) -> bytes:
    """One line/polygon record from one clipped piece's rounded vertices.

    Every vertex is inside the clip rectangle and every step is an exact
    multiple of `mc` and fits the signed delta (`clip.shape_pieces`
    guarantees all three -- by construction for `mc > 1`, 3-11), so the
    accumulator reproduces each vertex exactly. No vertex is clamped."""
    n_deltas = len(piece) - 1
    rec_len = 12 + n_deltas * 2
    out = bytearray(rec_len)
    hdr_word = (rec_len // 2) & 0xFFF   # bits 0:11
    out[0], out[1] = (hdr_word >> 8) & 0xFF, hdr_word & 0xFF
    flag_word = n_deltas & 0x7FF         # bits 0:10 = ncoord
    out[2], out[3] = (flag_word >> 8) & 0xFF, flag_word & 0xFF
    out[4], out[5] = (shape.type_code >> 8) & 0xFF, shape.type_code & 0xFF
    addl = (mult_exp & 0x7) | (int(shape.underground) << 9) | (int(shape.pen_up) << 10)
    out[6], out[7] = (addl >> 8) & 0xFF, addl & 0xFF
    xc, yc = piece[0][0], piece[0][1]
    sx = encode_region_coord(xc, coord_range=cr)
    sy = encode_region_coord(yc, coord_range=cr)
    out[8], out[9], out[10], out[11] = (sx >> 8) & 0xFF, sx & 0xFF, (sy >> 8) & 0xFF, sy & 0xFF
    j = 12
    for v in piece[1:]:
        dx = max(-128, min(127, (v[0] - xc) // mc))
        dy = max(-128, min(127, (v[1] - yc) // mc))
        xc += dx * mc
        yc += dy * mc
        out[j] = dx & 0xFF
        out[j + 1] = dy & 0xFF
        j += 2
    return bytes(out)


def _bg_point_record(shape: BackgroundShape) -> bytes:
    """Point shape: 12-byte record, no coords, no deltas."""
    out = bytearray(12)
    out[1] = 6  # rec_len // 2
    out[4] = (shape.type_code >> 8) & 0xFF
    out[5] = shape.type_code & 0xFF
    return bytes(out)


def encode_background_shape_records(shape: BackgroundShape, bounds: BoundingBox, *,
                                    coord_range: int | None = None) -> list[bytes]:
    """A BackgroundShape's records, clipped to its parcel (C when available,
    else the Python oracle `encode_background_shape_records_scalar`).

    Zero records when the shape lies outside the parcel (or degenerates on
    rounding), several when a polygon leaves and re-enters or a line crosses
    out and back (`kiwiw.clip`)."""
    cr = frame_range(bounds, coord_range)
    if shape.shape_class != 0:
        fast = _cenc.bg_shape_records(shape, bounds, cr)
        if fast is not None:
            return fast
    return encode_background_shape_records_scalar(shape, bounds, coord_range=cr)


def encode_background_shape_records_scalar(shape: BackgroundShape, bounds: BoundingBox, *,
                                           coord_range: int | None = None) -> list[bytes]:
    """Python reference encoder (the byte-identity oracle for the C path).

    Point shapes (`shape_class == 0`) produce one 12-byte record with no
    coords. A line (class 1, or any open class) or polygon (class 2) is
    clipped to the parcel's rectangle (`kiwiw.clip`, in the frame's raw
    lattice before rounding); each piece is one record whose first vertex
    is sx/sy and the rest signed-i8 delta pairs. Parseable by
    ``background.decode_background_frame()``.
    """
    if shape.shape_class == 0:
        return [_bg_point_record(shape)]
    cr = frame_range(bounds, coord_range)
    if not shape.coords:
        raise ValueError(
            f"BackgroundShape (shape_class={shape.shape_class}) has no coords"
        )
    mc, _ = _bg_mult(shape)
    fx, fy = _clip.to_raw(shape.coords, bounds, cr)
    rect = _clip.clip_rect(bounds, cr)
    pieces = _clip.shape_pieces(fx, fy, shape.shape_class == 2, rect, mc,
                                auto_rect_mult=True)
    for piece, _pm in pieces:
        for v in piece:
            if not (rect[0] <= v[0] <= rect[2] and rect[1] <= v[1] <= rect[3]):
                raise AssertionError(f"clipped vertex {v[:2]} outside {rect}")
    return [_bg_piece_record(p, shape, cr, pm, _mult_exp(pm)) for p, pm in pieces]


def encode_background_shape_bytes(shape: BackgroundShape, bounds: BoundingBox, *,
                                   coord_range: int | None = None) -> bytes:
    """`encode_background_shape_records`, concatenated."""
    return b"".join(encode_background_shape_records(shape, bounds, coord_range=coord_range))


def encode_background_shape_bytes_scalar(shape: BackgroundShape, bounds: BoundingBox, *,
                                          coord_range: int | None = None) -> bytes:
    """`encode_background_shape_records_scalar`, concatenated."""
    return b"".join(encode_background_shape_records_scalar(shape, bounds,
                                                           coord_range=coord_range))


def build_background_frame_bytes(
    shapes: list[BackgroundShape], bounds: BoundingBox, *,
    coord_range: int | None = None,
) -> bytes:
    """Build a complete Background Data Frame binary.

    All shapes are placed in a single "element" (one entry in the Background
    Distribution Header), grouped by ``shape_class`` (each class = one type
    unit in the element's type-unit table).  Parseable by
    ``background.decode_background_frame()``.
    """
    # Encode shape records, grouped by shape_class in input order. A shape
    # clipped away writes nothing; one split into pieces writes each piece.
    class_encoded: dict[int, list[bytes]] = defaultdict(list)
    for s in shapes:
        class_encoded[s.shape_class].extend(
            encode_background_shape_records(s, bounds, coord_range=coord_range))
    class_encoded = {sc: recs for sc, recs in class_encoded.items() if recs}
    if not class_encoded:
        # Minimal empty frame: header_size_raw=1 → hlen=sws(1)=2.
        return bytes([0, 1])
    sorted_classes = sorted(class_encoded.keys())
    n_units = len(sorted_classes)

    # Frame layout:
    #   [0-1] header_size_raw (u16)
    #   [2-5] one element table entry (4 bytes: raw_offset_word + raw_size_word)
    #   --- header ends here (6 bytes) ---
    #   [6..] element section:
    #     u16 n_units
    #     n_units * 4 bytes: type-unit table entries (boff_word + val_word)
    #     shape records sequentially

    header_bytes = 6                     # always even
    element_section_offset = header_bytes

    unit_table_bytes = 2 + n_units * 4  # n_units count word + 4 bytes per unit
    shapes_total = sum(
        sum(len(eb) for eb in class_encoded[sc]) for sc in sorted_classes
    )
    element_section_size = unit_table_bytes + shapes_total

    total_size = header_bytes + element_section_size
    if total_size % 2:
        total_size += 1

    buf = bytearray(total_size)

    # header_size_raw: sws(v) = header_bytes → v = header_bytes // 2 = 3.
    buf[0] = 0
    buf[1] = header_bytes // 2      # = 3

    # Element table entry at [2-5]:
    # raw_offset_word = element_section_offset // 2 = 3
    raw_offset_word = element_section_offset // 2
    esz = element_section_size if element_section_size % 2 == 0 else element_section_size + 1
    raw_size_word = esz // 2
    buf[2] = (raw_offset_word >> 8) & 0xFF
    buf[3] = raw_offset_word & 0xFF
    buf[4] = (raw_size_word >> 8) & 0xFF
    buf[5] = raw_size_word & 0xFF

    # Element section.
    p = element_section_offset

    # n_units (2 bytes)
    buf[p]     = (n_units >> 8) & 0xFF
    buf[p + 1] = n_units & 0xFF
    p += 2

    # Type-unit table.
    for sc in sorted_classes:
        n_shapes = len(class_encoded[sc])
        # boff_word: not used by the decoder → 0.
        buf[p] = 0; buf[p + 1] = 0
        # val_word: bits 0:11 = count, bits 14:15 = shape_class.
        val = (n_shapes & 0xFFF) | ((sc & 0x3) << 14)
        buf[p + 2] = (val >> 8) & 0xFF
        buf[p + 3] = val & 0xFF
        p += 4

    # Shape records.
    for sc in sorted_classes:
        for eb in class_encoded[sc]:
            buf[p:p + len(eb)] = eb
            p += len(eb)

    return bytes(buf)


# ---------------------------------------------------------------------------
# Names
#
# Ch.7.4 defines five String Data Record layouts (7.4.2.1.1 Attribute 1,
# bits 10:8): 1=Barycentric, 4=Linear-B, 5=Linear-C, 6=Symbol+String (3=
# Linear-A is spec-defined but never observed on R and not encoded here).
# docs/design/target-disc.md says "string_type=1 is not used" for name
# records; the plan's refine pass (PLAN.md, "Refinement findings
# (2026-09-05)") narrows that to level 0 specifically, citing a Brisbane
# spot check where level-0 records were {4, 5, 6}, level 2 was {1, 5}, and
# levels 4-12 were {1} only -- so type 1 *is* legitimate at levels >= 2.
#
# CONTRADICTION (report per brief 11's instructions, not resolved here):
# the full-country level-0 census in parser/refdata/profile/map.json
# (levels["0"].name.string_type_hist) shows 1,042,019 real string_type=1
# records at level 0 (5.5% of level-0 name records) -- the opposite of what
# both the design doc and the Brisbane spot check say. The single small
# CBD parcel sampled for the spot check apparently just doesn't contain any
# of whatever level-0 feature carries type 1 nationally (harness/checks/
# vocab.py's docstring already flags this same tension). Per the brief,
# this is NOT resolved silently: the encoders below never emit
# string_type=1 for level 0, honouring the design doc's stricter rule and
# the harness's hard "vocab" check (harness/checks/vocab.py fails the build
# if string_type=1 appears at level 0), even though real R disc data
# contradicts it.
# ---------------------------------------------------------------------------

def encode_name_record_bytes(record: NameRecord, bounds: BoundingBox, *,
                             coord_range: int | None = None) -> bytes:
    """Encode a NameRecord of string_type=1 (Barycentric) to bytes.

    Other string types are not supported by this function and return
    ``b""``. Used for level ``None``/non-zero levels by
    ``build_name_frame_bytes`` -- see its docstring for the level-0 vs.
    other-levels split.

    Parseable by ``name.decode_name_frame()``.
    """
    if record.string_type != 1:
        return b""   # unsupported type; caller must skip

    text_bytes = record.text.encode("latin-1", errors="replace") + b"\x00"
    if len(text_bytes) % 2:
        text_bytes += b"\x00"
    slen = len(text_bytes)          # byte count (= slen_word * 2)
    slen_word = slen // 2

    # Pixel coordinates.
    cr = frame_range(bounds, coord_range)
    if record.lat is not None and record.lon is not None:
        xc, yc = latlon_to_xy(record.lat, record.lon, bounds, coord_range=cr)
        xc = _clamp_coord(xc, cr)
        yc = _clamp_coord(yc, cr)
    else:
        xc = yc = 0
    sx = encode_region_coord(xc, coord_range=cr)
    sy = encode_region_coord(yc, coord_range=cr)

    # Body layout for string_type=1 (Barycentric), from name.py:
    #   body+0,1: u16 (undecoded word0, 0)
    #   body+2,3: sx
    #   body+4,5: sy
    #   body+6,7: slen_word
    #   body+8..: text_bytes
    body = (
        _u16(0)
        + _u16(sx)
        + _u16(sy)
        + _u16(slen_word)
        + bytes(text_bytes)
    )

    reclen = 6 + len(body)          # na(2) + attr1(2) + attr2(2) + body
    assert reclen % 2 == 0, f"reclen {reclen} is not even"

    na   = reclen // 2              # bits 0:11 of the na word
    attr1 = (
        (record.priority & 0x3F)
        | (int(record.vertical) << 6)
        # bit 7: undecoded, 0
        | (1 << 8)                  # string_type = 1
        | ((record.display_scale_flag & 0x1F) << 11)
    )
    attr2 = record.type_code & 0xFFFF

    return _u16(na) + _u16(attr1) + _u16(attr2) + body


def _encode_barycentric_coords(lat, lon, bounds: BoundingBox, coord_range: int) -> bytes:
    """The 6-byte "Barycentric Coordinates Information" (spec 7.4.2.1.2.1),
    shared verbatim by string types 1, 5 and 6 (Ch.7.4.2.1.6/.7 both say
    "similar to that applies when string type is barycentric string").
    Word 0 (Additional Background Information Type/Flag + reserved) is 0:
    we never reference an additional data frame, which word 0 == 0
    correctly and completely expresses (not an unknown-bytes zero-fill).
    """
    if lat is not None and lon is not None:
        xc, yc = latlon_to_xy(lat, lon, bounds, coord_range=coord_range)
        xc = _clamp_coord(xc, coord_range)
        yc = _clamp_coord(yc, coord_range)
    else:
        xc = yc = 0
    sx = encode_region_coord(xc, coord_range=coord_range)
    sy = encode_region_coord(yc, coord_range=coord_range)
    return _u16(0) + _u16(sx) + _u16(sy)


def _encode_char_info_list(text: str) -> bytes:
    """Single-language "Character Information Data List" (7.4.2.1.2.2):
    the "Character Information Data Size" field is omitted (spec note (1):
    "omitted if the language-specific character information is only one
    type") and the language-specific offset pointer table is omitted (spec
    note: "If only one type of language ... is stored, the ... table is
    deleted") -- we only ever emit one (English) language, so this is
    exactly ``slen_word`` (u16) + text bytes, no size/offset preamble.

    Per spec note (6) ("If the string ends with an odd byte, the field
    contains 00(16) as dummy data at the tail of the string"), there is no
    unconditional NUL terminator -- confirmed against R: a decoded/
    re-encoded Brisbane type-5 "ALICE STREET"/"CHARLOTTE STREET" record
    only byte-matched once the always-append-b"\\x00" behaviour (copied
    from the pre-existing string_type=1 encoder above, which still has it
    and is out of this brief's scope) was replaced with "pad by one byte
    only if the raw text length is odd".
    """
    text_bytes = text.encode("latin-1", errors="replace")
    if len(text_bytes) % 2:
        text_bytes += b"\x00"
    return _u16(len(text_bytes) // 2) + text_bytes


def _encode_attr1(priority: int, vertical: bool, string_type: int,
                   display_scale_flag: int) -> int:
    return (
        (priority & 0x3F)
        | (int(vertical) << 6)
        # bit 7: Height Information Flag -- undecoded/unused, 0
        | ((string_type & 0x7) << 8)
        | ((display_scale_flag & 0x1F) << 11)
    )


def encode_name_record_type5_bytes(record: NameRecord, bounds: BoundingBox, *,
                                   coord_range: int | None = None) -> bytes:
    """Encode a NameRecord of string_type=5 (Linear-C, spec 7.4.2.1.6):
    Barycentric Coordinates Information + Display Angle Information (2
    bytes) + Character Information Data List. Self-contained (no
    cross-frame reference), unlike type 4 -- see module docstring and
    ``build_name_frame_bytes``.

    Display angle round-trips exactly through ``name.py``'s
    ``angle_deg = extract(ang, 0, 8) - 90`` (best-effort decode formula,
    itself not independently derived from the spec's raw "0-359 clockwise
    from north" field -- see name.py's module docstring); this function is
    that formula's exact inverse for the low 9 bits, OR'd with
    ``record.angle_flags`` (bits 15:9: rotation-angle flag, character
    display orientation, string rotation mode -- undecoded into semantic
    fields, just preserved raw) so a real R record round-trips
    byte-identical; synthetic records default ``angle_flags=0`` ("fixed
    angle, normal to screen, no per-string rotation" -- the spec's literal
    zero-bit meaning).
    """
    if record.string_type != 5:
        return b""

    coords = _encode_barycentric_coords(record.lat, record.lon, bounds,
                                        frame_range(bounds, coord_range))
    angle_deg = record.angle_deg if record.angle_deg is not None else 0.0
    angle_low9 = (int(round(angle_deg)) + 90) & 0x1FF
    angle_field = ((record.angle_flags & 0x7F) << 9) | angle_low9
    char_info = _encode_char_info_list(record.text)

    body = coords + _u16(angle_field) + char_info
    reclen = 6 + len(body)
    assert reclen % 2 == 0, f"reclen {reclen} is not even"
    na = reclen // 2
    attr1 = _encode_attr1(record.priority, record.vertical, 5, record.display_scale_flag)
    attr2 = record.type_code & 0xFFFF

    return _u16(na) + _u16(attr1) + _u16(attr2) + body


def encode_name_record_type6_bytes(record: NameRecord, bounds: BoundingBox, *,
                                   coord_range: int | None = None) -> bytes:
    """Encode a NameRecord of string_type=6 (Symbol+String, spec 7.4.2.1.7):
    Barycentric Coordinates Information (coordinates = center of symbol) +
    String Placement (2 bytes) + Character Information Data List.
    Self-contained, no cross-frame reference.

    String Placement is fixed at "center alignment, above symbol" (bits
    15:14=10, 13:12=00) -- a real, spec-legal value (not a zero-fill), but
    not verified against R (no sampled type-6 record's raw bytes were
    decoded field-by-field for this sub-word; only the record's text/
    type_code/position were cross-checked). If this placement combination
    ever needs to vary per feature, that is unpinned-down and should be
    treated as an open question, not silently changed.
    """
    if record.string_type != 6:
        return b""

    coords = _encode_barycentric_coords(record.lat, record.lon, bounds,
                                        frame_range(bounds, coord_range))
    placement = (0b10 << 14) | (0b00 << 12)   # center-aligned, above symbol
    char_info = _encode_char_info_list(record.text)

    body = coords + _u16(placement) + char_info
    reclen = 6 + len(body)
    assert reclen % 2 == 0, f"reclen {reclen} is not even"
    na = reclen // 2
    attr1 = _encode_attr1(record.priority, record.vertical, 6, record.display_scale_flag)
    attr2 = record.type_code & 0xFFFF

    return _u16(na) + _u16(attr1) + _u16(attr2) + body


# string_type -> encoder, for build_name_frame_bytes's per-level dispatch.
# string_type=4 (Linear-B) has no entry: see build_name_frame_bytes.
_NAME_ENCODERS_BY_STRING_TYPE = {
    1: encode_name_record_bytes,
    5: encode_name_record_type5_bytes,
    6: encode_name_record_type6_bytes,
}


def build_name_frame_bytes(records: list[NameRecord], bounds: BoundingBox,
                            level: int | None = None, *,
                            coord_range: int | None = None) -> bytes:
    """Build a complete Name Data Frame binary.

    All records are placed in a single list. Parseable by
    ``name.decode_name_frame()``.

    ``level`` selects which string types may be emitted (per-level
    vocabulary; docs/design/target-disc.md "Name records", narrowed by
    PLAN.md's refine pass -- see the module docstring above):

    - ``level is None`` (default, and every call site that predates this
      brief): unchanged legacy behaviour -- only string_type=1 records are
      encoded, everything else is silently skipped. Kept as the default so
      existing callers (build_alldata.py, and every test that does not
      pass ``level``) are unaffected; do not rely on this branch for new
      level-0 output.
    - ``level == 0``: string_type in {5, 6} is encoded; string_type in
      {1, 4} is dropped. Type 1 is dropped because R's level-0 vocabulary
      forbids it (see the contradiction noted above -- this is a
      deliberate, reported policy choice, not an oversight). Type 4
      (Linear-B) is dropped because its "Offset to the Data to be drawn"
      field (spec 7.4.2.1.5(1)) is a displacement into the *road or
      background* frame's own bytes, which this function's signature
      (``records``, ``bounds``, ``level``) has no way to know -- computing
      it needs the encoded road/background frame's per-record byte offsets
      threaded in from the assembler, which is out of this brief's owned
      files (only ``build_name_frame_bytes`` and ``_make_name_record`` are
      owned; the frame-assembly call site is unit 12's). Per the brief:
      "Do not zero-fill it" -- so type-4 records are omitted rather than
      encoded with a fabricated offset. This still satisfies the contract
      ("the set of emitted string types is a subset of the profile's set
      for that level"): {5, 6} subset-of {4, 5, 6}.
    - other levels: string_type=1 is encoded (legitimate at levels >= 2
      per the refine pass); string_type=5 is also encoded opportunistically
      (level 2's profile is {1, 5}) since the encoder is self-contained and
      harmless if unused; types 4 and 6 are dropped for the same
      cross-frame/unverified reasons as at level 0. Per-level selection
      beyond this is unit 14's job (PLAN.md unit 14 depends on this unit).
    """
    if level is None:
        allowed = {1}
    elif level == 0:
        allowed = {5, 6}
    else:
        allowed = {1, 5}

    encoded = [
        _NAME_ENCODERS_BY_STRING_TYPE[r.string_type](r, bounds, coord_range=coord_range)
        for r in records if r.string_type in allowed
    ]
    encoded = [e for e in encoded if e]     # drop unsupported types

    if not encoded:
        # Minimal empty frame: header_size_raw=1 → hlen=sws(1)=2.
        return bytes([0, 1])

    # Frame layout:
    #   [0-1] header_size_raw
    #   [2-5] one list table entry (4 bytes: raw_offset_word + raw_count_word)
    #   --- header ends here (6 bytes) ---
    #   [6..] name records sequentially

    header_bytes = 6
    list_section_offset = header_bytes

    records_total = sum(len(e) for e in encoded)
    total_size = header_bytes + records_total
    if total_size % 2:
        total_size += 1

    buf = bytearray(total_size)

    buf[0] = 0
    buf[1] = header_bytes // 2      # header_size_raw = 3

    raw_offset_word = list_section_offset // 2
    raw_count_word = len(encoded)
    buf[2] = (raw_offset_word >> 8) & 0xFF
    buf[3] = raw_offset_word & 0xFF
    buf[4] = (raw_count_word >> 8) & 0xFF
    buf[5] = raw_count_word & 0xFF

    p = list_section_offset
    for e in encoded:
        buf[p:p + len(e)] = e
        p += len(e)

    return bytes(buf)


# ---------------------------------------------------------------------------
# Map frame
# ---------------------------------------------------------------------------

_MFDE_LEN_DEFAULT = 20   # levels 0-10 (DESIGN.md section 4)
_MFDE_LEN_LEVEL_12 = 12  # level 12's table stops at n_basic_map + n_ext_map
_ABSENT_MFDE = (0xFFFFFFFF, 0)   # DESIGN.md section 4: R's own "not present" sentinel
_HEADER_DSFLAG = 0x0064   # DESIGN.md section 2: WP1 emission (scale 1/10000 constant)
_HEADER_RG_ADDR_ABSENT = 0xFFFFFFFF   # DESIGN.md section 2: no route-guidance model in WP1
_HEADER_RG_SIZE_ABSENT = 0


def mfde_table_len(level: int) -> int:
    """Table length for *level*, per `DESIGN.md` section 4: 12 at level 12,
    20 at every other level (0-10). WP1 does not generate divided parcels
    (the long tail of 21-35-entry tables on `R`; unit 13's job)."""
    return _MFDE_LEN_LEVEL_12 if level == 12 else _MFDE_LEN_DEFAULT


def _pad_even(b: bytes | None) -> bytes | None:
    """Ensure a sub-frame has even byte length (required for unsws); ``None``
    or empty input means "no sub-frame" and passes through as ``None``."""
    if b is None or len(b) == 0:
        return None
    return b if len(b) % 2 == 0 else b + bytes(1)


def build_map_frame_bytes(
    level: int,
    llpid: tuple[float, float],
    llcode: tuple[int, int],
    road_bytes: bytes | None,
    bg_bytes: bytes | None,
    name_bytes: bytes | None,
    *,
    region_list: bytes | None = None,
    ext_frames: dict[int, bytes] | None = None,
) -> bytes:
    """Build a complete Map Frame binary, shaped per `DESIGN.md` sections 2-4.

    The output is parseable by ``parcel.decode_parcel()``. The mfde table is
    sized from *level* (``mfde_table_len``); indices 0-2 are filled from
    road/background/name when present, indices named in *ext_frames* are
    filled from their bytes, and every other index in range is the profile-
    confirmed absent sentinel ``(0xFFFFFFFF, 0)`` -- never zero-fill (target-
    disc.md's Unknown bytes policy).

    All present sub-frames (basic indices 0-2, then any *ext_frames* entries
    in ascending index order) are placed contiguously starting right after
    the mfde table, with the basic ones first. This keeps
    ``parcel.decode_parcel()``'s table-length derivation (the lowest
    in-buffer offset among indices 0-2) valid: that derivation only looks at
    indices 0-2, so at least one present basic sub-frame must sit at the
    very first post-table byte, or the decoded table length would come out
    wrong.

    Parameters
    ----------
    level:
        Map layer level (12, 10, 8, 6, 4, 2, or 0) -- determines the mfde
        table length (`DESIGN.md` section 4).
    llpid:
        ``(lat_deg, lon_deg)`` of the Lower Left Reference Parcel (header
        offset 2, `pid_t`) -- computed by the caller from the parcel's
        bounds.
    llcode:
        ``(cx, cy)`` Lower Left Ref. Parcel Location Code (header offset 10,
        each a byte 0-255) -- computed by the caller.
    road_bytes, bg_bytes, name_bytes:
        Encoded sub-frames (from ``build_road_frame_bytes`` /
        ``build_background_frame_bytes`` / ``build_name_frame_bytes``), or
        None for "not present".
    region_list:
        Encoded region-list bytes (`DESIGN.md` section 3), a multiple of 4
        bytes long. ``None`` (the default) emits what `DESIGN.md` says WP1
        emits at every level: ``nregion=0``, no region-list bytes.
    ext_frames:
        ``{index: bytes}`` for in-buffer Extended Data Frame content at mfde
        indices 3..(table length - 1). ``None``/omitted (unit 12's case)
        leaves every such index absent; WP2 fills these later.
    """
    region_list = region_list if region_list is not None else b""
    if len(region_list) % 4:
        raise ValueError(
            f"region_list must be a multiple of 4 bytes, got {len(region_list)}")
    nregion = len(region_list) // 4

    ext_frames = dict(ext_frames or {})
    mfde_len = mfde_table_len(level)
    # R census: at level >= 6 mfde[10] is a byte-identical
    # duplicate of the name sub-frame whenever a name frame is present.
    # L0-L4 keep absent (residual variant rule undecoded). Caller wins.
    if (level >= 6 and 10 <= mfde_len - 1 and 10 not in ext_frames
            and _pad_even(name_bytes) is not None):
        ext_frames[10] = _pad_even(name_bytes)
    max_ext_index = mfde_len - 1
    for idx in ext_frames:
        if not (3 <= idx <= max_ext_index):
            raise ValueError(
                f"ext_frames index {idx} out of range for level {level} "
                f"(table has {mfde_len} entries; ext indices are 3..{max_ext_index})")

    basic = [(0, _pad_even(road_bytes)), (1, _pad_even(bg_bytes)), (2, _pad_even(name_bytes))]
    ext = sorted((idx, _pad_even(b)) for idx, b in ext_frames.items())

    de_off = _MAP_FRAME_HEADER_SIZE + nregion * 4
    first_sf_offset = de_off + mfde_len * 6

    # Present sub-frames, basic (index order) first then ext (index order) --
    # see docstring for why this order matters to the decoder.
    ordered = [(i, b) for i, b in basic if b is not None]
    ordered += [(i, b) for i, b in ext if b is not None]

    slots: dict[int, tuple[int, int]] = {}   # index -> (offset, length)
    cursor = first_sf_offset
    for idx, b in ordered:
        slots[idx] = (cursor, len(b))
        cursor += len(b)

    total_size = cursor
    if total_size % 2:
        total_size += 1

    buf = bytearray(total_size)

    # 36-byte Map Frame Header (Ch.7.1.1 "Main Map Distribution Header"),
    # every field per DESIGN.md section 2's WP1-emission column:
    #   bytes 0-1:   Header Size (SWS) -- matches this buffer's total size
    #   bytes 2-4:   llpid lat as 3-byte geonum; byte 5: exp = 0
    #   bytes 6-8:   llpid lon as 3-byte geonum; byte 9: exp = 0
    #   bytes 10-11: llcode (byte 10 = cy, byte 11 = cx -- matches
    #                parcel.py's decode: llcode_cx = low byte, llcode_cy =
    #                high byte)
    #   bytes 12-13: dipid = 0x0000 (not divided) until unit 13
    #   bytes 14-17: pmcode = 0x00000000
    #   bytes 18-19: dsflag = 0x0064
    #   bytes 20-23: rlx/rly = 0x0000 (not emitted by WP1)
    #   bytes 24-27: geomagnetic strength/declination = 0x0000
    #   bytes 28-31: rg_addr = 0xFFFFFFFF (absent -- no route-guidance model)
    #   bytes 32-33: rg_size = 0x0000
    #   bytes 34-35: nregion
    buf[0:2] = _u16(total_size // 2)
    lat_lo, lon_lo = llpid
    buf[2:5] = geo_secs_bytes(lat_lo)
    buf[5] = 0
    buf[6:9] = geo_secs_bytes(lon_lo)
    buf[9] = 0
    cx, cy = llcode
    buf[10] = cy & 0xFF
    buf[11] = cx & 0xFF
    # bytes 12-17 (dipid, pmcode) already zero.
    buf[18:20] = _u16(_HEADER_DSFLAG)
    # bytes 20-27 (rlx, rly, geomagnetic) already zero.
    buf[28:32] = _u32(_HEADER_RG_ADDR_ABSENT)
    buf[32:34] = _u16(_HEADER_RG_SIZE_ABSENT)
    buf[34:36] = _u16(nregion)

    # Region list (DESIGN.md section 3).
    if region_list:
        buf[36:36 + len(region_list)] = region_list

    # mfde table.
    for i in range(mfde_len):
        eoff = de_off + i * 6
        if i in slots:
            off, size = slots[i]
            assert off % 2 == 0 and size % 2 == 0
            buf[eoff:eoff + 4] = _u32(off // 2)     # unsws: sws(v) = off
            buf[eoff + 4:eoff + 6] = _u16(size // 2)  # unsws: sws(v) = size
        else:
            buf[eoff:eoff + 4] = _u32(_ABSENT_MFDE[0])
            buf[eoff + 4:eoff + 6] = _u16(_ABSENT_MFDE[1])

    # Sub-frame content at its declared position.
    for idx, b in ordered:
        off, _size = slots[idx]
        buf[off:off + len(b)] = b

    return bytes(buf)
