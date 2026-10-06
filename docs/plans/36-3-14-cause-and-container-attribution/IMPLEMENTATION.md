# Implementation — 36 3-14 cause and container attribution, AU 3-11 routed proof

- Tool: the orchestrator is the Execute background worker. Unit workers would
  be Codex `gpt-6.1-sol`, but Codex is weekly-limited until 2026-10-10
  11:50 AEST, so Execute does the units and discloses it here and in each
  report.
- DESIGN landed at `233d09e`. Oracle in force: `4e6b0de7…`, unchanged by
  this plan.
- Scratch: `output/scratch-36/`. New discs are written only under that
  directory.
- Protected discs and the spool are hashed before and after each heavy
  chain by the plan-34 `snapshot` gate.
- Every heavy step runs under `run_heavy_python.py` + `output/.heavy.lock`.
  Encode is at most `-j4` and K1 at most `-j6`.
- Refine is skipped for all phases (DESIGN).

## Phase 1 — Region tool, 3-11 replay, routed proof

### 3-11 predecessor replay (Execute, guarded)

- Throwaway detached worktree
  `/home/codyh/workspace/open-pajero-maps-36-pre311` at `b7c7c42`, the
  parent of 3-11 code `9269ebb`.
- Chain: `output/scratch-36/run_p1_replay.{sh,log}`.
- Command: the same recipe as the 3-11 G build
  (`output/scratch-3-11/G_build.log`:
  `build_alldata.py --spool output/extract_timing/spool --out … -j 12`),
  run at `-j 4`.
- Pin gate: `87a01b14…`, 1,731,021,568 B. A mismatch is recorded as
  `replay-mismatch` and never re-pinned.
- **Result: PASS.**
  - `output/scratch-36/G_pre311/ALLDATA.KWI` has sha256 `87a01b14…`, size
    1,731,021,568 B (`sha_pre311.json`).
  - Encode wall 26 s (12:15:43–12:16:09 AEST).
  - Protected snapshot before and after: equal.
  - No `replay-mismatch`.

### Region-accounting tool (Execute)
- **Tool:** `docs/plans/04-c-core-orchestration/triage/oracle_chain/region_accounting.py`
  (`account --old --new --old-sha --new-sha --out [--spans]`).
- **Partition.** Each file is split into these named regions:
  - the fixed data_volume / MHT sectors and the MHT inline (leaf 29);
  - every unique Map Frame;
  - frame payload, read from the two-byte extent marker ×2;
  - frame allocation padding;
  - PMR records and tails;
  - PDMDH records, BMT arrays, record tail and sector pad.

  The partition must be complete and disjoint: Σ = file size, with 0 gaps
  and 0 overlaps.
- **Comparison is by index path,** never by offset:
  - frames and PMR buffers are matched by structure key;
  - PMR leaf DSA/BS fields are masked;
  - PDMDH bytes are compared outside the BMT address fields.
- **Fail-closed checks.** It refuses an existing output, checks both shas
  first, uses bounded preads, and exits 2 on an incomplete partition,
  unaccounted bytes or a bad extent.
- **Tests:** `parser/tests/test_region_accounting.py`, 6 synthetic tests
  passed:
  - key round-trip;
  - partition gap/overlap detection;
  - identical discs fully accounted;
  - grown frame named as payload + padding (parametrised ×2);
  - sha mismatch refused.

  Output-reuse refusal is in code, not covered by a dedicated test.
- **Deviation (surfaces):** no `parser/perf_inventory.json` entry.
  - That inventory classifies only modules under `parser/`
    (`test_perf_inventory.py`), and it lists no triage tool, including the
    sibling `oracle_chain.py`.
  - The tool lives in the DESIGN-owned triage directory.

### 3-11 multiset diff, routed proof, region accounting (guarded)
- **Chains:** `output/scratch-36/run_p1_routed.{sh,log}` (12:19–12:26 AEST)
  and `run_p1_region.{sh,log}` (12:26–12:28 AEST).
  - Every step ran under `run_heavy_python.py` + lock, with a protected
    snapshot before and after; all equal.
  - The first routed attempt (`run_p1_routed.attempt1.log`) refused a
    pre-existing work dir. The re-run used a fresh path; no output was
    reused.
