# Target disc — design intent (program of record)

This is the stable definition of *what we are building* and *how we judge it*.
Per-work-package plans under `docs/plans/` reference this doc; the phase docs
under `docs/phases/` are the historical research record and are superseded by
this doc wherever they disagree.

## Goal

One DVD-R that the Mitsubishi Pajero MMCS head unit accepts as a navigation
disc, whose map, routing, POI and address-search content is generated entirely
from an OpenStreetMap extract of **all of Australia**, at parity with the
reference 2007 WhereIS disc. The vehicle is in Queensland.

## Decisions that shape everything (2026-09-04)

1. **In-vehicle testing is last-mile, not a feedback loop.** A vehicle test
   yields almost no debuggable signal. Every evaluation before the final burn
   is offline: byte-level and structural comparison of the generated disc
   against the reference disc, using this project's own parser as the oracle.
   This supersedes the 2026-08-24 "favour frequent in-vehicle validation"
   scope decision and the "in-vehicle test after each sub-checkpoint" phasing.
2. **No partial milestone is a deliverable.** The first burn is full Australia,
   all seven map levels, all features. Regional subsets (Perth metro, region
   178, a 2×2 tile grid) remain useful only as fast development fixtures and
   must never be the shape of a script's *default* deliverable.
3. **Full parity means every map-dependent file is regenerated.** Nothing that
   references link IDs, coordinates or place content is copied from the
   reference disc. Copy-through is allowed only for content-independent
   resources (firmware, voice, UI graphics). Every index family under `IDX/`,
   plus `HWMAP.KWI` and `INDEXDAT.KWI`, is decoded and regenerated before the
   first burn.
4. **A rebuilt-original burn is a contingency**, used only if the OSM disc
   fails in the vehicle and a container-vs-content split is needed.
5. **Authoring and burning happen on this machine.** UDF-bridge image
   authoring tools are in scope to install.

## Evaluation: the offline oracle

"Parity" is defined operationally. For a generated disc `G` and the reference
disc `R`, a comparison harness (`parser/compare_disc.py`, owned by the first
work package) produces a report with these checks. A work package is done when
its files pass every check that applies to them.

