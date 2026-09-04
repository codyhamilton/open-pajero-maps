# Phase 3 — OSM ingestion and content pipeline

## Goal
Generate real map content from OpenStreetMap data for the target region, matching
the KIWI-W structures identified in Phase 1, built up incrementally:
roads only -> + names -> + POIs -> + address search, with an in-vehicle test after
each sub-checkpoint.

## Pipeline plan (synthesized 2026-09-01)

> **Status note 2026-09-04.** Stages 1–3 and the joint Link ID registry below
> were implemented on 2026-09-02 (`osm_to_parcel_geometry.py`, `kiwiw/synth.py`,
> `kiwiw/link_id_registry.py`, `osm_to_address_index.py`, `build_alldata.py`;
> commits `83169fa`..`540433c`) but are not yet described in this file. Their
> known deviations from the reference disc (name `string_type=1`, 3-entry mfde
> table, single-level assembly, Perth-only defaults) and the corrected program
> plan live in `docs/design/target-disc.md` and `docs/plans/`. The "in-vehicle
> test after each sub-checkpoint" phasing in this file is superseded there.

This section is a concrete, gap-annotated implementation plan for the full
OSM PBF → working disc image pipeline, written after Phase 2's byte-identical
round-trip writers were all proven. It supersedes the "not started yet" stub
that was here before. The detailed per-task progress notes from the
out-of-sequence route-planning work follow below.

### What the pipeline must produce

Starting from an OSM PBF extract:

1. `ALLDATA.KWI` — main map data (roads, background geometry, names, parcel
   management records, route planning frames)
2. `IDX/*.IDX` — address/POI search index chain (street names, address ranges,
   POIs, city selection)
3. `SPEC.KWI`, `METADATA.KWI`, `COUNTRY.KWI`, `VERSION.TXT`, `COVERAGE.BIN`,
   `DN/CLUSTER.DAT`, `PCT2MNG.KWI` — small metadata files (regenerable from
   new region parameters via `misc_writer.py` — already fully understood)
4. Copy-through unchanged from the reference disc: `LOADING.KWI` (firmware,
   ~31MB), `DICVCE56.KWI`, `GRA256D.KWI`, `KGRA256.KWI`, `PCT256D.KWI`,
   `KPCT256.KWI`, `PCT2DAT.KWI`, `KPCT2DT.KWI`, `KGRPDAT.KWI`, `VAR256D.KWI`,
   `COVERAGE/AUC.BMP`

Unknown status: `HWMAP.KWI` (highway overview, not decoded), `INDEXDAT.KWI`
(index data management, not decoded). Whether firmware requires these for
basic routing/search is untested — safe to copy through unchanged initially
and only invest in them if in-vehicle testing reveals a failure.

### Stage 1 — OSM geometry extraction and parcel tiling

**What exists**: `build_route_graph.py` extracts the routing intersection
graph from OSM PBF via pyosmium (ways, node coordinates, turn restrictions)
for a bounded bbox. No code exists for extracting display geometry — road
polylines, background polygons, or place names.

**What is missing**:

- A parcel tiling strategy: given a target region (e.g. Western Australia),
  decide how to carve it into block sets/blocks/parcels matching the KIWI-W
  mesh structure. The real disc uses 7 levels (12/10/8/6/4/2/0) with
  increasing tile density toward level 0. The tile counts (n_blocks_lat ×
  n_blocks_lng per level) need to be chosen and encoded into the LMR. No
  guidance on what counts to use — will need to be determined empirically or
  derived from the real disc's own LMR values and scaled.

- An OSM way geometry extractor that produces parcel-local road polyline
  coordinate chains (the source material for RoadLink records), not just
  intersection nodes. `build_route_graph.py` collapses each inter-node way
  segment to a single link length, discarding intermediate shape nodes — those
  shape nodes are needed for rendering.

- An OSM area/multipolygon → background shape extractor (coastlines, land use,
  water bodies, administrative boundaries that feed `BackgroundFrame`).

- An OSM addr/name tag → name record extractor (street names, place names,
  suburb names for `NameFrame`).

**Complexity: Large.** This is the single largest gap in the pipeline. Nothing
here exists yet; it is the prerequisite for building any real `ALLDATA.KWI`
parcel content.

### Stage 2 — Road-link encoder