- **Multiset diff** `87a01b14 → 013586b5` (`diff-3-11-au.json`, 140 s):
  - 37 changed L0 cells, 0 added, 0 removed;
  - frames 3,954,156 each side;
  - the cell list (sha `f03ebaab…`) equals the retained
    `Gnew.diff_cells.txt` (`9f2b0e55…`).
- **Routed diff** (`routed-3-11-au.json`, 225 s):
  - `routed_only_count` 0, `baseline_cells_missing_from_routed` 0,
    `routed_changed_total` 37;
  - `multiset_list_complete_under_routing` true;
  - frame-length fallbacks 0/0.
  - **Plan 31 F1 is discharged.**
- **Region accounting** (`region-3-11-au.json`, 62 s, max RSS 2.0 GiB):
  - **Totals:**
    - `complete_and_accounted` true, partition complete on both sides
      (3,956,302 regions, 0 gaps, 0 overlaps);
    - **unaccounted 0**;
    - file +224 = frame payload **+164** + frame padding **+60**
      (21,570,746 → 21,570,806).
  - **Frames:**
    - 41 frames changed payload; 7 changed allocation; 2,763,363 relocated;
    - frame padding nonzero bytes 0/0;
    - alias pattern equal.
  - **Other regions:**
    - PMR: 0 content differences after masking; 1,548 buffers relocated;
    - PDMDH: 1,695 differing bytes, all in BMT address fields;
    - data_volume, MHT and inline 29 equal.
  - **The 41 padding spans** (`region-3-11-au.spans.tsv`) equal plan 07's
    table (`docs/design/g-new-nonpayload-accounting.md`) on every row:
    - same old/new offset, old/new bytes and delta, with the same index-path
      label;
    - 34 × (−4) + 7 × (+28) = +60.
  - **Payload basis:** plan 07 quotes the manifest payload metric
    (1,597,341,290 → 1,597,341,454). The tool sums unique frame extents
    (1,684,874,982 → 1,684,875,146). Both bases give the same delta, +164.
    The absolute figures differ by definition, not by an unaccounted byte.

### Publication and wording
- **`oracle_chain.py publish`** gains `--routed-3-11` / `--region-3-11`.
  It validates the committed witness copies:
  - pins and protected flags;
  - 0 routed-only / 0 missing;
  - baseline list equal to the retained 37;
  - shas of the sibling cell lists;
  - region: complete, 0 unaccounted, +164, the padding pair, and deltas
    `[-4]×34 + [28]×7`.

  It then sets the 3-11 row to `replay-routed-verified`, drops the two stale
  residuals (no pre-3-11 disc; +60 B unattributed) and adds `replay_3_11`.
- **Evidence copies** in `triage/oracle_chain/evidence/`:
  - `{routed,diff,region}-3-11-au.*`;
  - `sha_pre311.json`;
  - `protected_{before,after}_3-11.json`.
- **Republish:**
  - Before the change, the publish command (`--au-diff`/`--perth-diff`
    from `output/scratch-31`, `--census output/scratch-31/census-3-11.json`)
    reproduced the committed `oracle_chain.{tsv,json}` except for one field:
    the plan 29 record sha (`ca1278f8…` → `7fb15a4d…`), from plan 37's
    legitimate R4 pointer edit.
  - Republishing refreshes that field.
- **Tests:** `parser/tests/test_oracle_chain.py` adds the committed-witness
  accept test and 5 tamper rejects. Oracle-chain, region, pin-contract and
  successor tests: 64 passed.
- **Wording.** The "+60 B unattributed" / "3-11 routed unproven" text is
  replaced by citations to plan 07 and this reproduction in:
  - the oracle-chain contract § Carried follow-ups;
  - the plan 31 record follow-ups (plus a post-close note);
  - the OVERVIEW blocker bullet.

  `residuals.tsv` R-G1-4 and R-G10-1 are marked `discharged`, leaving 13
  `blocks-phase3` rows.
- **Provenance:** a `docs/provenance.md` § `output/scratch-36/` entry.

