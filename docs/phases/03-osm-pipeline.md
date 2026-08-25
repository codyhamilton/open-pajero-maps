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
first-pass OSM-highway-class heuristic, not real CH contraction; aggregated-
intersection clustering unimplemented (road-ref table always written empty);
turn restrictions only handle simple one-via-node cases; link-cost "Link ID
Number" fields are synthetic; upper_node/upper_link/passage_code/
statistical_cost frames left absent (matches the real disc's near-zero use).

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
