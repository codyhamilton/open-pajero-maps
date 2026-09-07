# DESIGN — Map Frame shape, mfde/RP slot contract, ext-frame policy

Unit 06. Evidence: `parser/refdata/profile/map.json` (unit 03b, commit
`7c43efe4`) and `parser/refdata/grid.json` (unit 01), plus a short read-only
census this unit ran against the mounted reference disc
(`/run/media/codyh/464210-8480/ALLDATA.KWI`) at the seven spot-check
coordinates (`parser/refdata/spot_checks.json`) and all seven levels, to
fill header-byte gaps the profile does not census (`parser/harness/profile.py`
only tallies `nregion`, not the header's other bytes).

## 1. Scope and precedence

This file governs Map Frame shape for WP1 and the slot handoff to WP2:
what a from-scratch `synth.py`/`alldata_writer.py` build emits for the
36-byte header, region list and mfde table, and which of those bytes WP2
(route planning, Ch.9/10) later fills. `docs/design/target-disc.md` is the
stable design doc and wins on any conflict with this file. Where this
file's findings conflict with `PLAN.md`'s own refinement findings, that is
flagged here (Section 8) and in this unit's report, not resolved silently.

## 2. Map Frame header (36 bytes)

Spec: `spec/format_english/pdf/0701122e.pdf`, Ch.7.1.1 "Main Map
Distribution Header" — the table there gives every field's offset, length
and name directly; only `llpid`/`llcode`/`nregion` were previously decoded
in `parser/kiwiw/parcel.py`. The rest are decoded here for the first time,
against the spec table plus a 7-city × 7-level read-only sample (49 header
reads; not exhaustive, so "sample" confidence below is lower than
"profile").

| Offset | Len | Spec name | Observed on `R` | WP1 emission | Confidence |
|---|---|---|---|---|---|
| 0 | 2 | Header Size (SWS) | — | matches buffer size | high (already decoded) |
| 2 | 8 | Lower Left Reference Parcel ID (`llpid`, PID) | per-parcel lat/lon | computed from parcel bounds | high (already decoded) |
| 10 | 2 | Lower Left Ref. Parcel Location Code (`llcode`) | per-parcel block-relative x/y | computed | high (already decoded) |
| 12 | 2 | Divided/Integrated Parcel Identifier (`dipid`) | bits15:14 div/int/not-div flag, bit13 adjacent-info-present flag, bits9:8 division type 1..3, bits7:4/3:0 relative lat/lng or size-1. Sample: level 0/2 CBD parcels decode as `01` (Divided) type 1 pos (0,0); level 12 decodes as `11` (Not divided/integrated) | `0x0000` (not divided) until unit 13 lands | high for the bit layout (spec-confirmed + sample matches); sample too small to give the full population's split |
| 14 | 4 | Practical Management Code (`pmcode`) | sample constant `0x00000000` at every level/city sampled | `0x00000000` | medium (sample only, 49 reads, could hide rare non-zero area-number bytes) |
| 18 | 2 | Data Source Flag (`dsflag`) | sample constant `0x0064` at every level/city: bit14=0 (scale standard 1/100), bits13:0=100 → data source scale 1/10000, per spec's own worked example | `0x0064` | medium (sample only, but the constant value plus the spec's example matching to the byte is a strong signal for a single-source 2007 commercial dataset) |
| 20 | 2 | Real-length Data, X (`rlx`) | varies with level as expected for a per-LSB physical-distance field: level 0 samples ≈`0x0051`-`0x0054` (bit15=0 → 0.01 m units, ≈0.7-0.8 m/LSB); level 12 sample `0x8a02` (bit15=1 → whole metres, 2562 m/LSB) | not emitted (WP1's synth grid cell sizes are checked-in `grid.json` data, not derived per-parcel); leave `0x0000` until a per-parcel value is needed | low — plausible decode, not verified against a second, independent source |
| 22 | 2 | Real-length Data, Y (`rly`) | same pattern as `rlx`, e.g. level 0 ≈`0x0038` (0.56 m/LSB), level 12 `0x890a` (2314 m/LSB) | same as `rlx` | low, same caveat |
| 24 | 2 | Geomagnetic Strength Data | `0x0000` in every sample | `0x0000` | low (sample only; plausibly always absent on an AU disc, not confirmed) |
| 26 | 2 | Geomagnetic Declination Data | `0x0000` in every sample | `0x0000` | low, same caveat |
| 28 | 4 | Offset to Route Guidance Data Frame (`rg_addr`, DSA) | **level 0 only**: real, varying non-`0xFFFFFFFF` values in every level-0 sample (7/7 cities). **Levels ≥2**: `0xFFFFFFFF` in every sample (14/14). Spec (9): "When no actual data exists, FFFFFFFF(16) is assigned." | `0xFFFFFFFF` (absent) — WP1 has no route-guidance model | high for the absent/present split by level (spec-named field, sentinel matches spec text exactly); the real level-0 values themselves are not decoded |
| 32 | 2 | Size of Route Guidance Data Frame (`rg_size`) | pairs with `rg_addr`: nonzero at level 0, `0x0000` at levels ≥2 (spec (10): insignificant when offset is `0xFFFFFFFF`) | `0x0000` | high, same basis as `rg_addr` |
| 34 | 2 | Number of Regions for Route Planning Data (`nregion`) | see Section 3 | see Section 3 | high (profile-censused) |

**This resolves the brief's header ask with much higher confidence than
expected** because the spec table (Ch.7.1.1) turns out to name every field
directly — this was not obvious from the required reading alone (`parcel.py`'s
comment lists the field names but marks them all "undecoded"). The header's
own `rg_addr`/`rg_size` pair (offset 28-33) is the spec's actual, named
"Route Guidance Data Frame" pointer — see Section 8 for why this matters
against `PLAN.md`'s framing of mfde 12..19.

## 3. Region list

Spec: Ch.7.1.1 row 14 ("A Sequence of Route Planning Data Region Numbers")
and Ch.7.1.1 note (12): a 4-byte entry = 2-byte Level Number (bits 15:10,
range -31..31, -32=null/dummy) + 2-byte Region Number. `nregion` (row 13,
offset 34) counts how many.

Decoding `region_list_hex_hist`'s top entries against note (12)'s bit
layout: `08000000` → level field `0x0800 >> 10 = 2`; `10000000` → `4`;
`18000000` → `6`; `20000000` → `8`. These are exactly the route-planning
region-tree levels named in `docs/design/target-disc.md`'s pipeline diagram
("region tree (2/4/6/8)"). So a region-list entry is a **reference into
WP2's RP region tree**, not a Map-Frame-local structure — it is WP2's slot
by the same logic as mfde 3..19.

`nregion_hist` per level (profile): level 0 `{0: 65536, 1: 3639335}`,
level 2 `{0: 4096, 1: 227468}`, level 4 `{0: 256, 1: 14255}`, level 6 `{0:
16, 1: 923}`, level 8 `{0: 1, 1: 77}`, level 10 `{0: 9}`, level 12 `{0: 1}`.
Dominant value is 1 at levels 0-8 and 0 at levels 10/12, confirming
`PLAN.md`'s refinement finding as the *majority* case — but it is not
universal: a real, non-trivial minority of parcels (65536 at level 0 alone)
carry `nregion=0` on `R` today, with an empty region-list bytestring
(`region_list_hex_hist['']` count matches `nregion_hist['0']` exactly at
every level checked). This nuance is not in `PLAN.md`'s finding as stated;
see Section 8.

**WP1 emission: `nregion=0`, no region-list bytes.** This matches current
`synth.py` behaviour and is a legitimate value observed on `R` itself (not
fabricated), consistent with the Unknown bytes policy. **WP2 owns:**
populating `nregion=1` and the 4-byte (level, region) entry once the region
tree exists.

## 4. mfde table

Table length: `entry_count_hist` is dominant at 20 for levels 0-10 and
exactly 12 at level 12 (profile: level 12 `{"12": 1}`). This confirms
`PLAN.md`'s refinement finding exactly. Levels 0-10 also show a long tail of
21-35-entry parcels (e.g. level 0: 21..35, thousands of parcels) — these are
the divided/integrated parcels (Section 6); a non-divided parcel always has
exactly 20 (or 12 at level 12) entries; a divided parent parcel's own frame
can carry more. Entry byte size is fixed regardless of table length: 6
bytes (`u32` offset `D` + `u16` size `SWS`), per `parcel.py`'s `_read_entry`.

Per-index table (indices 0-19; level 12's table stops at 11 — see note
below). "Presence class" names match `checks/mfde.py`'s
`per_entry_index_class_hist` vocabulary (`absent` / `in_buffer` /
`out_of_buffer`).

| Index | What (Ch.7.1) | `R` presence class, all levels (profile) | WP1 emission | Owner |
|---|---|---|---|---|
| 0 | road frame (Basic Data Frame #1) | `absent` or `in_buffer` (absent when a parcel has no roads) | generated when road data exists, else absent | WP1 (already implemented) |
| 1 | background frame (Basic #2) | `in_buffer`, 100% at every level | always generated | WP1 (already implemented) |
| 2 | name frame (Basic #3) | `absent` or `in_buffer` | generated when name data exists, else absent | WP1 (already implemented) |
| 3 | Extended Data Frame slot 1 of 9 (`n_ext_map`=9, `grid.json`) | `absent`, 100%, every level | absent `(0xFFFFFFFF, 0)` | n/a — never populated on `R` |
| 4 | ext slot 2 | mostly `absent`; rare `in_buffer` **at level 0 only** (1689/3704871, 0.05%) | absent | WP1 (matches `R`'s dominant state); the rare in-buffer content is undecoded (no sub-frame kind decoder exists per `parcel.py`'s docstring) — open question |
| 5-9 | ext slots 3-7 | `absent`, 100%, every level | absent | n/a — never populated on `R` |
| 10 | ext slot 8 | mixed `absent`/`in_buffer` at every level (roughly 88-90% absent, 10-12% in-buffer) | absent | WP1 (matches dominant state); in-buffer content undecoded — open question, same as index 4 |
| 11 | ext slot 9 | `absent`, 100%, every level | absent | n/a — never populated on `R` |
| 12-19 | 8 further entries (brief's framing: "out-of-buffer route-guidance pointers"; this unit's finding: plausibly Ch.7.1 note (13) "Adjacent Parcel Address Information", 8 directions — **see Section 8, unresolved**) | mostly `out_of_buffer` at levels 0-10 (e.g. level 0 index 12: absent 6912 / out_of_buffer 3697959); **absent from the table entirely at level 12** (table length 12, no indices 12-19 at all) | absent `(0xFFFFFFFF, 0)` for every index in this group | contested — see Section 8; WP2 by `PLAN.md`'s framing, but this unit could not confirm that ownership |

None of the above is "zero-fill": every absent emission is the sentinel
`(0xFFFFFFFF, 0)` that the profile confirms is `R`'s own encoding for "not
present" (`profile["mfde"]["absent"] == [4294967295, 0]`, and per-level
`absent_values_observed` never shows any other pair).

**How the harness judges a slot's absence:** `parser/harness/checks/mfde.py`
checks (a) every generated parcel's mfde entry count is in the profile's
`entry_count_hist` (currently, only the dominant count — 20 or 12 — since
WP1 does not yet emit divided parcels); (b) every generated absent-value
pair is in the profile's `absent_values_observed` set; (c) per index, the
set of presence classes `G` uses is a subset of what the profile recorded
for that index on `R` (so emitting `absent` for an index that is
`in_buffer`-only on `R`, e.g. index 1, would fail; emitting `absent` for an
index that has *both* classes on `R`, e.g. index 4/10/12-19, passes). This
is why WP1 can safely leave indices 3-19 (and index 0/2 when no content
exists) as `absent` without failing the harness — Section 7 states which of
these WP2 is expected to later populate.

## 5. Ext frames in the Map Frame vs Ch.10.5 ext

These are two unrelated "ext" concepts and must not be conflated. The Map
Frame's own Extended Data Frame (Ch.7.1, mfde indices 3-11, `n_ext_map`=9
slots) is undecoded sub-frame content living **inside a map-layer parcel's
own buffer** — indices 4 and 10 are the only ones ever populated on `R`.
`parser/analyze_ext_frames.py`'s "ext" census is a completely different
Ch.10.5/10.5.1 structure: a per-region *Extended Route Planning Data
Frame* slot (`[12B MID][4B N][payload]`) inside WP2's own RP region frames,
owned by `route_planning.py`/`parse_region_frame`, with no relationship to
the Map Frame or its mfde table beyond sharing the word "ext" informally.

## 6. Divided/integrated parcels

Spec: Ch.7.1.1 note (3)/(3-1) for the `dipid` bit layout (Section 2 above);
`spec/format_english/pdf/0600122e.pdf` §(18)/(19)/(20) for the Level
Management Record's per-type "Number of Latitudinal/Longitudinal Divided
Parcels" fields (`grid.json`'s `n_parcels_lat`/`n_parcels_lng` arrays,
index 0=normal, 1..3=pardiv1..3), and its §"Main Map Divided Parcel
Management" for the parcel-management-record side.

`grid.json` gives the sub-grid size per type, constant across every level
checked (0, 2, 4, 6, 8, 10, 12): type 1 → `1 + n_parcels_lat[1]` =
`1+1=2` (**2×2**); type 2 → `1+3=4` (**4×4**); type 3 → `1+0=1`
(**1×1** — this is the *integrated* case: merging parcels down to one, the
opposite direction from dividing, per `dipid` bits15:14 = `10`). This
matches the brief's "2×2, 4×4, 1×1" claim exactly.

Occupancy from the profile: `parcel_count_by_type` at level 0 is
`{0: 3704819, 1: 52}` — only 52 parcels are recorded as `pardiv1` blocks at
the parcel-management-record level, vs. the header-`dipid` census in
Section 2 which found **every** level-0/2 CBD sample already `Divided`
type 1. These are different axes (block-level "does this block contain a
divided-parcel list" vs. per-parcel-frame "is this specific Map Frame
itself the product of division") and are not a contradiction: the CBD
parcels sampled are exactly the kind of high-density content the divide
rule below exists for.

**Rule WP1 applies (unit 13 implements):** divide a parcel when its
from-scratch Map Frame would exceed the profile's `mapframe_size.max` for
that level (`byte_totals_by_layer`/`levels.<n>.mapframe_size`, e.g. level 0
max = 136096 bytes, level 2 max = 129952, ..., level 12 max = 3808 — a
single value since level 12 has one parcel). **Which type to use first:**
type 1 (2×2) — the finest division that keeps sibling parcels closest to
normal size; escalate to type 2 (4×4) only if a 2×2 quadrant would still
exceed the envelope. Type 3 (1×1 integration) is not applicable to the
oversize-splitting case — it merges parcels together and is out of unit
13's scope.

## 7. Handoff to WP2

Slots WP1 leaves absent for WP2, and what WP2 must update to populate them:

| Slot | WP1 emission (absent) | WP2 fills with | Profile/harness.json keys WP2 must extend |
|---|---|---|---|
| Header `rg_addr`/`rg_size` (offset 28-33), level 0 only | `(0xFFFFFFFF, 0)` | Route Guidance Data Frame offset+size once WP2 decodes/generates that frame kind | new profile section under `levels.<n>` for the header's route-guidance pointer (none exists today — the profile only censuses `nregion`, not this field; see Section 8) |
| `nregion` / region list (Section 3) | `nregion=0`, no list bytes | `nregion=1` + 4-byte (RP-tree-level, region-number) entries | `levels.<n>.nregion_hist`, `levels.<n>.region_list_hex_hist` (already profiled; WP2's generated output is checked against these by extending `checks/mfde.py`-style logic) |
| mfde indices 12-19 | `(0xFFFFFFFF, 0)` × 8 | Contested — see Section 8. If WP2's spike confirms these are route-guidance pointers, WP2 fills them; if they turn out to be adjacent-parcel pointers, they are WP1's (unit 13's divided-parcel work is the natural owner, since adjacency is computable from the parcel grid WP1 already owns) | `levels.<n>.mfde.per_entry_index_class_hist` indices "12".."19" (already profiled) |
| mfde indices 4, 10 (rare in-buffer ext content) | `(0xFFFFFFFF, 0)` | Not clearly either WP's scope yet — undecoded sub-frame kind, format-analysis dead end per the brief's stated escape hatch ("if neither is possible ... goes to the user") | none yet |

## 8. Open format questions

1. **mfde 12-19: route-guidance pointers (PLAN.md's framing) vs. Adjacent
   Parcel Address Information (Ch.7.1.1 note (13), this unit's finding) —
   unresolved, reported per the brief's instruction not to resolve
   contradictions silently.** Evidence for the adjacency reading: (a) note
   (13) describes exactly 8 directions (upper, upper-right, right,
   lower-right, lower, lower-left, left, upper-left) matching the 8
   entries observed; (b) each entry in the "no adjacent parcels divided"
   case is `[4B DSA offset][2B BS size]` — byte-identical in shape to an
   mfde entry; (c) `3 (n_basic_map) + 9 (n_ext_map) + 8 = 20`, exactly the
   dominant entry count at levels 0-10, with **no** contribution from
   `n_basic_route`/`n_ext_route` (which the `decode_parcel` docstring
   already flagged as not accounting for the true length); (d) level 12
   (the single coarsest, neighbourless global parcel) has table length 12
   = `3+9+0` — no adjacency slots at all, which is exactly what "no
   neighbours" predicts and is hard to explain if these were route-guidance
   pointers instead. Against this: the header already has a spec-named,
   independently-confirmed Route Guidance Data Frame pointer (Section 2,
   offset 28-33) that is present at level 0 and absent elsewhere — if
   mfde 12-19 were *also* route guidance, there would be two redundant
   route-guidance pointer mechanisms in the same Map Frame, which is
   possible but unparsimonious. Observed bytes for one level-0 sample
   (Brisbane CBD, index 12): raw offset field resolves to an absolute
   sector address far outside the parcel's own buffer, consistent with
   either reading (a genuinely different parcel elsewhere, or a
   genuinely different content layer elsewhere). This unit did not
   decode a value at that sector to settle it — that decode is WP2's
   RP-placement spike or a small dedicated format-analysis pass, not
   this unit's scope. **Recommendation:** WP2's spike should check
   whether the address at mfde index 12 (say) resolves into the Ch.9/10
   RP region-frame layer or into another parcel's own Map Frame; whichever
   it is settles both this table's ownership and ends the ambiguity.

2. **`nregion=0` on `R` for a nontrivial minority of parcels (65536 at
   level 0) that is larger than the divided-parcel population** — not
   explained by Section 6's divided/integrated read. Possibly dummy/unused
   parcel slots in a block that a coarser occupancy count
   (`occupied_block_count`=1836 of `block_count`=2016 at level 0) doesn't
   fully account for (180 unoccupied blocks vs. 65536 empty parcels — not
   a clean multiple). Exact bytes: `region_list_hex_hist['']` = 65536,
   matching `nregion_hist['0']` = 65536 exactly, so at least the *pairing*
   (nregion=0 ⇒ zero-length list) is internally consistent; what those
   65536 parcels represent is not resolved here.

3. **Header offsets 12-27 (`dipid` through `geo_dec`) are decoded from a
   49-read sample (7 cities × 7 levels), not a full census.** The profile
   (`harness/profile.py`) does not currently tally any header byte besides
   `nregion`. If WP2 or a later unit needs firmer confidence than "sample"
   on `pmcode`/`dsflag`/`rlx`/`rly`/geomagnetic fields, extending the
   profile's per-parcel header census is a small, well-scoped follow-up
   (not done here — out of this unit's "profile as evidence, short
   read-only census" budget).

4. **Contradiction between this brief's Contract text and the evidence
   above:** the brief instructs grouping mfde 12-19 as "out-of-buffer
   route-guidance pointers" as a given. This unit's read of Ch.7.1.1 note
   (13) plus the entry-count arithmetic in Section 8.1 casts real doubt on
   that label. The brief's own Section 8 escape hatch ("open format
   questions ... so the user can decide or WP2 can spike") is used here
   rather than silently keeping the brief's framing or silently
   overriding it.