### Phase 1 review and remediation
Review: an independent Claude CLI clean-context seat (disclosed; Codex is
weekly-limited), on `0cb872e`. Full text: `REVIEW.md` § Phase 1.

- **Verdict: PASS_WITH_FOLLOWUPS.** All five Phase 1 outcomes were met.
  The reviewer re-checked the 41 plan-07 rows itself (41/41) and the 37-cell
  links.
- **F1 (medium): padding fail-closed.**
  - `region_accounting.py` now refuses (exit 2) when any of these is
    nonzero on either side:
    - frame padding;
    - PMR tail bytes;
    - frame padding of at least one logical sector (`frame_pad_oversize`).
  - All three pairs were re-run with the stricter tool (sha `183d0ee0…`):
    - chain `output/scratch-36/run_r2_region.{sh,log}`, 12:37–12:39 AEST,
      guarded;
    - protected snapshots before and after equal;
    - outputs in `output/scratch-36/r2/`.
  - All three are `complete_and_accounted`, with 0/0/0/0 for nonzero
    padding, nonzero tails, oversize and bad extents on both sides.
  - The spans files are byte-identical to the first runs.
  - The committed evidence is refreshed from `r2/`.
- **F2 (low): account-level tests added.**
  - A trailing 32-byte gap gives rc 2 and `gap_bytes` 32.
  - One nonzero padding byte gives rc 2.
  - An existing output is refused.
  - The relocation path is asserted when an allocation grows.
  - Region tests: 9 passed.
- **F3 (low): `replay_3_11` now checks the rows themselves.**
  - It compares the 41 spans row by row with the plan 07 ledger, parsed from
    `docs/design/g-new-nonpayload-accounting.md`, and with the committed
    spans TSV.
  - It reads `sha_pre311.json` and requires `87a01b14…`.
  - It sha-pins the spans TSV, the disc witness and the ledger in
    `supporting_evidence`.
  - New tamper tests: offset change and disc-witness change.
- **F4 (low): wording.**
  - Plan 31's Residual Risks line now names the 3-14 container scope only
    (+60 B: attributed by plan 07, reproduced here).
  - `phase3_synthesis/gates.tsv` G1/G10 carry post-close discharge notes.
- **F5 (low):**
  - The inline compare now iterates the union of inline indexes.
  - No pair has a trailing whole-file pad: every partition is complete, so
    no `trailing_pad` region was added.

## Phase 2 — 3-14 container/index/padding accounted

### Runs
- `output/scratch-36/run_p2_region.{sh,log}`, 12:32–12:33 AEST, with the
  first tool; then `run_r2_region` with the fail-closed tool.
- Both were guarded, with protected snapshots equal.
- PDMDH field classification: `hop_3_14/pdmdh_fields.py`, small preads,
  guarded (`runs/p2_pdmdh_fields.json`).
- `hop_3_14/container_summary.py` (no disc reads) validates each hop and
  writes `hop_3_14/container-{au,perth}.json`. It checks that:
  - every byte delta is named by region and unaccounted is 0;
  - payload delta = Σ per-cell frame deltas over plan 31's changed-cell list;
  - every PDMDH byte outside BMT address fields is a BMT size field of a
    size-changed PMR block;
  - PMR content changes and leaf-topology changes are confined to those
    blocks;
  - the PMR record delta is explained by those blocks.

### AU `013586b5 → 4ed9cd80` (file −38,916,640 B)
- **Partition:** complete both sides, unaccounted 0.
- **Named deltas:**
  - frame payload **−38,913,410**;
  - frame padding −3,198;
  - PMR records −12;
  - PMR tails −20;
  - every other region 0 (data volume, MHT, inline 29, all PDMDH
    sub-regions).
- **Payload vs cells:** Σ per-cell frame deltas over the 246,123 changed
  cells = −38,913,410 (**equal**).
- **Frames:**
  - 3,954,156 → 3,954,159; 247,961 payload changed; 230,608 allocations
    changed; 3,665,474 relocated;
  - alias pattern equal; nonzero padding / tail / oversize 0.