| Check | Definition |
|---|---|
| Decodes clean | Every structure in `G` is parsed by the project parser with zero errors, using the same code paths that parse `R`. |
| Pointers resolve | Every offset/sector/index pointer in `G` lands inside its target table or buffer, or (for pointers that on `R` reference another layer, e.g. mfde entries ≥3) carries the absent-slot value censused from `R` or a valid in-file sector; no `0xA5` poison, no out-of-range. |
| Same vocabulary | Every enumerated value in `G` (road type, display class, background type code, name string type, POI category, area code, frame kind, DCTF field usage) is drawn from the set observed in `R`. |
| Profile envelope | Per level / per file / per record kind, `G`'s size and count distributions fall inside a stated envelope around `R`'s (default 0.5×–2× on counts, ≤ `R`'s observed maximum on any per-parcel or per-record size). Level 0 road counts are exempt from the count envelope and bounded by size and capacity instead. Envelopes are recorded in the harness config, not hard-coded. |
| Container byte-diff | The volume header, MHT, PDMDH, LMR tables and copy-through frames of `G` differ from `R` only in an allowlisted set of fields (build stamp, sizes, sector addresses). |
| Cross-file consistency | Link IDs in the search indexes and route-planning frames resolve to map-layer links; coverage bounds agree across `METADATA.KWI`, `COVERAGE.BIN`, the volume header and the level management records; state partition of index files agrees with the map coverage. |
| Round-trip regression | `R` still round-trips byte-identical through the replicate-mode writers (`parser/tests/`). |
| Capacity | Total image size ≤ 4,700,000,000 bytes (single-layer DVD-R; the head unit's dual-layer support is unknown and not assumed). Reference disc: 2,389,671,936 bytes. |

Content-level spot checks (named coordinates in Brisbane, Sydney, Melbourne,
Perth, Hobart, Darwin, Adelaide resolving to the expected OSM street/place
names) are a fixture table consumed by the harness, not ad-hoc. Each check
reports PASS, FAIL or N/A; a check is applicable to a work package's output
when that package's plan says so, and the harness's config lists which files
and layers exist in `G`.

## Target disc: file by file

| File | Source | Owning work package |
|---|---|---|
| `ALLDATA.KWI` map layer (Ch.5–7: volume, MHT, PDMDH/LMR/BSMR/BMT, parcel mgmt, road/background/name frames) | generate | WP1 |
| `ALLDATA.KWI` management header record 29 frame (file offset 4096..6144; spec Ch.5.2 record 30, RESERVED extended part 1; content is a language/country code list) | copy verbatim | WP1 |
| `ALLDATA.KWI` route-planning layer (Ch.9/10), ext frames `0xAF1001xx/03xx/06xx`, build stamp | generate | WP2 |
| `ALLDATA.KWI` route-guidance parcel list (`routeoff`) and mfde entries 3..19 | generate | WP1 (census, absent-slot values) / WP2 (generate) |
| `IDX/SADSR2##.IDX` (address, one file per state: 201=WA 202=NT 203=SA 204=QLD 205=NSW 206=VIC 207=TAS, all seven decoded from address-range bboxes) | generate ×7 | WP3 |
| `IDX/POISR2##.IDX` (POI search, per state) | generate ×7 | WP3 |
| `IDX/POIAS2##.IDX`, `IDX/POIDT0##.IDX` (POI information, Ch.11.A.2.14 family) | generate | WP4 |
| `IDX/ITSSR2##.IDX` (intersection search) | generate ×7 | WP4 |
| `IDX/FWYSR2##.IDX` (freeway search) | generate | WP4 |
| `IDX/AGMSR*.IDX`, `ARGSR*.IDX`, `ARSNC2##.IDX`, `ARSSR.IDX` (the `DB0/JG0/LR0/MB0/MZ0/ND0/NF0/NS0/VL0` suffix set is unexplained) | generate | WP4 |
| `IDX/EMGSR*.IDX`, `EM2SR.IDX`, `EM3SR.IDX`, `FMCDT001.IDX` | generate | WP4 |
| `IDX/ZONEVSRC.IDX`, `ZONEZSRC.IDX`, `ZSEL*.IDX` (zone selection, Ch.11.A.2.2/3) | generate | WP4 |
| `INDEXDAT.KWI` (likely Ch.11.2 index data management, naming the per-state files) | generate | WP4 |
| `HWMAP.KWI` (likely highway overview) | generate | WP4 |
| `SPEC.KWI`, `METADATA.KWI`, `COUNTRY.KWI`, `VERSION.TXT`, `COVERAGE.BIN`, `DN/CLUSTER.DAT`, `PCT2MNG.KWI` | generate | WP5 |
| `COVERAGE/AUC.BMP` | generate if coverage changes, else copy | WP5 |
| `LOADING.KWI`, `DICVCE56.KWI`, `GRA256D.KWI`, `KGRA256.KWI`, `PCT256D.KWI`, `KPCT256.KWI`, `PCT2DAT.KWI`, `KPCT2DT.KWI`, `KGRPDAT.KWI`, `VAR256D.KWI` (content-independent) | copy | WP5 |
| Disc image (UDF bridge: ISO 9660 + UDF, volume id `464210-8480`) | generate | WP5 |

Implementation status per file lives in each work package's plan folder and
close-out record, not here.

## Pipeline shape and stage contracts

```
OSM PBF (Australia, dated extract)
   │
   ├─ geometry extraction ─► parcel IR per (level, ix, iy): RoadLink / BackgroundShape / NameRecord
   │                          (grid = reference LMR grid per level; all 7 levels)
   ├─ routing graph ────────► flat graph ─► CH contraction ─► region tree (2/4/6/8) ─► RpGraph per region
   ├─ address/POI/… ────────► per-state index IRs (streets, ranges, cities, POIs, intersections, freeways, zones)
   │
   ├─ LinkIdRegistry: osm_way_id ─► (parcel, positional link index)   ← single join key for all layers
   │
   ├─ encoders (synth.py, route_planning_writer.py, index_writer.py, misc_writer.py)
   ├─ assemblers (alldata_writer.build_alldata_kwi, roundtrip_idx_full "fromscratch" allocation)
   └─ image authoring (UDF bridge) ─► compare_disc.py report ─► burn
```

Contracts that every work package must honour:

- **Grid contract.** Parcel cells at every level 12..0 are the reference
  disc's own LMR grid (block set × block × parcel counts, cell sizes,
  coverage box E90..W142 crossing ±180°). Those parameters are checked-in
  data derived once from `R`; a build never reads the mounted reference. The
  generated LMR/BSMR/BMT shape per level equals `R`'s. Cell indices are
  global. A parcel that exceeds the Map Frame size envelope is divided (Ch.6
  divided/integrated parcels), never truncated.
- **Link identity.** A map-layer link's on-disc identity is its positional
  index within its parcel's road frame. `LinkIdRegistry` is the only source
  of that mapping for the route-planning and index layers; the join key from
  extraction onward is `(osm_way_id, ordinal)`, ordinal being the
  sub-polyline index after parcel splitting, so a way split across parcels
  is addressable in every piece.
- **Vocabulary.** Type/class codes emitted by any encoder come from a census
  of the reference disc (`R`), recorded in the harness config, not invented.
  Unmapped OSM tags map to the nearest observed code, and the mapping table
  is data, not code.
- **Name records** are emitted as the string types observed on `R` (4
  dominant; 5 and 6 present). `string_type=1` is not used.
- **State partition.** Index files are partitioned by state/territory using
  the same seven-way split as `R`; the state of a feature is decided by OSM
  `admin_level=4` boundary containment, not by bbox.
- **Route-planning placement.** RP frames are placed into the assembled
  `ALLDATA.KWI` through the same Map Frame / mfde references `R` uses; the
  region tree is a country-scale, load-balanced tree, not the 2×2 fixture.
- **Ext frames** (owned by WP2). `0xAF100600` and the 12-byte build stamp
  are reproduced; `0xAF100100`/`0xAF100300` are omitted until evidence of
  dependence.
- **Copy-through management data.** The frame pointed at by management
  header record 29 (0-based; spec record 30, RESERVED) is a language/country
  code list, not map content, and is carried byte-identical from `R`.
- **Unknown bytes policy** (from Phase 2): a region that is not understood is
  carried verbatim in round-trip mode, but in from-scratch mode it must be
  either generated from a decoded model or proven absent/zero on `R` — never
  silently zero-filled.
- **Determinism.** Given the same PBF and config, the build is byte-for-byte
  reproducible, so byte diffs between two builds isolate one change.
- **Capacity accounting.** Each layer reports its byte total; the harness
  sums them against the 4.7 GB budget. OSM's road density exceeds the 2007
  dataset's, so the budget is expected to bind at level 0; the harness
  reports the trade-off, and the decision (drop minor ways, or confirm
  dual-layer support on the head unit) is the user's.

## Work-package sequence

Each is one plan folder under `docs/plans/`, run through plan → refine →
execute → review → close-out. Order is by dependency and by how much of the
disc's bytes each de-risks.

1. **WP1 — Offline evaluation harness + full-Australia map layer.**
   `compare_disc.py` and the reference profile; fix the synth pipeline's
   known deviations (name types, mfde table, record-29 frame, single-level
   flat assembly); country-wide, all-level build that completes in bounded
   time and passes the harness. Its format-analysis spike on RP placement
   may overlap with WP2's start.
2. **WP2 — Route planning at country scale.** Load-balanced region tree over
   Australia, CH contraction at scale, Link IDs joined through the registry,
   RP frames placed into `ALLDATA.KWI`, `routeoff`/mfde 3..19 generated.
3. **WP3 — Address and POI indexes, all states.** OSM → `SADSR2##`/`POISR2##`
   for the seven states; POISR decode bugs fixed; category/area-code tables
   mapped; state assignment by boundary containment.
4. **WP4 — Remaining index families, `INDEXDAT.KWI`, `HWMAP.KWI`.** Format
   analysis and regeneration for every undecoded map-dependent file.
5. **WP5 — Metadata, image authoring, burn, in-vehicle acceptance.** Disc
   stamp and cluster index rules, coverage bitmap, UDF-bridge image, burn,
   vehicle test as final acceptance; contingency rebuilt-original disc.

## Non-goals

- Multi-region / non-Australian discs.
- Matching the reference disc's exact allocation order or exact bytes for
  OSM-derived content (only structural parity is required).
- Preserving the reference disc's WA-centric development fixtures.
- Firmware modification.

## Corrections to earlier docs (recorded here so they are not re-derived)

- `docs/phases/00-inventory.md` guessed the `2##` suffix on index files is a
  zoom level. Decoded bounding boxes show it is a state partition
  (201=WA, 202=NT, 203=SA, 204=QLD, 205=NSW/ACT, 206=VIC, 207=TAS, all
  seven confirmed by decoding each file's address-range bounding boxes).
- `docs/00-overview.md`'s 2026-08-24 test-access decision ("favour frequent
  in-vehicle validation") is superseded by decision 1 above.
- `docs/phases/03-osm-pipeline.md`'s "roads → names → POIs → address search
  with an in-vehicle test after each" phasing is superseded by decisions 1–2.
