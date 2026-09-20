# Map-layer parity remediation — design (2026-09-20)

Status: proposed. Extends `docs/design/target-disc.md` (program of record); where this doc
and that one disagree on the items below, this doc wins once accepted. Supersedes the
"proposed declared deviations" list in `docs/plans/01-eval-harness-and-map-layer.md`
("Build record, rebuild #6"), which was measured on a pre-brief-34 build.

## 1. Why this exists

A root-cause review (six parallel read-only investigations, 2026-09-20, decoding R and the
brief-34 G directly) found that most WP1 "deviations" are not natural differences between
OSM and the 2007 source. They are processing artifacts, and the harness passed several
structural mismatches because its checks are subset-based or loosened.

**Design principle (from the user).** The only accepted deviations are *natural*: derived
from the source data (OSM lacks it, or the extract excludes it). A difference caused by how
we process the data is a defect, not a deviation. Structural differences in the source that
could harm the disc are called out and compensated, not merely measured.

## 2. Evidence status

Evidence quality is stated per item. Nothing below was validated on the head unit.

| Tag | Meaning |
|---|---|
| **M** | Measured directly on R and current G (`output/ALLDATA.KWI`, 2026-09-19 10:27). |
| **H** | Hypothesis with strong support; must be confirmed by an offline test (Section 5) before dependent work is built. |
| **U** | Unknown; the head unit's behaviour cannot be determined offline. Treated as a risk, not a fact. |

`output/report.json` predates the brief-34 build and is stale. No fresh `compare_disc.py`
verdict exists; first action of the work is to regenerate it (Section 6, R0).

## 3. Findings and design changes

### F1. Parcel-local coordinate range (H, highest risk)

- R: node coordinates span 0..4096 at L2–L8 (rural L0 0..16384; urban L0 0..4096; divided
  sub-parcels 2048/4096). G: always 0..32767 (`coordconv.COORD_RANGE = 1<<15`, documented in
  its own docstring as "not spec-confirmed").
- R's clipped links end exactly at 4096, consistent with 4096 being the true full-cell range.
- If confirmed, G is spatially 8× too spread at L2–L8, and every position-based R-vs-G
  comparison done so far is invalid (counts and statistics remain valid).

**Design.** Coordinate range becomes a per-(level, parcel) parameter drawn from an R census,
not a constant. The encoder quantises OSM geometry to the parcel's native grid.

- New census `refdata/profile/coord_scale.json`: per level, per parcel class, the observed
  coordinate maximum and its correlation with Map Frame header word 6 (F2).
- `coordconv` takes `range_for(level, parcel_class)`; a parcel's class is chosen by a
  deterministic rule from the census (e.g. urban vs sparse by content extent), recorded in
  data, not code.
- Quantisation to the coarse grid also drives F5 (thinning).

### F2. Map Frame header words (M/H)

- G writes zero where R writes real values: word 6 (`dipid`, bytes 12–13), word 7
  (0x1200 at L0/L2, 0xff00 at L4), words 9–11 (0x0064 and per-level values), `n_intersections`
  (65535 in R, 0 in G), `n_additional_data`, `route_planning_level`. `dipid` of 0x0000 is
  spec-RESERVED (bits 15:14 = 00) and is written even on G's own divided sub-cells; the
  comment at `synth.py` ~943 ("until unit 13") is stale.
- Header word 0 is the header size in R (160/166/172 B; equals first data-slot offset in
  897 of 939 sampled L6 leaves). G writes `total_size//2` (`synth.py:951`).
  `DESIGN.md` line 33 ("matches buffer size") is wrong and is corrected by this work.

**Design.** Header words are generated from a decoded model, never zero-filled (Unknown-bytes
policy in `target-disc.md`).

- Census each word against parcel class, level and division state; pin semantics where the
  spec allows, otherwise reproduce R's value for the matching class and record it as data.
- `dipid`: `11` for undivided, `01` + type + position for divided, per R.
- Word 0: header size as in R.
- Fields that belong to route planning (`n_intersections`, `route_planning_level`, ext frames
  4/10, `nregion`) remain WP2 slots but are now explicitly listed with R's census values.

### F3. Size limit is per sub-frame, not per frame (M)