- **Leaf topology:** 12 only-old / 15 only-new frames.
  - `L0 23/16: 1285`, `L0 51/9: 988` and `L0 51/9: 1211` each go from 4
    children to 1 undivided leaf.
  - `L0 51/10: 768` gains children `/4…/15`.
- **PMR:** 3 buffers changed size and masked content, exactly `L0 23/16`,
  `L0 51/9` and `L0 51/10`:
  - record bytes 12,348→12,320, 13,612→13,556 and 12,616→12,688
    (Σ −12 = PMR record delta);
  - sectors 386→385, 426→424 and 395→397.
- **PDMDH:** 5,946 differing bytes.
  - 5,943 are in BMT address fields.
  - 3 are in BMT size fields, the low byte (entry offset 5) of those three
    blocks' entries.

### Perth `da13a775 → 04be2f6e` (file −160,992 B)
- **Partition:** complete, unaccounted 0.
- **Named deltas:**
  - frame payload **−161,380**;
  - frame padding +388;
  - PMR records +16;
  - PMR tails −16;
  - others 0.
- **Payload vs cells:** Σ per-cell deltas over the 795 changed cells =
  −161,380 (**equal**).
- **Frames:** 1,943 → 1,949. Topology: 8 only-old / 14 only-new (the same
  51/9 merges and 51/10:768 split as AU).
- **PMR:** 2 blocks (`L0 51/9`, `L0 51/10`).
- **PDMDH:** 20 differing bytes; 18 address bytes and 2 BMT size bytes of
  those blocks.

### Publication
- **`oracle_chain.py publish --container-3-14-au/--container-3-14-perth`**
  validates each summary:
  - `pass` true, with the hop pins;
  - unaccounted 0;
  - payload equals the cell sum;
  - changed-cell count equals the row's count.

  It drops the 3-14 residual "Container/index/padding relocation is outside
  this cell-identity measurement" and adds `container_account`.
- **Remaining 3-14 residual:** payload causes (Phase 3).
- **Committed:**
  - `hop_3_14/{container_summary.py, pdmdh_fields.py, pdmdh-fields-3-14.json,
    container-au.json, container-perth.json, region-3-14-perth.spans.tsv}`.
  - Not committed: the full AU region JSON (57 MB) and spans TSV (14.5 MB).
    They stay in `output/scratch-36/r2/`, sha-pinned in
    `container-au.json` → `inputs`.
- **Tests:** container_account accept (AU, Perth) and 4 tamper rejects;
  container_summary synthetic pass and payload-mismatch fail. Oracle /
  region / pin / successor tests: 77 passed.

### Phase 2 review and remediation
Review: an independent Claude CLI clean-context seat, on `b10e787`. Full
text: `REVIEW.md` § Phase 2.

- **Verdict: PASS_WITH_FOLLOWUPS.** All three Phase 2 outcomes were met.
  - The reviewer re-ran `container_summary.py` and got byte-identical
    summaries.
  - It recomputed the region-delta sums, the per-cell payload sums
    (−38,913,410 / −161,380), the BMT size-field bytes and the PMR record
    and tail deltas.
  - It judged the padding and tail naming honest under the F1 zero and
    oversize gates.
- **F1:** `container_account` now appends the summary to the row's
  `supporting_evidence`, so the TSV cites `hop_3_14/container-{au,perth}.json`
  with its sha.
- **F2:** "3-14 container unmeasured" is replaced in four places:
  - the oracle-chain contract;
  - plan 31's Residual Risks (as a post-close note);
  - OVERVIEW;
  - the `gates.tsv` G1 note.

  `residuals.tsv` R-G1-3 is `discharged`, leaving 12 `blocks-phase3` rows.
- **F3:** each outside-address PDMDH byte must have:
  - entry length 6;
  - field offset below the entry length;
  - old and new byte values equal to the corresponding byte of
    `size_sectors`.

  `pdmdh_fields.py` was not re-run: the lock is held by the Phase 3 encode,
  and its output for these in-range offsets is unchanged. The summary now
  enforces the bounds independently.
