"""Tests for the synthetic ALLDATA.KWI build pipeline.

Covers:
  test_pipeline_tiny    -- 2×2 tile grid with 3 road links per parcel;
                           encode → build_alldata_kwi → decode, assert fields.
  test_empty_parcel     -- a parcel with zero content produces valid frame bytes.
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

import pytest

# Make ``kiwiw`` importable without installing.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from kiwiw import alldata_writer as aw
from kiwiw import volume as _volume
from kiwiw.alldata_writer import SynthParcel, build_alldata_kwi
from kiwiw.model import (
    BoundingBox,
    MeshLocation,
    RoadLink,
    RoadNode,
)
from kiwiw.parcel import decode_parcel
from kiwiw.synth import (
    build_background_frame_bytes,
    build_map_frame_bytes,
    build_name_frame_bytes,
    build_road_frame_bytes,
    encode_road_link_bytes,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_BOUNDS = BoundingBox(lat_lo=-32.0, lat_hi=-31.5, lon_lo=115.75, lon_hi=116.25)


def _make_parcel_bounds(ix: int, iy: int, nx: int, ny: int,
                         outer: BoundingBox) -> BoundingBox:
    """Compute the cell bounds matching build_alldata_kwi's internal grid."""
    cell_lat = (outer.lat_hi - outer.lat_lo) / ny
    cell_lon = (outer.lon_hi - outer.lon_lo) / nx
    return BoundingBox(
        lat_lo=outer.lat_lo + iy * cell_lat,
        lat_hi=outer.lat_lo + (iy + 1) * cell_lat,
        lon_lo=outer.lon_lo + ix * cell_lon,
        lon_hi=outer.lon_lo + (ix + 1) * cell_lon,
    )


def _make_link(display_class: int, road_type: int,
                bounds: BoundingBox, n_nodes: int = 2) -> RoadLink:
    """Build a simple synthetic RoadLink with ``n_nodes`` evenly-spaced nodes."""
    from kiwiw.coordconv import COORD_RANGE

    step_x = int(COORD_RANGE) // (n_nodes + 1)
    step_y = int(COORD_RANGE) // (n_nodes + 1)
    nodes = []
    for k in range(n_nodes):
        xc = step_x * (k + 1)
        yc = step_y * (k + 1)
        from kiwiw.coordconv import xy_to_latlon
        lat, lon = xy_to_latlon(xc, yc, bounds)
        nodes.append(RoadNode(
            x=xc, y=yc, lat=lat, lon=lon,
            oneway=0, planned=0, tunnel=False, bridge=False,
        ))

    return RoadLink(
        display_class=display_class,
        road_type=road_type,
        altitude_flag=False,
        route_type_guidance_flag=False,
        pseudo3d_updown=0,
        route_planning_tag=False,
        link_id_flag=False,
        selected_link_flag=False,
        toll_flag=False,
        route_number_flag=False,
        infra_link_flag=False,
        link_id_number_flag=False,
        n_nodes=n_nodes,
        nodes=nodes,
        points=[(n.lat, n.lon) for n in nodes],
        raw_offset=0,
        raw_bytes=b"",
    )


def _decode_from_bytes(map_frame_bytes: bytes, bounds: BoundingBox):
    """Convenience: call decode_parcel on raw map-frame bytes."""
    loc = MeshLocation(
        level=0, parcel_type=0, blockset_index=0, block_index=0, parcel_index=0,
        bounds=bounds, sector_addr=0, size_logical_sectors=1,
    )
    return decode_parcel(loc, map_frame_bytes, n_basic_map=3, n_ext_map=0)


# ---------------------------------------------------------------------------
# test_pipeline_tiny
# ---------------------------------------------------------------------------

