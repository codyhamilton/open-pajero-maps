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

from .bitutils import geo_secs_bytes
from .coordconv import encode_region_coord, latlon_to_xy, COORD_RANGE
from .model import BackgroundShape, BoundingBox, NameRecord, RoadLink

_COORD_MAX = int(COORD_RANGE) - 1
_MAP_FRAME_HEADER_SIZE = 36


def _u16(v: int) -> bytes:
    if not 0 <= v <= 0xFFFF:
        raise ValueError(f"{v} does not fit in u16")
    return bytes((v >> 8, v & 0xFF))


def _u32(v: int) -> bytes:
    if not 0 <= v <= 0xFFFFFFFF:
        raise ValueError(f"{v} does not fit in u32")
    return bytes(((v >> 24) & 0xFF, (v >> 16) & 0xFF, (v >> 8) & 0xFF, v & 0xFF))


def _clamp_coord(v: int) -> int:
    return max(0, min(_COORD_MAX, v))


# ---------------------------------------------------------------------------
# Road
# ---------------------------------------------------------------------------

def encode_road_link_bytes(link: RoadLink, bounds: BoundingBox) -> bytes:
    """Encode a RoadLink to bytes from semantic fields (no raw_bytes needed).

    Produces a record parseable by ``road.decode_road_frame()``. Each node
    is encoded as a 6-byte node record; no intermediate delta points are
    emitted (nip = 0 for all nodes).
    """
    nodes = link.nodes
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
        # Use precomputed pixel coords (set by _make_road_link in osm_to_parcel_geometry).
        # If .x/.y are 0 (not set), fall back to lat/lon conversion.
        if node.x != 0 or node.y != 0:
            xc = _clamp_coord(node.x)
            yc = _clamp_coord(node.y)
        else:
            xc, yc = latlon_to_xy(node.lat, node.lon, bounds)
            xc = _clamp_coord(xc)
            yc = _clamp_coord(yc)

        nodeattr = (
            0                        # nip = 0 (no intermediate points)
            # bit 10: undecoded, 0
            | (int(node.bridge) << 11)
            | (int(node.tunnel) << 12)
            | (node.planned << 13)
            | (node.oneway << 15)
        )
        out += _u16(nodeattr)
        out += _u16(encode_region_coord(xc))
        out += _u16(encode_region_coord(yc))

    assert len(out) == total_len
    return bytes(out)


def build_road_frame_bytes(links: list[RoadLink], bounds: BoundingBox) -> bytes:
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
        dc_link_bytes[dc] = [encode_road_link_bytes(lk, bounds) for lk in dc_links[dc]]

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