- **F4 (partly):**
  - Done:
    - the summary reconciles `pmr_tails.delta` with the size-changed blocks
      and requires each of their tails to be below one sector;
    - it requires `tool_sha256` to equal the committed
      `region_accounting.py`;
    - it records `frame_pad_oversize`.
  - Not done: a whole-disc `pmr_tail_oversize` in `region_accounting.py`.
    - Unchanged blocks have identical buffers on both sides (masked hash
      equal) with zero tails, so this would be a writer-wide property, not
      a hop delta.
    - Disclosed as a follow-up, so the region runs did not need re-running.
- **F5:** `container_account` requires the summary's cell-list sha to equal
  the row's `authoritative_list` sha. A tamper test is added.
- **Tests:** a synthetic wrong-size-byte reject is added. Oracle / region /
  pin / successor tests: 79 passed.

## Phase 3 — 3-14 per-cell payload causes attributed

### Runs (all guarded: run_heavy_python + output/.heavy.lock, one at a time)
- `output/scratch-36/run_p3_endpoints.{sh,log}` (12:41–12:43 AEST): AU and
  Perth rebuilds from worktrees at `33006aa` (parent of `d35b565`) and at
  `d35b565`, with the pinned spool, `-j 4`.
- `run_p3_mech.{sh,log}` (12:43–12:57): mechanism-isolated builds plus
  `oracle_chain.py diff` of each against both endpoints.
- `run_p3_sections.{sh,log}` (12:57–13:01), `run_p3_detail.{sh,log}`
  (13:02–13:25), `run_p3_k1perth.{sh,log}` (12:54–12:57),
  `run_p3_k1au.{sh,log}` (13:01–13:25).
- Protected snapshots before/after equal for the endpoint, mech, sections and
  AU K1 chains (`protected_{before,after}_p3*.json`). The Perth K1 chain and
  the detail chain are read-only and took no snapshot.

### Outcome 1: endpoint control
- `33006aa` rebuild: AU `013586b5…`, Perth `da13a775…`.
- `d35b565` rebuild: AU `4ed9cd80…`, Perth `04be2f6e…`.
- All four reproduce byte-exact (`sha_E_{pre314,at314}{,_perth}.json`), so
  the code diff is the only input change. Of `d35b565`'s files only
  `parser/kiwiw/_cenc.c` reaches the build (the rest are docs and tests).

### Mechanism isolation (beyond the design: a whole-disc counterfactual)
- `d35b565`'s `_cenc.c` diff split into `hop_3_14/eo_only.patch` (hunks 1–4:
  `float.h`, the `eo_*` helpers, `chains()` moved, the `eo_clip` call in
  `bg_shape`) and `hop_3_14/chord_only.patch` (hunk 5: `best<0 || used` →
  `return -1`). Applied together to `33006aa` they give `d35b565`'s `_cenc.c`
  byte-exact.
- **EO-only build (`33006aa` + hunks 1–4) = `4ed9cd80` (AU) and `04be2f6e`
  (Perth), byte-identical to the 3-14 discs.** Its cell diff against old is
  exactly plan 31's list (246,123 / 795, sorted lists equal); against new, 0.
- Chord-only build: AU `40c1b07d…` (2,064,949,952 B; 77,071 cells changed
  vs old, leaves 3,954,156 → 5,003,334), Perth `a681efca…` (295 cells). With
  EO present the chord hunk contributes **0 bytes**.
- So every 3-14 byte is caused by the EO hunks. Facts in `hop_3_14/mech.json`
  (shas, patch shas, the eight diff summaries, sha-pinned in output).

### Outcomes 2, 3, 5: per-cell classes
- **Tools (read-only, committed):**
  - `hop_3_14/sections.py`: for each changed cell, splits every old and new
    frame (routed footprints) by its Main Map Data Frame Entry table into
    header / regions / ext table / road / background / name / ext / rest, and
    compares per section. Entry 0–2 offsets and sizes are excluded (they move
    whenever an earlier section changes length).
  - `hop_3_14/detail.py`: per-leaf section sizes, hashes and raw entry tables
    for every cell that is not background-only (82 AU, 3 Perth;
    `detail-{au,perth}.json`).
  - `hop_3_14/cells_causes.py` (no disc reads): evaluates all four byte
    predicates for every cell. They are disjoint by section pattern (each
    needs a different `(footprints_equal, sections_changed)` pair), and the
    tool refuses a cell where two hold. A cell with none is `unattributed`.
