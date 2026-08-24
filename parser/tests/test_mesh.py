"""Cross-check against the ground truth kiwiread.c already established
(see docs/phases/00-inventory.md): for the Melbourne coordinate
(-37.813629, 144.963058) at level 0, kiwiread.c (patched for the
antimeridian bug) found bbox [-37.833333,144.937500] to
[-37.812500,144.968750].

Requires the real disc mounted at /run/media/codyh/464210-8480/
(ALLDATA.KWI) -- skips if not present, since this is a hardware-specific
integration check, not a unit test with fixture data.
"""
import math
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

DISC = "/run/media/codyh/464210-8480/ALLDATA.KWI"


def test_melbourne_bbox_matches_kiwiread():
    if not os.path.exists(DISC):
        print("SKIP: disc not mounted")
        return
    from kiwiw.disc import AllData

    with AllData(DISC) as disc:
        parcel = disc.find_parcel(-37.813629, 144.963058, level=0)
        assert parcel is not None
        b = parcel.location.bounds
        assert math.isclose(b.lat_lo, -37.833333, abs_tol=1e-4)
        assert math.isclose(b.lat_hi, -37.8125, abs_tol=1e-4)
        assert math.isclose(b.lon_lo, 144.9375, abs_tol=1e-4)
        assert math.isclose(b.lon_hi, 144.96875, abs_tol=1e-4)
        # real data should have been decoded, not an empty parcel
        assert parcel.name is not None and len(parcel.name.records) > 0
    print("PASS: Melbourne bbox matches kiwiread.c ground truth")


def test_sydney_and_regional_nsw_locate_and_decode():
    if not os.path.exists(DISC):
        print("SKIP: disc not mounted")
        return
    from kiwiw.disc import AllData

    with AllData(DISC) as disc:
        harbour = disc.find_parcel(-33.868820, 151.209290, level=0)
        assert harbour is not None
        assert harbour.name is not None
        assert any("SEA" in r.text or "SYDNEY" in r.text for r in harbour.name.records)

        regional = disc.find_parcel(-33.8148, 151.0011, level=0)
        assert regional is not None
        assert regional.road is not None and len(regional.road.links) > 0
    print("PASS: Sydney-area coordinates locate and decode real data")


if __name__ == "__main__":
    test_melbourne_bbox_matches_kiwiread()
    test_sydney_and_regional_nsw_locate_and_decode()