def encode_background_shape_bytes(shape: BackgroundShape, bounds: BoundingBox) -> bytes:
    """Encode a BackgroundShape to bytes from semantic fields.

    Parseable by ``background.decode_background_frame()``.  Shapes with
    ``shape_class == 0`` (point) produce a 12-byte record with no coords.
    For line/polygon shapes, the first coord is encoded as sx/sy and the
    remaining coords are encoded as signed-i8 delta pairs.
    """
    if shape.shape_class == 0:
        # Point shape: 12-byte record, no coords, no deltas.
        hdr = 6  # rec_len // 2 = 12 // 2
        out = bytearray(12)
        out[0] = (hdr >> 8) & 0xFF
        out[1] = hdr & 0xFF
        out[4] = (shape.type_code >> 8) & 0xFF
        out[5] = shape.type_code & 0xFF
        return bytes(out)

    coords = shape.coords
    if not coords:
        raise ValueError(
            f"BackgroundShape (shape_class={shape.shape_class}) has no coords"
        )

    # First coordinate.
    lat0, lon0 = coords[0]
    xc0, yc0 = latlon_to_xy(lat0, lon0, bounds)
    xc0 = _clamp_coord(xc0)
    yc0 = _clamp_coord(yc0)

    # Determine mult_const exponent (bits 0:2 of addl word).
    mc = shape.mult_const if shape.mult_const >= 1 else 1
    mult_exp = 0
    mc_check = 1
    while mc_check < mc:
        mc_check <<= 1
        mult_exp += 1

    # Compute delta pairs.
    n_deltas = len(coords) - 1
    deltas: list[tuple[int, int]] = []
    xc, yc = xc0, yc0
    for lat_i, lon_i in coords[1:]:
        xc_i, yc_i = latlon_to_xy(lat_i, lon_i, bounds)
        xc_i = _clamp_coord(xc_i)
        yc_i = _clamp_coord(yc_i)
        dx = max(-128, min(127, (xc_i - xc) // mc))
        dy = max(-128, min(127, (yc_i - yc) // mc))
        deltas.append((dx, dy))
        # Accumulate with possible clamping quantization.
        xc = _clamp_coord(xc + dx * mc)
        yc = _clamp_coord(yc + dy * mc)

    rec_len = 12 + n_deltas * 2
    if rec_len % 2:
        rec_len += 1    # pad to even

    out = bytearray(rec_len)

    hdr_word = (rec_len // 2) & 0xFFF   # bits 0:11
    out[0] = (hdr_word >> 8) & 0xFF
    out[1] = hdr_word & 0xFF

    flag_word = n_deltas & 0x7FF         # bits 0:10 = ncoord
    out[2] = (flag_word >> 8) & 0xFF
    out[3] = flag_word & 0xFF

    out[4] = (shape.type_code >> 8) & 0xFF
    out[5] = shape.type_code & 0xFF

    addl = (
        (mult_exp & 0x7)
        | (int(shape.underground) << 9)
        | (int(shape.pen_up) << 10)
    )
    out[6] = (addl >> 8) & 0xFF
    out[7] = addl & 0xFF

    sx = encode_region_coord(xc0)
    sy = encode_region_coord(yc0)
    out[8]  = (sx >> 8) & 0xFF
    out[9]  = sx & 0xFF
    out[10] = (sy >> 8) & 0xFF
    out[11] = sy & 0xFF

    for i, (dx, dy) in enumerate(deltas):
        out[12 + i * 2]     = dx & 0xFF
        out[12 + i * 2 + 1] = dy & 0xFF

    return bytes(out)


def build_background_frame_bytes(
    shapes: list[BackgroundShape], bounds: BoundingBox
) -> bytes:
    """Build a complete Background Data Frame binary.

    All shapes are placed in a single "element" (one entry in the Background
    Distribution Header), grouped by ``shape_class`` (each class = one type
    unit in the element's type-unit table).  Parseable by
    ``background.decode_background_frame()``.
    """
    if not shapes:
        # Minimal empty frame: header_size_raw=1 → hlen=sws(1)=2.
        return bytes([0, 1])

    # Group by shape_class.
    class_shapes: dict[int, list[BackgroundShape]] = defaultdict(list)
    for s in shapes:
        class_shapes[s.shape_class].append(s)
    sorted_classes = sorted(class_shapes.keys())
    n_units = len(sorted_classes)

    # Encode shape records.
    class_encoded: dict[int, list[bytes]] = {}
    for sc in sorted_classes:
        class_encoded[sc] = [
            encode_background_shape_bytes(s, bounds) for s in class_shapes[sc]
        ]

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
        n_shapes = len(class_shapes[sc])
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
# ---------------------------------------------------------------------------

def encode_name_record_bytes(record: NameRecord, bounds: BoundingBox) -> bytes:
    """Encode a NameRecord of string_type=1 (Barycentric) to bytes.

    Other string types are not supported for synthetic encoding and return
    ``b""`` (skipped by ``build_name_frame_bytes``).

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
    if record.lat is not None and record.lon is not None:
        xc, yc = latlon_to_xy(record.lat, record.lon, bounds)
        xc = _clamp_coord(xc)
        yc = _clamp_coord(yc)
    else:
        xc = yc = 0
    sx = encode_region_coord(xc)
    sy = encode_region_coord(yc)

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


def build_name_frame_bytes(records: list[NameRecord], bounds: BoundingBox) -> bytes:
    """Build a complete Name Data Frame binary.

    All records are placed in a single list.  Only string_type=1
    (Barycentric) records are encoded; others are silently skipped.
    Parseable by ``name.decode_name_frame()``.
    """
    encoded = [encode_name_record_bytes(r, bounds) for r in records]
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

def build_map_frame_bytes(
    road_bytes: bytes | None,
    bg_bytes: bytes | None,
    name_bytes: bytes | None,
    bounds: BoundingBox,
) -> bytes:
    """Build a complete Map Frame binary.

    The output is parseable by ``parcel.decode_parcel()``.  Sub-frames are
    placed contiguously starting at byte 54 (= 36-byte header + 0-byte
    region list + 3 * 6-byte mfde entries).

    Parameters
    ----------
    road_bytes:
        Encoded road sub-frame (from ``build_road_frame_bytes``), or None.
    bg_bytes:
        Encoded background sub-frame (from ``build_background_frame_bytes``),
        or None.
    name_bytes:
        Encoded name sub-frame (from ``build_name_frame_bytes``), or None.
    bounds:
        Geographic bounding box of this parcel -- used only for the Map Frame
        Header's llpid lat/lon fields.
    """
    de_off = _MAP_FRAME_HEADER_SIZE          # = 36 (nregion=0 → no region list)
    n_mfde = 3                               # road, background, name
    mfde_table_size = n_mfde * 6            # 18 bytes
    first_sf_offset = de_off + mfde_table_size   # = 54

    # Ensure all sub-frames have even byte length (required for unsws).
    def _pad_even(b: bytes | None) -> bytes | None:
        if b is None or len(b) == 0:
            return None
        return b if len(b) % 2 == 0 else b + bytes(1)

    sub_frames = [_pad_even(road_bytes), _pad_even(bg_bytes), _pad_even(name_bytes)]

    # Compute sub-frame byte offsets within the map frame buffer.
    offsets: list[int | None] = []
    cursor = first_sf_offset
    for sf in sub_frames:
        if sf is not None:
            offsets.append(cursor)
            cursor += len(sf)
        else:
            offsets.append(None)

    total_size = cursor
    if total_size % 2:
        total_size += 1

    buf = bytearray(total_size)

    # 36-byte Map Frame Header (raw_bytes):
    #   bytes 0-1:  0 (undecoded)
    #   bytes 2-4:  lat_lo as 3-byte geonum
    #   byte  5:    exp = 0
    #   bytes 6-8:  lon_lo as 3-byte geonum
    #   byte  9:    exp = 0
    #   bytes 10-11: llcode = 0
    #   bytes 12-33: zeros (undecoded fields)
    #   bytes 34-35: nregion = 0
    buf[2:5] = geo_secs_bytes(bounds.lat_lo)
    buf[6:9] = geo_secs_bytes(bounds.lon_lo)
    # nregion at [34:36] = 0 (already zero)

    # mfde table (3 entries × 6 bytes, starting at de_off=36).
    for i, (sf, off) in enumerate(zip(sub_frames, offsets)):
        eoff = de_off + i * 6
        if sf is not None and off is not None:
            assert off % 2 == 0 and len(sf) % 2 == 0
            raw_off  = off       // 2   # unsws: sws(raw_off) = off
            raw_size = len(sf)   // 2   # unsws: sws(raw_size) = len(sf)
            buf[eoff:eoff + 4] = _u32(raw_off)
            buf[eoff + 4:eoff + 6] = _u16(raw_size)
        else:
            buf[eoff:eoff + 4] = _u32(0xFFFFFFFF)   # "not present" sentinel
            buf[eoff + 4:eoff + 6] = _u16(0)

    # Write sub-frames at their declared positions.
    for sf, off in zip(sub_frames, offsets):
        if sf is not None and off is not None:
            buf[off:off + len(sf)] = sf

    return bytes(buf)