- **Section patterns:** AU 246,041 background-only, 75 `table+background`,
  4 topology, 3 `background+name`. Perth 792 background-only and 3 topology.
- **Classes** (predicates verbatim in `summary-{au,perth}.json` →
  `predicates`):

  | class | predicate (short) | AU | Perth |
  |---|---|---:|---:|
  | `eo_bg_stitch` | footprints equal; only background sub-frame bytes differ | 246,041 | 792 |
  | `eo_bg_stitch_ext_relocation` | as above, plus every ext entry keeps presence and size and moves by exactly that leaf's background size delta; ext bytes equal | 75 (L6 74, L8 1) | 0 |
  | `eo_frame_ceiling_name` | only background and name differ; in each name-changed leaf both frames are within 64 B of 131,070, name moves opposite to background, and the larger-name side would exceed 131,070 with the other side's background | 3 | 0 |
  | `eo_division_ceiling` | one quadtree step (leaf count ×4); coarser side's largest frame within \|Δ background\| of 131,070; coarser side has fewer background bytes | 4 | 3 |
  | `unattributed` | — | **0** | **0** |

- **The 7 AU / 3 Perth non-payload-only cells (outcome 3):**
  - `eo_division_ceiling`: L0 (827,869), (828,862), (1797,424) coarsen
    4 → 1 as background shrinks (new single frames 130,696 / 130,820 /
    131,022 B). (832,856) refines 4 → 16 as background grows (old coarse
    frame 131,052 B). Perth has the same three cells (827,869), (828,862) and
    (832,856). The counts (AU 3 merges + 1 split) match plan 36 P2's
    leaf-topology account (`L0 23/16` / `51/9` merges, `51/10:768` split);
    the cell-to-block mapping was not separately checked.
  - `eo_frame_ceiling_name`: L0 (1739,569), (1892,711), (1974,820). Frames
    within 64 B of the ceiling. Name bytes trade against background bytes.
- **Files:** `hop_3_14/cells_causes-{au,perth}.tsv.gz` (one row per changed
  cell: class, footprints_equal, section pattern, leaves, and whether the
  chord-only build also changes the cell). Gzip, because the AU TSV is
  246,123 rows (715 KB gz). The summary pins both the gz sha and the raw TSV
  sha.
- **Not claimed:** the classes are byte predicates on the hop's own frames
  plus the whole-disc EO counterfactual. The `eo_division_ceiling` and
  `eo_frame_ceiling_name` predicates use measured lengths. They do not
  re-run the encoder's division or name-trim decision per cell. The
  division predicate compares background sums across different topologies
  (the finer side carries per-leaf duplication), so it bounds plausibility
  and does not show the coarse frame crossed the ceiling. For those 7 cells
  the causal link is the whole-disc EO-only counterfactual. A per-cell
  encoder probe of the coarse-frame size under `33006aa` vs EO would be the
  stronger proof (follow-up, not run). DVD (R)
  parity of the changed cells is not asserted (design non-goal).

### Outcome 4: per-kind K1 `checked` confinement
- **Tool:** `hop_3_14/k1_rows.py run` drives the unmodified K1 C checker
  (`quantisation_roundtrip` internals, `cenc.k1_check_band`) with every band
  exactly one cell row of one block (AU 127,549 bands, Perth 235), writing
  per-band per-kind `checked`. `compare` reports the whole delta, the delta
  inside bands holding a changed cell of that block, and every band with a
  delta and no changed cell.
- **Partition check:** band totals equal the recorded whole-disc K1 reports.
  AU old = `scratch-14/p3/indep/rem01/k1_311.json` (013586b5) and new =
  `k1_live.json` (4ed9cd80), every kind. Perth equals fresh whole runs.
- **AU result:** whole Δ = range −24,243,765, step −25,202,484, road_node
  −790, name_anchor −927, background +1,215,204, background_boundary
  −25,457,252, interior_cover −1,479, completeness 0, road_point 0. These are
  exactly R-G4-2's numbers.
  - 29,790 bands carry a delta, all among the 29,824 bands holding a changed
    cell.
  - Delta in changed-cell bands = whole delta. **Confined: true**
    (`hop_3_14/k1-confine-au.json`).
