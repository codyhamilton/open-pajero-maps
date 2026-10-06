# Implementation — 30 2-01 source-data parity

- Tool: orchestrator is the Execute background worker. Unit workers are Codex `gpt-6.1-sol` (reasoning high) via `codex exec -s workspace-write`, one seat at a time. Sandboxed workers leave changes in the tree; Execute runs heavy steps under `parser/tools/run_heavy_python.py` (takes `output/.heavy.lock`) and commits. If Codex is usage-limited, Execute does the unit itself and says so here.
- Session: queued after plan 29 (Cody's approval, 2026-10-06 06:33 AEST). DESIGN landed at `3447b39`.
- Worktree: `/home/codyh/workspace/open-pajero-maps-14-completeness` (detached; fast-forward pushes to `master`).
- Scratch: `output/scratch-30/` (run logs in `output/scratch-30/runs/`).
- Disc in force: successor `2ee3456a…`. Historical control `4ed9cd80…`. R pin `8c2d2027…`. Plan 29 R1 remediation runs in parallel and does not touch this plan's 2-01 cells.
- Protected, byte-untouched: `output/scratch-14/G_new`, `output/scratch-3-11/G_new`, `output/scratch-29/G_new`, `output/extract_timing/spool`, and the R disc (read-only mount).

## Phase 1 — Every 2-01 row is fingerprinted; type census and 288-template identity are proven

Refine skipped (DESIGN). One unit: `briefs/1-01-fingerprint-census.md`.

### 1-01 — fingerprint, census and template proof

- **Worker:** Codex `gpt-6.1-sol` (high), sandboxed, 06:36–06:47 AEST, 94,451 tokens. Report: `reports/1-01-fingerprint-census.md`.
- **Built:** `fingerprint.py` (subcommands `census`, `--disc` probe, `merge`), `fingerprint.tsv` (342 rows), `fingerprint_summary.json` (sha256 for all 688 inputs), `phase1_note.md`, and `parser/tests/test_parity_fingerprint.py` (synthetic, 22 passed).
- **Runs (Execute, guarded, `output/scratch-30/run_p1.{sh,log}`):** successor and historical disc probes exit 0, each with its full pin verified. Both give demanded-type total 0. The historical control equals the membership TSV. Merge exit 0.
- **Execute append-only wording corrections** (census 341 × 288 + 1 × 321): plan-14 record follow-up, `phase3_groups.md`, `per_rule_phase2_reconciliation.md`. OVERVIEW wording is deferred to Phase 2's narrowing.

### Phase 1 verification (Execute, cheap tier)

1. `fingerprint.tsv` covers 342 rows. It joins to the members TSV, `phase3_membership.tsv` and the plan-28 join (O01 340, O05 2: rows 246 and 567).
2. Census: **341 × 288 + 1 × 321 (dump_row 246, L0 (834,886))**.
3. 288 template: **341/341** have one cell-local 13-vertex polygon, branch c, span 1/12° × 1/8° (5′ × 7.5′, tolerance 1e-9°). Two signatures: **T1 191** (north-west start) and **T2 150** (south-west start). Exceptions: 0. Correction to DESIGN Ground: both have the *same* counter-clockwise winding and differ only in start corner.
4. Bands (bbox midpoint, descriptive): west 85, east 86, south_offshore 129, other 42.
5. G demanded-type count is 0 on successor `2ee3456a…` and on historical `4ed9cd80…`, for all 342 rows.
6. Heavy steps ran through `run_heavy_python.py` (lock), with logs in `output/scratch-30/runs/`.
7. R provenance: the retained scratch-14 decoded-coordinate proofs, sha-pinned. There was no fresh R-disc read; DESIGN Contract 6 prefers light reuse.

`artifact_feedback` was not called (workflow-service calls excluded).

**Phase 1 outcome verified.**

## Phase 2 — Every 2-01 row has a supply-path or unfixable-proven disposition

The approach is open: discriminator candidates are scored against the fixed outcome, and the comparison is recorded in `phase2_candidates.md` and the plan record. Refine skipped. One unit: `briefs/2-01-disposition.md`. Execute owns the OVERVIEW narrowing.

### 2-01 — supply-path / unfixable-proven disposition

- **Worker:** Codex `gpt-6.1-sol` (high), sandboxed, 06:50–07:12 AEST, 181,898 tokens. Report: `reports/2-01-disposition.md`. Candidate comparison: `phase2_candidates.md` (chosen: spool + PBF + lattice, 4.55/5).
- **Built:** `disposition.py` (`inventory`, `spool`, `pbf`, `publish`), `disposition.tsv` (342 rows), `disposition_summary.json`, `phase2_note.md`, and `parser/tests/test_parity_disposition.py` (synthetic, 36 passed; Execute re-ran it, 36 passed).
- **Runs (Execute, guarded, `output/scratch-30/run_p2.{sh,log}`):** inventory, spool (283.7 s, 575 MB peak), PBF (2,382.5 s, 6.05 GB cgroup peak including page cache, max RSS 258 MiB), and publish. All exit 0.
- **Result:** **243 supply-path / 0 unfixable-proven / 99 conflict-open.** Every supply witness is an OSM boundary relation (`type=boundary`; marine parks and habitat zones) that the spool lacks as an emitting demanded-code source. The 99 open rows (98 type-288, mostly south_offshore, plus row 246) carry PBF coverage gaps in their windows and list the discriminators tried. Details are in `phase2_note.md` § Execute measured result.

### Phase 2 verification (Execute, cheap tier)

1. `disposition.tsv` has 342 rows and joins exactly to the Phase 1 native keys and dump rows; publish validated the pins, hashes, wrapper logs and proof-event SHA256s.
2. Counts: **243 supply-path / 0 unfixable-proven / 99 conflict-open**. Type-288 is split (243 supply / 98 open); row 246 (type 321) is open.
3. DESIGN Outcome 6 holds: each of the 99 open rows carries `discriminators_tried` (lattice identity, retained demander, spool result, PBF result with gap counts).
4. No R geometry was copied; no disc, encoder, vocabulary or extractor change. The supply rows are successor-implement candidates, not fixes.
5. OVERVIEW: the carried source-data parity wording is narrowed to these counts with the TSV link (WP1 paragraph and the "What remains unfinished?" row). The seven O04 rows and the plan 04 Phase 3 blockers stay listed.
6. Heavy steps were serialised under the lock; the PBF peak (6.05 GB cgroup, 258 MiB RSS) stayed inside plan-25 guards.

`artifact_feedback` was not called (workflow-service calls excluded).

**Phase 2 outcome verified** (with 99 named conflict-open rows, as DESIGN Outcome 6 permits).

### Phase 2 reopened (Execute, 2026-10-06 08:20 AEST)

The Phase 2 close at `10ac108` is **superseded**. DESIGN's Phase 2 outcome is every row `supply-path` or `unfixable-proven`; 99 conflict-open does not meet it, although Outcome 6 allows named opens and the review passed. Execute's scan of the retained PBF evidence shows the 99 are open only because of PBF relation gaps, and most gaps come from the probe treating node and `subarea` members as missing geometry. Unit `briefs/2-02-pbf-relation-gaps.md` corrects that and resolves or names each remaining row. A partial close-out seat for this plan was stopped and its uncommitted moves were reverted.

### 2-02 — PBF relation-gap correction (code)

- **Worker:** a Codex `gpt-6.1-sol` (high) seat started this unit. It stopped
  at the Codex usage limit (~08:23 AEST; the next window opens at 11:19
  AEST). Execute (Grok Bot) finished it and discloses that here.
- **Changes in `disposition.py`:**
  - `area_members`: only area-role ways form rings. Node members
    (admin_centre, label) and `subarea` relation members are ignored instead
    of being reported as missing geometry.
  - Read-only cache replay commands: `pbf-cache`, `cache-pin` (hashes the
    PBF and reads its header) and `reuse` (refreshes the spool evidence
    against the legacy script `e54ea773…`).
  - Relations the legacy cache never stored with their member list
    (relation-member-limit) are named as
    `relation-not-retained-member-limit` gaps.
  - The remaining unresolved relations are listed in a `.requests.json`
    beside the PBF output.
  - CLI dispatch maps `-` to `_`. An unused, undefined complete-relation hook
    was removed.
- **Tests:** `parser/tests/test_parity_disposition.py`:
  - the expected gap name is now "missing relation member way";
  - adds an assertion that admin_centre members are ignored;
  - adds 3 new tests.
- **Measurement:** `output/scratch-30/run_p2b.sh` (log `run_p2b.log`) runs
  `reuse` → `cache-pin` → `pbf-cache` → `publish`, serially under the wrapper
  and lock. It is waiting for the shared heavy lock, which another project
  holds.

### 2-02 — measurement (Execute, guarded)

**Run chains.**

- `output/scratch-30/run_p2b.{sh,log}`: `reuse`, `cache-pin` (PBF
  `australia-260824.osm.pbf`, replication timestamp
  2026-08-24T20:20:50Z = 2026-08-25 06:20 AEST) and `pbf-cache` (102 s,
  RSS 165 MiB) all exited 0.
- The first `publish` failed closed with "stale probe input hash". The
  committed inventory probe was written by the legacy script `e54ea773…`,
  and `publish` reads the inventory non-historically.
- `output/scratch-30/run_p2c.{sh,log}` re-ran `inventory` with the current
  script (`disposition_inventory_r2.json`), then `publish`. Both exited 0.
- Every step ran under `run_heavy_python.py` and the lock. No disc,
  encoder, vocabulary or extractor was touched.

**Result: 338 supply-path / 0 unfixable-proven / 4 conflict-open**, up from
243 / 0 / 99.

- **95 rows flipped to supply-path.** All 95 are supplied by OSM relation
  8426743 (South-west Corner Marine Park, `type=boundary`, 45 members).
  That relation now assembles because node and `subarea` members are no
  longer treated as missing ring geometry. Each flipped row has a positive
  boundary-clipped production-C witness (1 record) in
  `output/scratch-30/disposition_pbf_r2.proofs.jsonl`.
- **No row moved the other way.**
- **Supply sources across all 338 rows** (OSM relation id, name, rows):
  - 8426743 South-west Corner Marine Park: 173
  - 8601872 Coral Sea Habitat Protection Zone: 94
  - 8426822 Gascoyne Marine Park: 30
  - 8602593 Abrolhos Marine Park: 24
  - 8426745 Eastern Recherche Marine Park: 11
  - 8602093 (unnamed): 3
  - 8602037 Central Eastern Marine Park: 1
  - 80500 Australia: 1
  - 8390145 Mermaid Reef Marine Park: 1

**The 4 conflict-open rows (exact account).**

| dump_row | cell (L0 ix, iy) | demanded code | stratum | In-cell PBF evidence |
|---:|---|---:|---|---|
| 246 | (834, 886) | 321 | 321-outlier | 284 candidates of code 321, but no 321 emitter (288 ×10 and 291 ×1 emit) |
| 396 | (2049, 1224) | 288 | 288-template T1 (−24.50..−24.42, 154.0..154.125) | 11 candidates of code 288, no emitter |
| 397 | (2050, 1224) | 288 | 288-template T1, same 4×4 grid | 10 candidates of code 288, no emitter |
| 775 | (1363, 1958) | 288 | 288-template T2 (−9.25..−9.17, 132.5..132.625) | 1 candidate of code 288, no emitter |

**Why these 4 are still open.** None has a positive supply witness, so the
PBF gaps decide the row:

- 39 relation gaps are common to all four rows (47 in the union), in five
  classes;
- the requested relation list is `relation_requests.json`: 61 ids at the
  PBF replication timestamp.

The five gap classes:

1. **Missing relation member ways (29 relations).** These ways are absent
   from the Australian extract itself. Examples: the Australia EEZ
   2647638, 2647601 (924 missing ways), 2202162 (1,746 missing ways),
   19269186 and 19269193 (459 and 531), the Coral Sea, Arafura and Oceanic
   Shoals marine parks, and several timezone and maritime relations. No
   in-PBF work can bound them. Their geometry needs a complete-relation
   source.
2. **Native-C vertex limit (5 common, 7 row-specific).** Examples are 80500
   Australia, 2316598, 7493850, 8043873 and 8653540. These relations exceed
   the probe's vertex cap.
3. **Nested area relations (3).** These are 12026353, 18183905 and
   18194886.
4. **Relation with no outer ring (1).** This is 19342817.
5. **Relations not retained because of the member limit (5).** These are
   4095122, 15480206, 16308779, 16308787 and 16308826; the legacy cache
   never stored their member list.

Row 396 also has one crossing/touching boundary gap (16623818).

**What would resolve them.** Each open row needs either a positive supply
witness or proof that no gap relation reaches its cell. Class 1 alone
blocks all four rows, and its data is not in the pinned PBF. So
0 conflict-open needs one of two Design-level choices:

- **(a)** Admit a pinned complete-relation snapshot for the 61 ids in
  `relation_requests.json` at 2026-08-24T20:20:50Z (for example, an
  Overpass attic query recorded with its own hash) as a second source pin,
  then re-run `pbf-cache` with it. Classes 2–5 are then also resolvable,
  with full geometry and a raised, topology-validated cap.
- **(b)** Rule the four rows `unfixable-proven` on the grounds that their
  supply evidence lies outside the pinned source. The current design does
  not authorise this.

Execute did **not** fetch external data. Phase 2's outcome (0
conflict-open) is **not met**, so plan 30 stays open and is not closed out.
The DESIGN does not authorise another source.

Per-row gap lists for Design (relation ids by class, row-specific gaps): `open_rows_account.md`.
