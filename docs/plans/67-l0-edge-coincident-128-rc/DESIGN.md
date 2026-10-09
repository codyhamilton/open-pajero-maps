---
design_id:
---

# R-G9-3-d-rem: the 128 L0 links whose every vertex is on the parent edge but outside their leaf rect — proven RC per link, then fix or proof

## Intent

Cody's standing rule (2026-10-05, hard): Maps is complete only when end-to-end generation matches the original DVD in every aspect that can be verified, every claim, assumption, and implementation aspect is verified and proven, and there are no unexplained deviations — each has a root cause.

Cody's hard bar as restated 2026-10-08: every deviation needs a proven root cause; no waivers; carried is not closed; never pick an arbitrary rule and call it proven.

Design brief (2026-10-08): draft a design for the undrafted Design-owned carried row R-G9-3-d-rem (128 links), with a proven-RC path and gates that carry no "optional" wording.

Master direct. Heavy work under flock + `run_heavy_python.py --memory-max 12G`, encode `-j4`, K1 ≤ `-j6`. **Out of scope and untouched:** F6 / kind-order, roads preference, L8 expansion (Cody). Assigned Execute instance: OpenCode DeepSeek Flash.

**Scratch-rule note (Design, 2026-10-09):** Cody's standing rule added: every phase outcome now includes a scratch receipt with named keep / delete lists (see "Scratch hygiene" and each phase). No other change to this draft.

## Problem

**Ground (GitHub `origin/master` `4bb96f0` (plan 65 close-out; rows 54–57 unchanged from `8498eec`), read-only on the box, 2026-10-08):**

1. **The row.** `triage/phase3_synthesis/residuals.tsv` R-G9-3-d-rem (line 57): "AU divided-L0 remaining all-vertices-on-parent-edge outside leaf rect after lon-wrap fix: **128** (by_edge E=32 N=39 S=26 W=29 +2 corners). Not lon-wrap; (1755,591)=0. Mechanism TBD". Owner "Design (**optional** residual class)"; status `maps-parity-carried`. Plan 53's record also says "Design: optional residual class" (L62) and the `l0_degen/README.md` says "optional follow-up".
2. **The census, before and after plan 53** (`trim_r_parity/l0_degen/`):

   | | `census.json` (sha `62e5e5d7…`, on `aeae426c`, schema `plan53-l0-degen-census-v2`) | `census_after.json` (sha `86de7f67…`, on `0c22b266…`) |
   | --- | ---: | ---: |
   | outside leaf rect, all vertices on parent edge | 5,969 | **128** |
   | E only | 5,871 | 32 |
   | N / S / W only | 39 / 26 / 29 | **39 / 26 / 29** |
   | corners | (E,N) 2, (E,S) 1, (W,N) 1 | (E,N) 1, (W,N) 1 |
   | inside leaf rect (same predicate) | 27 | not recorded |
   | coincident, not on parent edge | 209 | not recorded |
   | links in divided leaves | 569,300 (560 divided parents) | 563,528 |
   | per-parent list | `parents_outside` (534 parents) | not recorded; 20-record sample only |

   - **The N / S / W counts and the (W,N) corner are identical before and after the fix.** 96 of the 128 were untouched by plan 53's lon change. The 32 E-only + (E,N) 1 remain after it.
   - `census_after.json` is a reduced output: no schema, no inside / coincident counts, no per-parent list, no leaf division (`nx`) per record, and each sample record carries a single `point`, not the link's vertices.