class TestPipelineTiny:
    """2×2 grid, 3 road links per parcel; full encode → build_alldata_kwi
    → decode → field check."""

    NX = 2
    NY = 2
    COVERAGE = _BOUNDS
    LEVEL = 0
    LINKS_PER_PARCEL = 3

    def _make_parcels(self):
        """Build SynthParcel objects for a 2×2 grid."""
        synth_parcels = []
        expected = {}   # (ix, iy) -> list[RoadLink]

        for iy in range(self.NY):
            for ix in range(self.NX):
                cell_bounds = _make_parcel_bounds(
                    ix, iy, self.NX, self.NY, self.COVERAGE
                )
                links = [
                    _make_link(display_class=j % 2,
                               road_type=j % 4,
                               bounds=cell_bounds,
                               n_nodes=2)
                    for j in range(self.LINKS_PER_PARCEL)
                ]
                road_bytes = build_road_frame_bytes(links, cell_bounds)
                frame_bytes = build_map_frame_bytes(
                    road_bytes, None, None, cell_bounds
                )
                synth_parcels.append(SynthParcel(
                    ix=ix, iy=iy,
                    bounds=cell_bounds,
                    map_frame_bytes=frame_bytes,
                ))
                expected[(ix, iy)] = links

        return synth_parcels, expected

    def test_encode_decode_direct(self):
        """Encode then decode each parcel's map frame bytes directly."""
        synth_parcels, expected_links = self._make_parcels()

        for sp in synth_parcels:
            parcel = _decode_from_bytes(sp.map_frame_bytes, sp.bounds)
            assert parcel.road is not None, \
                f"parcel ({sp.ix},{sp.iy}) has no road frame"
            decoded_links = parcel.road.links
            orig_links = expected_links[(sp.ix, sp.iy)]
            assert len(decoded_links) == len(orig_links), (
                f"parcel ({sp.ix},{sp.iy}): "
                f"encoded {len(orig_links)} links, decoded {len(decoded_links)}"
            )

            # build_road_frame_bytes groups links by display_class (sorted),
            # so the decoded order matches sorted-by-DC order, not input order.
            sorted_orig = sorted(orig_links, key=lambda lk: lk.display_class)

            for i, (dec, orig) in enumerate(zip(decoded_links, sorted_orig)):
                assert dec.display_class == orig.display_class, \
                    f"link {i}: display_class mismatch"
                assert dec.road_type == orig.road_type, \
                    f"link {i}: road_type mismatch"
                assert dec.n_nodes == orig.n_nodes, \
                    f"link {i}: n_nodes mismatch"
                assert dec.altitude_flag == orig.altitude_flag
                assert dec.toll_flag == orig.toll_flag
                assert len(dec.nodes) == len(orig.nodes)
                for j, (dn, on) in enumerate(zip(dec.nodes, orig.nodes)):
                    assert dn.x == on.x, \
                        f"link {i} node {j}: x mismatch {dn.x} != {on.x}"
                    assert dn.y == on.y, \
                        f"link {i} node {j}: y mismatch {dn.y} != {on.y}"

    def test_build_alldata_kwi_structure(self):
        """build_alldata_kwi produces bytes with correct volume/MHT/PDMDH headers."""
        synth_parcels, _expected_links = self._make_parcels()

        kwi_bytes = build_alldata_kwi(
            parcels=synth_parcels,
            coverage=self.COVERAGE,
            level=self.LEVEL,
            grid_nx=self.NX,
            grid_ny=self.NY,
        )

        assert len(kwi_bytes) > 4096, "output must be at least volume + MHT"

        # Parse volume header.
        raw_hdr = kwi_bytes[:_volume.DATAVOL_SIZE]
        hdr = _volume.parse_volume_header(raw_hdr)
        assert hdr.contents_main_map is True
        assert hdr.logical_sector_size == 32
        assert hdr.sector_size == 2048

        # Parse MHT.
        raw_mht = kwi_bytes[_volume.DATAVOL_SIZE:_volume.DATAVOL_SIZE + _volume.MHT_SIZE]
        mht = _volume.parse_management_header_table(raw_mht)
        prdm = mht.entries[0]
        assert prdm.dsa != 0, "MHT entry 0 DSA must be non-zero"

        # Parse PDMDH.
        pdmdh_off = _volume.getsector(prdm.dsa, hdr.sector_size, hdr.logical_sector_size)
        raw_pdmdh = kwi_bytes[pdmdh_off:pdmdh_off + prdm.size * hdr.logical_sector_size]
        pdmdh = _volume.parse_pdmdh_full(raw_pdmdh)

        lmr = next((l for l in pdmdh.levels if l.level == self.LEVEL), None)
        assert lmr is not None, f"No LMR for level {self.LEVEL}"
        assert lmr.grid_nx == self.NX
        assert lmr.grid_ny == self.NY

    def test_build_alldata_kwi_decode_parcels(self):
        """Parcels decoded from the assembled KWI have correct road link counts."""
        synth_parcels, _expected_links = self._make_parcels()

        kwi_bytes = build_alldata_kwi(
            parcels=synth_parcels,
            coverage=self.COVERAGE,
            level=self.LEVEL,
            grid_nx=self.NX,
            grid_ny=self.NY,
        )

        # Write to a temp file so load_region can open it with a path.
        with tempfile.NamedTemporaryFile(suffix=".KWI", delete=False) as tf:
            tf.write(kwi_bytes)
            tmp_path = tf.name

        try:
            region = aw.load_region(
                path=tmp_path,
                level=self.LEVEL,
                blockset_indices=[0],
            )
        finally:
            os.unlink(tmp_path)

        n_leaves = sum(len(b.leaves) for b in region.blocks)
        assert n_leaves == self.NX * self.NY, \
            f"expected {self.NX * self.NY} leaf parcels, got {n_leaves}"

        for block in region.blocks:
            for leaf in block.leaves:
                assert leaf.parcel.road is not None
                assert len(leaf.parcel.road.links) == self.LINKS_PER_PARCEL