Brief 34's decision ("only limit is the u16 word count, 131,070 B") is right in spirit but
applied to the wrong quantity. Because word 0 is a header size, the real u16 limits are the
mfde sub-frame sizes. R itself has whole frames up to 158,560 B (L6) and 151,712 B (L8).

**Design.** Replace the whole-frame 131,070 cap in `build_alldata` / `divide` with a
per-sub-frame cap of 131,070; remove the frame-total cap. Keep R's per-kind maxima as
*context in the report* and add a **soft advisory** (not a build limit) flagging any
sub-frame above 2× R's per-kind maximum, because per-buffer head-unit limits are unknown (U).
The L0 background sub-frame at ~5× R's maximum (130 KB vs 25.9 KB) is the known instance;
F5 is expected to remove it, and the advisory is what proves it did.

### F4. Road type / display-class vocabulary (M)

OSM highway classes are mapped by tag census, which misplaces roads relative to R's
semantics: `track` -> type 2 / dc10 (R's main arterial class), `trunk` -> rare type 10 / dc0,
`primary` -> type 7 / dc4, `service` -> type 9. Sampled effects: Longreach type 2 is 15.7 km
of tracks; Brisbane R type 2 is 41 km vs 0.8 km in G; Ipswich Rd / Logan Rd arterials land in
types 7/8/10/3/0. R's L2 is 61% type 2 / 37% type 3, and L4–L8 are >=90% type 2; G's upper
levels are populated by types 0/7/10.

**Design.**

- Re-derive `vocab/bg_type.json`'s road counterpart (`vocab/road_type.json`) from
  **name-matched cells** (same street name in R and G) rather than per-tag frequency, so the
  target is R's *semantic* class for the road, not the most common code for the tag.
- Target mapping to validate: trunk/primary -> type 2 (dc10); secondary/tertiary -> type 2 or
  3 by level; residential -> 6; track/unsealed -> 9; service -> 6 or 9; motorway stays type 0.
- Level selection (`selection.json`) for L2–L8 rebuilt with type 2 as the backbone and
  R-like density.
- Duplicate dual-carriageway geometry (G type 0: 37 km vs 5 km in R, Brisbane) is reviewed as
  part of selection: R appears to carry a single centreline for motorways at coarse levels.
- New harness check `road_vocab`: per level, distribution of (road_type, display_class)
  within a stated distance of R's (chi-square-style bound recorded in `harness.json`), plus
  spot checks for named arterials.

### F5. Geometry density and generalisation (M)

- L8 roads: G 8.0 vertices/link vs R 3.8. Snapping to R's grid, dropping duplicates, then
  Douglas-Peucker at 1 grid pixel yields 29,076 vertices vs R's 28,873.
- L8 backgrounds: 442,663 -> 86,973 coordinates by the same steps (R: 727,405).
- Urban L0 roads: 2.5× R's vertices per km, median segment 3.7–4.2 m vs 14–18 m in R.
- Every G vertex is written as a 6-byte node (`encode_road_link_bytes` writes nip=0). R
  writes ~3–4 nodes plus ~4.1 2-byte intermediate points per link.

**Design.** A generalisation stage between extraction and encoding, data-driven per level:

1. Quantise to the native grid (F1).
2. Drop consecutive duplicate vertices.
3. Douglas-Peucker with a per-level tolerance (starts at 1 pixel; recorded in
   `refdata/generalise.json`).
4. Emit endpoints and significant vertices as nodes, remaining vertices as `nip` deltas (the
   encoder already supports `nip`; it is unused).
5. Determinism contract unchanged: same PBF + config -> identical bytes.

Tolerances are calibrated against R's per-level vertex-per-link and per-km statistics, not
chosen by eye.

### F6. Background selection at L0 (M)

`selection.json`'s `background_all` admits every tagged polygon; the catch-all vocabulary
code turns buildings into shapes. Melbourne CBD: 474 shapes (in a quarter of R's leaf area)
vs 17 in R; Sydney 479 vs 31; Adelaide 1,623 vs 23. G's polygons average 14 coordinates vs
46 in R.

**Design.**

- Admit land-use / water / park / coastline classes R draws (from the R background census),
  not "everything tagged". Buildings and sub-pixel polygons (after F1 quantisation) are
  dropped by rule, recorded in data.
- Cap remains a *safety* limit, not a selection mechanism.
- The catch-all `288` rule at L0/L2 (`vocab/bg_type.json`) is replaced by an explicit mapping
  plus an `unmapped -> drop` default. Its 47.6k current G cells are audited first (are they
  land mislabelled as sea?).

### F7. Sea, ocean and outback content (M)

- Occupancy is solved (R-only cells: 0 at every level; G-only edge cells: 102 at L0). The gap
  is content: about 86% of sampled L0 cells inside R's rectangle carry content in R that G
  lacks, mostly ocean polygons (types 288/289) and sea names (SOUTHERN OCEAN, CORAL SEA,
  TASMAN SEA, ...), then outback reserves (321), rivers/lakes (291/289), highway numbers.
- Cause: OSM `natural=coastline` is a line; the pipeline never builds ocean polygons, and
  `selection.json` does not admit `place=sea|ocean` at L0/L2. **Processing artifact.**
- Foreign land (PNG, Indonesia, NZ) is absent from `australia-260824.osm.pbf`. **Natural.**

**Design.**

- Ocean polygons: derive land polygons from coastline (OSM land-polygon processing),
  complement inside R's populated rectangle, assign 289, tile through the existing
  background path. Sea cells in R are typically one 12-coordinate polygon; this is the
  expected result, not a special case.
- Admit `place=sea|ocean|bay|strait` names at L0–L8; every cell gets its region or ocean
  name (F8).
- Reserves/rivers/lakes: admit via the same class rules as F6.
- The foreign-land tail is a **declared natural deviation**, listed with its evidence.

### F8. Name records (M)

The plan's claim that R's 19M names are "address/house-number strings OSM lacks" is
**unsupported**. In a stride sample (~450k parcels, 2.73M records, scaling to R's 19.08M):

| Class | Share |
|---|---|
| Type 5 road label per link | 39.9% |
| Type 4 `1=<road>` tag | 22.9% |
| Type 4 plain (parks, buildings, water, ocean) | 16.6% |
| Type 4 `A=<locality>,<REGION>` tag | 7.0% |
| Type 6 POI/park (20% empty string) | 6.8% |
| Type 1 route shields | 5.5% |

Numeric-only strings are ~4% (nearly all shields), not addresses. 44% of sampled records
repeat a string already in the same cell (per-link and per-road-type copies). R names ~85%
of L0 cells (~3.15M) against ~5% (~187k) for G, because every R cell carries a region or
ocean name. G emits only types 5 and 6, never type 4 or 1. R's text is ~99% uppercase, no
accents; G is Title Case with non-ASCII names. G's priority (5) and display-scale (0) values
lie outside R's (0/32 and 16/24/28); the vocab check passed anyway.

**Design.** Name emission is rebuilt to R's structure, all OSM-derived:

- Per-cell region/ocean name from admin boundaries / marine polygons (lifts coverage
  toward ~85%).
- Type 4 `A=<suburb>,<REGION>` per overlapping locality; type 4 `1=<ROAD>` alongside road
  labels; per-segment type 5 labels (not per way).
- Type 1 route shields from OSM `ref`.
- Uppercase; deterministic ASCII folding of accents (encoding and glyph coverage of the
  head unit are U -> fold is the safe choice; `name_writer` encoding is audited first).
- `priority` and `display_scale_flag` assigned by name class from R's census.
- Whether the head unit requires `A=` / `1=` for search is U: audited against the address
  search chain in `docs/archive/02-roundtrip.md` before deciding those records are optional.
- Acceptance: the L0 name_count envelope stays as-is; the deviation is only accepted if a
  dry-run tally with all of the above still falls outside it, and then only for the
  remainder attributable to OSM lacking the source text.

### F9. Link flags and node bits (M)

R sets `link_id_flag` (45%), `link_id_number_flag` (100%), `selected_link_flag` (47%),
`route_planning_tag` (12.5% at L0, 100% at L2–L8), `toll_flag` (1,147 links), node
bridge/planned bits. G leaves all false or absent. `oneway` is 0 on all 29.9M R nodes:
**one-way is not in the map layer** and belongs to WP2.

**Design.** Census what each flag correlates with (class, name presence, level). Populate
bridge/tunnel/toll from OSM tags; populate `link_id_flag` / `selected_link_flag` per the
census rule. Flags whose meaning cannot be established are set as R sets them for the
matching class (U), and recorded as such rather than left zero.

### F10. Divided parcels (M)

G has 533 divided parents at L0 (532 type-2 leaves) vs R's 13 (52 type-1 leaves, no type 2);
G divides big cities 4×4 where R uses 2×2. Most is a consequence of F5/F6 density; the rest
is `divide.plan_divisions` escalating past 2×2.

**Design.** After F5/F6, re-measure; then prefer R's 2×2 division before deeper escalation
and require `dipid` (F2) to be correct on every divided leaf.

### F11. Neighbour pointers, mfde 12–19 (M)

Spec Ch.7.1.1 item 17 defines these as Adjacent Parcel Address Information (8 direction
pointers), not route guidance. They are **WP1's**, not WP2's; `DESIGN.md` §7/§8 "contested"
is resolved by this. In R, index 12 is out-of-buffer on 3,697,959 of 3,704,871 L0 parcels;
G's absent value is spec-legal but declares "no neighbours". R's 21–35-entry tables (adjacent
divided-parcel records) are never emitted.

**Design.** Compute the neighbour pointers from the grid WP1 owns; emit R-style entry counts
including divided-neighbour records. Update `DESIGN.md` ownership accordingly.

### F12. Harness weaknesses (M)

| Weakness | Fix |
|---|---|
| `mfde`/`vocab`: "G is a subset of R" passes when G is poorer than R | Add a **coverage** direction: per level/index, G must use a stated fraction of R's values, weighted by R's frequency. |
| `shape` ignores BMT table presence (R 165, G 178 passes) | Compare which blocksets have tables and the no-data pattern; G-only tables must lie in the declared G-only edge set. |
| `container` PDMDH: length-only tolerance; positional diff misaligns when table counts differ | Compare BMT tables by (level, blockset) key, not position; verify shared tables entry-for-entry. |
| BMT DSAs not monotonic in G; unverified | Add ordering check; investigate whether the head unit assumes it. |
| No check on header words / coordinate maxima | New `header_words` and `coord_scale` checks (F1, F2). |
| `spotcheck` substring match ("Pulteney" matches "Pulteney Pokies") | Whole-word / normalised equality; add a Grenfell-in-northern-cell row. |
| `pointers`: any out-of-buffer mfde index >= 3 inside the file passes | Require the target to decode as a Map Frame. |
| Envelope sub-frame rows now pass at <=131,070 | Report the 2×-R advisory (F3); per-sub-frame cap only. |
| Stale `report.json` | Report carries the ALLDATA sha256 and mtime it was computed from; refuse to compare if it differs from `manifest.json`. |

## 4. Deviation ledger after this design

| Item | Status |
|---|---|
| L12 parcel_count 3 vs 1 | Closed (one undivided cell). L12 frame 4,992 B vs R 3,808 B remains to be re-assessed after F5–F7. |
| L0 background trim, L8 name trim | Closed / expected closed by F5, F6. |
| L8 background/road trims | Expected closed by F3 + F5; re-measure. |
| Blockset coverage | Closed. G-only edge cells (13 tables, 102 L0 cells) are declared natural: OSM contains land R's rectangle excludes. |
| PDMDH length tolerance | Legitimate (tail = BMT entries, byte-verified); check strengthened (F12). |
| Adelaide oracle amendment | Legitimate; fixture strengthened. |
| L0 name_count 0.149× | Not accepted. Re-measure after F8; residual only if OSM lacks the source. |
| Foreign land (PNG, Indonesia, NZ) | **Declared natural deviation** (not in the extract). |
| Other OSM-vs-2007 currency and sparsity differences | Natural; listed with per-cell evidence when observed. |

## 5. Verification order (offline oracle only)

Per the design doc, no vehicle test until full parity; every step below is an offline byte
or structural comparison.

1. **Coordinate range (F1).** Decode R with a 4096 range and overlay against OSM at matched
   cells (Brisbane, Sydney, rural QLD, outback). Confirm road positions coincide (no 1/8
   clustering) and that clipped links terminate at the cell edge. If it fails, stop and
   re-derive before anything depends on it.
2. **Header words (F2).** Regress word 6/7/9–11 on parcel class and level; confirm rules
   predict R's values for held-out cells at >99%.
3. Regenerate G with F1–F3; confirm the census predicts R's words on G.
4. Measure per-level vertices per link/km and per-kind sub-frame maxima against R (F5, F6).
5. Road-type distribution and named-arterial spot checks (F4).
6. Name coverage and name_count tally (F8) before running a full build.
7. Full build + regenerated `compare_disc.py`; deviations ledger updated from that run only.

## 6. Work breakdown

Sequenced by dependency; each item is one brief. Full-Australia rebuilds are ~32 s
assembly now (plan 02), so the rebuild loop is cheap; extraction is the slow step.

| # | Brief | Depends on | Gate |
|---|---|---|---|
| R0 | Regenerate `compare_disc.py` on current G; add sha/mtime stamp to report (F12) | — | Fresh report committed |
| R1 | Coordinate-range census and confirmation (F1) | R0 | Verification step 1 passes, or design revised |
| R2 | Header-word census and generator; correct `DESIGN.md` line 33 and stale `synth.py` comment (F2) | R1 | Step 2 |
| R3 | Per-sub-frame size cap, 2×-R advisory (F3) | R2 | pytest; unchanged bytes where nothing exceeds |
| R4 | Generalisation stage (F5) | R1 | Step 4 |
| R5 | Road vocabulary and level selection (F4) | R4 | Step 5 |
| R6 | Background selection and vocab catch-all audit (F6) | R4 | Step 4 |
| R7 | Ocean polygons and sea/outback classes (F7) | R6 | Cell-content census vs R |
| R8 | Name structure rebuild (F8) | R2 | Step 6 |
| R9 | Link flags and node bits (F9) | R2 | Census agreement |
| R10 | Division policy and neighbour pointers (F10, F11) | R2, R4, R6 | mfde entry-count coverage |
| R11 | Harness hardening (F12) | R0 (can run in parallel with R1–R10) | Checks fail on current G where expected |
| R12 | Full rebuild, verify, update deviation ledger | all | Step 7 |

R1 is the critical gate: R2, R4, R8 and everything downstream assume its outcome. R11 and
the WP2/WP3 format spikes (ext frames `0xAF100100`/`0300` correlation, turn-restriction
resolution failure in region 178, POI vendor category census) can run in parallel with
R1–R10 because they do not consume the map layer's encoding.

## 7. Structural source differences for later work packages (from the same review)

These do not change WP1 but constrain WP2–WP5 and are recorded so they are not re-derived.

- **WP2.** OSM has 14–27× R's routing nodes; only 1 of 57,372 restriction relations
  resolved in region 178 (diagnose before accepting any yield); via-way restrictions
  skipped; road class/flags are first-pass guesses to be frozen from an R census; ext
  frames `0100` (62% of ext bytes) and `0300` are undecoded and currently omitted without
  evidence (cheap offline correlation test first); link end-points are not always
  intersections (T-junctions on interior vertices occur in R and G alike), so the graph
  builder must split at shared vertices.
- **WP3.** R address ranges are per road link with side/parity flags (about half of QLD
  streets are center-link-only); OSM has points -> snap, interpolate, derive parity, and
  validate by re-deriving R's own ranges for one area. Suburb/parent hierarchy needs
  boundary polygons; POI category codes include vendor codes absent from the spec
  (e.g. 0xCF80, ~38% of the QLD sample); the POISR decoder has known bugs to fix first.
- **WP4.** Bodies of POIDT, ITSSR, FWYSR, AGMSR/ARGSR/EMGSR, HWMAP are undecoded; NT and TAS
  have no FWYSR in R; emergency and zone data have no practical OSM source.
- **WP5.** Low risk.

## 8. Decisions for the user

1. Accept the design principle (natural-only deviations) and the ledger in Section 4.
2. Accept ASCII folding of accented names (F8), or supply the head unit's font/encoding
   coverage.
3. Accept the foreign-land tail as a declared natural deviation.
4. Accept the R1 gate: if the 4096 range fails to confirm, the design pauses for re-analysis
   rather than proceeding on the current constant.
5. Approve running R11 and the WP2/WP3 spikes in parallel with R1–R10.
