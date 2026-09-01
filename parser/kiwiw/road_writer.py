"""Road-link encoder: inverse of road.decode_road_frame() at the
individual-RoadLink level.

Uses a 'copy-and-patch' strategy: starts with raw_bytes (the verbatim
on-disc bytes captured by road.decode_road_frame()), then overwrites only
the fields that road.py decoded semantically:

  - lattr word at byte offset 14 within the record: rebuilt from the
    RoadLink attribute flags (all decoded bits), preserving bit 5 which
    road.py never decoded.
  - Node records (starting at the SWS-decoded noff offset embedded in the
    4-byte header): the nodeattr word is rebuilt from the RoadNode attribute
    flags (bits 11-15), preserving nip (bits 0-9) and the undecoded bit 10;
    sx/sy are rebuilt from RoadNode.x/RoadNode.y via encode_region_coord().

All undecoded bytes (header bytes 8-13, the 'word 4-5' bits beyond n_nodes,
the 'word 6-7' shape_len bits beyond shape_len, intermediate-point delta
pairs, and the additional/altitude/passage-regulation trailer) are taken
verbatim from raw_bytes unchanged.

Because node coordinates are re-encoded from RoadNode.x/RoadNode.y (the
exact decoded pixel coordinates, not from lat/lon) there is zero
quantization loss for node positions:
    decode_region_coord(encode_region_coord(node.x)) == node.x  (exact)
"""
from __future__ import annotations

from .bitutils import extract, sws
from .coordconv import encode_region_coord
from .model import BoundingBox, RoadLink


def encode_road_link(link: RoadLink, bounds: BoundingBox) -> bytes:
    """Re-encode a decoded RoadLink to bytes that road.decode_road_frame()
    would parse back to an equivalent RoadLink.

    Parameters
    ----------
    link:
        A RoadLink decoded by road.decode_road_frame().  Must have
        ``raw_bytes`` set (always the case for links decoded from real
        disc data).
    bounds:
        The parcel's bounding box.  Required for API completeness (a
        fully-synthetic encoder that starts from lat/lon would use it to
        encode intermediate-point deltas); the current implementation does
        not need it because it reads delta bytes from raw_bytes verbatim.

    Returns
    -------
    bytes
        A byte string the same length as link.raw_bytes that decodes to a
        RoadLink with the same semantic fields as the input (exact for all
        flag fields and node coordinates; zero quantization error for node
        lat/lon because RoadNode.x/y are used directly).
    """
    raw = link.raw_bytes
    if not raw:
        raise ValueError(
            "RoadLink.raw_bytes is empty -- encode_road_link() requires "
            "raw_bytes captured by road.decode_road_frame()"
        )

    buf = bytearray(raw)

    # ------------------------------------------------------------------
    # Re-encode lattr at byte offset 14 within the record.
    # All 16 bits except bit 5 (which road.py never decoded) are rebuilt
    # from the decoded RoadLink attribute fields.
    # ------------------------------------------------------------------
    lattr_orig = (raw[14] << 8) | raw[15]
    bit5 = (lattr_orig >> 5) & 1  # undecoded; preserve verbatim

    lattr = (
        int(link.altitude_flag)
        | (int(link.route_type_guidance_flag) << 1)
        | (link.pseudo3d_updown << 2)
        | (int(link.route_planning_tag) << 4)
        | (bit5 << 5)
        | (int(link.link_id_flag) << 6)
        | (int(link.selected_link_flag) << 7)
        | (int(link.toll_flag) << 8)
        | (int(link.route_number_flag) << 9)
        | (int(link.infra_link_flag) << 10)
        | (int(link.link_id_number_flag) << 11)
        | (link.road_type << 12)
    )
    buf[14] = (lattr >> 8) & 0xFF
    buf[15] = lattr & 0xFF

    # ------------------------------------------------------------------
    # Re-encode node records.
    # noff = SWS(bits 0:7 of the u32 header at byte 0) gives the byte
    # offset from the start of this link record to the first node record.
    # ------------------------------------------------------------------
    hdr = (raw[0] << 24) | (raw[1] << 16) | (raw[2] << 8) | raw[3]
    noff = sws(extract(hdr, 0, 7))

    node_off = noff
    for node in link.nodes:
        # nodeattr word (bytes 0-1 of this 6-byte node record):
        #   bits 0:9  = nip (number of intermediate points that follow)
        #   bit  10   = undecoded; preserve
        #   bit  11   = bridge
        #   bit  12   = tunnel
        #   bits 13:14 = planned
        #   bit  15   = oneway
        nodeattr_raw = (raw[node_off] << 8) | raw[node_off + 1]
        nip = nodeattr_raw & 0x3FF        # bits 0:9
        bit10 = (nodeattr_raw >> 10) & 1  # undecoded; preserve

        nodeattr = (
            nip
            | (bit10 << 10)
            | (int(node.bridge) << 11)
            | (int(node.tunnel) << 12)
            | (node.planned << 13)
            | (node.oneway << 15)
        )
        buf[node_off] = (nodeattr >> 8) & 0xFF
        buf[node_off + 1] = nodeattr & 0xFF

        # sx, sy (bytes 2-3 and 4-5 of this node record): re-encode from
        # RoadNode.x/RoadNode.y (already exact pixel coords, no lat/lon
        # round-trip needed).
        sx = encode_region_coord(node.x)
        sy = encode_region_coord(node.y)
        buf[node_off + 2] = (sx >> 8) & 0xFF
        buf[node_off + 3] = sx & 0xFF
        buf[node_off + 4] = (sy >> 8) & 0xFF
        buf[node_off + 5] = sy & 0xFF

        # Advance past this node record: 6 bytes header + nip * 2 for the
        # intermediate-point delta pairs (bytes preserved verbatim from raw).
        node_off += 6 + nip * 2

    return bytes(buf)