3. **The census generator is not committed.** Plan 53's review soft note: census generators lived in scratch, JSON committed only. The predicate's leaf-rect convention (orientation of y, `nx` per parent, edge tolerance) cannot be read from the tree.
4. **Encoder conventions at tip** (`parser/kiwiw/_e2.c`):
   - `dv_assign` (L465–481): lat half-open — `dlat < 0 || dlat >= lat_span` → −1; lon normalised into [0,360) then `delta > lon_span` → −1, so the east edge is closed and the north edge open. `sx = dv_clamp(delta/cell_lon, nx)`, `sy = dv_clamp(dlat/cell_lat, nx)`, cell = `sy*nx + sx` (square division; `sy` counted from the south edge).
   - `dv_split` (L540–546) bisects a segment whose endpoints assign to different cells, to depth 18, then emits the piece into the cell of its first endpoint (`dv_leaf`).
   - `dv_halo` (L1081) builds halo candidates with a 1% inset on the leaf rect.
   - Plan 46 RC4 (divided-leaf clip rect; the function's docstring calls it "root cause 3") is committed as `parser/tools/bg_producer_scan.py::leaf_clip_geometry` (L384), tested in `parser/tests/test_bg_producer_scan.py`: rect = (sx·cr/nx, sy·cr/nx, (sx+1)·cr/nx, (sy+1)·cr/nx), c = sy·nx + sx, and **nx comes from the record's parcel_type: 1 → 2×2, 2 → 4×4**.
5. **Design's arithmetic on the committed samples (a lead, not a finding).** Treating each sample `point` as parent-raw (0…4096, y-up) and testing it against leaf `leaf` of an nx×nx division:

   | Convention | After (20 samples) inside own leaf rect | Before (30 samples) |
   | --- | ---: | ---: |
   | nx=2, encoder y-up | **20 / 20** | 0 / 30 |
   | nx=2, y flipped | 0 / 20 | 0 / 30 |
   | nx=4, y-up / flipped | 0 / 5 | 0 / 0 |

   - If the after-fix sample parents are 2×2, every sampled "outside" link is inside its leaf under the encoder's convention, which would make the 128 a census-predicate artefact.
   - It is not a finding: parcel_type (hence `nx`) is not recorded per record, only one vertex per record is given, and some divided parents are 4×4 (plan 53's (1755,591) assigns to cells 0 / 4 / 8). Whether the census's leaf rect used `cr` = 4096 is also unrecorded. The pre-fix samples are outside under every convention tested.
6. **Parity against R was never checked for this class.** No census of R's L0 links with the same predicate exists, so it is unknown whether R carries any edge-coincident links.

## Solution shape

### Domain: committed census pinned to the encoder convention

- **Owns:** `triage/trim_r_parity/l0_degen/census/` (new): a committed generator, a unit test, and `census_live.json` on `0c22b266…`.
- **Contract:**
  1. The leaf rect is taken from the committed `leaf_clip_geometry` (not a re-implementation): `nx` from the record's parcel_type, `cr` from the parent slot's frame range. A unit test asserts that the assignment side agrees with `dv_assign` on synthetic points on every edge, corner and the epsilon-past cases from plan 53, with the closed-east / open-north boundaries stated.
  2. Two predicates run side by side on the same links:
     - **P53** — a reconstruction of plan 53's predicate. It must reproduce 5,969 on `aeae426c` and 128 on `0c22b266` exactly, with the same by-edge split; otherwise the reconstruction is wrong and is fixed before anything else.
     - **PE** — the encoder-pinned predicate (item 1).
  3. Per link record: parent (ix, iy), leaf index, `nx`, dc, full vertex list in parent-raw, by-edge class under P53 and PE, spool `osm_way_id` / ordinal behind the link.
  4. Also records, on live, the counts plan 53 recorded pre-fix and dropped after: inside-leaf-rect and coincident-not-on-parent-edge (209 pre-fix). Any of these that is a deviation from R gets its own residual row; none is silently dropped.
  5. Deterministic; double run identical.
- **Non-goals:** any encoder change in this domain.

### Domain: per-link root cause

- **Owns:** `l0_degen/census/rc_table.json`: every one of the 128 (P53 set) with exactly one hypothesis accepted on evidence.
- **Contract:**
  1. **Hypotheses (defined before scoring):**
     - **H0 predicate artefact:** under PE the link is inside its own leaf rect; P53 used another rect convention or `nx`.
     - **H1 boundary asymmetry:** vertices exactly on the north edge assign −1 while east-edge vertices are inside (`dv_assign` half-open lat / closed lon); the piece lands in a cell whose rect it does not lie in.
     - **H2 bisection residue:** `dv_split`'s depth-18 cut emits an edge-running sub-segment into the first endpoint's cell.
     - **H3 halo:** the link is a `dv_halo` candidate (1% inset) emitted into a neighbouring leaf.
     - **H4 decode artefact:** D1 shows edge coordinates that the encoded bytes do not hold. Checked by the plan-53 independent bit-level decode (`decode_region_coord`).
     - **H5 genuine source geometry:** the OSM way runs exactly on the parent boundary in the spool, and the encoder's placement matches what R does with the same geometry.
  2. Evidence per link: independent decode of `raw_bytes`; spool vertices for the way; `dv_assign` result per vertex re-computed in a harness that calls the encoder function (not a re-implementation); halo membership.
  3. **R parity** for every link: R's L0 links in the same parent, under the same PE predicate, and R's coverage of the G link's geometry within 1 parent-raw. A link is a deviation if G's placement or geometry differs from R's, whatever hypothesis explains it.
  4. **Outcomes per link,** no other end state:
     - **non-deviation, proven:** H0 with PE inside, independent decode agreeing, and R parity showing no difference; or H5 with R carrying the same edge-running geometry the same way;
     - **encoder defect:** H1 / H2 / H3 with the mechanism shown on bytes, routed to the remedy domain;
     - **decode defect:** H4, routed to a D1 fix with its own test.
  5. A link that fits no hypothesis stays open with a named new hypothesis and its own evidence. It does not fall back to "residual class".
- **Non-goals:** a blanket rule applied to all 128 without per-link evidence.

### Domain: remedy and residual update

- **Owns:** any `_e2.c` / D1 change with tests; `residuals.tsv` R-G9-3-d-rem; the `l0_degen/README.md` and plan 53 record wording.
- **Contract:**
  1. **Encoder fix.** Confined change with unit tests at the boundary. A successor oracle from a full AU `-j4` encode must show:
     - confined diff vs `0c22b266…`, changed set listed and every changed cell traced to a fixed link or its halo;
     - PE census on the successor: every encoder-defect link from Phase 2 gone, no new edge-coincident link;
     - R-DVD no-worse on every changed parent (plan 48 precedent);
     - Perth successor vs `5b86d33e…`;
     - K1 failing 0; close gates a/b/c.

     Design accepts before promotion; the OVERVIEW oracle line moves.
  2. **Non-deviation proofs** are recorded per link in `rc_table.json` with the evidence fields filled; the row is discharged only when every one of the 128 has an outcome.
  3. `residuals.tsv` R-G9-3-d-rem: owner text "Design (optional residual class)" is replaced with the plan 67 outcome. The plan 53 record line "Design: optional residual class" and the README "optional follow-up" get a pointer to plan 67. Records are amended by append, not rewritten.
- **Non-goals:** F6, roads preference, L8 expansion; re-opening plan 53's lon fix unless Phase 2 evidence names it.

### Memory guardrails (all phases)

- Serial under `flock output/.heavy.lock` + `run_heavy_python.py --memory-max 12G` (MemorySwapMax=0).
- Census streams per divided L0 parent from the disc; spool lookups use the bounded LRU caches (4096) and `clear_spool_caches` per batch (plan 57).
- Full AU encode at `-j4` with the `bench_build.py` tree sampler (plan 58: AU tree ~15.3 GB-class). K1 ≤ `-j6`.
- OOM or cap trip → stop_for_design with peak. Peaks go into the plan-56 ledger as `ledger/l0_edge_plan67.json` + SUMMARY row.

### Scratch hygiene (all phases; Cody standing rule, 2026-10-09)

- **Rule (Cody):** Execute cleans its scratch after every phase, keeping only what the ledger or the next phase needs. **A phase is not done until its scratch is cleared.** The receipt below is part of every phase outcome.
- **This plan's scratch:** `output/scratch-67/`, any git worktree this plan adds, any temp dir its runs create (named in the run log), and the wrapper's cgroup scopes. Nothing else.
- **Never deleted by this plan:** `output/.heavy.lock` (shared flock file); other plans' `output/scratch-*` (some are pinned evidence, e.g. `oracle_chain/pin_contract.py` pins `output/scratch-32/…`); the spool of record; the R (DVD) image; the disc in force and earlier oracle discs; `.venv-rp`.
- **What may be kept:** committed artefacts first. Ledger rows carry the peak fields copied from the wrapper log, so the log itself is not kept. Anything the next phase needs that cannot be committed goes under `output/scratch-67/keep/`, listed with path, bytes and sha256, and is deleted at the end of the phase that consumes it.
- **Receipt** (`scratch_receipt` in the plan note, one per phase):
  1. `du -sb output/scratch-67` before cleanup and after;
  2. after: `test ! -e output/scratch-67` (gone), or `ls -A output/scratch-67` shows only `keep`, with its contents listed;
  3. `git worktree list` shows no worktree from this plan (after `git worktree remove` + `git worktree prune`);
  4. every temp dir named in the phase's run logs is gone, and no wrapper scope from the phase is still running;
  5. kept list checked: every kept path exists, committed paths appear in `git ls-files`, `keep/` items match their recorded sha256.
- A missing or failing receipt means the phase is not done. The final phase ends with `output/scratch-67` gone.

## Decisions

1. Plan number **67**. Master direct. Three phases: committed census; per-link RC; remedy / residual.
2. The first gate is reproducing plan 53's 5,969 and 128 exactly with a committed generator. Nothing is scored on a predicate that cannot reproduce the recorded number.
3. The per-link outcome set is closed (non-deviation proven / encoder defect / decode defect / open with a named hypothesis). "Residual class" and "optional" are not outcomes.
4. Tip `4bb96f0`; live oracle `0c22b266…`, Perth `5b86d33e…`.

## Assumption ledger

### Assumption 1

- **Question:** Is the plan 53 predicate reconstructable without the scratch generator?
- **Answer chosen:** Yes, from `census.json`'s schema fields (`lpath`, `leaf`, `point`, `outside_by_edge`) and the README definition, checked against both recorded totals.
- **Rationale:** two independent totals (5,969 / 128) plus the by-edge splits pin the predicate tightly.
- **If wrong:** the scratch generator is recovered if still on the Execute box (`output/scratch-50/` or similar); otherwise PE alone is used and the 128 are re-derived under PE, with the difference to the recorded 128 stated.

### Assumption 2

- **Question:** Does R's L0 division and link encoding allow the same PE predicate?
- **Answer chosen:** Yes: R is read through the same D1 decoder and leaf paths as G in the plan 46 / 52 measurements.
- **Rationale:** `l8_frag/remeasure.json` reads R leaf paths and parent-raw geometry with the same tooling.
- **If wrong:** R parity falls back to coverage of G's link geometry by any R link in the parent, with the predicate difference recorded.

### Assumption 3

- **Question:** Is the 20/20 nx=2 result (Ground item 5) evidence of H0?
- **Answer chosen:** No, a lead only.
- **Rationale:** parcel_type / `nx` not recorded; single vertex per sample; some parents are 4×4.
- **If wrong:** nothing depends on it; Phase 1 measures it.

## Open questions

1. Whether plan 53's scratch generator still exists on the Execute box. Refine checks before writing the reconstruction.
2. What the first `lpath` element in `census.json` is (e.g. 521 / 553 / 650 / 681), so P53 can be reconstructed. Refine reads the D1 leaf-path layout used by `bg_producer_scan.py`.

## Phases

### Phase 1 — Committed census reproduces 5,969 / 128, then PE on live

- **Outcome:** committed generator + unit test against `dv_assign`. P53 reproduces 5,969 on `aeae426c` (if the disc is still on the box; otherwise stated) and 128 on `0c22b266`, by-edge splits equal. PE counts on live with full per-link records, inside and coincident-not-on-parent-edge counts restored. Double run identical. Peak in the 56 ledger.
- **Scratch cleared (part of the outcome):** keep generator + predicate unit test, `census_live.json` and the P53 reproduction record (committed); 56-ledger row. Phase 2 reads only these. The `aeae426c` disc is not this plan's and is not deleted. Delete `output/scratch-67/` contents: decoded L0 link dumps, per-parent shards, double-run copies once compared, wrapper logs once copied. Proof: the phase's `scratch_receipt` (see "Scratch hygiene").
- **Surfaces:** `triage/trim_r_parity/l0_degen/census/`; `parser/tests/` (predicate test); `docs/provenance.md`.
- **Approach:** known. **Depends on:** none. **Refine:** Open questions 1–2.

### Phase 2 — Every one of the 128 has a proven outcome

- **Outcome:** `rc_table.json` with all 128 links: hypothesis H0–H5 (or a named new one) accepted on per-link evidence (independent decode, spool vertices, `dv_assign` harness, halo membership), R parity, and outcome. Counts per outcome. Any link with no accepted hypothesis is named open with its evidence.
- **Scratch cleared (part of the outcome):** keep `rc_table.json` with every per-link evidence field inline, and the `dv_assign` harness (committed). Delete independent-decode dumps, spool vertex extracts, R decodes, halo-membership intermediates, temp dirs. Proof: the phase's `scratch_receipt` (see "Scratch hygiene").
- **Surfaces:** `l0_degen/census/`; `output/scratch-67/` (gitignored).
- **Approach:** open (which hypotheses hold is not known; the per-link evidence fields are the yardstick). **Depends on:** Phase 1. **Refine:** hypothesis definitions fixed before scoring.

### Phase 3 — Remedy landed or proofs recorded; residual updated

- **Outcome:** encoder / decoder defects fixed with tests and a Design-accepted successor oracle (confined diff vs `0c22b266`, PE census clean, R-DVD no-worse, Perth, K1, close gates); non-deviation proofs recorded per link. `residuals.tsv` R-G9-3-d-rem discharged only when all 128 have an outcome; otherwise the row stays open (not discharged) and names the exact open links and their hypotheses, without "optional". Plan 53 record and README pointers appended.
- **Scratch cleared (part of the outcome):** keep the fix + tests, `successor_oracle_<sha>.json`, the promoted disc at the disc-in-force path (outside scratch), `residuals.tsv`, README and plan 53 pointers, ledger row. Delete the whole `output/scratch-67/`: non-promoted candidate encodes, AU / Perth build trees, PE re-census intermediates, K1 dumps, any `keep/`. Proof: the phase's `scratch_receipt` (see "Scratch hygiene").
- **Surfaces:** `parser/kiwiw/_e2.c` and/or D1 + tests; `successor_oracle_<sha>.json`; OVERVIEW oracle line; `residuals.tsv`; `l0_degen/README.md`; `docs/plans/53-l0-degenerate-east-edge-roads.md` (append).
- **Approach:** known (per outcome). **Depends on:** Phase 2. **Refine:** only for an encoder / decoder fix.

## Provenance

- Tip GitHub `origin/master` **`4bb96f0`** (fetched 2026-10-08; drafted against `8498eec`, re-checked at `4bb96f0`). Sources: `triage/phase3_synthesis/residuals.tsv` lines 56–57; `docs/plans/53-l0-degenerate-east-edge-roads.md`; `trim_r_parity/l0_degen/{README.md, discriminate.json (ae672c30…), census.json (62e5e5d7…), census_after.json (86de7f67…), successor_oracle_0c22b266.json, cells_aeae426c_to_0c22b266.tsv}`; `parser/kiwiw/_e2.c` L461–481 (`dv_clamp`, `dv_assign`), L530–546 (`dv_leaf`, `dv_split`), L1081 (`dv_halo`); `parser/tools/bg_producer_scan.py` L384 (`leaf_clip_geometry`); plan 46 record L39 (RC4); plan 53 record L48 (soft note) and L62; plan 58 record (AU tree peaks).
- Sample-convention table (Ground item 5) computed by Design on the box from the committed JSON samples; not committed.
- Siblings: **66** (R-G9-3-b piece count).
- Rejected: discharging the 128 as a "residual class"; a blanket rule without per-link evidence; treating the nx=2 sample result as proof; "optional" or carried end states.
- Box draft only. No commit from Design.
