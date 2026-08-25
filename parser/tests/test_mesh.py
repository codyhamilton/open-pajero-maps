"""Cross-check against the ground truth kiwiread.c already established
(see docs/phases/00-inventory.md): for the Melbourne coordinate
(-37.813629, 144.963058) at level 0, kiwiread.c (patched for the
antimeridian bug) found the *undivided top-level* parcel cell bbox
[-37.833333,144.937500] to [-37.812500,144.968750].

Post parcel-index-bug-fix (see docs/phases/01-format-analysis.md, "Parcel
iteration-order bug: ROOT CAUSE FOUND AND FIXED"), this coordinate
actually resolves one level deeper, into a divided/integrated sub-parcel
(a real, correctly-decoded Docklands-area parcel: "TELSTRA DOME",
"A=DOCKLANDS, MELBOURNE,VICTORIA") -- kiwiread.c's own debug tool doesn't
print that finer level, only the coarser top-level bbox it happened to
land its `isin()` scan on. So the fixed behaviour is checked by
*containment* within kiwiread's top-level bbox, not exact equality: the
real fine-grained parcel must nest inside the coarse one both tools agree
on, which is the only cross-check kiwiread.c's own (differently-indexed,
see the flagged discrepancy below) output can still offer.

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


def test_melbourne_bbox_nests_in_kiwiread_top_level_cell():
    if not os.path.exists(DISC):
        print("SKIP: disc not mounted")
        return
    from kiwiw.disc import AllData

    with AllData(DISC) as disc:
        parcel = disc.find_parcel(-37.813629, 144.963058, level=0)
        assert parcel is not None
        b = parcel.location.bounds
        # kiwiread.c's top-level (undivided) cell for this coordinate.
        top_lat_lo, top_lat_hi = -37.833333, -37.8125
        top_lon_lo, top_lon_hi = 144.9375, 144.96875
        assert top_lat_lo - 1e-4 <= b.lat_lo <= b.lat_hi <= top_lat_hi + 1e-4
        assert top_lon_lo - 1e-4 <= b.lon_lo <= b.lon_hi <= top_lon_hi + 1e-4
        # real data should have been decoded, not an empty parcel
        assert parcel.name is not None and len(parcel.name.records) > 0
        # real, plausible Docklands/Melbourne content -- see the writeup.
        assert any("DOCKLANDS" in r.text or "MELBOURNE" in r.text
                   for r in parcel.name.records)
    print("PASS: Melbourne parcel nests inside kiwiread.c's top-level bbox "
          "and decodes real Docklands-area content")


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

        # NOTE: despite the old name, (-33.8148, 151.0011) is not actually
        # near the Hunter Valley (that's ~100 km further north, around
        # -32.7..-32.9) -- it's in Sydney's Parramatta/Camellia/Granville
        # area. The pre-fix build of this test happened to decode "YENGO
        # NATIONAL PARK"/"POKOLBIN STATE FOREST" here, which -- given the
        # coordinate's real location -- was itself the parcel-index bug
        # manifesting, not a valid cross-check; it just weren't caught at
        # the time because there was no independent oracle yet. Post-fix,
        # this now decodes real Camellia/Granville, Sydney content, which
        # matches the coordinate's actual real-world location.
        regional = disc.find_parcel(-33.8148, 151.0011, level=0)
        assert regional is not None
        assert regional.road is not None and len(regional.road.links) > 0
        assert regional.name is not None
        assert any("SYDNEY" in r.text for r in regional.name.records)
    print("PASS: Sydney-area coordinates locate and decode real data")


if __name__ == "__main__":
    test_melbourne_bbox_nests_in_kiwiread_top_level_cell()
    test_sydney_and_regional_nsw_locate_and_decode()