# ---------------------------------------------------------------------------
# test_empty_parcel
# ---------------------------------------------------------------------------

class TestEmptyParcel:
    """A parcel with zero roads/backgrounds/names produces valid frame bytes."""

    BOUNDS = BoundingBox(lat_lo=-32.0, lat_hi=-31.9, lon_lo=115.9, lon_hi=116.0)

    def test_empty_road_frame(self):
        road_bytes = build_road_frame_bytes([], self.BOUNDS)
        assert len(road_bytes) >= 8
        # Should be parseable (minimal frame with 0 display classes).
        from kiwiw.road import decode_road_frame
        frame = decode_road_frame(road_bytes, self.BOUNDS)
        assert frame.n_display_classes == 0
        assert frame.links == []

    def test_empty_background_frame(self):
        bg_bytes = build_background_frame_bytes([], self.BOUNDS)
        assert len(bg_bytes) >= 2

    def test_empty_name_frame(self):
        name_bytes = build_name_frame_bytes([], self.BOUNDS)
        assert len(name_bytes) >= 2

    def test_empty_map_frame_parseable(self):
        """A fully-empty map frame decodes without error."""
        frame_bytes = build_map_frame_bytes(None, None, None, self.BOUNDS)
        parcel = _decode_from_bytes(frame_bytes, self.BOUNDS)
        assert parcel.road is None
        assert parcel.background is None
        assert parcel.name is None

    def test_empty_parcel_in_kwi(self):
        """build_alldata_kwi handles a single empty parcel."""
        frame_bytes = build_map_frame_bytes(None, None, None, self.BOUNDS)
        sp = SynthParcel(ix=0, iy=0, bounds=self.BOUNDS, map_frame_bytes=frame_bytes)
        coverage = self.BOUNDS
        kwi_bytes = build_alldata_kwi(
            parcels=[sp],
            coverage=coverage,
            level=0,
            grid_nx=1,
            grid_ny=1,
        )
        assert len(kwi_bytes) > 4096  # at least volume + MHT headers


# ---------------------------------------------------------------------------
# test_encode_decode_road_link_fields
# ---------------------------------------------------------------------------

class TestRoadLinkFieldSurvival:
    """Each RoadLink flag field round-trips through encode → decode."""

    BOUNDS = BoundingBox(lat_lo=-32.0, lat_hi=-31.5, lon_lo=115.75, lon_hi=116.25)

    def _roundtrip(self, **kwargs) -> RoadLink:
        defaults = dict(
            display_class=1, road_type=2,
            altitude_flag=False, route_type_guidance_flag=False,
            pseudo3d_updown=0, route_planning_tag=False,
            link_id_flag=False, selected_link_flag=False,
            toll_flag=False, route_number_flag=False,
            infra_link_flag=False, link_id_number_flag=False,
        )
        defaults.update(kwargs)
        link = _make_link(
            display_class=defaults["display_class"],
            road_type=defaults["road_type"],
            bounds=self.BOUNDS,
        )
        # Override flag fields.
        for k, v in defaults.items():
            if k not in ("display_class", "road_type"):
                setattr(link, k, v)

        road_bytes = build_road_frame_bytes([link], self.BOUNDS)
        frame_bytes = build_map_frame_bytes(road_bytes, None, None, self.BOUNDS)
        parcel = _decode_from_bytes(frame_bytes, self.BOUNDS)
        assert parcel.road is not None
        assert len(parcel.road.links) == 1
        return parcel.road.links[0]

    def test_road_type(self):
        for rt in range(8):
            dec = self._roundtrip(road_type=rt)
            assert dec.road_type == rt, f"road_type {rt}: got {dec.road_type}"

    def test_display_class(self):
        for dc in range(4):
            dec = self._roundtrip(display_class=dc)
            assert dec.display_class == dc

    def test_toll_flag(self):
        dec = self._roundtrip(toll_flag=True)
        assert dec.toll_flag is True

    def test_altitude_flag(self):
        dec = self._roundtrip(altitude_flag=True)
        assert dec.altitude_flag is True

    def test_node_coordinates(self):
        """Node x/y survive encode → decode exactly."""
        from kiwiw.coordconv import COORD_RANGE
        link = _make_link(display_class=0, road_type=0, bounds=self.BOUNDS, n_nodes=3)
        road_bytes = build_road_frame_bytes([link], self.BOUNDS)
        frame_bytes = build_map_frame_bytes(road_bytes, None, None, self.BOUNDS)
        parcel = _decode_from_bytes(frame_bytes, self.BOUNDS)
        dec_link = parcel.road.links[0]
        for j, (dn, on) in enumerate(zip(dec_link.nodes, link.nodes)):
            assert dn.x == on.x, f"node {j} x: {dn.x} != {on.x}"
            assert dn.y == on.y, f"node {j} y: {dn.y} != {on.y}"
