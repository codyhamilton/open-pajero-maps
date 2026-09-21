# Map Frame header word 7 (pmcode high half): analysis on R

Scope: R (2007 reference disc, `ALLDATA.KWI`) only. Read-only analysis; scripts were run from the session scratchpad
and are not checked in. Numbers below are from full-disc walks (L0: 3,704,871 leaves; L2: 231,564 leaves).

## Result

Word 7 is exactly derivable from the road sub-frame. Facts, with the rule scored on the whole disc (the rule has
no fitted parameter, so fit and held-out are the same population; the census's sha1 split gives the same result):

| Level | Rule | Correct | Exceptions |
|---|---|---|---|
| L0 | `0x1200` iff the parcel has a road sub-frame with >=1 link, else `0xFF00` | 3,704,843 of 3,704,871 (99.99924%) | 28, all road parcels stored `0xFF00`, all with 1 link |
| L2 | `0x1200` iff any of the 16 L0 parcels inside this L2 parcel (4 x 4 in lat x lon) has a road sub-frame, else `0xFF00` | 231,548 of 231,548 undivided L2 parcels (100%); includes all 10,767 background-only `0x1200` parcels | 0 (the 16 divided L2 parcels of half size were skipped by the grid keying, not tested) |
| L4 and up | `0xFF00` | census: never 0x1200 | n/a |

The Phase 2 rule (sub-frame presence at the same level) fails at L2 because L2 road frames are generalised: an L2
parcel can have no road frame of its own (background only) while L0 parcels beneath it have roads. 10,767 of
208,923 background-only L2 parcels are in that situation, and *every one* of them has an L0 road descendant;
none of the other 198,156 background-only L2 parcels does. The joint table (L2 content x L0 descendants):

| L2 own content | L0 descendant has road | L2 word 7 |
|---|---|---|
| road or name present (22,629) | yes, all | 0x1200 (22,629) |
| background only (10,767) | yes | 0x1200 (10,767) |
| background only (163,592 + 34,560) | no | 0xFF00 (198,152; 4 more are divided) |

## Reading it against the spec (fact)

Spec ch. 7.1 (`spec/format_english/pdf/0701122e.pdf`, field 5, note 4) defines the Practical Management Code as a
u32 at header offset 14: bits 31-24 = **Area Number** (0-255, "refers to area information defined in the metafile,
such as a passage classification"); bits 23-8 = supplementary parcel information (23 = infrastructure-1 area,
22 = infrastructure-2 area, 10 = area in which data for all roads has been created, 9/8 = suburb/city flag);
bits 7-0 reserved. So word 7 (bytes 14-15) is the Area Number byte plus supplementary bits 23-16, and word 8
(bytes 16-17) carries bits 15-0 including bits 10/9/8. On R: word 8 is 0 everywhere, word 7 low byte is 0
everywhere, so only the Area Number is used. 0xFF = 255 is the "no area" value; 18 (0x12) is an area
that references a metafile entry we do not have. Inference (not verified): the metafile entry probably marks
"road-data area" (passage classification applies), consistent with the road-presence rule and with bit 10 semantics,
which R never sets.

## What was tested and rejected (fact, L2, 231,564 parcels unless stated)

- Composition at the same level: content-bearing parcels (road or name frame present) are 22,629 of 22,629
  `0x1200`; background-only parcels fail 10,767 / 208,923 (Phase 2 result reproduced).
- `wp.parcel` header words: word 8 always 0; dipid 0xE000 for all background-only parcels of both classes; word 7
  low byte always 0.
- Background type mix (background-only, 208,923): pure sea (type 288) is 137,652 of 137,652 `0xFF00`; every mix that
  includes land types is mixed: 289 alone 1,154 of 33,022 `0x1200`; 291 alone 3,509 of 9,203; 289+291 2,411 of 6,381;
  empty shape list 1,973 of 15,225; 321 alone 420 of 2,216. Shape count is not a threshold (0x1200 occurs at every
  count 0 to 12+). No sea/land distinction explains it (only "pure sea => 0xFF00", which follows from the road rule).
- Spatial: 8-neighbour majority scores 95.68% overall, 96.38% on background-only (base rate 95.1%): essentially no
  lift. Aligned coarser blocks (1-12 x 1-8 parcels) "any content in block" best gives 11,431 errors of 208,919. Chebyshev distance to
  the nearest L2 content parcel gives a smooth decay (36% at distance 1, 0.3% at 10), i.e. 0x1200 is a halo around road areas,
  not a region polygon. 0x1200 is confined to land and to the populated south-east/east/south-west; in Sydney every parcel is 0x1200.
- Route-planning `practical_mgmt_code` (0x12000000 vs 0xFF000000): 0x12 occurs only at RP level 2 (250 of 351 regions
  with data; levels 4, 6, 8 are 0xFF in all 1,513). It is not a function of RP sub-frame presence (same mask has both
  codes: `111100011` gives 219 with 0x12 and 94 with 0xFF). Overlay with map L2 parcels by centre: parcels inside a 0x12 RP
  region are 80% word 7 = 0x12 (16,790 of 21,037 in exactly-one-region cases), inside 0xFF regions 40%.
  Related in spirit (both are the Area Number, both 0x12 only on the finest routable levels) but the two regions are
  not the same sets; treat RP separately. Not derived here.
- Frame size: 0x1200 frames are larger only because they carry more content; no independent size threshold.
- Spec ch. 7.1.1: read (above). The metafile area table is not on the disc and not in the archived spec.

## Best rule and recommendation

Rule (source-derivable, no OSM-side land/sea mask needed):

```
pmcode_word7(L0 parcel)  = 0x1200 if parcel has road sub-frame with >=1 link else 0xFF00
pmcode_word7(L2 parcel)  = 0x1200 if any L0 parcel inside it has road sub-frame else 0xFF00
pmcode_word7(L>=4)       = 0xFF00
word 8 = 0, word 7 low byte = 0
```

Accuracy on R: L2 100% (231,548/231,548 tested); L0 99.99924% (28 exceptions, single-link road parcels stored 0xFF00, no
separator found in link count or shape count). Overall over both levels 99.9999%.
Because G builds L0 road frames from OSM, the rule is computed after L0 generation and needs no extra source; for L2 the
generator must look at L0 children when writing the L2 header (a two-pass or post-pass patch). The L0 exceptions are
0.0008% of road parcels and can be recorded as a documented residual (tolerance, not exemption). Recommendation:
adopt this rule as the model rule, replace the "blocked" status, and update `docs/schema/map-frame.md:35`
(word 7 = Area Number, 18 iff road data exists at L0 or below, else 255; word 8 = 0). The meaning of area 18 in the
metafile stays undocumented (spec-defined field, metafile absent).

Caveats: divided L2 parcels (16) and L0 integrated parcels (22 with cell height 0 in my grid key) were not separately
scored; the L0 population is included in the 3.70M above. The L2 test used road sub-frames at L0 as observed in R; a
generator with different L0 road coverage than R will shift word 7 accordingly, which is by design.