- **Perth:** 107/107 bands, confined (`k1-confine-perth.json`).
- **Granularity:** the empirical check is row-band level. K1 bands are cell
  rows (`k1_check_band` has no column filter), and the checker was not
  modified. Cell-level confinement follows from the checker's code:
  - the point kinds and the background, boundary and cover kinds count per
    decoded leaf vertex, against spool-only context;
  - completeness requirements are keyed by cell over spool shapes and the
    cell's own leaves.

  So a cell whose frames and footprints are byte-identical contributes
  identical `checked` counts. That argument reads `_k1.c`, `_k1_bg.c` and
  `_k1_cmp.c` at HEAD; it is not a cell-filtered run.

### Publication
- `oracle_chain.py publish --causes-3-14-au/--causes-3-14-perth` validates
  each `summary-*.json`:
  - kind and hop pins;
  - cells equal to the row's count;
  - class sum equal to cells;
  - cell-list sha equal to `authoritative_list`;
  - unattributed list length equal to its count;
  - EO-only build equal to the new disc.

  It removes "Payload causes not measured", sets `unexplained_count` 0 and
  status `measured-identities-causes-attributed`, and adds `cause_classes`
  and the summary to `supporting_evidence`.
- Before the change the publish command reproduced the committed
  `oracle_chain.{tsv,json}` byte-exact (`output/scratch-36/pubcheck3`).
- Both 3-14 rows now carry **no residuals**.
- **Tests:** `test_hop_3_14_causes.py` (7 tests: section split, the three
  detail predicates, k1_rows compare confined / not confined / layout
  change); `test_oracle_chain.py` causes accept (AU, Perth), 7 tamper
  rejects, and committed gz ↔ summary. Oracle / region / pin / successor /
  hop tests: 96 passed.

### Phase 3 review and remediation
Review: an independent Claude CLI clean-context seat (disclosed; Codex is
weekly-limited), on `af0178b`, 13:28–13:32 AEST. Full text: `REVIEW.md`
§ Phase 3.

- **Verdict: PASS_WITH_FOLLOWUPS.** All five outcomes were met (outcome 4 at
  row-band level, cell level by code argument, judged sound for `checked`).
  - The reviewer recomposed the patches (`_cenc.c` sha `5c43e00d…` equals
    `d35b565`).
  - It matched the mech shas to the run logs and recounted the classes from
    the sections TSVs and detail JSONs.
  - It recomputed the K1 compare from the band TSVs, and re-checked the
    predicate margins (name trades 131,146 / 131,960 / 131,264 B; merge
    headroom 374 / 250 / 48 B).
- **F1:** `residuals.tsv` R-G1-1, R-G1-2 and R-G4-2 are marked discharged.
  The `gates.tsv` G1 and G4 notes and the OVERVIEW blocker bullet are
  updated. Plan 04 Phase 3 is not claimed.
- **F2:** `docs/provenance.md` § `output/scratch-36/` gains the Phase 3
  entries: discs, shas, `p3/`, run logs, snapshots and worktrees.
- **F3:** the `eo_division_ceiling` predicate text (summary `predicates`)
  and "Not claimed" now carry the caveat.
- **F4:** `cells_causes.py` evaluates every predicate for every cell. A
  non-background cell without a detail record is refused. The wording is
  now "disjoint by section pattern".
- **F5:** 78 → 82 detail cells.
- **F6:** `mech.json` → `code.worktree_cenc_sha256` (EO `dba9f5e6…`, chord
  `40afa697…`) joins the runs to the committed patches.
- **F7:** `causes_account` also checks:
  - the committed `cells_causes-*.tsv.gz` sha against the summary (and cites
    the gz in `supporting_evidence`);
  - `classes_by_level` sums against the row's `counts_by_level`.

  New tamper tests: levels, gz.
- **F8:** info, no action.
- Summaries regenerated (counts unchanged), `oracle_chain.{tsv,json}`
  republished. Oracle / region / pin / successor / hop tests: 98 passed.
