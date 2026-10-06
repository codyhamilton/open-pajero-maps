# Proven causes and proposed emission correction

All three deviations are real frame-occupancy differences. No equivalence
between a record-less indexed frame and an absent BMT is claimed. Each verdict
is presently `conflict-open`: code and offline proof are ready; the new disc,
live K1, Perth and protected-input measurements are Execute's outstanding gates.

The evidence is the committed `witnesses/{g_successor,g_historical,r,spool,summary}.json`.
Only those JSON bytes and parser source were read. The polygon bounds below
were independently decoded from retained source-record bytes, whose SHA-256s
were checked in `test_source_polygons_all_west_of_their_target_frame`.
No live spool or disc was opened.

| L0 cell | Source row | Own class-2 polygon longitude range | Names before guard | Successor shell |
| --- | ---: | --- | ---: | --- |
| (0,541) | 11689 | 77.2489619–77.8036849 | 1 | 320 bytes, leaf [928] |
| (0,562) | 13990 | 73.243665–81.8108106 | 0 | 160 bytes, leaf [1600] |
| (0,563) | 14169 | 77.0–78.25 | 0 | 160 bytes, leaf [1632] |

All input polygons lie strictly west of the cell lattice's longitude-90 lower
edge. Each own record has zero roads and one class-2/type-288 polygon; no
background was routed into any of these cells by the full Phase 1 E1 scan.
The historical edge assignment of out-of-span data explains why these own
records exist at ix=0; the name's historical clamp is established in plan 29.
The witnesses do not contain extractor provenance for each polygon, so their
precise earlier extractor assignment history is not newly asserted here.
It is the current own-row emission policy, after clipping, that causes the
observed three frame-occupancy deviations.

The exact source-to-output chain is:

1. `parser/kiwiw/descriptor.py:156`, `build`, sets existence for every spool
   cell (`bits[iy, ix] = True`, line 170) in addition to the parcel-mask
   rectangle. `parser/build_alldata.py:109`, `load_parcel_mask`, reads L0
   rectangle ix=576..2303, iy=0..2143. ix=0 is outside this rectangle: none of
   these three shells is required by mask filling. Spool existence survives
   irrespective of post-assembly record count.
2. `parser/kiwiw/_e2.c:1231`, `kw_e2`, resolves `has_own` (1272–1284) and
   admits it even outside the mask. The own data enters `kw__encode_rec`
   at 1350; `n >= 0` unconditionally yields an E2 index row at 1354–1367.
   There is no test for semantic emptiness before indexing.
3. `parser/kiwiw/_cenc.c:898`, `bg_shape`, transforms longitudes to cell
   coordinates (913), then clips through `chains` (937); `enc_bg` (1012)
   writes only emitted shapes. These disjoint class-2 polygons emit no
   record. `enc_bg`'s `n_units == 0` branch (1080) still returns the empty
   list header `0001`, length 2. `encode_common` (1264) writes the 36-byte
   header and 20 MFDEs (1304–1336), placing that empty background subframe
   at 156. It returns 158 bytes, not an absence signal. Packed logical-sector
   alignment accounts for the 160-byte indexed extent on 562/563.
4. For 541 only, `parser/kiwiw/cenc.py:113`, `E1Spool._guard_names`, drops
   the stale out-of-span O03 name through private mappings. Its old indexed
   extent is 320 bytes. `parser/build_alldata.py:325`, `_e2_job`'s name-drop
   branch, probes the original, checks equal topology and pads the filtered
   frame to that extent. The retained source polygon still clips away as
   above. Probe-and-pad explains the additional padding, not a requirement
   to retain frame occupancy. See plan 29 and the out-of-span admission
   contract. No name-drop operation applies to 562 or 563.
5. `parser/kiwiw/frame_table.py:104`, `IndexedLayout`, derives populated
   blocks from every frame index row. `parser/kiwiw/alldata_writer.py:686`,
   `build_alldata_kwi`, derives `has_bmt` from `lay.present_blocksets`.
   A record-less shell therefore allocates a real block and BMT. Its
   absence branch (728), when no other block in the blockset has frames,
   instead writes `EMPTY_BMT_OFFSET = 0xFFFFFFFF * 2`
   and `EMPTY_BMT_SIZE = 0` (480–481), serialized as raw `FFFFFFFF/00000000`.
   The R witness proves this exact absent-BMT sentinel at blockset 32,
   BSMR offset 11134, hex `0020ffffffff00000000`; the hardened reader replay
   proves all 2,048 block-0 slots absent, with no lookup failures.

None of these cells goes through division, trimming or halo reconstruction:
their historical and successor frames fit the whole-cell threshold; both
G witnesses have one top-level leaf per cell and no divided topology.
The source geometry is lost through ordinary clipping, and 541's name through
coverage admission. A generic trimming/division explanation would be false.

