# Phase 3 — OSM ingestion and content pipeline

## Goal
Generate real map content from OpenStreetMap data for the target region, matching
the KIWI-W structures identified in Phase 1, built up incrementally:
roads only -> + names -> + POIs -> + address search, with an in-vehicle test after
each sub-checkpoint.

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