**What exists**: `parcel_writer.write_road_frame()` serializes a `RoadFrame`
by replaying `RoadLink.raw_bytes` verbatim from the real disc. There is no
encoder that takes semantic fields (coordinate chain, road class, speed,
display class, connectivity flags) and produces new raw bytes.

**What is missing**: A road-link encoder for the multilink/polyline format
decoded by `road.py`. The format is high-confidence (kiwiread.c corroborates
it): 16-byte link header (road type, display class, node count, shape length,
connectivity flags, lattr), delta-encoded parcel-local coordinate pairs (6
bytes per pair from `coordconv.decode_region_coord`), and a per-display-class
display-flag word. The existing decoder in `road.py` shows every field but the
writer only replays `raw_bytes` — no inverse of `decode_region_coord` /
`encode_region_coord` has been written.

**Complexity: Medium.** The format is well understood; the encoder is
straightforward to build from the decoder. The fiddly part is the
parcel-local coordinate system (delta encoding, parcel-local origin
derived from the block bounds) — the inverse of `coordconv.xy_to_latlon`.
Prerequisite for generating any new map parcel.

### Stage 3 — Background and name frame encoders

**What exists**: `parcel_writer.write_background_frame()` and
`write_name_frame()` replay verbatim raw bytes. No encoder from semantic
fields exists for either.

**What is missing**:

- Background: OSM polygon/area geometry → background shape records. The
  background format (coordinate chains, background type codes, optional name/
  auxdata trailers) is medium-confidence (Phase 1: "inferred, not
  spec-confirmed"). The road-type code mapping from OSM tags to KIWI-W
  background codes is only ~50% identified — an OSM→code mapping will
  necessarily have gaps and best-effort choices for uncatalogued types.

- Names: OSM name/addr tags → name records. The `string_type=4` (Linear-B)
  format is now understood (Phase 2 parcel content pass fixed the 2-byte
  miscount and confirmed `na`-derived record boundaries). Other string types
  (0, 2, 3, 7) remain undecoded; only type 4 can be generated from scratch.
  The name record's header word is currently replayed verbatim.

**Complexity: Medium-large for background** (code-mapping uncertainty is the
main risk; the format itself is tractable). **Medium for names** (type 4 is
understood, but building the tag-extraction, deduplication, and coordinate
assignment logic takes work).

### Stage 4 — Route planning hierarchy (at scale)

**What exists**: This is the most complete stage. `contraction.py` implements
real Contraction Hierarchies; `build_route_hierarchy.py` builds a 4-level
(2/4/6/8) region tree with boundary nodes and cross-region escape links;
`route_planning_writer.py` encodes all Ch.9/Ch.10 record types including the
Road Reference Table (aggregated-intersection clustering). Self-consistent
round-trip confirmed over a small 2×2-tile test area. All 28 tests pass.

**What is missing (honest gaps, from docs)**:

- Scale: the current builder targets a small test area. Scaling to a full
  region (thousands of regions across Australia) needs a spatial tiling
  strategy, load-balanced region tree, and efficient multi-pass CH contraction.
  The 26.6× node-density gap between raw OSM and real-disc level-2 regions is
  measured; what it implies for CH contraction depth at country scale is not.

- `DEFAULT_LEVEL_FRACTIONS` (the per-level node-population split: 55/25/13/7%)
  is a defensible heuristic, not a measured disc statistic. The real per-level
  population fractions were never established.

- The `uppermost_identical_level` 3-bit encoding (`level/2`) is not
  independently spec-confirmed.

- `cluster_nodes()` does not yet propagate `global_id` / `uppermost_identical_level`
  from cluster members — needs a decision when combined with the hierarchy builder.

- **Cross-layer Link ID assignment**: the route-planning frame's "Link ID
  Number" field (Ch.10.10.2) connects each RP link to its counterpart in the
  main map's `RoadFrame`. Currently synthetic (sequential) because no main-map
  link writer existed when this was built. A real pipeline needs Link IDs
  assigned jointly across both layers during parcel geometry extraction (Stage 1).
  This is the most critical inter-stage dependency.

**Complexity: Encoding machinery is done. The outstanding work is Large at
country scale** (spatial tiling, region tree, joint Link ID assignment).

### Stage 5 — Address and POI search index generation

**What exists**: `index_writer.py` and `roundtrip_idx_full.py` can write and
reassemble `SADSR201.IDX` from a parsed intermediate representation
(fromscratch mode: self-consistent after re-parse, byte-layout provably
different from the original). The self-describing DCTF/matching-record format
is fully understood. Street name search (38,120 records), address ranges
(344,276 records, all fully verified by the full-file pass), and nested city
selection frames all round-trip correctly for the real disc's data.

**What is missing**:

- No code to build the IR from OSM data. A new extractor is needed that reads
  OSM PBF and populates: SRMX street name records (STID, KYCH name, NXST, NXCT
  cross-reference fields); SRT1 address-range records (RLXY geocoded
  coordinate, HSST/HSEN house-number range, Link ID); SRHA city-selection
  records; POISR POI records (name, category, geocoded coordinate). All of
  these need the DCTF field schema and STFG presence bitmaps to match.

- The `category_data` blob (ARCD/CTGY tables) is not decoded and cannot be
  regenerated. The real disc's category tables drive how streets/POIs are
  classified for the on-screen category filter. This is a significant unknown;
  the safest first approach is to copy the category blob verbatim from the
  reference disc and only add new categories if the firmware rejects the file.

- `POISR201.IDX` whole-file assembly is not complete: decode bugs remain
  (nibble-field pairing, city-name matching records overrunning record
  boundaries) from the Phase 2 full-file pass.

- The city-name (SRHA) matching-record decode bug is pre-existing and unresolved.

- 7 levels per index type (SADSR201..207, POISR201..207, etc.): only
  SADSR201 (level 1) is proven. The other levels have the same format but have
  never been assembled from scratch.

**Complexity: Large.** Building a sorted, self-consistent street/POI database
from OSM and encoding it into the KIWI-W schema — including handling the
STID/NXST/NXCT cross-reference graph between city, street, and address-range
frames — is the dominant unsolved problem for the address-search feature.

### Stage 6 — Final file assembly

**What exists**: `alldata_writer.py` assembles `ALLDATA.KWI` from loaded
region data in de novo mode (self-consistent, tested on levels 6 and 8: 84
structures, all re-parsed consistently). The metadata files are trivially
regenerable via `misc_writer.py` (7/7 byte-identical for the reference disc).

**What is missing**:

- De novo assembly tested only on levels 6/8 (a few hundred parcels). Not
  validated on the larger levels 0/2/4 that hold most of the disc's real
  content; the allocation logic should be the same but at much higher volume.

- The "management frame" at real-disc file offset 4096..6144 is not reproduced
  by the de novo assembler. What it contains and whether the firmware requires
  it for routing/search is unknown — the safe first approach is to copy it
  from the reference disc or leave the slot empty and test in-vehicle.

- Route-planning cross-layer placement: mfde entries in the `MapFrame` that
  reference route-planning data (the entries with absolute-disc-sector-looking
  offsets, carried as opaque table entries in Phase 2) need to be placed
  correctly in the assembled file. This requires the joint Link ID assignment
  from Stage 4 to be resolved first.

- Volume header fields (coverage bounds, disc title, data version, maker
  identification stamps) need updating for the new region/data.

- POISR201.IDX full assembly not done; SADSR202..207 and POISR202..207 untested.

**Complexity: Medium** for ALLDATA.KWI (extending proven de novo logic to more
levels, updating pointer fields). **Large** for IDX full set (depends on Stage 5).

### Recommended implementation order

Ordered from highest-confidence/lowest-risk to hardest/most uncertain:

1. **Metadata files** — regenerate `SPEC.KWI`, `METADATA.KWI`, `COUNTRY.KWI`,
   `VERSION.TXT`, `COVERAGE.BIN` from new region parameters. Already fully
   understood; a few-hour task. Prerequisite: final target coverage bounds.

2. **Parcel-local coordinate encoder** (Stage 2 prerequisite) — implement
   the inverse of `coordconv.decode_region_coord` / `xy_to_latlon` so that a
   WGS84 lat/lon can be expressed as a parcel-local delta-encoded pair. Needed
   by every subsequent encoding stage.

3. **Road-link encoder** (Stage 2) — implement the `RoadLink` encoder from
   semantic fields (coordinate chain, road class, display class, connectivity)
   to raw bytes, tested against a hand-crafted minimal parcel. Medium
   complexity; unblocks Stage 1.

4. **Background and name encoders** (Stage 3) — implement encoders for Linear-B
   name records and background shapes. Can be done in parallel with Stage 2
   once the coordinate encoder exists.

5. **OSM geometry extractor and parcel tiler** (Stage 1) — the largest new
   engineering task. Build the OSM PBF → parcel geometry pipeline: road
   polylines, background polygons, name records, and a tile tiling strategy.
   Stages 2-4 must be done first so that each extracted OSM object can be
   immediately encoded and tested.

6. **ALLDATA.KWI full assembly at scale** (Stage 6 core) — extend the de novo
   assembler to all 7 levels with the new tile grid, update LMR/BSMR/BMT.
   Depends on Stage 5.

7. **Route planning at scale** (Stage 4 extension) — extend the hierarchy
   builder to the full target region, resolve joint Link ID assignment with
   the main map layer. Depends on Stage 5.

8. **Address index generation** (Stage 5 core) — extract street names, house
   numbers, POIs from OSM and populate DCTF/matching-record format into a
   self-consistent SADSR/POISR index set across all 7 levels. The largest
   single unsolved problem in the pipeline; depends on nothing except
   pyosmium and the existing index writer.

9. **In-vehicle testing** after each sub-checkpoint: roads only → +names →
   +POIs → +address search, per the original Phase 3 goal.

### Where the real difficulty lies

All the byte-encoding writers are complete or straightforwardly extensible.
The hard work is not "how to encode a given structure's bytes" — that is
solved — but "how to extract, tile, and organize OSM data into the right
structure." Specifically:

- **Stage 1 (parcel geometry extraction)** is the critical-path blocker for
  any real ALLDATA.KWI content.
- **Stage 5 (address index generation)** is the dominant unsolved problem for
  address search and the largest single engineering task.
- **Stage 4 (route planning at scale)** has working machinery but needs
  substantial scale engineering and the joint Link ID assignment resolved.

The category_data blob (ARCD/CTGY) and the POISR decode bugs are secondary
risks that can be deferred past the first roads-only in-vehicle test.

## Not started yet (main sequence)
The roads -> names -> POIs -> address-search sequence depends on Phase 2's
round-trip succeeding on real hardware, and hasn't started.

## Early, out-of-sequence work: route-planning writer prototype (2026-08-25)

Route-planning (Ch.9/Ch.10) was investigated ahead of the main Phase 3 sequence
because it was the last major unknown in the disc size-budget analysis (see
`docs/00-overview.md` decision log and `docs/phases/01-format-analysis.md`,
"Route planning / region data"). Once the byte format was decoded, a follow-up
agent built and tested a first prototype writer — this is scoping/risk-reduction
work, not the start of the real roads-first pipeline above.

**What was built** (`parser/kiwiw/route_planning_writer.py`,
`parser/build_route_graph.py`, `parser/osm_to_route_planning.py`):
- Ch.9/Ch.10 encoders — exact inverse of every decoder in
  `parser/kiwiw/route_planning.py` (level/region management records, node/
  link/regulation/between-link-cost/link-cost/node-coordinate records, road
  reference table, ext frames).
- An OSM->routing-graph extractor (pyosmium-based) for one bounded bbox, with
  a first-pass highway-class hierarchy heuristic and OSM turn-restriction
  parsing.
- Per the project owner's explicit instruction, **vendor structure is matched
  by default** rather than simplified away: all fields/frames the spec
  defines are present, including the undocumented "ext" frames (one populated
  with the confirmed 12-byte disc-stamp User ID from the earlier cross-file
  stamp finding, five left absent — matching the real disc's own pattern of
  populating only 1-2 of 6 ext slots per region). Nothing is omitted without
  positive evidence it's unused.

**Test region**: region 178, level 2 (WA, south of Perth) — picked directly
off the disc's own decoded Ch.9 table. Real disc values for this region: 106
nodes, 282 links, 1 rank, `road_class_mask` covering classes 2-3.

**Round-trip result**: encoded 114,216 bytes for an OSM-derived graph over
the same bbox; decoded back via `parse_rp_frame()` plus new record-level
decoders — fully self-consistent (header node/link counts match the decoded
graph exactly, all node/link/cost/coord records check out field-by-field).
Ch.9 header + region-table round-trip separately verified, bbox/level/size
fields recovered correctly through `geo_secs`'s ~1/8-arcsec quantization.
`parser/tests/`: 13/13 passed before and after, no shared `kiwiw/*.py` files
modified.

**A genuine spec-vs-disc discrepancy found and resolved**: Ch.10.10.2 lists
all 6 Link Cost Record fields (incl. the 2-byte Average Travelling Time word)
as mandatory, implying a fixed 16-byte record — but the disc's own
`link_cost_rec_size` Level Management field is **14**, and region 178's
link_cost subframe divides evenly only as `6-byte header + 154*14-byte
records`. Resolved: the Average Travelling Time word is only present when
the rank's `avg_travel_time` flag is set (false for region 178, hence all
14-byte records). This refines the prior "no ambiguity found" note, which
covered the header/subframe-table level, not individual record layout.

