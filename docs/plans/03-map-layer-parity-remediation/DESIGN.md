# Map-layer parity remediation

## Intent

User request, verbatim:

> research each deviation and explain causes, not just the measured deviation. Further, conduct an analysis of what else is different between reference and target. In principle, we want to see the only deviations be natural - meaning they are derived from the source data, not out of the way we have processed it. Even so, we should look critically at structural differences in source data and how that might lead to problems in the generated disc. Structural differences in the source are worth calling out and may require compensation. So our analysis needs to understand root causes

> produce a design  which captures these changes

> produce using the /workflow:design

(Source analysis: `FINDINGS.md`. It carries the evidence, numbers and findings F1–F12 this design cites.)

## Problem

WP1 (`docs/plans/01-eval-harness-and-map-layer.md`) was declared functionally complete pending acceptance of nine "declared deviations". A root-cause review (2026-09-20) decoded R and the current G directly and found that most of those deviations are **processing artifacts, not natural source differences**, and that the harness passed several structural mismatches because its checks are subset-based, length-only or loosened. The generated map layer differs from R in ways that could make the disc wrong or unusable in the vehicle, and the project's rule is that the vehicle test is last-mile, so these must be found and fixed offline. The differences:

- G's parcel-local coordinates span 0..32767; R's span 0..4096 (L2–L8) and 0..16384 (sparse L0) (hypothesis, strong; G may be 8× too spread).
- G writes zeros in Map Frame header words where R writes real values (`dipid`, words 7, 9–11, and others), and writes word 0 as `total_size//2` where R writes the header size.
- The size cap is applied to the whole frame at the u16 ceiling; the real u16 limit is per sub-frame.
- OSM road classes are mapped to the wrong R road types and display classes; geometry is not generalised (2.5× R's urban vertex density, every vertex a 6-byte node); L0 backgrounds admit buildings; no ocean polygons or sea names; names miss R's type-4/1 records, casing, coverage and priority values; link flags and neighbour pointers are unset.

Until these are fixed or genuinely shown natural, WP2–WP5 build on a map layer that does not match R structurally.

## Solution Shape

After this change the generated map layer is *R-native* in every structural respect the harness and the spec can establish: the same coordinate model, header words, road/display vocabulary, generalisation density, background and name structure and link/neighbour fields as R, populated from OSM. Every remaining difference from R is one of a short, evidence-backed list of **natural deviations** (source data lacks it, or the extract excludes it), and each is stated with its cause. The harness can now detect the differences that used to pass (coverage-direction vocabulary, header words, coordinate scale, BMT presence, sub-frame advisories), and its report is bound to the exact `ALLDATA.KWI` it evaluated.

The work is one linear-then-fan-out sequence: establish the truth and harden the oracle, settle the coordinate model (a hard gate), apply the native encoding, then bring content (geometry, vocabulary, backgrounds/sea, names, flags) to R's shape, then verify and close the deviation ledger. Every phase's approach is known: where the correct approach is not yet established (e.g. the coordinate model), the phase's first unit is research that resolves it to a single canonical answer; the design is not a try-multiple-and-iterate one.

### Domain: Native encoding model

- Owns: the parcel-local coordinate range per (level, parcel class); the Map Frame header word generator; the per-sub-frame size cap.
- Contract:
  - `parser/refdata/profile/coord_scale.json`: for each level and parcel class, the R-observed coordinate maximum and the deterministic rule assigning a parcel to a class; plus the mapping from Map Frame header words 6, 7, 9, 10, 11 (and word 0 = header size) to (level, parcel class, division state). Generated from R, checked in, never read from the mounted disc at build time (Grid contract in `docs/design/target-disc.md`).
  - Encoders take the coordinate range from this data, not a constant: `coordconv.range_for(level, parcel_class)` replaces `COORD_RANGE`; the C encoder receives it as a parameter, not its own constant.
  - Header words are never zero-filled: each is generated from the model or proven zero in R for that class.
  - Size cap: every sub-frame (road, background, name, …) <= 131,070 bytes (mfde u16 word count). Whole-frame size is not capped. R's per-kind maxima are reported; any sub-frame above 2× R's per-kind maximum is an **advisory** (never a build failure), and a persisting advisory becomes a ledger entry with its cause. Where nothing exceeds R's maxima, output bytes are unchanged by the cap change.
- The schema is keyed by (level, parcel class, division state) and includes urban L0 (4096) and divided sub-parcels (2048/4096). The parcel-class rule must be content-independent (a function of grid position/level/division), so Phase 5 generalisation cannot invalidate it. `range_for(level, parcel_class, division_state) -> int`; the C encoder receives the value as an argument per call.
- Header-word exemption: `n_intersections`, `route_planning_level`, `n_additional_data`, ext-frame slots and `nregion` are WP2-owned. They are the only words allowed to differ from the model in Phase 4, and are listed with R's census values in `coord_scale.json`'s header section.
- Non-goals: populating the WP2-owned words above.

### Domain: Content generalisation and selection

- Owns: what OSM content reaches each level and in what geometric form (thinning, division), the road/display-class and background-type vocabularies, and the ocean/sea construction.
- Contract:
  - `parser/refdata/generalise.json`: per-level snap grid, Douglas-Peucker tolerance (in native grid pixels), and node-vs-intermediate-point rule; calibrated so per-level vertices-per-link and per-km fall within a stated band of R's (band recorded in `harness.json`).
  - `parser/refdata/vocab/road_type.json` / `display_class.json` derived from name-matched R↔OSM cells so a road's semantic class equals R's for the same road; unmapped tags drop, never fall through to a catch-all.
  - `parser/refdata/selection.json` admits only background classes R draws (from the R background census); buildings and sub-pixel polygons (after quantisation) are dropped by rule; `background_all` and the L0/L2 catch-all `288` rule are removed.
  - Ocean: land polygons derived from `natural=coastline`, complemented inside R's populated rectangle, emitted as background type 289 through the existing background path.
  - Division prefers R's 2×2 before deeper escalation, and every divided leaf carries a correct `dipid`.
- Ocean construction also covers `place=sea|ocean|bay|strait` admission, reserves (321) and rivers/lakes (291), per F7.
- Numeric bands (vertex density, class distribution, flag prevalence, distance tolerance, name mix) are fixed **before any tuning**: Phase 1 delivers a bands section in `harness.json` with a stated derivation rule (a tolerance around R's per-level statistic, stated as a fraction) and a recorded review. Bands are never adjusted after seeing G.
- Non-goals: content OSM cannot supply (PNG, Indonesia and NZ land, absent from `australia-260824.osm.pbf`) — a declared natural deviation; per-tag frequency as a vocabulary basis.

### Domain: Names and link fields

- Owns: name record structure and text form; link flag and node bit population; mfde neighbour entries 12–19.
- Contract:
  - Every populated cell carries a region or ocean name; type 4 `A=<suburb>,<REGION>` and `1=<ROAD>` records, type 5 per-segment labels, type 1 route shields from OSM `ref`.
  - Text is ASCII-folded and uppercase (user decision); `priority` and `display_scale_flag` assigned by name class from R's census, always drawn from R's observed values.
  - Link flags (`link_id_flag`, `selected_link_flag`, `route_planning_tag`, toll/bridge/tunnel/planned bits) populated from OSM tags or from R's per-class census rule; a flag whose meaning cannot be established takes R's value for the matching class and is recorded as unverified.
  - mfde 12–19 carry adjacent-parcel pointers computed from the WP1 grid, with R-style entry counts including divided-neighbour records (spec Ch.7.1.1 item 17 assigns these to WP1; `DESIGN.md` of plan 01 §7/§8 "contested" is resolved accordingly).
- Before name work, the `name_writer` encoding and search chain are audited against the schema (F8); the L0 name_count envelope rule stays as-is. Name attribution method: on a stride sample of R strings, the fraction with no OSM counterpart is the natural-shortfall figure; the remainder is a defect.
- Flag table: `docs/schema/flags.md` lists every link flag and node bit with its R census, the OSM source (if any), its status (*known* / *unknown*), and the value G writes. An unknown flag is never accepted silently: it takes R's per-class value, is recorded in the table and the ledger as a documented deviation with a stated test to run later, and is never left undocumented.
- Ledger classes: *natural* (source lacks it) and *documented-unknown* (flag-table entry with a pending test). Nothing else is admissible, and every entry states its cause.
- Non-goals: one-way and turn restrictions (WP2; R's map-layer node oneway is 0 on all 29.9M nodes); the head unit's use of `A=`/`1=` tags for search (unknown; emitted regardless).

### Domain: Verification and deviation ledger

- Owns: `parser/harness`, `parser/refdata/harness.json`, and the deviation ledger in `docs/design/target-disc.md`.
- Contract:
  - `compare_disc.py` report carries the sha256 and mtime of the `ALLDATA.KWI` it evaluated and refuses to compare when they differ from `output/manifest.json`.
  - New checks: `header_words`, `coord_scale`, `road_vocab` (distribution and named-arterial spot checks), `name_coverage`.
  - Strengthened checks: `mfde`/`vocab` gain a coverage direction (G must use a stated share of R's values by R frequency); `shape` and `container` compare BMT tables by (level, blockset) key and check DSA ordering; `pointers` requires targets to decode as Map Frames; `spotcheck` uses whole-word equality and gains a Grenfell-in-northern-cell row; envelope sub-frame rows become "<=131,070 with 2×-R advisory".
  - Ledger: every difference from R that remains after the final build is listed with its source-data cause; anything caused by processing is a failure, not an entry.
- Non-goals: head-unit behaviour (no in-vehicle test before the full-Australia burn); the WP2+ layers.

## Architectural Implications

- **Stable docs.** `docs/schema/` is the authoritative, validated definition of the disc structure (status per row: verified / observed / spec-only / assumed / unknown); the unknowns (WP2/WP3 spikes: ext frames `0xAF100100`/`0300`, turn-restriction yield, POI vendor category codes, suburb hierarchy, undecoded WP4 families) are its `UNKNOWNS.md` index, so they are not re-derived. `docs/OVERVIEW.md` and `docs/ARCHITECTURE.md` are rewritten by the docs consolidation. `docs/design/target-disc.md` is the working program of record. `docs/design/target-disc.md` is updated in Phase 10 (deviation ledger, header word 0, mfde 12–19 ownership, size-limit semantics).
- **Corrections to recorded assumptions.** `docs/plans/01-…/DESIGN.md` line 33 says Map Frame word 0 "matches buffer size"; R shows it is the header size. Its §7/§8 treat mfde 12–19 as contested/WP2; the spec assigns them to WP1. Brief 34's premise ("the only limit is the u16 whole-frame size") is superseded by the per-sub-frame cap.
- **Plan 01.** Its nine "proposed declared deviations" are withdrawn; the ledger is regenerated in Phase 10 and plan 01 is closed out afterwards, not before.
- **Rebuild cost.** The coordinate range is baked into the spool at extraction (`spool.py` stores pixel ints; the extractor calls `latlon_to_xy` at extraction time; `_cenc.c` has its own copy of the range), so both encoders must derive pixels from lat/lon (the spool stores lat/lon, and encoders already recompute pixels when x/y is unset), which lets Phase 3 reuse the existing spool without re-extraction or re-quantise. Extraction is still needed for Phase 8 (names live in the spool); its time is measured in Phase 1. Assembly is ~32 s. Worktree copies under `.claude/worktrees/` are stale and must not be edited.
- **Determinism.** Every phase preserves byte-for-byte reproducibility for the same PBF and config (Determinism contract, `target-disc.md`).
- **Sequencing.** WP2 route-planning work assumes the native coordinate model and header words; it should not start before Phase 4 closes.

## Decisions

- **Scope (user, 2026-09-20):** this design covers WP1 map-layer remediation only. The WP2/WP3 spikes are documented as unknowns in `docs/schema/`, not designed here.
- **Coordinate-range gate (user):** hard stop. If the offline test does not confirm R's range model, the design is bounced for re-analysis; nothing downstream proceeds on the current constant.
- **Names (user):** fold to ASCII uppercase.
- **Approach flags (user):** all phases are `known`. There is one canonical approach in each case, whether or not it is known today; where information is missing, the phase begins with research that resolves it. No divergent-candidate builds.
- **Principle (user, Intent):** only natural deviations (derived from source data) are accepted; processing artifacts are defects.

### Amendment 2026-09-22 (user) — Phase 2 restart

The first Phase 2 attempt did not close (see `IMPLEMENTATION.md` "Phase 2 gate verdict", `EVIDENCE-2-03.json`, `WORD7-ANALYSIS.md`). The user amends the phase as follows; Phase 2's Outcome above is read subject to this amendment.

1. **Coordinate gate redefined (relative, plus R-only measures).** The absolute overlay match-rate thresholds (`MATCH_MIN 0.8` and siblings) are low-signal: OSM and the 14-year-old proprietary R source genuinely disagree, so an absolute match rate measures source drift as much as the coordinate model. The gate is now:
   - (a) **Relative discrimination.** For each parcel class, the assumed range beats every alternative range considered — including the 32768 negative control — by a clear, *pre-stated* relative margin.
   - (b) **R-only measures pass.** Coordinate maximum vs the class range; clipped links terminating at the cell edge; occupied fraction of the cell extent (no clustering into a sub-region).
   - Match rate against OSM is reported as a **diagnostic** with a recorded source-disagreement baseline. It is not pass/fail.
   - The margin and every threshold are stated in the tool docstring **before** the run and are not tuned after seeing results. All four named cells are evaluated.
2. **Two known bugs are fixed before the overlay is re-run.** `parser/harness/walk.py` L0 sparse frame bounds (all 16 slots are given the tile's bounds; the L0 sparse *frame* is the 4x4 tile at 16384) and the y orientation in `parser/kiwiw/coordconv.py` `xy_to_latlon` (y increases northward; the code is y-down and contradicts its own docstring). This authorises editing `coordconv.py`, which Phase 2's Surfaces listed read-only. Encoders keep byte-identical behaviour unless the fix requires otherwise; where it does, the impact is recorded for Phase 3.
3. **Word 7 (pmcode) is resolved, not blocked.** `WORD7-ANALYSIS.md` is adopted as the model rule: Area Number 18 (`0x1200`) iff road data exists at L0 (for L2, iff any L0 descendant has a road sub-frame), else 255 (`0xFF00`); L4 and above always `0xFF00`; word 8 = 0 and word 7's low byte = 0. The 28 single-link L0 misses are a recorded residual **tolerance**, not an exemption. `docs/schema/map-frame.md`'s pmcode row is updated, and the generator's need for an L2 post-pass (L2 headers read their L0 children) is recorded as Phase 4 scope. The meaning of area 18 in the metafile stays documented-unknown.
4. **Unit 2-04 runs** (schema rows and gate verdict). If the redefined gate genuinely fails, the phase does not close and the run reports `unsuccessful` with the evidence.

### Amendment 2026-09-23 (user) — grounded phase gates

The Phase 2 restart still did not close, and the post-mortem showed why: one criterion was grounded and passed cleanly, three were pooled statistical proxies against worker-picked thresholds and failed for reasons unrelated to the coordinate model. The user directs that every phase gate be re-examined on that axis. This amendment restates the Outcome of Phases 2 through 10. Phase 1 is closed and is not touched. Where an Outcome clause below conflicts with the clause of the same name in the Phases section, this amendment governs.

**Classification rule.** Every gate criterion is now labelled **grounded** or **necessarily-statistical**.

- **Grounded** means one of: a spec citation, by chapter and section; a per-record invariant whose violations are counted against a stated denominator, passing at zero violations or at an enumerated residual explained record by record; or a byte-exact, round-trip or closed-form identity.
- **Necessarily-statistical** means no better ground truth exists. Such a criterion must state its denominator, must derive its band from a measured baseline rather than a chosen number, and must appear in the tool docstring before the run. A worker may never pick a threshold mid-phase.

**Retirement rule.** Where the research below found a grounded measure underneath a fuzzy one, the fuzzy one is retired rather than retuned. A pooled similarity score whose failure mode is a property of the data's density, not of the hypothesis under test, cannot be rescued by moving its threshold.

**Provenance.** Six read-only research units ran on 2026-09-23 against R and the archived spec. Their censuses live in the session scratchpad and are not checked in; each criterion below names its sample size, and no criterion is load-bearing until the check that asserts it is committed under `parser/`.

**Evidence status — applies to every criterion below, not only Phase 2.** Except where a criterion cites a file already in the repo (`EVIDENCE-2-08.json`, `parser/refdata/profile/coord_scale.json`, `WORD7-ANALYSIS.md`) or a spec chapter, every "zero violations over N records" figure in this amendment comes from a scratchpad census that no one can re-run from the repo today. Those figures state what the grounded invariant *is* and what R was measured to do; they do **not** state that a gate passes. A phase closes only when the check asserting its invariant is committed under `parser/` and re-run. Read every Phase 4 through 9 figure below with that qualifier attached.

#### Phase 2 — Outcome, as amended

Grounded, all pass/fail with no thresholds:

1. **Coordinate maximum vs class range.** No parcel holds a coordinate exceeding its class range. Spec 7.2.2.1.1.2 (road) and 7.3.2.2.1.1 (background): the u16 is bits 12:0 coordinate value and bits 15:13 relative position; a basic parcel is 4096 x 4096 and an integrated parcel up to 4096 x 8 = 32768. Per-parcel violation count. The denominator is the full-disc census in `parser/refdata/profile/coord_scale.json`, produced by the committed `parser/tools/coord_scale_census.py`: 28 (level, class, division) classes, 452,199 content-bearing parcels of R's 3,951,973, `exceeds_max` zero in every class. `EVIDENCE-2-08.json` `gate.b_coord_max_over_range` restates the same invariant over the overlay's 12-cell pools and is **not** the basis for this criterion — the earlier framing of that pooled figure as class-wide was wrong, and the disc-wide census is cited in its place.
2. **Cross-parcel continuity — replaces `a_relative_discrimination`.** A road link crossing a parcel boundary is stored independently on both sides. Decoded under the assumed range and frame, the two copies of the shared endpoint must land on the same place. Per matched pair; denominator all boundary-adjacent endpoint pairs at a shared edge. Measured on R with no OSM: median separation 0.0 m at L2 (n=300), L4 (304), L6 (300), L8 (33), L0 urban (313) and L0 sparse (303, tile frame at 16384). Every alternative — half range, double range, and the 32768 negative control — gives a median separation between 1,370 m and 593,000 m with essentially every pair over 1 km. For `divided_pardiv1` the parent-4096 model yields 3,425 matched pairs across 13 groups (median 122 m, max 349 m, none over 1 km) while both renormalised alternatives find **no edge nodes at all** at their own predicted edge.

   Two limits stated rather than glossed. First, the check tests (range, frame origin, frame extent) as a bundle, not range alone: a wrong range paired with a compensating frame would still place the two copies together, and the alternatives measured are the ones someone thought to name — half, double, 32768, and the two divided renormalisations — not an exhaustive hypothesis class. It falsifies the specific rivals that were live, which is what the gate needs, and it should not be described as isolating the range constant. Second, edge-node *selection* uses a tolerance expressed as a fraction of the range under test, so a wrong range would feed the check a different input set. At the full-leaf classes the medians are 0.0 m and the rivals are three to five orders out, so the selection effect cannot account for the result. At `divided_pardiv1` the 122 m median sits inside exactly that tolerance, so **criterion 2's divided result is provisional** until it is re-measured at a tolerance fixed in absolute raw units rather than as a percentage of range. The divided class rests meanwhile on criterion 3, which is spec-cited and tolerance-free.
3. **Divided sub-parcel containment — replaces `b_axis_coverage` for that class.** Spec 7.2.2.1.1.2 (2) and (3): "For a divided parcel: The normalized coordinate in the original basic parcel is used (Each relative position in the integrated parcel is set to 0). However, the range of the X-axis coordinate may be restricted depending on the parcel divided." Every shape point of sub-parcel k (0 = SW, 1 = SE, 2 = NW, 3 = NE) therefore lies inside quadrant k of the parent leaf's 4096 frame. Per-point violation count, zero permitted. Measured 52 sub-parcels, 77,207 shape points, zero outside their quadrant. This also disposes of the 0.5625 axis-coverage "failure": 9/16 is the geometric ceiling for a correctly decoded sub-quadrant, 8/16 for sub 3. The 0.75 threshold is retired for divided parcels; `axis_coverage` stands unchanged for the full-leaf classes, which already reach 1.0.
4. **Boundary-node mirror — replaces `b_clip_exact_share`.** A link end-node whose raw coordinate is exactly 0 or exactly the class range is a genuine boundary crossing: the adjacent parcel holds an end-node at the mirrored coordinate, crossed axis = range - value, other axis unchanged. Per-node violation count; denominator all exact-coordinate nodes with a resolvable neighbour, with nodes at the extract's outer edge excluded from the denominator rather than failed. Measured L6 316/316 and L8 64/64 matched to 0 raw units. The pooled share is retired, not retuned: its premise — near an edge implies should be exact — is false. Non-exact near-edge nodes matched a neighbour only 64 times in 240, because at L6 and L8 R carries only motorway, trunk and primary, so most near-edge endpoints are ordinary dead ends. The crossing-to-dead-end ratio is a property of road density per level, so no threshold on this measure can separate a right model from a wrong one. Related spec mechanism: 7.2.2.1.1.3, the on-boundary node flag, which states that identical node information is held in neighbouring parcels.
5. **Header-word rules agree exactly.** Words 0, 6, 7, 9, 10 and 11 are predicted on every R parcel. The criterion is exact agreement with every disagreement enumerated and individually explained — not "at least 99%", which was an arbitrary bar over rules that are closed-form or table-exact. Measured: word 0 exact with its 42 exceptions explained (L6 `nregion`=1 leaves with 21/22/23 mfde entries bordering divided parcels); word 6 exact; word 7 3,704,843 of 3,704,871 at L0 with the 28 single-link residual named in `WORD7-ANALYSIS.md` and exact at L2 and above; word 9 exact; words 10 and 11 miss only on table keys never seen, never on a wrong value.

Diagnostic, not pass/fail: the OSM overlay match rate, reported with its recorded source-disagreement baseline. Amendment 2026-09-22 demoted the absolute match rate; this amendment demotes relative discrimination against OSM as well, on the evidence that it measures source drift — at Brisbane CBD and Sydney the 32768 negative control outscored the correct range — and that criterion 2 settles the same question inside R.

Carried into the re-run: the `divided_pardiv1` continuity median of 122 m is most likely the edge-selection tolerance, 6 % of range, admitting nodes that are near but not on the boundary; an absolute-unit tolerance is to be used when the check is implemented. The mirror invariant was tested only on same-block neighbours, so block- and blockset-crossing neighbour lookup must exist before it is load-bearing.

Disposition of the 2026-09-22 clause **"no clustering, measured as the occupied fraction of the cell extent"**: retired, not carried. For divided sub-parcels its ceiling is geometric (criterion 3), so the measure tested the quadrant model, not clustering. For full-leaf classes it already reaches 1.0 and so discriminates nothing. Where it was meant to catch a decode that collapses content into a corner, criterion 2 catches the same failure directly and two-sidedly.

#### Phase 3 — Outcome, as amended

Grounded: `range_for` feeds both encoders and no `COORD_RANGE` constant remains (a source check, not a judgement); the `coord_scale` check PASSES; two builds are byte-identical at worker counts 1, 4 and 12; `pytest parser/tests` passes. The first clause is tightened: "coordinate maxima equal `coord_scale.json`" is content-dependent — a sparse cell legitimately never reaches its maximum — and is replaced by **zero parcels exceeding their class range**, the same invariant Phase 2 uses, plus a **per-vertex quantisation round-trip**: lat/lon to pixel to lat/lon agrees within half a pixel for every vertex written.

#### Phase 4 — Outcome, as amended

Grounded: header words 0, 6, 7, 9 to 11 match the model on every parcel except the WP2 exemption list and the Phase 2 explained exceptions; `dipid` is valid on divided and undivided parcels; the `header_words` check PASSES; output bytes are unchanged where no sub-frame exceeds R's maxima; the stale comment at `synth.py` ~942 is corrected; builds are reproducible.

The size cap stops being a guess. Spec 7.1.2, remark 2 on the Basic and Extended Data Frame Management Record: "This field describes the size of a data frame. When the data frame contains no actual data, 0000(16) is assigned to this field." The absent-entry sentinel for the mfde SWS word is 0x0000, not 0xFFFF — sentinel choice is per field in this format, and 7.2 shows both conventions in adjacent tables. So the u16 encodes its full range and **the per-sub-frame ceiling is 131,070 bytes**, not 131,068. Corroborated by a disc-wide census of 3,951,973 leaves: no present entry carries SWS 0xFFFF, no present entry carries SWS 0, no D-absent entry carries a non-zero SWS. R's largest observed SWS is 62,476, so R does not probe the boundary itself; the citation carries the decision and the census shows no contradiction.

New grounded criterion, from a defect this research exposed: **the multilink shape-information-size word (road record offset 6, bits 11:0) equals the byte length of the node records plus their intermediate points**, on 10,063,962 of 10,063,962 links disc-wide with zero mismatches. Spec 7.2.2.1.1 item 2 classifies the parent field mandatory and 7.2.2.1.1.1 item 3-1 gives the size range 1 to 4095 with no zero-means-absent exception. **G writes 0 there.** That is a conformance defect against a now full-disc-verified invariant, and Phase 4 closes only when G writes the true value.

Design gap resolved here rather than carried: `rg_size` (word 16) is non-zero on real L0 route-guidance parcels but is absent from the header-word exemption list this phase checks against. Phase 4 adds it to the exemption list explicitly, with its R census recorded, before the `header_words` check is allowed to pass.

#### Phase 5 — Outcome, as amended

Grounded:

- **Every intermediate-point delta is representable.** Spec 7.2.2.1.1.2, remarks 4-1 and 4-2: "This field describes the offset from the X-axis [Y-axis] coordinate of the previous shape point to the X-axis [Y-axis] of the target shape point. The allowable range is between -128 and 127. Shape points are nodes or intermediate points." A generator must insert a node wherever a post-quantisation delta would exceed that range; zero violations.
- **No type-2 divisions.** R uses 2x2 division exclusively: 0 of 3,951,973 parcels use type 2, at any level. Zero-violation criterion.
- Intermediate points are written as `nip` deltas by both encoders, with C and Python byte-identical.

Necessarily-statistical, with their bands now derived rather than picked:

- **Per-level vertices per link and per km.** No spec answer exists for how many vertices a road should have. The band stays, but is stated against R's full-disc per-level node-per-link and nip-per-node distributions, with the denominator named, rather than against a single ratio. The snap-grid hypothesis was tested and rejected: coordinate divisibility by 2^k decays at roughly the 50-%-per-doubling rate of uniform low-order bits at every level (L8 divisible-by-4 is 0.270, not near 1.0), so there is no coarse fixed grid at higher levels to convert this into a quantisation invariant.
- **Degenerate deltas.** "G emits zero zero-length segments" was a candidate hard invariant and is falsified: R emits (0,0) intermediate-point deltas at every level — L8 0.785 % of 3,567, L6 2.361 % of 25,797, L4 1.747 % of 174,793, L2 2.415 % of 755,448, L0 0.000154 % of 159,511,522. The criterion becomes a per-level pass fraction of non-degenerate intermediate points against those measured rates, not a zero-tolerance check. The four-order-of-magnitude L0 asymmetry is observed and unexplained; it is recorded, not rationalised.

Kept unchanged: the advisory ledger entry for any sub-frame exceeding 2x R's per-kind maximum. It is advisory in the original Outcome and stays advisory — an enumeration with a stated comparand, not a gate.

Removed as unprovable: **"divided-parent counts fall toward R's."** Neither ch.6 nor ch.7.1 states a numeric division trigger — ch.6.1.1 defines only the counting and addressing of parcels already divided — and the obvious hypothesis is falsified by counterexample: an L4 divided parent's four children sum to about 5,988 bytes of content while an undivided L4 parcel of about 118,456 bytes exists on the same disc. R's 42 divided parents (13 at L0, 4 at L2, 13 at L4, 7 at L6, 5 at L8) cannot be reproduced from any size rule now known. Phase 5 therefore gates only on the type-1-only invariant and on the per-sub-frame ceiling from Phase 4; **why** R divides a given parcel is recorded as a documented unknown with a first test, not as a target count. A per-sub-frame-specific size hypothesis — would any individual road, background or name sub-frame have exceeded 131,070 bytes undivided — was not tested and is the named next step.

#### Phase 6 — Outcome, as amended

Grounded, and two of them are shipping defects this research exposed:

- **Display-scale flags.** Spec 7.3.2.2.1 defines background record +2 bits 15:11 as display-scale flags 1 to 5, with all-zero meaning never displayed. The value is an exact function of (level, type code) with zero exceptions over 7,080,921 shapes: L0 0x1C for all nine type codes; L2 0x18 for 288/289/290/291/321/578 and 0x10 for 322/640/1024 (599 of 599 instances, exactly the element-5 codes); L4, L6, L8 and L10 0x18; L12 0x10. **G writes 0** (`synth.py` sets the flag word to the delta count masked to 11 bits), so every background shape G emits is, by the spec's own definition, never drawn. Zero-violation criterion against a censused table.
- **Element placement.** Element index is an exact function of (type code, shape class) across all seven levels with no counterexample in 7,080,921 shapes: (289,area)→7, (289,line)→8, (291,area)→7, (291,line)→8, (290,area)→7, (290,line)→8, (288,area)→7, (321,area)→2, (578,line)→9, (1024,area)→5, (640,area)→5, (322,area)→5, and at L10/L12 (306,line)→4 and (528,line)→19. **G groups everything by shape class into a single element.** Zero-violation criterion; this replaces the eight-point sample that was all the schema had.
- **Polygon closure.** Spec 7.3.2.2.1.1.1 requires the delta sums to vanish. Measured 0 failures in 4,391,246 area records. Zero-violation criterion.
- **Multiplication constant.** n is confined to 0 through 6 in 7,080,921 shapes; n = 7 never occurs. Membership criterion.
- **Land mislabelled as sea = 0**, and the 102 G-only L0 cells enumerated with lat/lon and content and each classified. These are counts and enumerations, not thresholds, and stand as written.

Necessarily-statistical: the per-level background type and count distribution, and the L0 CBD shape counts against R's 17/31/23/122. These are genuine distribution judgements; their band comes from the Phase 1 bands section and their denominator is stated.

Dropped: **polygon winding.** Spec 7.3.2.2.1.1.1 calls for counterclockwise, but R itself does not comply — signed area is genuinely mixed at every level, for example L8 with 7,390 CCW, 4,502 CW and 628 degenerate of 12,520. A rule R breaks cannot gate G. Recorded as a spec/R conflict in the schema, with R's observation winning, and not used as a criterion at all.

#### Phase 7 — Outcome, as amended

Grounded:

- **`display_class = f(road_type)`**, per record. The schema carried this on histogram-sum agreement, which two different mappings can satisfy. It is now a per-record full-disc census: 10,063,962 of 10,063,962 links, zero violations, every road type mapping to exactly one display class at every level. This converts the largest part of Phase 7 from a judgement into an invariant G satisfies by construction.
- **Per-level value-set membership and level confinement.** Display class sets: L0 {0,2,3,4,7,9,10,12}, L2 {0,4,9,10,12}, L4–L8 {0,4,10,12}, L10/L12 empty. Road types {0,2,7,10} appear at every road-bearing level; {3} only at L0 and L2; {5,6,8,9,12} only at L0; {1,4,11,13,14,15} never appear anywhere. Emitting a value outside its level's set, or a level-confined code above its level, is a violation. This generalises "tracks are not in R's arterial class" and "no type 9 above L0" into one membership rule. Reserved road-type codes 14 and 15 are never emitted, 0 of 10,063,962 — spec ch.32.2.
- The named-arterial fixtures (Ipswich Rd, Logan Rd, Bradfield Hwy, Pacific Motorway, Cahill Expressway) are exact per-row pass/fail, retained as a deterministic spot check rather than the primary gate.
- Spec ch.32.1's stated drawing-order property — "class codes 15 to 3 are set in the order in which they are to be drawn" — is a spec-grounded ordering constraint on display class, independent of the labelling dispute, and is asserted as such.

Necessarily-statistical, with its band now derived: **G and R assign the same road type to the same named road.** The threshold is set against R's own internal name-matched self-consistency ceiling, measured this session: L2 9.64 % inconsistent (126 of 1,307 multi-matched names, from 4,000 parcels and 9,795 matches), L0 6.21 % (46 of 741, from 3,000 parcels and 67,716 matches). The threshold is set **per level**, not pooled: at L0, at most 1 - 0.0621 = 0.9379 agreement may be demanded; at L2, at most 1 - 0.0964 = 0.9036. Levels above L2 have no measured ceiling yet and may not carry a name-matched agreement gate until one is measured. This is the "record the source-disagreement baseline" discipline of Amendment 2026-09-22 applied to Phase 7.

Recorded as a spec/R conflict, not a criterion: ch.32.1 marks display classes 9 and 10 reserved, yet R uses both heavily (370,408 and 848,884 links at L0). "Reserved codes are never emitted" therefore holds for road type and is false for display class; both facts go in the schema.

Left open and named as such: **why R promotes a given road above L0.** The route-planning tag is 100 % at L2–L8 and 12.5 % at L0 — a hard descriptive fact about R — but no generative rule recoverable from the disc explains the selection. Phase 7 continues to rely on the calibrated `selection.json` for this and does not claim a deterministic gate over it.

#### Phase 8 — Outcome, as amended

Grounded:

- **Name-offset pointers resolve.** Spec 7.3.2.2.1 item 5. Every background record with the name flag set (+6 bit 12) carries a 2-byte offset resolving to a real name record in the same parcel's name sub-frame: 2,258,249 of 2,258,249 at L0, zero dangling; never set at L2 and above. Zero-violation pointer invariant, far stronger than a proportions band.
- **`priority` and `display_scale_flag` membership.** Exact per-level sets with zero exceptions in 16,378,969 name records: priority {0,32} at L0 and {32} everywhere else; display scale flag L12 {16}, L10 {24}, L2–L8 {16,24}, L0 {0,24,28}.
- **Uppercase ASCII.** Zero lowercase or non-ASCII characters in 16,378,969 records, superseding the earlier 1,237-record sample that suggested about 1 % were not. Zero-violation criterion for the decoded string types.
- The L0 `name_count` dry-run tally against R's 19.08M with the shortfall attributed record by record — an attribution exercise with a stated denominator, not a threshold.

Corrected, because the old clause was false: **"every populated cell carries a region or ocean name" is an L0 phenomenon, not a cross-level invariant.** Measured per-level coverage of background-bearing cells that also hold at least one name record: L0 87.8 % (2,005,892 of 2,283,527), L2 5.45 % (12,619 of 231,564), L4 8.67 % (1,258 of 14,511), L6 22.2 % (208 of 939), L8 48.7 % (38 of 78), L10 33.3 % (3 of 9), L12 1 of 1. The criterion becomes per-level coverage against R's own per-level figure, which is a measured baseline rather than a blanket target.

Necessarily-statistical: the string-type 4/5/6/1 proportions against R's per-level mix, band from the Phase 1 bands section, denominator stated.

#### Phase 9 — Outcome, as amended

The old "prevalence per level within the band of R's" is replaced. Most of these flags are not distributions at all once split by level.

Grounded:

- **Disc-wide constants**, zero exceptions across 10,063,962 link visits: `link_id_number_flag` always set, `infra_link_flag` clear, `route_number_flag` clear, `pseudo3d_updown` 0, `route_type_guidance_flag` clear, `altitude_flag` clear.
- **`link_id_flag` at L0** equals `n_nodes > 2` exactly, 9,897,898 of 9,897,898. Spec 8-1-4 names it the Link ID Differential Information Delete Flag, which is consistent. The rule does not hold above L0 (25,365 counterexamples of 95,877 at L2) and is not claimed there.
- **`selected_link_flag`** (spec 8-1-3, Navigable MultiLink Flag): exact 100 % set at L2 and exact 100 % clear at L4–L8 (70,187 of 70,187). At L0 it is determined by road type at 99.9697 % (9,894,899 of 9,897,898) with the residual confined to road types 7 and 12 and enumerated.
- **`route_planning_tag`** (spec 8-1-8): exact at L2–L8. At L0 determined by road type at 99.9961 % with a 388-link residual, mostly road type 10, enumerated.
- **Node bits follow the spec reading, not the code's names.** Bit 15 is one-way validity, 100 % zero across 30,348,229 nodes. Bits 14:13 are the one-way code, elevated to 29–37 % non-zero in the Melbourne, Sydney and Brisbane CBD boxes against a 4.14 % L0 baseline. Bit 12 is building-planned road, 100 % zero disc-wide — which rules out the code's "tunnel" label, since Australia has road tunnels. Bit 11 is tunnel, rare but non-zero (957 of 29,866,457 at L0). Bit 10 is bridge, 0.35 % at L0 and elevated two- to fivefold in the boxes around the Sydney Harbour, West Gate, Story and Gateway bridges; **the code does not decode it at all.** Phase 9 renames the fields to the spec's meanings and adds bit 10 before it populates anything from OSM, or it will write the wrong bits. This **supersedes `docs/schema/flags.md`**, where all five node-bit rows currently carry status `unknown` with the note "conflict... not resolved here"; Phase 9 resolves the conflict in the spec's favour and must rewrite those rows rather than leave the two documents disagreeing.
- **mfde 12–19** resolve to the correct grid-neighbour Map Frame, and `n_entries = 20 + sum(count)` holds on 100 % of 15,537 R leaves at L4–L10. Exact resolution, not a distribution match.
- **`flags.md` completeness** is lint-checkable: every flag and node bit R uses has a row. Enumeration, not a threshold.

Necessarily-statistical, and only this one: **`toll_flag`.** No R-internal correlate exists — toll links spread across road types 0, 2, 3, 5, 6 and 7 at every level with no exclusive subset — so OSM `toll=yes` is the only source. Its band is R's exact measured per-level prevalence: L0 0.0116 %, L2 0.494 %, L4 0.828 %, L6 1.177 %, L8 1.448 %.

Named as unresolved: `link_id_flag`'s rule above L0; and bit 11's identification as tunnel rests on prevalence plausibility, with no named-tunnel spot check yet run. Both are recorded, not assumed.

#### Phase 10 — Outcome, as amended

Already enumeration-based and grounded: byte-exact determinism over two builds, a capacity byte count against 4.7 GB, and every check either PASSING or carrying a ledger entry. One tightening: "contributing no processing-caused differences" is a judgement as written. Each ledger entry must name its cause from the closed vocabulary — *natural* or *documented-unknown* — and cite its evidence, and an entry that can cite neither is a defect, not a deviation.

#### What this changes about the work, not only the measurement

Three criteria above are not new ways of measuring the same thing; they are defects the old fuzzy gates could not see. G writes 0 into the background display-scale flag word, which the spec defines as never displayed. G writes 0 into the mandatory multilink shape-information-size word. G places every background record in a single element instead of R's censused (type code, shape class) element. Phases 4 and 6 own the fixes; none is authorised here, since this amendment is design work.

#### Schema rows this amendment supersedes

Each row below is stale against a finding above. The owning phase rewrites it as part of its work; none is rewritten here, and until then a reader of `docs/schema/` gets the weaker pre-amendment story.

- `map-frame.md`, size-limit row: "the true max may be 131,068 ... undecided | unknown" — superseded by the 7.1.2 remark-2 citation (Phase 4). Note that `parser/build_alldata.py` already hardcodes 131,070 and `FINDINGS.md` F3 recommended it on 2026-09-20; the spec citation is the first independent grounding for a value the code had assumed, and the amendment claims nothing more than that.
- `map-road.md`, `display_class = f(road_type)`: status `verified` on histogram-sum evidence, which the row itself notes does not assert the function — superseded by the per-record census (Phase 7). Until that census is committed, neither version is backed by a runnable check.
- `map-background.md`: display-scale-flags row ("sample is small"), element-placement row ("inferred from the 8-point sample"), polygon-vertex-order row ("winding ... not measured") — superseded by Phase 6, including the finding that R violates the spec's winding requirement.
- `map-name.md`: coverage row ("~85% of L0 cells") and uppercase row ("the ~1% is unexamined") — superseded by Phase 8's per-level coverage table and the zero-exception uppercase census.
- `flags.md`: the five node-bit rows, as stated under Phase 9.

The Assumption Ledger entry "Coordinate range 4096/16384 is the true full-cell range" is deliberately left untouched, because Phase 2 is not closed here. Whoever closes Phase 2 must update that entry in the same change; closing it without doing so would be a scope violation.

#### Adversarial pass, 2026-09-23

One adversarial review ran against this amendment from a clean context. Applied: criterion 1's denominator was wrong and now cites the full-disc `coord_scale.json` census instead of the 12-cell overlay pools; the uncommitted-evidence caveat now governs every phase rather than Phase 2 alone; criterion 2's bundled hypothesis and its range-relative edge tolerance are stated, with the divided result marked provisional; the superseded schema rows are listed; the dropped occupied-fraction clause and the Phase 5 advisory ledger entry get explicit dispositions; Phase 7's band is a per-level formula rather than "roughly 90 to 94 %"; Phase 9 says it supersedes `flags.md`. Noted and not acted on: the "threshold in the docstring before the run" rule is unauditable until the tools exist, and is to be checked when they land.

#### Recommendation on closing Phase 2 — for the user to decide

`b_coord_max_over_range` alone is not enough to close Phase 2, but not because it is weak. It is a one-sided bound: it proves no coordinate exceeds its range, which a range that is too *large* also satisfies. That is exactly why the 32768 control was not eliminated by it.

The recommendation is to close Phase 2 on criteria 1 through 5 above, with criterion 2 — cross-parcel continuity — as the decisive companion. It is R-internal, immune to the source drift that broke the OSM measure, two-sided (it fails a range that is too large as hard as one that is too small), and it separates the assumed model from every alternative by three to five orders of magnitude. Criterion 3 carries a direct spec citation that names the divided-parcel model the continuity test independently selected. That is a stronger position than the plan has held at any point.

Two conditions attach. The continuity and mirror checks currently exist only as scratchpad censuses; they must be committed under `parser/tools/` and re-run before the gate verdict counts, and the mirror check needs block-crossing neighbour lookup. And the `divided_pardiv1` continuity median of 122 m should be re-measured at a tighter edge tolerance to confirm it is matching noise rather than a small residual mis-model.

**Phase 2 is not closed by this amendment.** The design is left ready for a re-run against the criteria above; the verdict is the user's.

### Amendment 2026-09-23 (design agent) — the adjacency unit is the frame, not the leaf slot

**Provenance, stated plainly: this amendment is machine-driven research, not a user decision.** It was written by the design agent under the run's self-correction protocol after the grounded gate re-run (2-12) returned NOT CLOSED with criteria 2 and 4 failing at `L0_sparse`. Every figure below comes from direct measurement against R at `/run/media/codyh/464210-8480` by read-only probes in the session scratchpad; the probes are not checked in, and per this design's own evidence rule no criterion below is load-bearing until the committed tool re-runs it. The units this amendment adds (2-13, 2-14, 2-15) are what commits it. The user has not reviewed this; if the user disagrees with any of it, the units are the place to reverse it.

**The Assumption Ledger's hard stop is not triggered.** The ledger entry "Coordinate range 4096/16384 is the true full-cell range. Tested in Phase 2. If false: hard stop, re-analyse (user decision)" names the case where the coordinate model is *false*. The research found the opposite: the model is confirmed, and confirmed more strongly than before, including by a two-sided cross-class measurement no earlier tool made. The entry stays untouched here for the same reason the 2026-09-23 user amendment left it untouched — Phase 2 is not closed by this amendment either — and 2-15 still owns updating it in the change that closes the phase.

#### Root cause of the criterion 2 and 4 failures at L0_sparse

Both failures have one cause, and it is a bookkeeping gap in the checking tools, not a property of R.

`parser/tools/r_neighbours.py` (`LeafIndex.neighbour`, `EDGE_DELTA`) steps **one top-level leaf slot** on the level's global leaf grid. For every class except `L0_sparse` that is also one coordinate frame, so the step is correct. For `L0_sparse` it is not: unit 2-05 established that the L0 sparse coordinate frame is the **4x4 integrated-parcel tile at range 16384**, and all 16 leaf slots of such a tile alias **one** Map Frame. `r_neighbours` documents this gap in its own output notes (`"l0_is_per_leaf_slot"`: "a sparse tile aliases 16 leaf slots to one Map Frame; each slot is still counted and looked up independently here"). Units 2-10 and 2-11 consumed the leaf-step lookup anyway.

Two consequences, both measured:

- **Denominator inflation.** All 16 aliased slots return the same `(dsa, size)` and the same frame bbox, so `RReader.decode` returns identical links for all 16 and each tile's qualifying node set is counted 16 times. Probe: 128 of 128 tiles in the first sampled block resolve to one distinct `(dsa, size)`.
- **Self-neighbours.** For 12 of the 16 aliased slots a one-slot step lands **inside the same frame**, so the "neighbour" is the source parcel itself and no mirrored node at `range - value` exists. Only the 4 slots in the column or row adjacent to the crossed edge reach a genuinely adjacent tile. That predicts exactly a 1-in-4 match rate, and criterion 4's numbers are exactly that: denominator `11536 = 16 x 721`, matched `2884 = 4 x 721`, violations `8652 = 3 x 2884`, with **100 % of the 8652 violations classified `same_block`** — the signature of a parcel failing to mirror against itself.

Criterion 2's `L0_sparse` residual has the same origin. Its own recorded examples pair leaf 4 with leaf 36 and leaf 12 with leaf 13 — pairs of slots *inside one tile* — at frame-scale separations (9,214.5 m and 11,715.4 m). The 328 over-threshold pairs are not 328 disagreements about coordinates; they are within-tile pairs the leaf-step lookup should never have formed.

**Decisive re-measurement.** Under the same sampling rule (spread over 40 blocks, `MIN_NODES_PER_CLASS 300`) and the same pre-stated constants, with the adjacency unit set to the tile instead of the leaf slot: `blocks_visited 9, n_tiles 1152, n_candidate_nodes 721, denominator 721, matched 721, violations 0`, crossings `same_block 662 / cross_block 57 / cross_blockset 2`. Criterion 4 at `L0_sparse` goes from 8,652 of 11,536 violations to **zero**.

#### New grounded rule: one global raw lattice per level

The fix is not a special case for L0 sparse. The research found a single formulation that covers every class and makes the invariant frame-shape-independent:

> At every level, R's raw coordinate resolution is **4096 raw units per top-level leaf slot**. A coordinate frame covers an n x n block of slots and carries range `n x 4096`: n = 1 for a basic parcel (L0 urban, an L2-L8 leaf, a divided parent), n = 4 for an L0 sparse integrated-parcel tile, giving `4 x 4096 = 16384`. A parcel's global coordinate is `X = gx0 * 4096 + x_local`, `Y = gy0 * 4096 + y_local`, where `(gx0, gy0)` is the frame's south-west leaf slot on the level's global leaf grid.

This is what spec 7.2.2.1.1.2 describes when it says "a basic parcel is 4096 x 4096 and an integrated parcel up to 4096 x 8 = 32768": the integrated parcel's range is a whole multiple of the basic parcel's, because the raw unit is the same physical size at both. Under the lattice, the mirror rule stops being a statement about one frame's range and becomes an identity: **a boundary end node appears at the identical global (X, Y) in every frame that shares that point.** `crossed = range - value` is the n = 1 special case.

Measurements under this formulation, all against R, all at exact integer equality with no tolerance:

- L0 sparse tiles, 9 blocks, 1,152 tiles: **721 / 721**, zero violations.
- L0 urban, the **whole** urban population (all 252 urban tiles across 69 blocks, 2,863 urban frames with content), per edge incidence: denominator 100,958, matched 100,818, violations 140. By crossing kind: `L0_urban -> L0_sparse` **5,352 of 5,353** (one violation); `L0_urban -> L0_urban` 95,466 of 95,605.
- Per-node figures (edge nodes / failures): L0 168,712 / 93; L2 (13 blocks) 4,063 / 4; L4 (20 blocks) 6,933 / 1; L6 (whole population) 746 / 0; L8 (whole population) 66 / 0. These reproduce the already-passing classes exactly — L2's 4,067 / 4,061 / 6 in `EVIDENCE-2-11.json` is the same population.

The `L0_urban -> L0_sparse` figure is the load-bearing one. It is a **cross-class** crossing between a 4096 basic-parcel frame and a 16384 integrated-parcel tile frame, and it can only come out at 5,352 of 5,353 if 16384 is exactly 4 x 4096 *and* the tile's origin sits on the leaf grid where the model says. No earlier tool made a two-sided cross-class measurement; `boundary_mirror_census` excluded differing frame extents from the denominator as `scale_mismatch` (114 at L0_urban), which is precisely the crossings that carry this evidence. The 4096/16384 model is confirmed by the case the old check threw away.

#### Corner incidences are a distinct case, and the spec grounds them

Read per edge, corner nodes look catastrophic: 64 corner incidences at L0 with 51 violating (80 %). They are not violations of the lattice; they are a wrong reading of the invariant. Spec 7.2.2.1.1.3, the on-boundary node flag, says identical node information is held in neighbouring **parcels**, plural — and a node at a frame corner is shared by three other frames, not one. Scored per node ("some frame sharing this point holds a node at the identical global (X, Y)") the corner population collapses to **40 nodes / 1 failure** at L0 and **2 / 0** at L2. The per-node, any-sharing-frame reading is therefore the criterion, and the per-edge reading is retired as an artefact of testing one edge at a time.

#### Criteria 2 and 4, as re-stated

Criterion 1, 3 and 5 stand exactly as the 2026-09-23 user amendment wrote them; they passed on the re-run and are not touched. Criteria 2 and 4 are restated:

**2. Cross-parcel continuity (restated).** A road link crossing a frame boundary is stored independently on both sides; the two copies of the shared endpoint occupy the same point on the level's global raw lattice. Per matched pair; denominator all boundary endpoint pairs at a shared **frame** edge, the adjacency unit being the frame, not the leaf slot. Endpoint *selection* is exact — a node qualifies only when its raw crossed-axis coordinate is exactly 0 or exactly the frame range — and pairing is exact lattice equality. This retires `EDGE_TOL_RAW` and `PAIR_TOL_RAW` under this design's own retirement rule: the grounded exact measure was found underneath the tolerance-based one, so the tolerance is retired rather than retuned. The alternative-range scoring (half, double, 32768, the two divided renormalisations) is kept, because it is what makes the criterion two-sided.

**4. Boundary-node mirror (restated).** A link end node exactly on a frame edge is answered by an end node at the identical global (X, Y) in a frame sharing that point. Per node, at exact integer equality, zero tolerance. Denominator: all exact-coordinate nodes with at least one resolvable sharing frame, nodes at the extract's outer edge excluded from the denominator rather than failed, and counted-and-reported exclusions retained. A node at a frame corner is satisfied by **any** of the frames sharing that point (7.2.2.1.1.3, "neighbouring parcels", plural), not by one nominated edge neighbour. `scale_mismatch` is **no longer an exclusion**: under the lattice a 4096 frame facing a 16384 frame is an ordinary crossing and must be in the denominator, because it is the strongest available evidence for the range model.

**The measured residual is 152 records disc-wide, and the enumeration cap must exceed it.** Composition: 93 at L0_urban, 1 at `L0_urban -> L0_sparse`, 4 at L2, 1 at L4, 53 at divided `pardiv1`. `RESIDUAL_ENUM_CAP = 200` is above that, but the reason 2-12 failed criterion 2 was a cap below the residual, so the cap must be checked against the residual it has to print and every record enumerated with both parcels' identifiers and both raw coordinates. Character of the residual, so the enumeration has something to say: at L2 and L4 the offsets are **1-2 raw units** — R's two copies of one node disagree by rounding. At L0_urban the 93 are mostly **44-245 raw units** with one at 1,243, which is too large for rounding and is consistent with a link *terminating on* the boundary without crossing it — the same "dead end on the line" mechanism this design already used to retire `b_clip_exact_share` — plus four at 1 unit. None of this is an explanation until 2-14 enumerates it record by record; the criterion is not satisfied by a plausible story about a residual.

#### The carried `divided_pardiv1` provisional concern is resolved

The 2026-09-23 amendment marked criterion 2's divided result provisional and suspected its 122 m median was the range-relative edge tolerance admitting nodes near but not on the midline. It was. Measured over the whole divided population with exact midline selection and **no tolerance**: 3,300 midline nodes (L0 1,951, L2 345, L4 738, L6 224, L8 95), **53 failures** (L0 3, L2 1, L4 44, L6 4, L8 1), so 3,247 exact. Nearest offsets on the failures sit at 1-24 raw units. The provisional marking is lifted: the divided parent-4096 model holds at exact equality, with a 53-record enumerable residual. Criterion 3 (spec-cited, tolerance-free, zero violations) is unaffected.

#### Two tool defects that become load-bearing

- **`coord_scale_census._work` builds `WalkedParcel` without `frame_bounds`** (GATE-2 Carried 5). `WalkedParcel.__post_init__` then defaults `frame_bounds` to the leaf bbox, so 075fc99's "invert against the frame bbox, not the leaf" never takes effect in that worker. It was harmless for criterion 1 because raw values round-trip through whichever bbox both directions use. It stops being harmless the moment anything computes the global lattice from that worker's output, so 2-13 fixes it.
- **`boundary_mirror_census`'s verdict logic is wrong, independent of the L0_sparse bug.** `elif len(violation_examples) >= min(violations, 20): verdict = "pass_with_residual"` labels a class `pass_with_residual` whenever it can print twenty examples, whatever share of the denominator they cover; that is how a 75 % violation rate came back labelled `pass_with_residual` and needed GATE-2 to override it by hand. The verdict must be tied to the residual's **coverage of the denominator**: `pass` at zero violations, `pass_with_residual` only when every violation is enumerated, `fail` otherwise.

#### Units this amendment adds

2-09 through 2-12 are history and are not re-run or re-briefed; 2-12's gate verdict is superseded by 2-15. **This amendment does not re-run the gate and does not close Phase 2** — 2-15 does, and 2-15 owns the Assumption Ledger update in the same change.

| Unit | Brief | Depends on | May run alongside |
|---|---|---|---|
| 2-13 frame adjacency and the global raw lattice in `r_neighbours.py` | `briefs/2-13-frame-adjacency.md` | nothing | nothing |
| 2-14 continuity and mirror re-run on frame adjacency (criteria 2, 3, 4) | `briefs/2-14-continuity-and-mirror-rerun.md` | 2-13 | nothing |
| 2-15 grounded gate verdict (criteria 1-5) and Assumption Ledger | `briefs/2-15-grounded-gate-verdict.md` | 2-13, 2-14 | nothing |

### Amendment 2026-09-25 (user) — the build hot path moves to C at a cell-range boundary

**Provenance.** The decisions below are the user's, relayed by the orchestrator (`IMPLEMENTATION.md`: "Orchestrator decision: the build hot path moves to C at a cell-range boundary", "Research: where the build time goes, and the C porting scope", "3-12 … stopped, no outcome"). The design agent chose the placement, the stage order within the constraints the user set, the per-level budgets (derived from the profile below), and the `quantisation_roundtrip` redesign. Each of those choices is in the Assumption Ledger.

**Why.** The full-Australia build went from 36.7 s (3-07) to about 108 s (3-11). New per-shape and per-cell work (3-09's overlap pre-pass, 3-11's rectangle detection) and its tests landed in Python first. C mirrors followed, and a Python→C handoff ran once per cell. Profile of L0 at `-j 12` on the 3-11 tree (full build 108.3 s, L0 96.3 s): overlap scan `_scan` 27.1 s (Python/numpy); overlap `merge_raw` about 30 s (Python; re-serialises every record, handing 11.25 GB to C from a 4.45 GB spool); the divide fallback for 563 parents about 27 s (Python, with C measuring); per-cell glue about 6.5 s; C `kw_encode_cell` about 5 s (3.70M ctypes calls, 2.27M of them for empty cells). The user's words: "It has to be absolutely clear, since our main problem is new work (tests and build) hit python and then we have to refactor later onto C. Clearer boundaries on both sides will avoid this."

This amendment adds **Phase 3C** (Phases section). It pauses Phase 3's remaining units until 3C closes and changes what those units are (Phase 3's units table). It also adds four standing contracts. They bind every phase from 3C onward, and every brief must carry them.

#### Contract B — the build boundary

The build pipeline (`build_alldata.py` and everything it calls) has exactly two C entry points, E1 and E2, plus the transitional E3 (Stage 1 only), and the assembly copy under H4. Nothing else crosses from Python to C on the build path.

Both entry points are called once per cell range, over the same contiguous cell-count ranges (the partition in `docs/ARCHITECTURE.md`, "Partition and merge"). So per level, E1 calls = E2 calls = number of ranges. The gate asserts that equality.

- **E1, level pre-pass: one call per cell range.**
  - Input: the level descriptor (below), the range, and the level's whole spool `.data`/`.idx`, zero-copy from the mmap.
  - Output: fixed-width routing rows `(target ix, target iy, source spool offset, coverage kind)`. There is one row for each existing cell *outside its source cell* that a shape in this range passes through, or that a polygon wholly covers (`coverage kind` = interior cover). These are rows only, with no geometry. Copying geometry would rebuild the 11.25 GB handoff that this boundary removes.
  - Python may only concatenate and partition these rows by target range, as one vectorised operation. It never interprets them further.
- **E2, range encode: one call per cell range.**
  - Input: the level descriptor, the range, the level's whole spool (zero-copy, so borrowed shapes are read in place from any range), and the E1 rows routed to this range.
  - C orders each cell's borrowed shapes canonically, by source `(iy, ix)` then spool index. So the output does not depend on the range partition or on the order rows arrive.
  - Output:
    1. **A frame buffer.** All finished Map Frame bytes for the range, including divided sub-frames.
    2. **A frame index.** One row per frame, in canonical order, keyed `(level, ix, iy, parcel_type, sub_ix, sub_iy)`, with offset, size and per-kind sub-frame sizes. Python assembles from the buffer and index without making a Python object per frame. The row layout is fixed at refine.
    3. **A declined list** of `(ix, iy, reason)`, one row per cell C did not finish.
    4. **Merged content for declined cells, transitional.** Each declined cell's own and borrowed shapes, in spool-record format.
    5. **Additive deterministic counters** for the manifest. Before 3-10 these are exactly 3-11's counters (overlap statistics, trimmed items, halo names). 3-10 adds the dropped-name-anchor counter, and that is a deliberate manifest change.
    6. **C-side stage timers.** These go to the bench record and never to the manifest (Output invariance, `docs/ARCHITECTURE.md`).
  - E2 also emits the frames for masked-in empty cells (today's `_fill_masked`), so no per-cell Python remains.
- **E3, transitional sub-parcel measure (Stage 1 only).** While division is still Python, the transitional divide may call a C measure once per candidate sub-parcel, as today's divide does. Without it, the divide path falls back to Python encoding and the Stage 1 wall gate cannot be met. E3 is the only permitted third entry point. It is deleted in Stage 2, together with the declined list's only reason.
- **The level descriptor** is built by Python once per level and passed as data. It holds:
  - the grid geometry;
  - the frame-class and range rule as a table from `coord_scale.json` via `kiwiw/mesh.py`;
  - the level mask of existing cells;
  - the 131,070-byte ceiling and the kind limits;
  - the priority and keep-order tables used for trimming and division;
  - every vocabulary table the encoders read.
  C evaluates these per cell. Python does not. The build takes no imports from the extractor (`assign_to_parcel`, `g_frame_range` and `frame_bounds` today). Their rules become descriptor data from `kiwiw/mesh.py`.
- **Declined cells are transitional.** While division is still Python (Stage 1), the only permitted reason is "needs division". At Phase 3C's close, no reason is permitted, E3 and output 4 are gone, a non-empty declined list is a build error, and no Python fallback exists.
- **Cross-cell dependent fields.** Some fields depend on a neighbour's state, not the cell's own content. Examples are the header or entry fields that differ next to a divided neighbour (Phase 2's 42 word-0 exceptions) and the neighbour pointers (Phase 9). Such fields are resolved in C, by one of two routes:
  - a division-state pass, before E2, whose result travels in the descriptor; or
  - a C patch during assembly (H4).
  They are never patched in Python. The phase that first needs such a field chooses between the two, in a design amendment if the choice changes E1/E2.

**C owns everything on the per-shape and per-cell path:**
- decoding spool records for encoding;
- the overlap scan and the merge of borrowed shapes;
- clip, densify and round;
- `mult_const` selection;
- road, background and name record encoding, sub-frame and Map Frame encoding, and size measurement;
- division, retile, trim and name halo;
- per-cell frame class and range evaluation;
- the out-of-cell name-anchor drop (3-10's assembly half).

**Python owns:**
- planning: the level list, the cell-range partition and the level descriptor;
- the mask and the thresholds, as data;
- the CLI and the worker pool;
- reading spool bytes and routing pre-pass bytes;
- assembly orchestration: the frame table, block placement, DSA/BMT and the `ALLDATA.KWI` write, all vectorised over C's buffer and index. Today `IndexedLayout` builds divided blocks per frame in Python. That is a leak: it moves to the vectorised or C path in Stage 2;
- the manifest and the bench record;
- every verification and analysis tool: decoders, `SpoolReader`, the harness, censuses, `compare_disc.py`, the R round-trip writers.

**Never implemented in Python.** None of the following may exist in Python in any form: a build module, a test helper, a test oracle, a fallback, or a tool that re-runs it. The single exception is the R round-trip writers named below. They encode *decoded R* for decoder proofs, never spool content.
- a loop over the shapes, records or vertices of a cell for the build;
- spool-record decoding feeding an encoder;
- overlap or cell-coverage computation;
- clipping, densifying or rounding of written geometry;
- `mult_const` choice;
- record, sub-frame or Map Frame encoding, or size measurement of an encoding;
- division, retile, trim or name-halo selection;
- a per-cell or per-shape call into C.

A Python fallback for when C is absent is also forbidden: `KIWIW_NO_C` and the no-compiler fallback are deleted, and a build without a compiler fails. New build behaviour lands in C with its tests at the boundary (Contract T), or it does not land.

**Outside this boundary:** extraction (`osm_to_parcel_geometry.py` and the other `osm_to_*` stages). It produces the spool and stays Python. 3-10's extractor half is therefore Python work. See Open Questions for whether extraction later gets a boundary of its own.

**The R round-trip writers** (`road_writer`, `background_writer`, `name_writer`, `parcel_writer`, `alldata_writer`'s replicate mode) re-encode *decoded R* to prove the decoders byte-exact. They are verification tools and stay Python. They may never be called on the build path, and never used to produce or check G's bytes. Their shared helper `synth.frame_range` moves to `kiwiw/mesh.py` when `synth.py`'s encoders are deleted.

#### Contract H — hot paths and budgets

The named hot paths:

| ID | Hot path | Side |
|---|---|---|
| H1 | Level pre-pass (E1) over every spool chunk | C |
| H2 | Range encode (E2): spool decode through finished frames, including division | C |
| H3 | Handoff: building E1/E2 arguments and unpacking their results | Python wrapper around C |
| H4 | Assembly: frame table merge, block placement, `ALLDATA.KWI` write | Python/numpy vectorised over C's buffers; any per-frame work in C |

Budget: a full-Australia build at `-j 12` from `output/extract_timing/spool`, on the project build host, completes in **under 60 s wall**. The 35 s baseline predates the overlap work. The per-level budgets are derived from the 3-07 build (no overlap) and the 3-11 profile:

| Stage | 3-07 measured | 3-11 measured | Budget |
|---|---|---|---|
| L0 encode, pre-pass included | 27.9 s | 96.3 s | ≤ 38 s |
| &nbsp;&nbsp;of which L0 pre-pass (H1) | none | 27.1 s | ≤ 5 s |
| L2 encode | 0.5 s | 1.6 s | ≤ 2 s |
| L4–L12 encode, together | 1.4 s | 1.7 s | ≤ 2 s |
| Outside encode (spool open, H4, manifest) | 6.8 s | 8.2 s | ≤ 10 s |
| **Full build wall** | **36.7 s** | **108.3 s** (105–123 s spread) | **≤ 60 s** (budgets sum to 52 s; 8 s headroom) |

**Done evidence.** Any unit that touches a hot path reports, per level:
- the Python / C / handoff time split. C time is the E1/E2 timers summed over workers. Handoff time is the time in the Python wrapper around each C call, outside C. Python time is the rest of worker time. All three are scaled to wall as in the 2026-09-25 profile.
- the full-build wall.
- the E1 and E2 call counts.

Timings and call counts go to the bench record, never the manifest.

**Measurement.** Every wall and stage figure used as a gate is the median of three full builds. One run is not a verdict.

**Regressions.** A unit whose full-build wall rises above the previous recorded build by more than the run-to-run spread must name the specific mechanism. That spread is measured at 3C's baseline, three runs. Accepting the rise as a trade-off is not enough. From Phase 3C's close onward, **every phase outcome includes a full build at `-j 12` within the wall and per-level budgets.**

#### Contract T — tests

The build logic has no Python copy, not even as a test oracle. The oracle is:
- the Python decoder;
- the goldens;
- invariants measured on R.

Tests come in three layers.

- **(a) Boundary tests: the default home for every new build test.**
  - pytest calls E1/E2 through `cenc.py` on fixture spool bytes and fixture pre-pass bytes.
  - It decodes the output with the Python decoder.
  - It asserts on decoded content or on invariants: in-range coordinates, clip-rectangle containment, delta representability, frame-size ceilings and the like.
- **(b) A C unit-test binary for internals the boundary reaches poorly**, such as edge-step splitting, rectangle detection and clip corner cases.
  - It is built by the same mechanism that builds the extension.
  - It is run from pytest, so `pytest parser/tests` stays the single entry point.
- **(c) Goldens.**
  - A golden is a **closed fixture spool**: a cell range plus every cell whose shapes reach into it, in spool format, together with the expected frame bytes and their sha256. The pre-pass is never stored. The test always produces it by running E1 on the fixture, so goldens captured in Stage 0, before E1 exists, stay valid across the port. Layer (a) boundary fixtures are built the same way.
  - Before each port step, the goldens are captured from the current build. The ranges must cover:
    - L0 urban dense;
    - L0 sparse;
    - a cell receiving borrowed edge shapes and one receiving an interior-cover rectangle;
    - a divided L0 parent with trim and name halo;
    - L2;
    - a divided L4 parent;
    - an edge-of-coverage cell.
  - The fixture set is committed under `parser/tests/fixtures/` and chosen small enough to commit. Anything that cannot be committed is recorded in `docs/provenance.md`.
  - The port must reproduce every golden byte for byte. After that, the Python module and its internals-level tests are deleted, and the goldens stay as regression tests.
  - A unit that *intends* to change output bytes re-captures the goldens it affects in the same commit and states why. Byte-identity gates apply to ports only.

Current exposure, all removed or rewritten by Phase 3C's close:
- `synth` is imported by 10 test files. Harness tests that use it to fabricate fixture frames switch to layer (a) fixtures produced through E2, or to committed fixture bytes.
- `divide` is imported by 3 test files, `clip` by 2 and `overlap` by 1.
- `test_cenc.py` checks C against the Python encoder. Its C-vs-Python cases are replaced by goldens and boundary tests, then deleted.

#### Contract W — worker waiting rules (process; every brief carries it verbatim)

1. Chain every slow check (builds, `compare_disc`, round-trips, probes) in one background script that writes a status line per step: `STEP <name> OK|FAIL <seconds>`, then a final `DONE` or `ABORT`.
2. Block on that script with **one** monitor whose match covers every terminal state (`DONE`, `ABORT`, any `FAIL`, script exit).
3. Never end the turn to wait. A subagent that ends its turn has ended. Never spend no-op turns polling.
4. Never pipe a long command through `| tail` (or any filter that hides progress and defeats backgrounding). Redirect to a log file and read the log.
5. A check slow enough to need many waits is a finding to investigate, not a thing to wait out.

#### Verification-tool decisions

- **`quantisation_roundtrip.py` becomes a check of the decoded disc against the spool.** Today it re-runs Python `clip.shape_pieces` and `overlap.build_level` to reconstruct the written vertices. Contract B forbids that as a copy of build logic, and the 3-11 record shows the danger: the tool silently did not exercise the coarse-`mult_const` path.
  - The tool reads the built `ALLDATA.KWI` with the Python decoder and the spool with `SpoolReader`. It imports no build module.
  - It runs in parallel over blocks.
  - It keeps the invariants that do not need the clip algorithm:
    - every decoded vertex lies inside `[0, range]`;
    - road nodes, road points and name anchors each agree with their spool source record within half a raw unit per axis;
    - every decoded background vertex not on the frame boundary lies within half a raw unit per axis of an outline of a spool shape of the same type at that level, found by the tool's own spatial index;
    - every decoded background vertex *on* the frame boundary lies inside or on a same-type spool polygon (point in polygon, with half-unit tolerance). This covers crossings, corners, coarse-`mult_const` rectangles and interior covers, which 3-11 showed can otherwise go untested;
    - completeness: for each `(cell, type)`, every spool polygon whose interior meets the cell appears as at least one decoded piece. For each interior-cover cell, the cell centre lies inside its source polygon;
    - every step is representable.
  - It gives up the per-origin breakdown (original / crossing / corner / step-split), which needs the clip algorithm. Crossing and corner correctness stays with the frame-edge mirror probe against R.
  - The earlier instruction to pass a pool to `build_level` is superseded, because the tool no longer calls `build_level`.
  - This redesign lands before `overlap.py` or `clip.py` is deleted.
- **`coord_scale` is parallel and raw.**
  - It decodes in parallel over blocks.
  - It judges raw coordinates against the class range directly, skipping `parcel_extent`'s lat/lon round-trip.
  - On the 3-11 disc (`87a01b14…`) it must return the identical verdict and counts (PASS, 0 of 1,461,347 parcels, 73 classes) in ≤ 120 s at `-j 12`. It currently takes 10–15 min single-process.
- The redesigned round-trip on the 3-11 disc must report 0 failing background vertices, and exactly the one known name-anchor failure (3-10's), in ≤ 120 s at `-j 12`.

#### Phase 3's remaining units

- **3-12 is withdrawn.** Its premise, trimming overlap duplication in `overlap.py`, would be work on Python that Phase 3C deletes. Its wall-time half is absorbed by Contract H. Its disc-size question is re-issued as **3-13**, which runs on the C pipeline after 3C closes: is interior-cell duplication still the dominant disc-size cost against R? It is measured first, and "no code change" is a complete outcome. Any trim lands in C, at the boundary, under Contract T.
- **3-10 is held and re-scoped.**
  - The extractor half (`assign_to_parcel` returns `None` outside the lon span) is unchanged and stays Python.
  - The assembly half, dropping name records outside their cell with counts, lands in C inside E2 and reports through the E2 counters.
  - Its round-trip alignment is the redesigned tool's name-anchor rule.
  - Phase 3 re-uses the existing spool, so the extractor fix does not reach the disc in Phase 3. It is verified by a unit test, and it takes effect at the next re-extraction (Phase 8). Phase 3's disc evidence is the C drop guard alone.
  - It depends on Phase 3C.
- **Phase 3's Outcome clause "`range_for` feeds both the Python and C encoders"** reads, from 3C onward, as "`range_for`'s rule reaches the C encoder through the level descriptor". No Python encoder remains to feed.
- **3-05** (determinism matrix) and **3-06** (phase evidence) run on the C pipeline. They depend on Phase 3C, 3-10 and 3-13. 3-06 also reports the Contract H budget table.

## Assumption Ledger

Each assumption names the phase that tests it and what happens if it is false.

- **Coordinate range 4096/16384 is the true full-cell range.** Tested in Phase 2, CLOSED 2-15 (`GATE-2.md`). Rests on: one global raw lattice at 4096 raw units per top-level leaf slot (`X = gx0*4096 + x_local`, `Y = gy0*4096 + y_local`); a coordinate frame is an n x n block of leaf slots at range n x 4096 (n=1 a basic parcel, n=4 the L0 sparse integrated-parcel tile, range 16384); and the cross-class `L0_urban <-> L0_sparse` boundary-mirror measurement (criterion 4, 113 matched / 1 violation, committed re-run) as two-sided evidence that 16384 is exactly 4 x 4096, not an independent constant. If false: hard stop, re-analyse (user decision) — not triggered.
- **Coastline lines in the extract close into land polygons** (extract-edge breaks, islands). Tested in Phase 6 by the no-land-labelled-as-sea audit. If false: ocean construction is re-analysed before Phase 6 closes.
- **Name-matched R↔OSM cells are a valid basis for road vocabulary.** Tested in Phase 7 on held-out named arterials. If false: research a different basis before mapping.
- **R's word 0 rule holds beyond the 95.5% (897/939) of sampled leaves where it equals the first data-slot offset.** Phase 2 explains the 42 exceptions before the gate closes; the criterion is "matches R's rule or the exception is explained".
- **Copying R's value for a flag whose meaning is unknown is harmless to the head unit.** Not accepted blindly (user decision): each such flag is a flag-table entry and a ledger deviation with a later test; none is undocumented.
- **Country-scale re-extraction is affordable** (needed for Phase 8). Phase 1 measures extraction wall time.
- **(2026-09-25, design agent) Phase 3C is a lettered phase between Phase 3 and Phase 4, not a Phase 4 that renumbers the rest.**
  - Rationale: the user required the C pipeline before 3-12, 3-10, 3-05 and 3-06, and Phase 3's outcome ("two builds byte-identical at 1/4/12") is only honest if it is measured on the pipeline that ships.
  - Renumbering would invalidate every brief and record that cites Phases 4–10.
  - If wrong, the phases are renumbered at close-out. No outcome changes.
- **(2026-09-25, design agent) Port order: Stage 1 is the overlap scan, merge and per-cell encode together; Stage 2 is division.**
  - Rationale: the order follows the profile's payoff (the user's rule). Merge and per-cell encode share one handoff, so porting the scan alone would leave the 11.25 GB re-serialisation in place.
  - If wrong, Stage 1 splits in two. The gates are unchanged.
- **(2026-09-25, design agent) A declined cell returns its merged content in spool-record format, so the transitional Python divide can run without Python overlap.**
  - Rationale: this lets Stage 1 delete `overlap.py` while division is still Python.
  - If wrong, Stage 1 keeps `overlap.py` until Stage 2. The declined list still must be empty at close.
- **(2026-09-25, design agent) The per-level budgets are derived, not measured.**
  - L0 ≤ 38 s is a ceiling, not a model: 3-07's 27.9 s L0 (which still included the Python divide and per-cell glue that 3C removes) plus about 10 s for the pre-pass and borrowed-shape encode that 3-09 added. The other stages are 3-11's measured values rounded up. Stage 0 re-derives the L0 split from C-cost terms (pre-pass, encode, divide) once its baseline exists.
  - If Stage 0's baseline shows the derivation is wrong, the per-level split may be re-derived in a design amendment. The 60 s wall does not move (user).
- **(2026-09-25, design agent) The 3-11 record's "rect-detection overhead" attribution for its 105–123 s wall spread is wrong.** The research profile found no such cost.
  - Consequence: Stage 0 re-measures the baseline three times, and the spread from those runs is the regression threshold.
  - If the spread is itself large (over 10 %), finding its cause is Stage 0 work before any port.
- **(2026-09-25, design agent) `quantisation_roundtrip` gives up its per-origin breakdown** (original / crossing / corner / step-split) because it no longer re-runs the clip.
  - Crossing and corner correctness is covered by the frame-edge mirror probe against R, and by golden and boundary tests on clip corner cases.
  - If a defect later hides behind the lost breakdown, the fix is a layer (b) C test, never a Python clip.
- **(2026-09-25, design agent) The R round-trip writers stay Python and are verification-only.** They re-encode decoded R, not the spool, so they duplicate the format, not the build.
  - If one is later needed on the build path, that need lands in C, and the writer stays a verifier.
- **(2026-09-25, design agent) 3-12 is withdrawn rather than re-scoped, and its size question becomes 3-13.**
  - Rationale: 3-12's brief is written against `overlap.py`, which Stage 1 deletes.
  - If wrong, nothing is lost: 3-13 asks the same question on the surviving code.

## Open Questions

- Foreign-land absence is accepted as natural (user). The 102 G-only L0 cells outside R's populated rectangle (13 BMT tables) are unexplained until Phase 6 lists them with lat/lon and content; each is then natural (source land outside R's rectangle) or a defect.
- Whether the head unit requires `A=`/`1=` name tags or reads header word 0 / `dipid` — unknowable offline; treated as risk, mitigated by R-equivalence.
- Extraction wall time at country scale (undocumented); affects how many full re-extractions Phases 3–5 can afford.
- **`rg_size` (word 16) is unspecified** (Phase 2 Carried item 1). Bounced here by Phase 3's refinement rather than absorbed: Phase 3's Outcome does not claim word 16, and Phase 4's Outcome names words 0, 6, 7, 9–11 but not 16. It must be resolved in a design pass before Phase 4 is refined, or Phase 4 will be refined against a surface with no contract.
- **`RESIDUAL_ENUM_CAP` has two contradicting values** (Phase 2 Carried item 8). `parser/tools/continuity_census.py` and `boundary_mirror_census.py` both set 400; the 2026-09-23 design-agent amendment states 200 for the same cap. Reported by 2-14 and again by 2-15, never resolved, and moot at Phase 2's 12 total residuals — but it is a contradiction between the design text and the code, so it is bounced here rather than fixed by a Phase 3 unit. One of the two sources is wrong and the design must say which.
- **The L0 sparse frame is a shape difference between R and G, and no phase owns it.** R aliases sixteen leaf slots into one integrated-parcel tile at range 16384; G writes sixteen separate frames, which `harness/walk._is_sparse_tile` — a structural test against whichever disc is walked — correctly classes as `urban` at range 4096. Each disc is therefore self-consistent and Phase 3's amended Outcome (zero parcels exceeding their *own* class range) is provable on both, which is why this does not block Phase 3's refinement. But nothing in Phases 3–10 makes G build the 4x4 integrated-parcel tile that R builds, so the two discs will keep differing in frame shape at L0 sparse. Either that is accepted as a recorded deviation or a phase must claim it.
- **Does extraction get its own C boundary and wall budget?** (2026-09-25) Contract B deliberately stops at the spool. Extraction (`osm_to_parcel_geometry.py`, Python) is outside it, and its country-scale wall time is still not recorded here. Phase 8 needs re-extraction. If extraction is slow enough to limit how often Phases 5–8 can iterate, a boundary like Contract B may be needed there too. That is a user decision, not a guess. **Decided (user, 2026-09-25): not now.** Extraction is not on the build path and has no measured problem. It gets a recorded wall budget when next run at country scale, and is ported only if it exceeds that budget.
- **How the multi-file C extension and the layer (b) test binary are built.** (2026-09-25) Today `cenc.load()` compiles one file with gcc on demand into `_cenc.so`. Contract B removes the no-compiler fallback, so gcc becomes a hard build requirement. Two choices are open: on-demand compile versus an explicit setup step, and whether the build products are gitignored (and so recorded in `docs/provenance.md`). Refine settles the mechanism for Stage 0. If a setup step is chosen, it changes how the project is run, which is a user decision. **Decided (user, 2026-09-25):** compile on demand, as today. Build products are gitignored and recorded in `docs/provenance.md`, and gcc is a stated requirement.
- **Do fixture goldens for all seven ranges fit in git?** (2026-09-25) The L0 dense and divided-parent spool slices may be large. Anything that does not fit is regenerated from the full spool and recorded in `docs/provenance.md` (CLAUDE.md rule). The layer (c) contract then depends on a local spool, and CI cannot run it. Stage 0 measures the sizes. Whether a spool-dependent golden is acceptable is a user decision. **Decided (user, 2026-09-25):** commit goldens that are small. Any that are too large stay local, with regeneration from the spool recorded in `docs/provenance.md`, and their tests skip when the spool is absent. There is no CI today, so nothing is lost yet.

## Phases

The count and order are fixed at sign-off. The one exception is Phase 3C, which the 2026-09-25 user amendment inserted mid-Phase 3. It is lettered, not numbered, so that Phases 4–10 keep their numbers and every brief reference to them stays valid. Order: Phase 3 units through 3-11, then Phase 3C, then Phase 3's remaining units, then Phase 4. Phases 6 and 7 both edit `selection.json` and are sequenced, not parallel. Phases 8 and 9 touch the same encoder and check files and are sequential (8 then 9). Phase 3 (coordinates) and Phase 4 (header words, cap) are separate so failures stay isolated.

### Phase 1 — Baseline truth and non-invasive harness hardening

- Outcome: running `parser/compare_disc.py` against the current `output/ALLDATA.KWI` produces a report whose recorded sha256 equals `output/manifest.json`'s ALLDATA sha256; running it against a different file refuses to compare and says why. The strengthened `mfde`, `vocab`, `shape`, `container`, `pointers` and `spotcheck` checks (F12 items that need no new census) run on the current G and report the differences already known (G-only BMT tables, non-monotonic BMT DSAs, poorer-than-R vocabulary coverage, Grenfell row) as FAIL or advisory as designed, with the expectation list recorded.
- Surfaces: `parser/compare_disc.py`, `parser/harness/{report,context,registry}.py`, `parser/harness/checks/{mfde,vocab,shape,container,decode,spotcheck}.py`, `parser/refdata/harness.json`, `parser/refdata/spot_checks.json`, `parser/tests/test_harness_*.py`.
- Also delivers: the numeric bands section in `harness.json` (a stated fractional tolerance around R's per-level statistic, reviewed, never adjusted after seeing G) used by every later "within band" outcome; a measured extraction wall time (for Phase 8); a vertices-per-km and road-length census of R (needed by Phase 5's density band); a recorded review of the bands before any run on G; and `docs/schema/` rows (status `unknown`) holding every WP2–WP5 unknown from the source analysis with a first test for each. Phase 1 succeeds when every FAIL the strengthened checks report on the current G is on the recorded expectation list.
- Approach: known
- Depends on: nothing
- Units:

| Unit | Brief | Depends on | May run alongside |
|---|---|---|---|
| 1-01 report binding | `briefs/1-01-report-binding.md` | nothing | 1-02, 1-05, 1-06, 1-07, 1-08 |
| 1-02 R density census | `briefs/1-02-density-census.md` | nothing | 1-01, 1-05, 1-06, 1-07, 1-08 |
| 1-03 bands + review | `briefs/1-03-bands.md` | 1-02 | 1-01, 1-05, 1-06, 1-07, 1-08 |
| 1-04 coverage direction (mfde, vocab) | `briefs/1-04-coverage-direction.md` | 1-03 | 1-01, 1-05, 1-06, 1-07, 1-08 |
| 1-05 shape/container BMT | `briefs/1-05-shape-container-bmt.md` | nothing | all others except 1-09 |
| 1-06 pointers + spotcheck | `briefs/1-06-pointers-spotcheck.md` | nothing | all others except 1-09 |
| 1-07 extraction timing kickoff | `briefs/1-07-extraction-timing-kickoff.md` | nothing | all others except 1-09 |
| 1-08 schema unknown rows | `briefs/1-08-schema-unknowns.md` | nothing | all others except 1-09 |
| 1-09 expectation run and record | `briefs/1-09-expectations-and-close.md` | 1-01, 1-03..1-08 (1-07 finished) | nothing |

### Phase 2 — Coordinate model and header-word census (gate)

- Outcome: `parser/refdata/profile/coord_scale.json` exists, and decoding R at its per-class range and overlaying it against OSM at four named cells (Brisbane CBD, Sydney, rural QLD, outback) puts matched roads within a recorded distance tolerance with no clustering into a sub-region of the cell, clipped links terminating at the cell edge; the header-word rules predict R's words 0, 6, 7, 9, 10, 11 on held-out cells at ≥99%, with every exception (R's word 0 differs from the first data-slot offset in 42 of 939 sampled leaves) explained; the tolerance is the Phase 1 band and "no clustering" is measured as the occupied fraction of the cell extent and coordinate maximum relative to the cell. If either fails, the phase does not close: the design is bounced for re-analysis (user decision).
- Surfaces: new `coord_scale.json`; a census tool under `parser/tools/`; `parser/kiwiw/coordconv.py` (read-only here); `parser/kiwiw/parcel.py` decode paths; `docs/schema/` rows for the model.
- Approach: known
- Depends on: Phase 1
- Units:

Units, as re-briefed for the restart (Decisions, "Amendment 2026-09-22 (user) — Phase 2 restart"). 2-01 and 2-02 are already done and committed and are neither re-run nor re-briefed; 2-03 is superseded by 2-08. The two bug fixes gate the overlay re-run, and 2-04 depends on everything.

| Unit | Brief | Depends on | May run alongside |
|---|---|---|---|
| 2-01 coordinate-range census (R per level/class/division; class rule; L0 density basis) — **done (2cbe296)** | `briefs/2-01-coord-range-census.md` | nothing | nothing |
| 2-02 header-word census and rule (words 0, 6, 7, 9, 10, 11; 42 exceptions; held-out) — **done** | `briefs/2-02-header-word-census.md` | 2-01 | — |
| 2-03 overlay vs OSM at four cells — **superseded by 2-08** (first run's record: `EVIDENCE-2-03.json`) | `briefs/2-03-overlay-test.md` | 2-01 | — |
| 2-05 L0 sparse coordinate frame in `harness/walk.py` (leaf vs frame; re-derive `density.json`) | `briefs/2-05-l0-sparse-frame.md` | nothing | 2-07 |
| 2-06 y orientation in `coordconv` and every copy of its formula | `briefs/2-06-y-orientation.md` | 2-05 | 2-07 |
| 2-07 word-7 (pmcode) adoption in the census tool and `coord_scale.json` | `briefs/2-07-word7-adoption.md` | nothing | 2-05, 2-06, 2-08 |
| 2-08 overlay re-run against the redefined gate (relative discrimination + R-only measures) | `briefs/2-08-overlay-rerun.md` | 2-05, 2-06 | 2-07 |
| 2-04 schema rows and gate verdict (redefined criteria) | `briefs/2-04-schema-rows-and-gate.md` | 2-05, 2-06, 2-07, 2-08 | nothing |

Units, as re-briefed for the grounded gate (Decisions, "Amendment 2026-09-23 (user) — grounded phase gates"). 2-01 through 2-08 are history and are neither re-run nor re-briefed; 2-04's gate verdict is superseded by 2-12. Criteria 1 and 5 already have committed tested tools (`coord_scale_census.py`, `header_word_census.py`) and get no new unit — 2-12 re-runs them. Criteria 2, 3 and 4 have no implementation under `parser/` and get 2-10 and 2-11, both of which need the neighbour lookup 2-09 builds.

| Unit | Brief | Depends on | May run alongside |
|---|---|---|---|
| 2-09 R leaf-neighbour lookup (block- and blockset-crossing) | `briefs/2-09-neighbour-lookup.md` | nothing | nothing |
| 2-10 cross-parcel continuity + divided quadrant containment (criteria 2, 3) | `briefs/2-10-continuity-and-quadrant.md` | 2-09 | 2-11 |
| 2-11 boundary-node mirror across resolved neighbours (criterion 4) | `briefs/2-11-boundary-mirror.md` | 2-09 | 2-10 |
| 2-12 grounded gate verdict (criteria 1–5) and schema rows | `briefs/2-12-grounded-gate-verdict.md` | 2-09, 2-10, 2-11 | nothing |

Units, as re-briefed after the grounded gate returned NOT CLOSED (Decisions, "Amendment 2026-09-23 (design agent) — the adjacency unit is the frame, not the leaf slot"). 2-09 through 2-12 are history and are neither re-run nor re-briefed; 2-12's gate verdict is superseded by 2-15. The cause of criteria 2 and 4 failing was that `r_neighbours` steps one leaf slot where the L0 sparse frame is a 4x4 tile, so 2-13 fixes the adjacency unit, 2-14 re-runs both censuses on it, and 2-15 gives the verdict.

| Unit | Brief | Depends on | May run alongside |
|---|---|---|---|
| 2-13 frame adjacency and the global raw lattice in `r_neighbours.py` | `briefs/2-13-frame-adjacency.md` | nothing | nothing |
| 2-14 continuity and mirror re-run on frame adjacency (criteria 2, 3, 4) | `briefs/2-14-continuity-and-mirror-rerun.md` | 2-13 | nothing |
| 2-15 grounded gate verdict (criteria 1–5) and Assumption Ledger | `briefs/2-15-grounded-gate-verdict.md` | 2-13, 2-14 | nothing |

### Phase 3 — Native coordinates

- Outcome: after assembly from the existing spool (encoders derive pixels from lat/lon; no re-extraction), decoding G shows per-level, per-class, per-division-state coordinate maxima equal to `coord_scale.json`; `range_for` feeds both the Python and C encoders (no `COORD_RANGE` constant remains); the `coord_scale` check PASSES; two builds are byte-identical at worker counts 1/4/12; `pytest parser/tests` passes.
- Surfaces: `parser/kiwiw/{coordconv,synth,cenc,spool}.py`, `parser/kiwiw/_cenc.c`, `parser/osm_to_parcel_geometry.py`, `parser/build_alldata.py`, new `coord_scale` check, `parser/tests/{test_cenc,test_synth_*,test_spool_binary,test_build_alldata}.py`.
- Approach: known
- Depends on: Phase 2
- Units:

Refined against the Outcome as amended 2026-09-23 ("grounded phase gates"), which supersedes the maxima-equality clause above with zero parcels exceeding their class range plus a per-vertex quantisation round-trip. The migration is staged so each unit leaves the tree green: 3-01 lands `range_for` and the decode side behind a temporary legacy default, 3-02 threads the range into both encoders with output bytes unchanged, 3-03 supplies the real per-parcel ranges and deletes the legacy constant (this is where the disc's bytes change), and 3-04 builds the measurements in parallel on entirely new files. The determinism matrix is six full builds (roughly an hour), so it splits at the kickoff per the refine rule: 3-05 runs it and hands off shas, 3-06 verifies the phase outcome clause by clause.

Surfaces beyond the list above, found in recon and in scope: `parser/kiwiw/{road,background,name,model,road_writer,background_writer,divide}.py`, `parser/harness/walk.py`, and the four `parser/tools/` censuses that invert the decoder's scale (`coord_scale_census`, `continuity_census`, `boundary_mirror_census`, `road_density_census`, `overlay_test`) — changing only one side of the conversion would silently move Phase 2's committed evidence. The `1 << 15` occurrences in `parser/kiwiw/{volume,volume_writer,route_planning}.py` and `parser/osm_to_route_planning.py` are bit flags, and `COORD_RANGE_RL` in `parser/tools/header_word_census.py` is a route-planning-layer constant; none is in scope for the "no `COORD_RANGE` constant remains" source check.

| Unit | Brief | Depends on | May run alongside |
|---|---|---|---|
| 3-01 `range_for` and the decode side taking its range from the frame | `briefs/3-01-decode-side-range.md` | nothing | nothing |
| 3-02 both encoders take the coordinate range as a parameter (bytes unchanged) | `briefs/3-02-encoders-take-range.md` | 3-01 | 3-04 |
| 3-03 the build path supplies each parcel's real range; the legacy constant dies | `briefs/3-03-build-path-supplies-range.md` | 3-01, 3-02 | 3-04 |
| 3-04 the `coord_scale` check and the per-vertex quantisation round-trip | `briefs/3-04-coord-scale-check-and-roundtrip.md` | 3-01 | 3-02, 3-03 |
| 3-08 the parse path takes each frame's real range; `PARSE_RANGE` dies (added 2026-09-24, fixer for 3-03's finding) | `briefs/3-08-parse-path-range.md` | 3-03 | nothing |
| 3-07 clip background geometry to the frame, as R does (added 2026-09-24 by the orchestrator on R evidence) | `briefs/3-07-clip-to-frame.md` | 3-03, 3-04, 3-08 | nothing |
| 3-09 every cell a background shape overlaps receives it (added 2026-09-24, fixer for 3-07's edge content loss) | `briefs/3-09-shape-to-every-overlapped-cell.md` | 3-07 | nothing |
| 3-10 a point outside coverage is not clamped into an edge cell (added 2026-09-24, fixer for the name-anchor round-trip failure) — **re-scoped and re-sequenced 2026-09-25**, see the 3-10 row below | `briefs/3-10-name-cell-clamp.md` | — | — |
| 3-11 mult_const selection for exact-rectangle background shapes (added 2026-09-24, fixer for 3-09's disc-size concern) | `briefs/3-11-mult-const-selection.md` | 3-09 | 3-10 |
| 3-12 re-measure overlap duplication cost after mult_const, trim if it still dominates (added 2026-09-24) — **withdrawn 2026-09-25**, superseded by Phase 3C and 3-13 | `briefs/3-12-overlap-duplication-remeasure.md` | — | — |
| 3-10 (re-scoped 2026-09-25): extractor half in Python; the assembly drop guard in C inside E2 | `briefs/3-10-name-cell-clamp.md` (to be re-briefed) | Phase 3C | 3-13 |
| 3-13 re-measure interior-cell duplication's share of disc size on the C pipeline; trim in C only if it dominates (added 2026-09-25) | to be briefed | Phase 3C | 3-10 |
| 3-05 the determinism matrix (kickoff and hand-off), on the C pipeline | `briefs/3-05-determinism-matrix.md` (to be re-briefed) | Phase 3C, 3-10, 3-13 | nothing |
| 3-06 Phase 3 evidence against the amended outcome, plus the Contract H budget table | `briefs/3-06-phase-evidence.md` (to be re-briefed) | 3-04, 3-05, 3-07, 3-09, 3-10, 3-11, 3-13, Phase 3C | nothing |

As amended 2026-09-25, the last four rows above are authoritative for 3-10, 3-13, 3-05 and 3-06. Units 3-01 to 3-04, 3-07, 3-08, 3-09 and 3-11 are done and stand. Phase 3 is paused after 3-11 while Phase 3C runs, and resumes with 3-10 and 3-13. Phase 3 closes only after Phase 3C closes.

Phase 2's final Carried items are placed as follows. **Absorbed into Phase 3:** none of the open items belongs to it — the three Phase-3-relevant observations (the `COORD_RANGE` duplication across `coordconv`/`synth`/`osm_to_parcel_geometry`/`_cenc.c`, the 2-06 y-orientation result that every new signature must preserve, and the rebuild-cost premise that the spool carries lat/lon for every vertex kind) are written into 3-01, 3-02 and 3-03 as contract, and the rebuild-cost premise was re-confirmed against the code, with the correction that both encoders currently *prefer* the spool's 32768-scale `n_x`/`n_y` columns, which 3-02 must remove for spool reuse to be sound. **Left with their owners:** items 2 (pointer non-frame targets, Phase 9's), 3 (`road_density_census.py`'s stale `LENGTH_BASIS` wording, cosmetic), 4 (`pointer_nonframe_targets.examples` not regenerating identically), 9 (`continuity_census.py`'s greedy double-count), 10 (prior Phase 1 items). **Bounced to Open Questions**, because each touches a contract or a phase outcome rather than an implementation: item 1 (`rg_size`, word 16) and item 8 (the `RESIDUAL_ENUM_CAP` 400-vs-200 contradiction).

### Phase 3C — Build pipeline in C at the cell-range boundary

- **Outcome.** At phase close, all of the following hold:
  - `build_alldata.py` crosses into C only through E1 and E2, each once per cell range with equal call counts, and through the H4 assembly copy, as Contract B defines them. E3 is gone.
  - None of the following exists anywhere in `parser/`, checked by grep: `parser/kiwiw/overlap.py`, `clip.py` or `divide.py`; `synth.py`'s `build_road_frame_bytes`, `build_background_frame_bytes`, `build_name_frame_bytes` and `build_map_frame_bytes`; `cenc.py`'s per-cell API (`kw_encode_cell`); `KIWIW_NO_C`; extractor imports in `build_alldata.py`.
  - A full-Australia build at `-j 12` from `output/extract_timing/spool` produces `ALLDATA.KWI` with sha256 `87a01b14b612d58ba49f326542339ef4d6fc1871c9201842c7961108a2797862` (1,731,021,568 B), the 3-11 disc. Its manifest counters are equal to 3-11's.
  - E2's declined list is empty at every level.
  - The Perth fixture build is byte-identical at `-j 1` and `-j 4` (sha256 `da13a775…`).
  - The bench record shows every Contract H budget met: full wall ≤ 60 s, L0 ≤ 38 s with pre-pass ≤ 5 s, L2 ≤ 2 s, L4–L12 ≤ 2 s, outside-encode ≤ 10 s. It also shows the per-level Python / C / handoff split.
  - `pytest parser/tests` passes. It runs the Contract T layers: boundary tests, the C unit-test binary, and the goldens.
  - No test imports a deleted module, and no test compares C against a Python encoder.
  - The redesigned `quantisation_roundtrip` and `coord_scale` meet their verification-tool outcomes (0 background failures and exactly 1 name-anchor failure; PASS with 0 of 1,461,347 parcels), each in ≤ 120 s at `-j 12`.
  - `docs/ARCHITECTURE.md`'s module map and its "C kernel" and "Spill and indexed assembly" contracts describe Contract B, not the per-cell kernel.
- **Stages.** The order is fixed; refine cuts the units.
  - **Stage 0, baseline and scaffolds:**
    - re-measure the 3-11 build three times with the split, which gives the run-to-run spread (the 3-11 attribution of its 105–123 s spread is ledgered as wrong);
    - bench-record instrumentation for the split;
    - the Contract T layer (a) harness and the layer (b) binary build;
    - golden capture for every fixture range.
    The verification-tool redesigns run alongside Stage 0. They must land before Stage 1 deletes `overlap.py`.
  - **Stage 1, E1 and E2 take the overlap scan, the merge and the per-cell encode (the profile's largest block, about 55–60 s of L0).**
    - Divisions are still declined. The transitional Python divide consumes E2's merged content and measures through E3.
    - Delete `overlap.py`, the per-cell ctypes path, and their internals tests.
  - **Stage 2, division, retile, trim and name halo move into E2.**
    - The declined list becomes empty.
    - Delete `divide.py`, `clip.py`, E3, E2's merged-content output, the per-frame Python in `IndexedLayout`'s divided blocks, `synth.py`'s build encoders, `KIWIW_NO_C` and the no-compiler fallback, and `test_cenc.py`'s C-vs-Python cases.
    - `frame_range` moves to `kiwiw/mesh.py`.
    - Harness tests stop fabricating fixtures through `synth`.
  - **Close:** rewrite `docs/ARCHITECTURE.md` and verify the budget table.
- **Step gates.** Every stage 1 and stage 2 step that changes the build path is gated on all of these:
  - the full-disc sha `87a01b14…` at `-j 12`;
  - Perth `-j 1` == `-j 4`;
  - the goldens;
  - a step wall within Contract H's regression rule.
  Each step deletes the Python it replaced in the same unit.
- Surfaces:
  - `parser/kiwiw/_cenc.c` (may split into several C sources), `parser/kiwiw/cenc.py`;
  - `parser/build_alldata.py`;
  - `parser/kiwiw/{overlap,clip,divide,synth,spill,frame_table,alldata_writer,mesh}.py`;
  - `parser/tools/{quantisation_roundtrip,bench_build}.py`, the `coord_scale` check and census;
  - `parser/tests/` (`test_cenc`, `test_clip`, `test_divide`, `test_overlap`, `test_synth_*`, `test_harness_*`, `test_name_encode`, `test_alldata_writer`, and new boundary, golden and C-unit tests), `parser/tests/fixtures/`;
  - `docs/ARCHITECTURE.md`, `docs/provenance.md` (if any fixture is not committed).
- Approach: known. The byte-exact C parity technique (`-ffp-contract=off`, `rint`, identical operation order) is already proven by `_cenc.c`, and every step has a byte-identity yardstick.
- Depends on: Phase 3 units 3-01 to 3-04, 3-07, 3-08, 3-09 and 3-11.
- **Downstream effect.** Phase 3 resumes after this phase (3-10, 3-13, 3-05, 3-06). Phases 4–10 name Python build modules (`synth`, `divide`) in their Surfaces lists. From this phase on, those surfaces are read as the C sources behind E1/E2, and Contract B governs where the work lands.

### Phase 4 — Header words and per-sub-frame size cap

- Outcome: header words 0, 6, 7, 9–11 match the model on every parcel except the WP2-owned exemption list and the Phase 2 explained exceptions; `dipid` is valid on divided and undivided parcels; the `header_words` check PASSES; the size cap applies per sub-frame at 131,070 and the whole-frame cap is gone; output bytes are unchanged where no sub-frame exceeds R's maxima; the stale comment at `synth.py` ~942 is corrected; builds are reproducible.
- Surfaces: `parser/kiwiw/{synth,parcel,divide,parcel_mgmt}.py`, `parser/build_alldata.py`, `parser/harness/checks/{envelope,decode}.py`, new `header_words` check, `parser/tests/{test_divide,test_synth_map_frame,test_build_alldata,test_harness_mfde}.py`.
- Approach: known
- Depends on: Phase 3

### Phase 5 — Geometry generalisation and division

- Outcome: on a full-Australia build, per-level vertices per link and vertices per km fall within the band recorded in `harness.json` around R's (L8 roads ≈ R's 28.9k vertices from 107k; urban L0 within band), intermediate points are written as `nip` deltas by both encoders, each sub-frame above 2× R's per-kind maximum at L0–L8 is an advisory with a ledger cause, and divided-parent counts fall toward R's (2×2 preferred; L0 far below the current 533).
- Surfaces: new `parser/refdata/generalise.json` and a generalisation stage in or beside `osm_to_parcel_geometry.py`; `parser/kiwiw/{synth,divide,road_writer}.py`, `parser/kiwiw/_cenc.c`/`cenc.py`; envelope and new density checks; `parser/tests/{test_road_encoder,test_cenc,test_divide}.py`.
- Approach: known
- Depends on: Phase 4

### Phase 6 — Background classes and ocean polygons

- Outcome: G's background type and count distribution per level, including reserves (321) and rivers/lakes (291), match R's per-class census within the Phase 1 band; L0 CBD cells hold shape counts in R's order of magnitude (Melbourne/Sydney/Adelaide/Perth CBD cells recorded against R's 17/31/23/122); every cell in the sampled 0.25° grid that R fills with sea carries an ocean polygon (type 289; sea names belong to Phase 8); the 102 G-only L0 cells are listed with lat/lon and content and each is classified natural or defect; the catch-all `288` cells are audited (land mislabelled as sea = 0); foreign land is the only listed cell content missing from R.
- Surfaces: `parser/refdata/{selection,vocab/bg_type}.json`, `parser/osm_to_parcel_geometry.py` (background loop, bg predicate ~694, coastline/land-polygon handling), background encode path in `parser/kiwiw/synth.py`/`_cenc.c`, `parser/tests/{test_vocab,test_selection,test_background_encoder,test_parcel_geometry}.py`.
- Approach: known
- Depends on: Phase 5

### Phase 7 — Road vocabulary and level selection

- Outcome: for streets present in both R and G (name-matched cells), G's road type and display class equal R's for ≥ a recorded share (named arterials Ipswich Rd, Logan Rd, Bradfield Hwy, Pacific Motorway, Cahill Expressway resolve to R's class); at L2–L8 the type distribution is within the band of R's (type 2 as backbone); tracks are not in R's arterial class; dual-carriageway duplicate geometry at coarse levels is within R's density; the `road_vocab` check PASSES.
- Surfaces: `parser/refdata/vocab/{road_type,display_class}.json`, `parser/refdata/selection.json`, `parser/kiwiw/{vocab,selection}.py`, `parser/harness/checks/vocab.py` and new `road_vocab`, `parser/tests/{test_vocab,test_selection}.py`.
- Approach: known
- Depends on: Phase 6 (sequenced after it: both edit `selection.json`)

### Phase 8 — Name structure

- Outcome (sea/ocean names are owned here, not by Phase 6): in G, every populated cell carries a region or ocean name; string types 4 (`A=`, `1=`, plain), 5 (per segment), 6 and 1 are emitted in proportions within the band of R's per-level mix; all text is uppercase ASCII; `priority` and `display_scale_flag` values on every name record are drawn from R's observed set; the `name_coverage` check PASSES and a dry-run tally shows the L0 name_count against R's 19.08M, with any remaining shortfall attributed record-by-record to source text OSM lacks.
- Surfaces: `parser/osm_to_parcel_geometry.py` (`_make_name_record` ~530 and name gates), `parser/refdata/selection.json`, `parser/build_alldata.py`, `parser/kiwiw/{cenc,model,spool}.py`, `parser/kiwiw/_cenc.c`, `parser/kiwiw/vocab.py` (remove the `string_type=1`-at-L0 rejection; R has 1,042,019 such records), `parser/kiwiw/synth.py` (name encoders ~528–719, latin-1 sites), `parser/kiwiw/name_writer.py` unchanged for round-trip, `parser/harness/checks/vocab.py`, new `name_coverage`, `parser/tests/{test_name_encode,test_name_encoder,test_name_record_vocab}.py`.
- Approach: known
- Depends on: Phase 6

### Phase 9 — Link flags, node bits and neighbour pointers

- Outcome: flag and node-bit prevalence per level within the band of R's (`link_id_flag`, `selected_link_flag`, `route_planning_tag`, toll, bridge, tunnel, planned); mfde entries 12–19 carry computed adjacent-parcel pointers that decode to the correct neighbouring Map Frame in the harness, with entry counts matching R's distribution including divided-neighbour records; `docs/schema/flags.md` exists and every link flag and node bit R uses has a row (R census, OSM source, known/unknown, G value, pending test); no flag is undocumented.
- Surfaces: `parser/osm_to_parcel_geometry.py` (flag defaults ~470–475), `parser/kiwiw/{synth,road_writer,divide,parcel_mgmt}.py`, `parser/harness/checks/{mfde,decode}.py`, `parser/tests/{test_road_encoder,test_boundary_links,test_harness_mfde,test_synth_map_frame}.py`.
- Approach: known
- Depends on: Phases 4, 5, 6 and 8 (both edit `synth.py`, `osm_to_parcel_geometry.py` and the mfde/decode checks, so they are sequential)

### Phase 10 — Full rebuild, verification and ledger closure

- Outcome: a single full-Australia extraction and build from the final code produces a `compare_disc.py` report (bound to its ALLDATA sha256) in which every check PASSES or its remaining difference is a ledger entry with a source-data cause, contributing no processing-caused differences; entries are only *natural* or *documented-unknown* (a flag-table entry with a pending test); `docs/design/target-disc.md`, plan 01's records and `docs/schema/` rows are updated (status changes carry evidence) (deviation ledger, word 0, mfde 12–19 ownership, size semantics); the user has accepted or rejected the final ledger; capacity is within 4.7 GB; determinism verified by two builds.
- Surfaces: `output/`, `docs/design/target-disc.md`, `docs/schema/`, `docs/plans/01-eval-harness-and-map-layer.md`, `docs/provenance.md`, `docs/schema/flags.md`.
- Approach: known
- Depends on: Phases 7 and 9

## Provenance Notes

- Brief 34 removed R-derived size caps ("R's maxima are observations, not limits") — correct in spirit, but it applied the u16 limit to the wrong quantity. The evidence that header word 0 is the header size means the ceiling is per sub-frame; the 2×-R advisory retains the safety signal without inventing a build limit the format does not have.
- The plan-01 claim that R's 19M L0 names include address strings OSM lacks was not supported by a stride sample; the gap is mostly structural (name coverage per cell, per-link copies, type-4/1 tags), so it is treated as a defect until re-measured.
- Rejected: continuing with the current 32767 constant while flagging risk (user chose hard stop); divergent-candidate builds for ocean polygons or road vocabulary (user: one canonical approach, research first).
- The stale `output/report.json` (pre-brief-34) is why Phase 1 binds reports to a build hash before anything else is trusted.
