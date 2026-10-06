# Phase 2 discriminator comparison

The fixed outcome is a per-native-key verdict over **341 × 288 + 1 × 321 (246)**. A demanded-code production-C emitter proves a supply path. Template identity or the retained demander's zero-area clip alone cannot prove a negative supply verdict. The worker cannot open the spool, PBF or discs; actual probe execution is Execute's responsibility.

Scores are 1–5, with weighted total `0.35 × verdict soundness + 0.30 × source coverage + 0.20 × root-cause discrimination + 0.15 × execution economy`. A score describes the implemented candidate's capabilities, not measured source availability. Unknown geometry, missing relation members and resource limits remain explicit coverage gaps.

| Candidate | Soundness | Coverage | Cause discrimination | Economy | Total |
| --- | ---: | ---: | ---: | ---: | ---: |
| (a) Spool window | 4 | 3 | 2 | 5 | **3.45** |
| (b) Streamed PBF query, including bounded relation assembly | 5 | 5 | 3 | 2 | **4.15** |
| (c) Lattice identity from the Phase 1 census | 1 | 2 | 2 | 5 | **2.10** |
| (a) + (c) | 4 | 3 | 4 | 5 | **3.85** |
| (b) + (c) | 5 | 5 | 5 | 2 | **4.55** |
| **(a) + (b) + (c), chosen** | **5** | **5** | **5** | **2** | **4.55** |

The last two tie on outcome capability. Adding (a) gives a direct existing-spool source identity, checks Phase 1 demander cell pins and supplies an independent source-path control; those benefits justify its smaller additional streamed scan. Candidate (b) is needed before any absence claim because extract selection, centroid storage and relation-tag inheritance can hide a supply path outside the existing spool. Candidate (c) distinguishes the 288 cohort from row 246; it cannot settle either cohort by itself.

## Chosen search and encode contracts

For each native key, the search window is the target L0 cell plus **one cell on every side**, recorded in degrees as `[lat_min,lat_max,lon_min,lon_max]`. The production-C probe clips into the **target cell**, rather than admitting any emitter in the halo. Source admission uses bbox intersection, which includes polygons enclosing the window even when none of their vertices lies inside it. Source centroid distance never excludes a source. All plan-30 windows are within the Australian non-wrapping longitude interval.

**(a)** scans every indexed L0 spool cell, in sorted batches of 4,096 index entries. It decodes one cell at a time, with a **64 MiB** cap. Every class-2 ring of every code whose bbox intersects a window is tried. The scan requires contiguous, exhaustive index coverage of the data file and verifies each retained demander cell's SHA256, byte span, ordinal and coordinate count. This is a geometry-window query over the complete L0 input, not a centroid-cell shortcut.

**(b)** makes a relation-catalogue pass and a node/way pass over the named PBF. Coordinates, required member-way geometries and relation membership are held in disk SQLite with a **4 MiB** cache and disk temporary storage. Source geometry is filtered by the same windows. The query uses production `kiwiw.vocab.load('bg_type')`, records production selection admission, and includes every non-road way with at least three coordinates, including the production extractor's closure of open ways. It also joins `multipolygon` and `boundary` relation members by **OSM node IDs**, inherits relation tags, and preserves holes through doubled bridges between existing source vertices. No bridge adds polygon area; the production even-odd C path is the authority. Nested, missing, branched, invalid, overlapping or otherwise unsupported relations are named gaps. An unknown bounding box conservatively affects every negative verdict.

Bounds are **20,000** coordinates per streamed source/compound ring, **2,000** members per relation, **2,048** edges for the bounded topology validation, and **200,000** densified mirror points. Native C has a separate **2,048-coordinate** source/clip cap because its even-odd intersection work can grow quadratically. Limit failures record gaps, rather than absence. Complete relation bboxes outside every window are rejected before topology/encode work; unknown or partial bboxes cannot exclude an enclosing polygon. Ambiguous antimeridian source edges are coverage gaps. Relation boundaries are checked for self/cross intersections and proper hole containment; exact rational orientation is used when the floating-point orientation is ambiguous. There is no new dependency installation.

**(c)** checks the full Phase 1 sequence signature, 13-coordinate count, branch c and exact span against the aligned 4×4 L0 tile at tolerance **1e-9°**. It uses the measured signatures **T1 191 + T2 150**, with their same counterclockwise winding. Each evaluated source also records whether its boundary coincides with that grid rectangle. The predicate is explanatory evidence, never an OSM absence inference.

The probe reuses `complete_repair_2-02.py`'s `CProbe`, which compiles a read-only include of production `_cenc.c` and calls `kw__bg_shape`, and that reproducer's independent `encoder_piece_densified` plus `cell_local_2-01.py`'s `clip_rect`. Every candidate is checked as the original ring, the clipped boundary, and the original ring with wire-valid **mult=1**. Production C applies its own even-odd repair, densification, rounding and cleaning. A negative C return, output overflow or a resource limit is a gap. A synthetic square must emit before the probe starts. No R coordinates enter a source/encode probe.

## Verdict rules and limits

* `supply-path`: at least one actual demanded-code C record in the target cell. Evidence identifies the source, chosen encode variant, coordinate hash and successor implement path. A positive remains valid when another discriminator has gaps.
* `unfixable-proven` for a 288 template: both exhaustive probes completed, no gap affects that member, and neither probe found a demanded-code emitter across the tried variants. The cause is `type-semantic mismatch` when an alternate code does emit, otherwise `WhereIS-only lattice`. Negative evidence is scoped to the pinned spool/PBF, production vocabulary and stated window; it is not a claim about future OSM edits.
* Row 246 has its own positive path or proof. A representability ceiling can be proven when **every** correct-code source is identically a line (zero latitude or longitude span) and all C variants emit zero. A non-degenerate sliver's negative probes do not establish all-repair impossibility. No correct-code source, or an unresolved non-degenerate geometry, leaves row 246 open for a further discriminator.
* `conflict-open`: a probe is pending, a coverage gap affects the row, a template/grid exception occurs, or row 246 lacks a justified allowed cause. Every such row lists the tried and outstanding discriminators.

The real-data counts are deliberately unknown before Execute's runs. The generated worker baseline is **0 supply-path / 0 unfixable-proven / 342 conflict-open**. It retains measured Phase 1 evidence and records `pending-spool` and `pending-pbf` for each row. It was produced by `inventory` → `publish`, not by hand. This baseline does not close Phase 2.