**The key finding — quantified evidence of how much graph contraction is
needed**: extracting OSM's primary/secondary/tertiary intersection graph for
region 178's exact bbox (matching its own `road_class_mask`) gives **2,819
nodes / 5,567 links / 3,747 link-cost records**, vs. the real region's
**106 nodes / 282 links** — a **26.6x** ratio. An unfiltered run (all
routable highway classes) gave 16,844 nodes / 40,666 links (~159x),
confirming the gap isn't a tag-selection artifact. Also: of 57,372
OSM turn-restriction relations seen for this bbox, only 1 resolved into the
small graph — most reference roads/nodes too fine-grained for this coarse
level. This is direct evidence that a real level-2 route-planning region is
a heavily contracted, long-distance sparse layer (consistent with the
CH/highway-hierarchy design in the spec), not "the local network filtered to
major road classes."

**Known simplifications in this prototype, explicitly not hidden**: single
standalone region only — no multi-level 2/4/6/8 hierarchy tree or
cross-region boundary-node bookkeeping yet; hierarchy/rank assignment is a
first-pass OSM-highway-class heuristic, not real CH contraction; turn
restrictions only handle simple one-via-node cases; link-cost "Link ID
Number" fields are synthetic; upper_node/upper_link/passage_code/
statistical_cost frames left absent (matches the real disc's near-zero use).

## Aggregated-intersection clustering implemented (2026-08-27)

Follow-up to the "aggregated-intersection clustering unimplemented" line
above. Per project direction, this was promoted from a deferred design
decision to in-scope-now work once measured against the real disc — see
`docs/phases/01-format-analysis.md`, "Ch.10.13 Road Reference Table
(aggregated-intersection clustering, 2026-08-27)" for the full survey.

**Is it actually used on the real disc?** Yes, heavily: 89.6% of the
1,864 real regions (1,670 regions) have a non-empty Ch.10.13 Road
Reference Table, 218,440 Aggregated Node Information records in total,
92.4% of them in level-8 (finest-grain) regions. The prior prototype's
implicit assumption that an always-empty table was a safe simplification
is falsified.

**What was implemented**: `parser/build_route_graph.py`'s new
`cluster_nodes()` merges two kinds of OSM node groups (each plausibly one
physical intersection) into a single `RpNode`: (1) every graph node lying
on an OSM `junction=roundabout`/`circular` way, and (2) connected
components of non-boundary graph nodes joined by links shorter than 20 m
(catching dual-carriageway splits/joins and similarly tight simple
intersections — the real disc's own median of 2 composition links / 1
subordinate node per record suggests this "two nodes merge into one" case
dominates). Cluster size is capped at 1 representative + 5 subordinates,
matching the real disc's observed max. `parser/kiwiw/route_planning_writer.py`
gained `RpAggregatedNode` and `write_aggregated_node_record()`/an extended
`write_road_reference_table()` that encodes non-empty tables matching the
byte layout decoded from the real disc (see Phase 1 doc for the
confidence breakdown per field — envelope fields HIGH confidence,
internal variable-length arrays MEDIUM-HIGH/best-effort, since this
table's internal padding rule was reverse-engineered from byte
arithmetic, not read unambiguously off the (garbled) archived spec text).
`parser/kiwiw/route_planning.py`'s decoder (`parse_road_reference_table`)
was extended symmetrically, so writer and reader share one byte-layout
understanding.

**Validation — region 178, re-run with clustering enabled**: OSM
extraction for the same bbox/road classes as the original prototype run
now produces 2,819 raw graph nodes -> **1,518 after clustering** (402
clusters merged), vs. the real region's 106 nodes — the contraction ratio
drops from the previously-measured 26.6x to **14.3x** purely from this
one clustering pass (still far from parity: reaching real-disc density
requires the actual multi-level CH-hierarchy contraction, out of this
task's scope — see the "real bottleneck" note in Phase 1). The full RP
frame (`osm_to_route_planning.py`) encodes cleanly (94,626 bytes for this
bbox) and round-trips through both the shared `kiwiw.route_planning`
decoder and this script's own record-level decoders with **zero
problems**, including a new road-reference-table check that decodes the
written table and compares every field (`node_number` sequence,
composition-link-cost-numbers, subordinate-node-offsets,
subordinate-node-order-by-link) against what `cluster_nodes()` produced —
402 aggregated records written, 402 decoded, exact field match.
`parser/tests/test_route_planning.py` (new) adds 7 synthetic-graph unit
tests covering the road-reference-table codec in isolation (empty case,
single record with every variable-length array populated, multi-record
walk) and `cluster_nodes()` (close-pair merge with link/cost/regulation
remapping, no-op when nothing qualifies, a 4-node roundabout ring). All
25 tests in `parser/tests/` (18 pre-existing + 7 new) pass.

**Honesty about confidence**: the clustering *rule* (which OSM node
groups to merge) is a best-effort heuristic that cannot be checked
node-for-node against the real disc's own clustering — the real disc's
contraction is independent of this project's specific OSM extract. Only
structural validation was possible (round-trips through the decoder,
shaped like real records) — not "matches what the real disc would do for
this exact area." The byte *layout* the clustering feeds into, by
contrast, is grounded in the real-disc survey above (HIGH confidence
envelope, MEDIUM-HIGH confidence internal arrays, 95.6% exact
byte-accounting across all 218,440 real records).

**Interaction with the parallel multi-level/CH-contraction work**: this
clustering pass operates purely within one already-built single-region
`RpGraph` (post-hoc merge of graph nodes), independent of how that graph
was assembled. It does not touch cross-region boundary-node handling or
multi-level hierarchy construction, and should compose with that
parallel work without changes on either side — a region built by the
real multi-level pipeline can still be passed through `cluster_nodes()`
as a final step before writing. If that work changes `RpNode`
(e.g. `global_id`/`uppermost_identical_level`, added in parallel to this
task), `cluster_nodes()` currently only reads `lat`/`lon`/`is_boundary`/
`rank`/`links` and copies the representative node's `rank`/`lat`/`lon`
into the merged node — it does not yet propagate `global_id` or
`uppermost_identical_level` from cluster members, which would need a
decision (e.g. keep the representative's) if/when the two lines of work
are combined.

## Real multi-level (2/4/6/8) CH contraction + cross-region boundary links (2026-08-27)

Follow-up to the "first-pass OSM-highway-class heuristic, not real CH
contraction" and "no multi-level 2/4/6/8 hierarchy tree or cross-region
boundary-node bookkeeping" items in the route-planning prototype's known
simplifications above.

**What was built**:
- `parser/kiwiw/contraction.py` — a from-scratch, genuine Contraction
  Hierarchies node-contraction implementation (Geisberger et al. 2008):
  edge-difference priority, lazy re-evaluation, bounded witness search
  (`max_settled`) to decide whether a shortcut is actually needed when
  contracting a node. The witness-search bound is a standard, *safe*
  over-approximation — it can add a few unneeded shortcuts, but can never
  wrongly omit one, so shortest-path preservation always holds regardless
  of the bound. `assign_levels()` maps each node's contraction rank to a
  level in {2,4,6,8} via configurable cumulative fractions
  (`DEFAULT_LEVEL_FRACTIONS = (0.55, 0.25, 0.13, 0.07)`, ascending by
  rank) — chosen to be a *defensible* geometrically-decreasing shape (each
  level sparser than the last, matching CH/highway-hierarchy intuition and
  this project's own region-tree study below), **not a measured disc
  statistic** — the disc's own per-level *population* fractions were never
  established, only the level *order* and per-level road-class narrowing.
  `contract()` can also emit `snapshots`: the alive-node up-graph at a
  requested contraction-step count, needed so each level's own link set
  reflects only the shortcuts that exist by the time that level's node set
  has stabilized (see below — using the *final* completed contraction's
  full shortcut graph for every level, tried first, produced an
  unencodable `u16` link count for a coarse-level region — ~19x more
  links than the field can hold).
- `parser/tests/test_contraction.py` (new, 5 tests) — synthetic-graph
  correctness tests: line graphs, random weighted grids (multiple sizes/
  seeds), and a hand-built "cheap bypass" case that specifically checks
  the witness search actually suppresses an unneeded shortcut (not just
  that shortcuts exist). The key methodological finding while building
  these: shortest-path preservation through the CH search graph only holds
  for **rank-based suffixes** of the contraction order (the nodes that
  "survive" to a coarser level) — an arbitrary index-based node subset is
  *not* guaranteed connectivity, a subtlety the first draft of these tests
  got wrong (returned "no path" for valid pairs) before being fixed.
- `parser/study_region_hierarchy.py` (new) — empirical study of the real
  mounted disc's region tree, decoding **all 1,883 region records** (100%
  of the population) and node/coordinate data for 80 regions. Findings:
  - Region hierarchy is a genuine parent/child **tree** (Ch.9.2.1's
    `parent_region`/`first_child_region`/`n_child_regions`), not spatial
    tiling — **507/507 (100%)** of parent/child index pairs checked are
    mutually consistent. Level order, confirmed empirically (not assumed):
    child -> parent is **2 -> 4 -> 6 -> 8 -> (-32 dummy root)** — level 2
    is the finest (leaf, zero children per region), level 8 is coarsest
    (root-ward, every region has children).
  - Per-level `is_boundary` fraction (mean over 20 decoded regions/level):
    level 2 = 0.176, level 4 = 0.116, level 6 = 0.030, level 8 = 0.045.
  - **Spec-confirmed boundary-node definition** (found via `pdftotext` of
    `spec/format_english/pdf/1000122e.pdf`, Ch.10.6/10.7): *"A boundary
    node is defined as a node that has a link to another region.
    Therefore, the boundary node is either a node on the region boundary
    or a node inside the region which has a link to another region."*
    Ch.10.7.1.1 item (8) "Region Number": present (8-byte Link Record)
    only when the *owning node* is a boundary node, giving the region
    number where the *adjacent* node of that specific link exists
    (`0xFFFF` = "no region", used for a boundary node's links that don't
    actually cross regions — **all** of a boundary node's link records are
    8 bytes, not just the crossing one(s)). A direct empirical test
    (matching real regions' flagged boundary-node coordinates against
    their real parent region's own node coordinates) only matched
    **12/1,579 (0.8%)** — inconclusive, most likely due to this study's
    own incomplete multi-grid Node Coordinate table decoding rather than a
    wrong hypothesis; not asserted as proven.
- `parser/build_route_hierarchy.py` (new) — the actual multi-level
  builder: collects one OSM road graph over a bounded multi-region test
  area (default: `REGION_178_BBOX`, split into a 2x2 grid of leaf tiles —
  "a few adjacent regions' bboxes", not a country-scale tiling), runs one
  *global* CH contraction over the flat graph, assigns levels from
  contraction rank, builds a genuine 4-level parent/child region tree
  (level 2 = the 4 leaf tiles; level 4 = pairwise merges; level 6 = single
  merge of level 4; level 8 = single root — wiring the real
  `parent_region`/`first_child_region`/`n_child_regions` fields), and
  encodes every region through the existing Ch.9/Ch.10 writer.
  Cross-region **escape links** are wired for real: a boundary node (its
  uppermost level is above its region's own level) gets an extra
  `RpLink` to its own instance's index in the parent region, with
  `region_number` set to the parent's `region_no` — using the
  `write_link_record(region_number=...)` support that already existed,
  unused, in the original prototype commit. `RpLink` gained a
  `region_number: int | None` field; `encode_rp_frame` was updated to
  write the 8-byte record form (with `0xFFFF` for a boundary node's
  non-crossing links) whenever the owning node is a boundary node, and
  `osm_to_route_planning.py`'s round-trip decoder (`decode_link_record`,
  `round_trip_check`) was updated to decode variable-size (6 vs. 8 byte)
  link records and verify `region_number` — this had been silently
  wrong (fixed-6-byte-stride) until a round-trip test caught it.
  Only reused the road classes present across all 4 real levels per the
  study above ({0,1,2,3} = motorway/trunk/primary/secondary+tertiary) —
  extracting *all* OSM highway tags for the same bbox first produced a
  ~6x larger graph (16,844 nodes) than the real single-region prototype's
  own 2,819-node figure for the identical bbox, which would have been
  inconsistent with this project's "match the real disc's own scope"
  convention.

**Validation, end-to-end, over the real OSM extract** (`--max-settled
150`, 3,475-node flat graph after road-class filtering, 9,336 shortcuts
added by contraction): 9 Ch.9 region records (1 dummy root + 4 level-2 +
2 level-4 + 1 level-6 + 1 level-8), **7/7** parent/child index-consistency
checks pass, **8/8** regions' Ch.10 frames round-trip byte-for-byte with
**zero problems** (including the new boundary-link 8-byte-record/
region_number checks above), and — the core correctness claim for task
item 1 — **100/100 shortest-path checks match with 0 mismatches at every
one of the 4 levels** (sampled node pairs, shortest path in the CH search
graph restricted to that level's surviving node subset vs. shortest path
in the original, fully uncontracted OSM graph). `parser/tests/`: 28/28
pass (5 new contraction tests + 3 new boundary-link tests + the 20
pre-existing).

**Level sizes for this test area**: level 2 = 4 leaf regions with
2575/717/115/29 nodes; level 4 = 2 regions with 1491/59; level 6 = 1
region with 693; level 8 = 1 root region with 243. Flat graph (3,475
nodes) -> level-8 root (243 nodes) = a **14.3x** reduction — in the same
ballpark as, though not forced to match, the single-region prototype's
separately-measured 14.3x (post-clustering) / 26.6x (pre-clustering)
ratios against the *real disc's* region 178, since these numbers come
from different comparison baselines (this run's own synthetic level-8
root vs. that run's real-disc-decoded region 178).

**What's proven vs. assumed, stated plainly**:
- PROVEN: the CH contraction algorithm itself preserves shortest-path
  distances (100/100, 0 mismatches, both on synthetic test graphs and on
  the real OSM extract). PROVEN: the region tree's parent/child linkage
  mechanism, and the Ch.10.7.1.1 boundary-node Link Record byte layout
  (region_number field, 8-byte conditional record) both round-trip
  correctly through the existing decoder infrastructure.
- SPEC-CONFIRMED but not independently cross-checked against a real
  multi-region disc extract: the literal definition of a boundary node as
  "has a link to another region."
- ASSUMED/best-effort, explicitly not proven: (1) this project's specific
  choice of "a boundary node's cross-region link goes to its own instance
  in the parent region" — a defensible reading given how `is_boundary` is
  derived here, but the spec's own definition is broader (any link to
  another region, including sibling regions at the same level, which this
  region-tree shape doesn't need); (2) `DEFAULT_LEVEL_FRACTIONS`, the
  per-level node-population split — no real per-level population
  statistic was ever established from the disc, only level order and
  per-level road-class narrowing; (3) `uppermost_identical_level`'s 3-bit
  encoding (this code writes level/2, i.e. 1-4) — not independently
  spec-confirmed; (4) region tree shape (2x2 leaf grid, pairwise merge) is
  a small defensible demonstration, not a load-balanced country-scale
  tiling strategy.
- OUT OF SCOPE, unchanged: turn restrictions, aggregated-intersection
  clustering / Road Reference Table (owned by the parallel clustering
  work above — composes independently, since this task's region tree
  builds a plain `RpGraph` per region that could still be passed through
  `cluster_nodes()` as a final step), non-default ext frames.

**Scope-of-work impact**: reinforces rather than changes the prior estimate
that the byte-encoding work is tractable (took roughly one session, matching
the ~1-2 day Ch.9 / low-single-digit-day Ch.10 estimate) and that **the real
bottleneck is generating the multi-level hierarchical routing graph itself**.
The 26.6x node-count contraction ratio is new, concrete evidence — previously
an assumption ("won't match exactly"), now a measured number for one real
region that can anchor future estimates of the CH-hierarchy engineering
effort.

**Next**, if continuing this line of work: (1) determine whether the
undocumented "ext" frames are required by the firmware (still untested), (2)
build real multi-level hierarchy construction (a genuine CH/highway-hierarchy
contraction, not the heuristic used here) across more than one region, with
cross-region boundary-node handling, (3) decide the aggregated-intersection
clustering approach, since it's currently a no-op.