## Emission rule (unit 2-02; replaces 2-01's three-cell whitelist)

2-01's `_omit_witnessed_l0_shells` hard-coded `((0,541),(0,562),(0,563))`.
Execute did not accept a coordinate whitelist, and 2-02 replaced it with a
general rule. 2-02 was finished by Execute (Codex usage limit; see
IMPLEMENTATION).

**Rule.** For every level, take the parcel-mask rectangle that
`load_parcel_mask()` gives (`parser/refdata/parcel_mask.json`). Outside that
rectangle, an undivided cell (`pt = sx = sy = 0`) whose final encoded frame
is exactly the encoder's empty shell is not indexed. Inside the rectangle
nothing changes. A build with no mask (`--no-fill-mask`) also changes
nothing.

**Where it is implemented.** `parser/build_alldata.py`:

- `is_empty_shell(raw, level, ix, iy)` and `_empty_shell_header` define
  `_cenc.c encode_common`'s record-less frame for that very cell:
  - a 36-byte header with the standard metadata and the cell's `iy%256` /
    `ix%256` bytes;
  - 20 MFDEs (12 at level 12), all absent except background;
  - a background pointer to the two-byte empty list `0001`;
  - only zero bytes after that (plan 29's probe-and-pad extent).
- Any road, name or extended pointer, region list, non-empty background,
  metadata or size difference, or non-zero trailing byte keeps the frame.
- `_omit_outside_mask_shells(level, index, spill, rect)` applies the rule
  after plan 29's probe-and-pad topology comparison and after the
  declined-row check. Retained index rows and frame bytes are untouched.
- `_e2_job` receives the level's full mask rectangle, not the fixture-clipped
  one.

**R basis.**

- `load_parcel_mask`'s contract (brief 26c): inside each level's rectangle,
  R materialises a Map Frame for every cell, including empty ones. This is
  why an empty frame inside the mask must stay.
- The same contract says that outside the rectangle, R's populated cells are
  only those with content.
- Phase 1's replayed R witness shows the R behaviour at the three cells:
  blockset 32 is the absent-BMT sentinel and all 2,048 block-0 slots are
  `empty_slot`.

The rule removes exactly the frames that the cause above produces: an own
record clipped to nothing, then indexed unconditionally.

**What would falsify it.** Any R frame outside the mask whose bytes are
record-less. Execute's bounded R check (`phase2_gates.py r-check`) tests
every cell the rule removed on the real build. Through plan 29's hardened
reader, it requires each removed cell to be `empty_slot` on R `8c2d2027…`. A
`lookup_failed`, a resolved R frame, or a removed cell at a non-L0 level
(where that reader is unavailable) fails the gate. The three Phase 1 cells
must be in the removed list.

**Gates.** `phase2_gates.py diff` compares whole-frame multisets for every
cell at every level and lists every changed cell. It classifies each one as:

- `removed_outside_mask_empty_shell`: the new disc indexes nothing there,
  every old frame there is the exact shell for that cell, and the cell is
  outside its level's mask;
- `other`: anything else.

It passes only with zero `other` cells. No coordinates are fixed. Perth uses
the same classified diff against `04be2f6e…` with `--no-require-phase1`,
instead of requiring SHA equality, because Perth may legitimately contain
outside-mask shells.

**Unchanged.** E2 counters still describe the kernel's work, including
frames built before omission. FrameTable and build counts describe the
published frames. Source filtering, K1 and tolerances are unchanged.

**Contract amendment.** Execute amends
`docs/design/out-of-span-name-guard.md`:

- probe-and-pad preserves the guarded-versus-original chunk topology and
  extents as an intermediate guarantee;
- the final disc then omits outside-mask empty shells, so confinement of the
  final disc is by classified cell identity.

Removing frames changes packed offsets and index allocation, so equal sizes
and byte-range confinement are not expected. The exact serial commands are
in `phase2_commands.md`.

The synthetic layout test captures the actual writer's PDMDH in memory,
without disc writes or C encoding. With the three Phase 1 rows removed and a
retained cell in another blockset, the writer produces blockset 32's exact
absent-BMT offset/size. A second case preserves a content cell in another
block of the same blockset: its BMT remains allocated, block 0 has the
individual `FFFFFFFF/0000` no-data entry, and the other frame is unchanged.
The Phase 1 census covers block 0, not the other 31 blocks; which absence
encoding the full AU build uses depends on their occupancy. Final AU behavior
still needs the guarded measurements.

Plan-29's carried structural residual is not yet discharged. All three cells
share the clipped-own-record/unconditional-index cause, with 541 additionally
carrying pad-after-name-drop. Their next verdict can be `fix-landed` only after
Execute's successor, block census, exact cell diff, K1, Perth and protected-input
gates pass. Plan 04 Phase 3, overall DVD parity and Maps completeness remain open.
