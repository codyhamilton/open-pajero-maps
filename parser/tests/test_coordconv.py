"""Tests for `kiwiw.coordconv` (Plan 03, unit 3-01):

- `range_for(level, parcel_class, division_state)` -- the frame's real
  divisor, sourced from `refdata/profile/coord_scale.json`, with the
  settled rule that any divided sub-parcel gets the parent frame's range
  (4096) regardless of that sub's smaller *observed* maximum there.
- the range-taking `xy_to_latlon` / `latlon_to_xy` / `encode_region_coord`.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from kiwiw.coordconv import encode_region_coord, latlon_to_xy, range_for, xy_to_latlon
from kiwiw.model import BoundingBox

B = BoundingBox(lat_lo=-28.0, lat_hi=-27.0, lon_lo=153.0, lon_hi=154.0)


# --------------------------------------------------------------- range_for

def test_range_for_l0_sparse_normal_is_16384():
    assert range_for(0, "sparse", "normal") == 16384


def test_range_for_l0_urban_normal_is_4096():
    assert range_for(0, "urban", "normal") == 4096


@pytest.mark.parametrize("level", [2, 4, 6, 8, 10, 12])
def test_range_for_every_other_level_full_normal_is_4096(level):
    assert range_for(level, "full", "normal") == 4096


@pytest.mark.parametrize("level", [0, 2, 4, 6, 8])
def test_range_for_pardiv1_sub0_is_4096_not_2048(level):
    # coord_scale.json's recorded "max" for pardiv1_sub0 is 2048 (the SW
    # quadrant's observed extent within the parent's 4096 frame) -- the
    # frame's real range is the parent's, 4096, never that smaller number.
    assert range_for(level, "divided", "pardiv1_sub0") == 4096


@pytest.mark.parametrize("sub", [1, 2, 3])
def test_range_for_other_pardiv1_subs_also_4096(sub):
    assert range_for(0, "divided", f"pardiv1_sub{sub}") == 4096


def test_range_for_absent_triple_raises_keyerror():
    with pytest.raises(KeyError):
        range_for(0, "urban", "pardiv1_sub0")  # urban has no divided state
    with pytest.raises(KeyError):
        range_for(999, "full", "normal")  # no such level
    with pytest.raises(KeyError):
        range_for(2, "nonsense_class", "normal")


# --------------------------------------------------------------- encode_region_coord

def test_encode_region_coord_at_range_is_region_1_value_0():
    assert encode_region_coord(4096, coord_range=4096) == (1 << 13)


def test_encode_region_coord_below_zero_raises():
    with pytest.raises(ValueError):
        encode_region_coord(-1, coord_range=4096)


def test_encode_region_coord_above_range_raises():
    with pytest.raises(ValueError):
        encode_region_coord(4097, coord_range=4096)


# --------------------------------------------------------------- round-trip / orientation

@pytest.mark.parametrize("rng", [4096, 16384])
def test_latlon_xy_round_trip_within_half_pixel(rng):
    for xc, yc in [(0, 0), (rng, rng), (rng // 2, rng // 3), (1, rng - 1)]:
        lat, lon = xy_to_latlon(xc, yc, B, coord_range=rng)
        xc2, yc2 = latlon_to_xy(lat, lon, B, coord_range=rng)
        assert abs(xc2 - xc) <= 0.5
        assert abs(yc2 - yc) <= 0.5


@pytest.mark.parametrize("rng", [4096, 16384])
def test_y_increases_northward(rng):
    lat_low, _ = xy_to_latlon(0, 0, B, coord_range=rng)
    lat_high, _ = xy_to_latlon(0, rng, B, coord_range=rng)
    assert lat_high > lat_low
